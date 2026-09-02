#!/usr/bin/env python3
"""Measure low sun's RENDERED OUTCOME on the lap route, as a function of sun azimuth.

    python3 scripts/calibrate_low_sun_azimuth.py --azimuth 315
    python3 scripts/calibrate_low_sun_azimuth.py --condition clear      # the reference

One lap per invocation, driven by pure pursuit -- the same path the training data was
collected through, so the numbers are directly comparable to it. Writes one JSON per
config; scripts/report_low_sun_calibration.py assembles them.

WHY THIS EXISTS. T06-F20 chose Town06's 5 degrees by matching a rendered outcome on the
SIX-SECTION route, and T06-F41 measured that the lap route renders 37.8% darker under low
sun, putting low sun/clear at 0.300 against the 0.410 target. Sun AZIMUTH was never chosen
at all: it has always been 0.0, inherited from CLEAR_BASELINE, which is the worst band the
lap has -- the sun sits in the camera's FOV for 44.0% of the route including one unbroken
1,008 m stretch, against Town04's 28.2%/24.7%.

The condition is declared by its rendered outcome (T06-F20), so the azimuth is chosen by
measuring, not by picking a number off the geometry.
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "pipeline"))

import carla  # noqa: E402
import carla_determinism as cd  # noqa: E402
import carla_env as env  # noqa: E402
import config as C  # noqa: E402
from imaging import preprocess_for_model  # noqa: E402
from route import load_route, pure_pursuit_route, signed_cte_route  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", default="low_sun")
    ap.add_argument("--azimuth", type=float, default=None,
                    help="sun azimuth for this run; omit to use the preset's own")
    ap.add_argument("--every", type=int, default=2, help="sample every Nth step")
    ap.add_argument("--out-dir", default="results/town06/low_sun_calibration")
    args = ap.parse_args()

    if args.azimuth is not None:
        os.environ["SUN_AZIMUTH_OVERRIDE"] = str(args.azimuth)

    client = cd.bind_client(carla.Client("127.0.0.1", C.PORT))
    client.set_timeout(120.0)
    world = env.load_study_map(client)
    original = world.get_settings()
    env.enable_sync_mode(world)          # carries require_deterministic()

    route = load_route(C.SECTIONS[0])
    vehicle = camera = None
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWNS[C.SECTIONS[0]])
        camera, q = env.set_condition(world, vehicle, args.condition)
        speed = env.SpeedController()
        env.warmup_to_speed(world, vehicle, q, speed,
                            steer_fn=lambda v: pure_pursuit_route(route, v.get_transform())[0])

        w = env.weather_params(args.condition)
        sun_az = float(w.sun_azimuth_angle) % 360.0
        fov = float(getattr(env, "CAM_FOV", 90.0))

        means, blown, in_fov, hint = [], [], [], None
        n_route = len(route)
        for step in range(C.steps_for(C.SECTIONS[0]) + 20):
            env.update_spectator(world, vehicle)
            frame = world.tick()
            image = env.grab_frame(q, frame)
            tf = vehicle.get_transform()
            loc = tf.location
            _, hint = signed_cte_route(route, loc.x, loc.y, hint)
            steer, _, _ = pure_pursuit_route(route, tf, hint)

            if step % args.every == 0:
                a = np.asarray(preprocess_for_model(env.raw_to_bgr(image)), dtype=np.float32)
                if a.max() > 1.5:
                    a = a / 255.0
                means.append(float(a.mean()))
                blown.append(float((a > 0.95).mean()))
                # is the sun inside the camera's horizontal FOV from here?
                off = abs(((tf.rotation.yaw - sun_az + 180.0) % 360.0) - 180.0)
                in_fov.append(bool(off <= fov / 2.0))

            thr, brk = speed.control(vehicle)
            env.apply_control(vehicle, carla.VehicleControl(throttle=thr, brake=brk,
                                                            steer=steer))
            if hint is not None and hint >= n_route - 2:
                break

        m = np.array(means)
        out = dict(
            condition=args.condition,
            sun_azimuth=sun_az,
            sun_altitude=float(w.sun_altitude_angle),
            exposure=C.exposure_for(args.condition),
            mean=float(m.mean()), std=float(m.std()),
            p05=float(np.percentile(m, 5)), p95=float(np.percentile(m, 95)),
            blown_frac=float(np.mean(blown)),
            sun_in_fov_frac=float(np.mean(in_fov)),
            samples=int(len(m)),
            determinism=dict(deterministic_control=bool(C.DETERMINISTIC_CONTROL),
                             rules_digest=cd.digest(), lock_problems=cd.check_lock(),
                             server_cmdline=cd.server_cmdline(C.PORT)),
        )
        d = os.path.join(REPO, args.out_dir)
        os.makedirs(d, exist_ok=True)
        tag = args.condition if args.azimuth is None else f"{args.condition}_az{int(sun_az):03d}"
        with open(os.path.join(d, f"{tag}.json"), "w") as fh:
            json.dump(out, fh, indent=2)
        print(f"  {tag}: mean {out['mean']:.4f} +/- {out['std']:.4f}  "
              f"blown {out['blown_frac']:.4f}  sun-in-FOV {100*out['sun_in_fov_frac']:.1f}%  "
              f"n={out['samples']}")
        return 0
    finally:
        try:
            if camera:
                camera.destroy()
            if vehicle:
                vehicle.destroy()
        except Exception:
            pass
        world.apply_settings(original)


if __name__ == "__main__":
    sys.exit(main())

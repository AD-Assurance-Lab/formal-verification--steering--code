#!/usr/bin/env python3
"""Drive ONE lap in ONE condition and record what that condition actually RENDERS.

    STUDY_MAP=Town06 python3 scripts/measure_lap_condition.py --condition night

One lap per invocation, pure pursuit, the same path the training data is collected
through, so the numbers are directly comparable to it and to each other. A clean server
before each (A-4). Writes one JSON per condition; report_lap_conditions.py assembles them.

WHY THIS EXISTS, AND WHY IT IS ONE INSTRUMENT.

T06-F20 fixed the rule: A CONDITION IS DECLARED BY ITS RENDERED OUTCOME, not by its sun
angle or its shutter. Enforcing that rule needs a number, and this repo accumulated three
separate tables of "Town06 lap brightness" -- 0.1371 / 0.2054 / 0.2525 for the same clear
lap -- because each was computed from whatever frames happened to be on disk. Dataset
frame means are not a measurement of a route: a DAgger set is a sample of the poses that
policy visited, so comparing two of them measures the two policies as much as the two
routes. T06-F41 drew "the lap renders 37.8% darker under low sun" from exactly such a
comparison, and driving it with one instrument does not reproduce it (0.414 against the
0.410 target, not 0.300).

So: one script, one route, one preprocessing path, a clean server each. Every statistic
the study depends on comes out of here or it does not get quoted.

WHAT IS RECORDED, and why each one:

  mean            the brightness the condition is calibrated on (T06-F20)
  sigma           WITHIN-frame contrast -- the discriminator condition_signature uses
                  for night, and the one R-SIM-4 asserts on every run
  p01             the black floor fog's airlight lifts -- the fog discriminator
  frac_dark       how much of the network's input carries no signal at all
  blown_frac      the other end: pixels saturated by the sun
  identify()      the condition this frame is CLASSIFIED as, per-frame, over the lap.
                  evaluate.py RAISES on a mismatch, so a condition that stops classifying
                  as itself aborts runs part-way through rather than at their start.

TWO VIEWS, because this study has two networks and they do not see the same image.
The TEACHER crops rows 180:400 to 200x66 and keeps about 60 rows of sky; the STUDENT
crops 240:450 to 168x28 and is road only. On the Town06 lap the sky renders black, so
the teacher's view carries ~12% dead pixels and a within-frame sigma above 0.10 in
CLEAR -- which is condition_signature's threshold for NIGHT.

That is not a defect in either crop, but it is a trap: condition_signature's thresholds
were derived on the STUDENT's view, and evaluate.py asserts them on the STUDENT's view.
Measuring classification on the teacher's view says "clear looks like night" and means
nothing. Both are recorded here, and identify() is run on the student's view only.
"""
import argparse
import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, os.path.join(REPO, "pipeline"))

import carla  # noqa: E402
import carla_determinism as cd  # noqa: E402
import carla_env as env  # noqa: E402
import config as C  # noqa: E402
from imaging import preprocess_for_model  # noqa: E402
from student import student_preprocess  # noqa: E402
from route import load_route, pure_pursuit_route, signed_cte_route  # noqa: E402
from condition_signature import identify, stats  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", required=True)
    ap.add_argument("--azimuth", type=float, default=None,
                    help="sun azimuth override for this run; omit to use the preset's own")
    ap.add_argument("--shutter", type=float, default=None,
                    help="camera shutter override for this run (a SWEEP knob, not a "
                         "setting: the committed value lives in CONDITION_EXPOSURE)")
    ap.add_argument("--every", type=int, default=2, help="sample every Nth step")
    ap.add_argument("--tag", default=None, help="output basename; defaults to the condition")
    ap.add_argument("--out-dir", default="results/town06/lap_conditions")
    args = ap.parse_args()

    if args.azimuth is not None:
        os.environ["SUN_AZIMUTH_OVERRIDE"] = str(args.azimuth)
    if args.shutter is not None:
        os.environ["EXPOSURE_SHUTTER_OVERRIDE"] = f"{args.condition}:{args.shutter}"

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
        exposure = C.exposure_for(args.condition)   # already carries the override
        sun_az = float(w.sun_azimuth_angle) % 360.0
        fov = float(getattr(env, "CAM_FOV", 90.0))

        keys = ("mean", "sigma", "p01", "p99", "frac_dark")
        acc = {k: [] for k in keys}                 # teacher view
        acc_s = {k: [] for k in keys}               # student view
        blown, in_fov, labels, hint = [], [], [], None
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
                bgr = env.raw_to_bgr(image)
                a = np.asarray(preprocess_for_model(bgr), dtype=np.float32)
                sv = np.asarray(student_preprocess(bgr, C.TOWN06_INPUT_W,
                                                   C.TOWN06_INPUT_H), dtype=np.float32)
                s, ss = stats(a), stats(sv)
                for k in keys:
                    acc[k].append(s[k])
                    acc_s[k].append(ss[k])
                blown.append(float((a > 0.95).mean()))
                # identify() on the STUDENT view -- the view its thresholds were
                # derived on and the view evaluate.py asserts.
                labels.append(identify(sv)[0])
                off = abs(((tf.rotation.yaw - sun_az + 180.0) % 360.0) - 180.0)
                in_fov.append(bool(off <= fov / 2.0))

            thr, brk = speed.control(vehicle)
            env.apply_control(vehicle, carla.VehicleControl(throttle=thr, brake=brk,
                                                            steer=steer))
            if hint is not None and hint >= n_route - 2:
                break

        want = env.canonical_condition(args.condition)
        # condition_signature still speaks the pre-rename vocabulary for low sun.
        want_label = "shadows" if want == "low_sun" else want
        frac_as_self = float(np.mean([l == want_label for l in labels]))
        misread = sorted({l for l in labels if l != want_label})

        out = dict(
            condition=want, sun_azimuth=sun_az,
            sun_altitude=float(w.sun_altitude_angle), exposure=exposure,
            samples=int(len(labels)),
            blown_frac=float(np.mean(blown)),
            sun_in_fov_frac=float(np.mean(in_fov)),
            classified_as_self_frac=frac_as_self,
            misclassified_as=misread,
            determinism=dict(deterministic_control=bool(C.DETERMINISTIC_CONTROL),
                             rules_digest=cd.digest(), lock_problems=cd.check_lock(),
                             server_cmdline=cd.server_cmdline(C.PORT)),
        )
        for k in keys:
            for src, dst in ((acc, out), (acc_s, out.setdefault("student_view", {}))):
                v = np.array(src[k])
                dst[k] = dict(mean=float(v.mean()), std=float(v.std()),
                              p05=float(np.percentile(v, 5)), p95=float(np.percentile(v, 95)))

        d = os.path.join(REPO, args.out_dir)
        os.makedirs(d, exist_ok=True)
        tag = args.tag or want
        with open(os.path.join(d, f"{tag}.json"), "w") as fh:
            json.dump(out, fh, indent=2)
        sv_ = out["student_view"]
        print(f"  {tag}: teacher-view mean {out['mean']['mean']:.4f} | student-view "
              f"mean {sv_['mean']['mean']:.4f} sigma {sv_['sigma']['mean']:.4f} "
              f"p01 {sv_['p01']['mean']:.4f} dark {sv_['frac_dark']['mean']:.3f}  "
              f"blown {out['blown_frac']:.4f}  "
              f"classified-as-self {100 * frac_as_self:.1f}%"
              + (f" (else {'/'.join(misread)})" if misread else "")
              + f"  n={out['samples']}")
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

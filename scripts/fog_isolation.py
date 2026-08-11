#!/usr/bin/env python3
"""Isolate fog scattering from the illumination change bundled into the fog preset.

`carla_env.set_weather("fog")` sets cloudiness=90 and sun_altitude=45 alongside
fog_density=70, while the clear preset is cloudiness=80 and sun_altitude=90. So any
clear-vs-fog delta measured from those presets conflates fog scattering with a lower sun
and heavier cloud, and cannot answer whether the renderer's fog brightens or darkens a
road surface.

This sweeps fog_density with the clear illumination HELD FIXED, which is the only form
of the measurement that means anything.

Physics: Koschmieder is I = I0*t + A*(1-t). On a road darker than the airlight A, fog
must BRIGHTEN it (d_mu > 0) and must always REDUCE contrast (sigma falls monotonically).
If the renderer darkens a dark road, it is not doing airlight scattering and a
Koschmieder disturbance model cannot be fitted to it.

    python scripts/fog_isolation.py --poses 20
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import carla  # noqa: E402
import carla_env as env  # noqa: E402
import config as C  # noqa: E402
from calibrate_exposure import RESULTS, grab, lane_poses, road_stats  # noqa: E402

DENSITIES = (0.0, 10.0, 25.0, 40.0, 55.0, 70.0, 85.0, 100.0)


def set_fog_only(world, density, fog_distance=10.0):
    """Clear illumination, fog density varied. Nothing else moves."""
    env.set_clear_weather(world)              # cloudiness 80, sun_altitude 90
    w = world.get_weather()
    w.fog_density = density
    w.fog_distance = fog_distance
    w.fog_falloff = 0.2
    world.set_weather(w)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--poses", type=int, default=20)
    ap.add_argument("--step-m", type=float, default=12.0)
    args = ap.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    chosen = dict(shutter=C.EXPOSURE_SHUTTER_SPEED, iso=C.EXPOSURE_ISO,
                  fstop=C.EXPOSURE_FSTOP, gamma=C.EXPOSURE_GAMMA)

    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)
    vehicle = camera = None
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
        vehicle.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
        poses = lane_poses(world, args.poses, args.step_m)
        camera, cam_queue = env.spawn_camera(world, vehicle, exposure=chosen)

        print(f"exposure {chosen}")
        print(f"{len(poses)} poses, clear illumination held fixed "
              f"(cloudiness=80, sun_altitude=90)\n")
        print(f"  {'density':>8s} {'mu':>7s} {'sigma':>8s} {'d_mu':>8s} {'sigma/sigma0':>13s}")

        rows, base = [], None
        for d in DENSITIES:
            set_fog_only(world, d)
            mus, sigmas = [], []
            for tf in poses:
                vehicle.set_transform(tf)
                vehicle.set_target_velocity(carla.Vector3D(0, 0, 0))
                for _ in range(3):
                    grab(world, cam_queue, world.tick())
                img = grab(world, cam_queue, world.tick())
                mu, sigma = road_stats(env.raw_to_bgr(img))
                mus.append(mu)
                sigmas.append(sigma)
            mu, sigma = float(np.mean(mus)), float(np.mean(sigmas))
            if base is None:
                base = (mu, sigma)
            rows.append(dict(density=d, mu=mu, sigma=sigma,
                             d_mu=mu - base[0], sigma_ratio=sigma / base[1]))
            print(f"  {d:8.0f} {mu:7.3f} {sigma:8.4f} {mu - base[0]:+8.3f} "
                  f"{sigma / base[1]:13.2f}")

        d_mus = [r["d_mu"] for r in rows[1:]]
        ratios = [r["sigma_ratio"] for r in rows[1:]]
        brightens = all(x > 0 for x in d_mus)
        darkens = all(x < 0 for x in d_mus)
        contrast_falls = all(a >= b - 1e-6 for a, b in zip(ratios, ratios[1:]))

        print("\n" + "=" * 72)
        print(f"  road mu at clear illumination : {base[0]:.3f}")
        print(f"  monotone contrast reduction   : {contrast_falls}")
        print(f"  direction of mean shift       : "
              f"{'BRIGHTENS' if brightens else 'DARKENS' if darkens else 'NON-MONOTONE'}")
        print()
        if brightens and contrast_falls:
            print("  -> Consistent with airlight scattering. Koschmieder is fittable;")
            print("     proceed to D4 (depth-based per-pixel fit of beta and A).")
        elif darkens:
            print("  -> The renderer DARKENS a road darker than any plausible airlight.")
            print("     This is not airlight scattering, and a Koschmieder model cannot")
            print("     be fitted to it. E9 fails: report as a simulator-fidelity finding")
            print("     and reconsider fog's place in the condition order (D2).")
        else:
            print("  -> Non-monotone. Investigate before fitting anything.")
        print("=" * 72)

        path = RESULTS / "fog_isolation.json"
        with open(path, "w") as fh:
            json.dump({"exposure": chosen, "poses": len(poses), "rows": rows}, fh, indent=2)
        print(f"\nwrote {path}")

    finally:
        if camera is not None:
            camera.destroy()
        if vehicle is not None:
            vehicle.destroy()
        world.apply_settings(original)


if __name__ == "__main__":
    sys.exit(main())

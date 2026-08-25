#!/usr/bin/env python3
"""Can ONE fixed exposure hold clear noon and headlight-lit night without clipping?

The chosen exposure (shutter 800, f/2.8) puts the clear road at mu=0.290, which is the
real-camera target, but crushes 50.5% of the night road ROI to exactly 0. Clipping to the
sensor floor destroys information irreversibly, so:

  - the policy cannot learn from those pixels, and
  - the night disturbance model is no longer the clean affine map g*x0 + c*H. The clamp
    still composes soundly as two ReLUs, so it stays verifiable, but it is not linear and
    what the clamp removed cannot be recovered.

Brightening to rescue night pushes clear back toward the washed-out regime that made the
fog airlight unidentifiable in the previous generation. This measures whether a setting
exists that satisfies both, or whether the exposure has to become condition-dependent.

    python scripts/exposure_dynamic_range.py --poses 12
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
from calibrate_exposure import RESULTS, grab, lane_poses  # noqa: E402

# Fractions of the road ROI allowed at the sensor floor / ceiling.
MAX_CLIP_FRAC = 1.0      # percent

SWEEP = [dict(shutter=s, iso=100.0, fstop=2.8, gamma=2.2)
         for s in (800.0, 400.0, 200.0, 100.0, 50.0, 25.0, 12.0, 6.0)]


def roi_stats(bgr):
    lo, hi = C.ROAD_ROI_ROWS
    g = bgr[lo:hi, :, :].astype(np.float32).mean(axis=2)
    return dict(
        mu=float(g.mean() / 255.0),
        sigma=float(g.std() / 255.0),
        clip_lo=float((g < 1.0).mean() * 100.0),
        clip_hi=float((g > 254.0).mean() * 100.0),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--poses", type=int, default=12)
    args = ap.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)

    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)
    vehicle = None
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
        vehicle.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
        poses = lane_poses(world, args.poses, 12.0)

        print(f"{len(poses)} poses. Target: clear mu in {C.TARGET_ROAD_MU}, "
              f"all clipping < {MAX_CLIP_FRAC}%\n")
        header = (f"  {'shutter':>8s} | {'clear mu':>8s} {'sigma':>7s} {'clip_hi%':>8s}"
                  f" | {'night mu':>8s} {'sigma':>7s} {'clip_lo%':>8s} | verdict")
        print(header)
        print("  " + "-" * (len(header) - 2))

        rows = []
        for exp in SWEEP:
            camera, cam_queue = env.spawn_camera(world, vehicle, exposure=exp)
            try:
                per = {}
                for cond in ("clear", "night"):
                    env.set_weather(world, cond, vehicle)
                    acc = []
                    for tf in poses:
                        vehicle.set_transform(tf)
                        vehicle.set_target_velocity(carla.Vector3D(0, 0, 0))
                        for _ in range(3):
                            grab(world, cam_queue, world.tick())
                        acc.append(roi_stats(env.raw_to_bgr(
                            grab(world, cam_queue, world.tick()))))
                    per[cond] = {k: float(np.mean([a[k] for a in acc])) for k in acc[0]}
            finally:
                camera.destroy()

            lo, hi = C.TARGET_ROAD_MU
            clear_ok = lo <= per["clear"]["mu"] <= hi
            clip_ok = (per["night"]["clip_lo"] < MAX_CLIP_FRAC
                       and per["clear"]["clip_hi"] < MAX_CLIP_FRAC)
            verdict = ("BOTH" if clear_ok and clip_ok
                       else "clip ok" if clip_ok
                       else "clear ok" if clear_ok else "-")
            rows.append({**exp, "clear": per["clear"], "night": per["night"],
                         "clear_in_target": clear_ok, "clipping_ok": clip_ok})
            print(f"  {exp['shutter']:8.0f} | {per['clear']['mu']:8.3f} "
                  f"{per['clear']['sigma']:7.4f} {per['clear']['clip_hi']:8.1f}"
                  f" | {per['night']['mu']:8.3f} {per['night']['sigma']:7.4f} "
                  f"{per['night']['clip_lo']:8.1f} | {verdict}")

        both = [r for r in rows if r["clear_in_target"] and r["clipping_ok"]]
        print("\n" + "=" * 72)
        if both:
            print(f"  A single exposure satisfies both: shutter={both[0]['shutter']:.0f}")
            print("  -> keep one camera configuration; no condition-dependent exposure.")
        else:
            usable = [r for r in rows if r["clipping_ok"]]
            print("  NO single exposure satisfies both.")
            if usable:
                b = min(usable, key=lambda r: r["clear"]["mu"])
                print(f"  Darkest clear with acceptable clipping: shutter={b['shutter']:.0f}, "
                      f"clear mu={b['clear']['mu']:.3f} (target {C.TARGET_ROAD_MU})")
                print("  -> either accept a brighter clear baseline, or declare a")
                print("     condition-dependent exposure. Both are defensible; both must")
                print("     be stated. See FINDINGS F4.")
            else:
                print("  Nothing clears the clipping bound. Night's dynamic range exceeds")
                print("  what 8 bits at a single exposure can carry.")
        print("=" * 72)

        path = RESULTS / "dynamic_range.json"
        with open(path, "w") as fh:
            json.dump({"poses": len(poses), "rows": rows}, fh, indent=2)
        print(f"\nwrote {path}")
    finally:
        if vehicle is not None:
            vehicle.destroy()
        world.apply_settings(original)


if __name__ == "__main__":
    # One CARLA client per port. Two synchronous clients on one world interleave ticks
    # and silently corrupt each other -- see pipeline/carla_lock.py for the run this
    # cost. Every entry point that ticks the world takes the lock, in both directions:
    # it refuses to start over someone else's run, and its own run is visible to them.
    from carla_lock import carla_lock, CarlaBusy
    try:
        with carla_lock(owner=" ".join(sys.argv[:3])):
            sys.exit(main())
    except CarlaBusy as exc:
        raise SystemExit(str(exc))

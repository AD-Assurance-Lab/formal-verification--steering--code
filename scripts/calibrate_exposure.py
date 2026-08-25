#!/usr/bin/env python3
"""M1's first measurement: pin the camera's exposure, and test the D1 diagnosis.

The previous generation ran `sensor.camera.rgb` with only `image_size` and `fov` set,
leaving CARLA's default per-frame HISTOGRAM auto-exposure active for every capture. This
script measures what that did and what fixing it changes.

Three questions, all answered in one CARLA session:

  1. Under auto-exposure, does the clear road ROI sit near mu = 0.81 (reproducing F9)?
  2. Does some manual exposure setting put it in the real-camera range [0.28, 0.34]?
  3. E7/E9 -- at the chosen setting, does rendered NIGHT still read "darker but SHARPER"
     (mean down, contrast UP), and does rendered FOG darken the road? Both anomalies are
     predicted to be auto-exposure artifacts. If they survive manual exposure they are
     genuine renderer properties and the disturbance models must change shape.

Every number is measured over N distinct poses, never one frame -- a single-frame
photometric comparison previously produced a confident, wrong, sign-reversal claim.

    python scripts/calibrate_exposure.py --poses 25
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import carla  # noqa: E402
import carla_env as env  # noqa: E402
import config as C  # noqa: E402

RESULTS = Path(__file__).resolve().parent.parent / "results" / "exposure"

# Sweep grid. CARLA's manual exposure follows the photographic triangle, so the effective
# exposure scales as (iso / fstop^2) * (1 / shutter_speed). Only that combination matters,
# but sweeping the axes separately keeps the reported setting physically interpretable.
SWEEP = [
    dict(shutter=s, iso=i, fstop=f, gamma=2.2)
    for s in (60.0, 120.0, 200.0, 400.0, 800.0)
    for i in (100.0,)
    for f in (1.4, 2.8, 5.6)
]


def road_stats(bgr):
    """Mean and std over the road ROI, in [0,1]. Grayscale, full image width."""
    lo, hi = C.ROAD_ROI_ROWS
    roi = bgr[lo:hi, :, :].astype(np.float32) / 255.0
    gray = roi.mean(axis=2)
    return float(gray.mean()), float(gray.std())


def grab(world, cam_queue, expected_frame, timeout=5.0):
    """Thin alias for carla_env.grab_frame, kept so existing callers keep working.

    This WAS a second implementation of frame-id matching. Two copies of the same logic
    is how trap 13 happened -- a fix landed in one and missed the other -- so there is
    now one implementation, in carla_env.
    """
    return env.grab_frame(cam_queue, expected_frame, timeout=timeout)


def lane_poses(world, n, step_m=12.0):
    """N poses walking forward along the ego's lane from the eastbound spawn."""
    carla_map = world.get_map()
    start = carla.Location(x=C.SPAWN_EASTBOUND["x"], y=C.SPAWN_EASTBOUND["y"],
                           z=C.SPAWN_EASTBOUND["z"])
    wp = carla_map.get_waypoint(start, project_to_road=True,
                                lane_type=carla.LaneType.Driving)
    poses, seen = [], 0
    while len(poses) < n and seen < n * 6:
        tf = wp.transform
        tf.location.z += 0.4          # keep the vehicle above the surface on teleport
        poses.append(tf)
        nxt = wp.next(step_m)
        seen += 1
        if not nxt:
            break
        wp = nxt[0]
    return poses


def measure(world, vehicle, poses, exposure, conditions=("clear",), settle=3):
    """Mean/std of the road ROI per condition, averaged over poses, at one exposure."""
    camera, cam_queue = env.spawn_camera(world, vehicle, exposure=exposure)
    try:
        out = {}
        for cond in conditions:
            env.set_weather(world, cond, vehicle)
            mus, sigmas = [], []
            for tf in poses:
                vehicle.set_transform(tf)
                vehicle.set_target_velocity(carla.Vector3D(0, 0, 0))
                # Let the teleport and any renderer state settle before trusting a frame.
                for _ in range(settle):
                    frame = world.tick()
                    grab(world, cam_queue, frame)
                frame = world.tick()
                img = grab(world, cam_queue, frame)
                mu, sigma = road_stats(env.raw_to_bgr(img))
                mus.append(mu)
                sigmas.append(sigma)
            out[cond] = dict(mu=float(np.mean(mus)), sigma=float(np.mean(sigmas)),
                             mu_sd=float(np.std(mus)), n=len(mus))
        return out
    finally:
        camera.destroy()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--poses", type=int, default=25)
    ap.add_argument("--step-m", type=float, default=12.0)
    args = ap.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)

    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)
    vehicle = None
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
        vehicle.set_autopilot(False)
        vehicle.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
        poses = lane_poses(world, args.poses, args.step_m)
        print(f"{len(poses)} poses along the eastbound lane, {args.step_m} m apart\n")

        report = {"poses": len(poses)}

        # --- Q1: reproduce the auto-exposure baseline ---------------------------
        print("=" * 72)
        print("Q1  AUTO-EXPOSURE (the previous generation's configuration)")
        print("=" * 72)
        auto = measure(world, vehicle, poses, dict(mode="histogram"),
                       conditions=("clear", "fog", "night"))
        for cond, s in auto.items():
            print(f"  {cond:6s}  mu={s['mu']:.3f} +/-{s['mu_sd']:.3f}   sigma={s['sigma']:.4f}")
        report["auto_exposure"] = auto

        # --- Q2: sweep manual exposure for the real-camera target ---------------
        print()
        print("=" * 72)
        print(f"Q2  MANUAL EXPOSURE SWEEP -- target clear road mu in {C.TARGET_ROAD_MU}")
        print("=" * 72)
        lo, hi = C.TARGET_ROAD_MU
        rows, best = [], None
        for exp in SWEEP:
            s = measure(world, vehicle, poses, exp, conditions=("clear",))["clear"]
            hit = lo <= s["mu"] <= hi
            rows.append({**exp, **s, "in_target": hit})
            print(f"  shutter={exp['shutter']:6.0f} iso={exp['iso']:5.0f} "
                  f"f/{exp['fstop']:<4} -> mu={s['mu']:.3f} sigma={s['sigma']:.4f}"
                  f"{'   <-- IN TARGET' if hit else ''}")
            mid = (lo + hi) / 2.0
            if best is None or abs(s["mu"] - mid) < abs(best["mu"] - mid):
                best = rows[-1]
        report["sweep"] = rows
        report["best"] = best

        # --- Q3: E7/E9 at the chosen exposure -----------------------------------
        print()
        print("=" * 72)
        print("Q3  E7/E9 -- are night's contrast inversion and fog's sign artifacts?")
        print("=" * 72)
        chosen = {k: best[k] for k in ("shutter", "iso", "fstop", "gamma")}
        print(f"  at {chosen}\n")
        manual = measure(world, vehicle, poses, chosen,
                         conditions=("clear", "fog", "night"))
        report["manual_exposure"] = manual
        report["chosen"] = chosen

        base_mu = manual["clear"]["mu"]
        base_sigma = manual["clear"]["sigma"]
        print(f"  {'cond':6s} {'mu':>7s} {'sigma':>8s} {'d_mu':>8s} {'sigma ratio':>12s}")
        for cond, s in manual.items():
            print(f"  {cond:6s} {s['mu']:7.3f} {s['sigma']:8.4f} "
                  f"{s['mu'] - base_mu:8.3f} {s['sigma'] / base_sigma:12.2f}")

        print()
        night_ratio = manual["night"]["sigma"] / base_sigma
        auto_night_ratio = auto["night"]["sigma"] / auto["clear"]["sigma"]
        print(f"  E7  night sigma ratio: auto {auto_night_ratio:.2f}x -> "
              f"manual {night_ratio:.2f}x")
        print("      (previous study measured 2.1-3.7x RISE under auto-exposure;")
        print("       physical night should LOWER contrast, i.e. ratio < 1)")
        print(f"      -> {'ARTIFACT, resolved' if night_ratio < 1.0 else 'SURVIVES -- genuine renderer property'}")

        fog_dmu = manual["fog"]["mu"] - base_mu
        print(f"\n  E9  fog d_mu = {fog_dmu:+.3f} "
              f"(auto-exposure measured {auto['fog']['mu'] - auto['clear']['mu']:+.3f})")
        print("      Koschmieder on a dark road predicts BRIGHTENING (d_mu > 0).")
        print(f"      -> model and renderer {'AGREE' if fog_dmu > 0 else 'DISAGREE'} in sign")

        path = RESULTS / "exposure_calibration.json"
        with open(path, "w") as fh:
            json.dump(report, fh, indent=2)
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

#!/usr/bin/env python3
"""Capture the steering-vs-lateral-offset frames ONCE, and persist them.

WHY THIS EXISTS. `measure_restoring_gain.py` and `certify_restoring.py` both place the
vehicle at lateral offsets, evaluate, print, and throw the frames away. Every re-analysis
therefore costs a CARLA run, and re-captures are not bit-identical (weather settling, camera
warm-up), so successive analyses were not strictly comparable. Persisting the projected
model inputs makes every downstream question -- restoring gain, equilibrium offset, a future
student -- an offline computation on one fixed capture.

WHY A FINER GRID NEAR ZERO. The quantity that decides the outcome is the EQUILIBRIUM offset,
where the disturbance bias is cancelled by the restoring response. Measured open-loop reach
is 0.02-0.22 m and the CTE budget is 0.668 m, so the decision is made entirely inside
|o| <= 1 m. The old grid's 0.5 m spacing there was coarser than the effect being measured.

Saves projected inputs (3x28x84, exactly what the network consumes) rather than raw BGR:
1000x smaller, and the projection is the fixed, verified separable map used everywhere else.

    python scripts/capture_offset_frames.py
"""
import sys
import csv
import json
import math
from pathlib import Path

import numpy as np
import torch
import carla

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
import carla_env as env  # noqa: E402
import verifiable_disturbance as vd  # noqa: E402
from imaging import raw_to_bgr  # noqa: E402
from carla_lock import carla_lock  # noqa: E402

OFFSETS = np.array([-2.0, -1.5, -1.0, -0.75, -0.5, -0.25, 0.0,
                    0.25, 0.5, 0.75, 1.0, 1.5, 2.0])
CONDS = ["clear", "fog", "night", "shadows"]
N_POSE = 40   # dense along-route sampling: run-length filtering needs spatial order
OUT = REPO / "results" / "calibration" / "offset_frames_seg.npz"


def main():
    base = REPO / "pipeline" / "data" / "live_pairs"
    with open(base / "manifest.csv") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r["weather"] == "clear" and r["direction"] == "westbound"]

    # Poses stratified by DISTURBANCE STRENGTH when available, uniform-along-route
    # otherwise. Uniform sampling put every shadow pose at the 37th percentile of shadow
    # strength while 12.1% of the route was darker than any of them, and that is precisely
    # the stretch where the closed loop departs -- verification cannot certify frames it
    # never looked at. Poses differ per condition because the strong frames do.
    strat = REPO / "results" / "calibration" / "strat_poses.json"
    if strat.exists():
        sp = json.loads(strat.read_text())
        pose_by_cond = {c: sp.get(c, sp.get("night")) for c in CONDS}
        pose_by_cond["clear"] = pose_by_cond.get("clear") or sp["night"]
        print(f"using strength-stratified poses from {strat.name}")
    else:
        u = rows[200:: max(1, (len(rows) - 300) // N_POSE)][:N_POSE]
        pose_by_cond = {c: u for c in CONDS}
        print("using uniform-along-route poses (no strat_poses.json)")

    npose = min(len(v) for v in pose_by_cond.values())
    pose_by_cond = {k: v[:npose] for k, v in pose_by_cond.items()}
    n = len(CONDS) * npose * len(OFFSETS)
    frames = np.zeros((len(CONDS), npose, len(OFFSETS), 3, 28, 84), np.float32)
    print(f"capturing {n} frames: {len(CONDS)} conditions x {npose} poses "
          f"x {len(OFFSETS)} offsets")

    with carla_lock(owner="offset frame capture"):
        cl = carla.Client(C.HOST, C.PORT)
        cl.set_timeout(120.0)
        world = cl.get_world()
        orig = world.get_settings()
        s = world.get_settings()
        s.synchronous_mode = True
        s.fixed_delta_seconds = C.FIXED_DT
        world.apply_settings(s)
        v = cam = None
        try:
            v = env.spawn_vehicle(world, C.SPAWN_WESTBOUND)
            v.apply_control(carla.VehicleControl(brake=1.0))
            # settle to the driven ride height BEFORE freezing physics; a 0.29 m error here
            # produced a fog disagreement that cost three wrong hypotheses.
            for _ in range(40):
                world.tick()
            z = v.get_transform().location.z
            v.set_simulate_physics(False)

            for ci, cond in enumerate(CONDS):
                if cam is not None:
                    cam.destroy()
                cam, q = env.set_condition(world, v, cond)
                # weather and auto-exposure both settle on later ticks, never the write tick
                for _ in range(25):
                    f = world.tick()
                    try:
                        env.grab_frame(q, f)
                    except Exception:
                        pass
                for pi, r in enumerate(pose_by_cond[cond]):
                    yaw = float(r["yaw"])
                    nx = -math.sin(math.radians(yaw))
                    ny = math.cos(math.radians(yaw))
                    for oi, off in enumerate(OFFSETS):
                        v.set_transform(env.make_transform(
                            dict(x=float(r["x"]) + nx * off,
                                 y=float(r["y"]) + ny * off, z=z, yaw=yaw)))
                        for _ in range(4):
                            world.tick()
                        while True:
                            fid = world.tick()
                            try:
                                img = raw_to_bgr(env.grab_frame(q, fid))
                                break
                            except Exception:
                                pass
                        frames[ci, pi, oi] = vd._project(
                            img.astype(np.float32) / 255.0, 84, 28
                        ).reshape(3, 28, 84)
                print(f"  {cond}: {npose*len(OFFSETS)} frames")
        finally:
            try:
                if cam:
                    cam.destroy()
                if v:
                    v.destroy()
            except Exception:
                pass
            world.apply_settings(orig)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUT, frames=frames, offsets=OFFSETS, conds=np.array(CONDS),
        pose_x=np.array([[float(r["x"]) for r in pose_by_cond[c]] for c in CONDS]),
        pose_y=np.array([[float(r["y"]) for r in pose_by_cond[c]] for c in CONDS]),
        pose_yaw=np.array([[float(r["yaw"]) for r in pose_by_cond[c]] for c in CONDS]))
    print(f"\nwrote {OUT}  ({OUT.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

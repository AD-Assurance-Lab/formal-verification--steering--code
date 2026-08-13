#!/usr/bin/env python3
"""Capture steering response over a (lateral offset x heading error) grid.

WHY YAW HAD TO BE ADDED (F23). Every earlier capture placed the vehicle at lateral offsets
with its heading ALIGNED to the path, so the policy's response to heading error was never
observed. Closing the loop on offset feedback alone makes it an undamped oscillator, and
forward Euler then puts the discrete spectral radius above one:

    k_psi   0.0   -> |lambda| 1.115  diverges
    k_psi  -0.2   -> |lambda| 1.040  diverges
    k_psi  -0.5   -> |lambda| 0.915  stable

which is exactly what the tube did -- every condition, including clear weather where the
real vehicle holds 0.13 m. The divergence was a missing state, not a loose bound: the spring
was measured and the damper was not.

GRID. Offsets span the lane; yaws span the heading errors a lane-keeper actually sees. Both
are needed jointly rather than separately because the steering response to offset depends on
heading (a car pointed back toward the lane needs less correction than one pointed away),
and treating them as additive would discard precisely that coupling.

Saves projected model inputs (3x28x84), the same fixed separable projection used everywhere
else in the study.

    python scripts/capture_offset_yaw.py [--poses 40] [--segment A]
"""
import sys
import csv
import json
import math
import argparse
from pathlib import Path

import os
import numpy as np
import carla

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
import carla_env as env  # noqa: E402
import verifiable_disturbance as vd  # noqa: E402
from imaging import raw_to_bgr  # noqa: E402
from carla_lock import carla_lock  # noqa: E402

OFFSETS = np.array([-1.5, -1.0, -0.6, -0.3, 0.0, 0.3, 0.6, 1.0, 1.5])
YAWS = np.array([-6.0, -3.0, 0.0, 3.0, 6.0])       # degrees of heading error
CONDS = os.environ.get("OY_CONDS", "clear,fog,night,shadows").split(",")
OUT = REPO / os.environ.get("OY_OUT", "results/calibration/offset_yaw.npz")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--poses", type=int, default=40)
    ap.add_argument("--start-m", type=float, default=0.0)
    ap.add_argument("--length-m", type=float, default=160.0)
    args = ap.parse_args()

    base = REPO / "pipeline" / "data" / "live_pairs"
    with open(base / "manifest.csv") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r["weather"] == "clear" and r["direction"] == "westbound"]
    xy = np.array([[float(r["x"]), float(r["y"])] for r in rows])
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))])
    want = np.linspace(args.start_m, args.start_m + args.length_m, args.poses)
    idx = sorted({int(np.argmin(np.abs(d - w))) for w in want})
    poses = [rows[i] for i in idx]

    n = len(CONDS) * len(poses) * len(OFFSETS) * len(YAWS)
    frames = np.zeros((len(CONDS), len(poses), len(OFFSETS), len(YAWS), 3, 28, 84),
                      np.float32)
    print(f"capturing {n} frames: {len(CONDS)} cond x {len(poses)} poses x "
          f"{len(OFFSETS)} offsets x {len(YAWS)} yaws")

    with carla_lock(owner="offset-yaw capture"):
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
            for _ in range(40):
                world.tick()
            z0 = v.get_transform().location.z
            v.set_simulate_physics(False)
            for ci, cond in enumerate(CONDS):
                if cam is not None:
                    cam.destroy()
                cam, q = env.set_condition(world, v, cond)
                for _ in range(25):
                    f = world.tick()
                    try:
                        env.grab_frame(q, f)
                    except Exception:
                        pass
                for pi, r in enumerate(poses):
                    yaw0 = float(r["yaw"])
                    nx = -math.sin(math.radians(yaw0))
                    ny = math.cos(math.radians(yaw0))
                    for oi, offv in enumerate(OFFSETS):
                        for yi, dy in enumerate(YAWS):
                            v.set_transform(env.make_transform(
                                dict(x=float(r["x"]) + nx * offv,
                                     y=float(r["y"]) + ny * offv,
                                     z=z0, yaw=yaw0 + float(dy))))
                            for _ in range(4):
                                world.tick()
                            while True:
                                fid = world.tick()
                                try:
                                    img = raw_to_bgr(env.grab_frame(q, fid))
                                    break
                                except Exception:
                                    pass
                            frames[ci, pi, oi, yi] = vd._project(
                                img.astype(np.float32) / 255.0, 84, 28).reshape(3, 28, 84)
                print(f"  {cond}: {len(poses)*len(OFFSETS)*len(YAWS)} frames", flush=True)
        finally:
            try:
                if cam:
                    cam.destroy()
                if v:
                    v.destroy()
            except Exception:
                pass
            world.apply_settings(orig)

    np.savez_compressed(
        OUT, frames=frames, offsets=OFFSETS, yaws=YAWS, conds=np.array(CONDS),
        pose_x=np.array([float(r["x"]) for r in poses]),
        pose_y=np.array([float(r["y"]) for r in poses]),
        pose_yaw=np.array([float(r["yaw"]) for r in poses]))
    print(f"\nwrote {OUT}  ({OUT.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

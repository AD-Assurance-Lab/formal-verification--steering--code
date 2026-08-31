#!/usr/bin/env python3
"""Park the ego at the lap's start and at its proposed end so a human can SEE the bounds.

The Town04 ledger drove to loop closure (~3,035 m) while the certificate covers the
scored prefix (2,861 m), so half of every mixed-student run's worst CTE was measured in
the western intersection -- the 181 m the study excludes because the lane centreline is
undefined there and the lane markings leave the camera's view on approach.

Choosing where the lap ends is a judgement about what the camera can see, so it is made
by looking, not by arithmetic. This holds the car at a chosen arc-length along the route
with the spectator behind it, ticking so the render stays live, until it is killed.

    --at start          the spawn point
    --at scored-end     the current 2,861 m cut
    --at 2800           any arc length in metres

    STUDY_MAP=Town04 TOWN04_REDO=1 CARLA_WINDOWED=1 DISPLAY=:0 \
        python3 scripts/inspect_lap_bounds.py --at scored-end
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
import numpy as np                                            # noqa: E402
import carla                                                  # noqa: E402
import carla_env as env                                       # noqa: E402
import config as C                                            # noqa: E402
from route import load_route                                  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", default="start",
                    help="'start', 'scored-end', or an arc length in metres")
    ap.add_argument("--direction", default="eastbound")
    ap.add_argument("--lock-spectator", action="store_true",
                    help="keep snapping the spectator behind the car. OFF by default: "
                         "the point of this tool is to LOOK AROUND, and re-aiming the "
                         "spectator every tick fights the mouse.")
    args = ap.parse_args()

    rt = np.asarray(load_route(args.direction), dtype=float)
    seg = np.linalg.norm(np.diff(rt[:, :2], axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    if args.at == "start":
        want = 0.0
    elif args.at == "scored-end":
        want = float(C.LAP_END_M)
    else:
        want = float(args.at)
    i = int(np.argmin(np.abs(arc - want)))
    x, y = rt[i, 0], rt[i, 1]
    nxt = rt[min(i + 1, len(rt) - 1)]
    yaw = float(np.degrees(np.arctan2(nxt[1] - y, nxt[0] - x)))

    print(f"\nroute '{args.direction}': {arc[-1]:.0f} m of geometry, "
          f"scored prefix {C.LAP_END_M:.0f} m")
    print(f"holding at {arc[i]:.0f} m  (index {i}/{len(rt)}, "
          f"{100*arc[i]/arc[-1]:.1f}% along)")
    print(f"  position ({x:.1f}, {y:.1f})  yaw {yaw:.1f} deg")
    print(f"  {arc[-1]-arc[i]:.0f} m remain to loop closure\n")

    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)
    vehicle = None
    try:
        spawn = {"x": float(x), "y": float(y), "z": 0.5, "yaw": yaw}
        vehicle = env.spawn_vehicle(world, spawn)
        env.apply_control(vehicle, carla.VehicleControl(throttle=0.0, brake=1.0))
        env.update_spectator(world, vehicle)
        world.tick()
        print("PARKED. The spectator is FREE -- fly it in the CARLA window:", flush=True)
        print("  right-mouse drag to look, WASD to move, Q/E down and up.", flush=True)
        print("Kill me when done.", flush=True)
        n = 0
        while True:
            world.tick()
            if args.lock_spectator:
                env.update_spectator(world, vehicle)
            n += 1
            if n % 250 == 0:
                print(f"  still holding ({n} ticks)", flush=True)
    except KeyboardInterrupt:
        print("\n  released")
    finally:
        try:
            if vehicle:
                vehicle.destroy()
        except Exception:
            pass
        world.apply_settings(original)
    return 0


if __name__ == "__main__":
    sys.exit(main())

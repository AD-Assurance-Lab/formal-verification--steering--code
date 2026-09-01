#!/usr/bin/env python3
"""Drive the Town06 continuous lap with pure pursuit, on screen, so a human can watch it.

This is a LOOK, not a measurement. It exists so the route and the PPC bridge points can be
confirmed by eye before anything is built on them -- the same reason the Town04 lap end was
chosen by parking the car there rather than by arithmetic.

The expert drives the whole lap. Bridge spans are announced as they are entered and left,
so the handover points can be judged in the window rather than inferred from a table.

    STUDY_MAP=Town06 CARLA_PORT=3000 CARLA_WINDOWED=1 DISPLAY=:0 \
        python3 scripts/practice_lap.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
import numpy as np                                            # noqa: E402
import carla                                                  # noqa: E402
import carla_determinism as cd                                # noqa: E402
import carla_env as env                                       # noqa: E402
import config as C                                            # noqa: E402
from route import pure_pursuit_route, signed_cte_route        # noqa: E402

ROUTES = REPO / "pipeline" / "data" / "routes_town06"


def main():
    cd.install_cleanup_handlers()
    lap = np.load(ROUTES / "lap.npy")
    meta = json.loads((ROUTES / "lap_meta.json").read_text())
    bridges = meta["bridges"]
    arc = np.concatenate([[0.0], np.cumsum(
        np.linalg.norm(np.diff(lap[:, :2], axis=0), axis=1))])
    print(f"\nTown06 practice lap: {meta['length_m']:.0f} m, "
          f"{meta['scored_m']:.0f} m scored, {len(bridges)} PPC bridges")
    for a, b in bridges:
        print(f"   bridge {a:7.0f} -> {b:7.0f} m")
    print()

    client = env.connect()
    world = env.load_town04(client)          # honours STUDY_MAP
    original = env.enable_sync_mode(world)
    vehicle = camera = None
    try:
        spawn = {"x": float(lap[0, 0]), "y": float(lap[0, 1]), "z": 0.5,
                 "yaw": float(lap[0, 2])}
        vehicle = env.spawn_vehicle(world, spawn)
        # warmup_to_speed drains the camera queue each tick, so it needs a real camera.
        camera, cam_q = env.set_condition(world, vehicle, "clear")
        speed = env.SpeedController()
        env.warmup_to_speed(world, vehicle, cam_q, speed,
                            steer_fn=lambda v: pure_pursuit_route(lap, v.get_transform())[0])
        print("driving the lap with pure pursuit -- watch the CARLA window\n", flush=True)
        hint, in_bridge, worst = None, False, 0.0
        for step in range(int(meta["length_m"] / (C.TARGET_SPEED_MS * C.FIXED_DT)) + 200):
            tf = vehicle.get_transform()
            # order and unpacking exactly as evaluate.py does it: pure_pursuit_route
            # returns (steer_norm, steer_rad, nearest_index) and the INDEX is the hint.
            cte, hint = signed_cte_route(lap, tf.location.x, tf.location.y, hint)
            steer, _, hint = pure_pursuit_route(lap, tf, hint)
            worst = max(worst, abs(cte or 0.0))
            here = arc[hint] if hint is not None and hint < len(arc) else 0.0
            nowb = any(a <= here <= b for a, b in bridges)
            if nowb != in_bridge:
                print(f"  {here:7.0f} m  {'ENTER' if nowb else 'LEAVE'} bridge "
                      f"(PPC {'takes over' if nowb else 'hands back'})", flush=True)
                in_bridge = nowb
            thr, brk = speed.control(vehicle)
            env.apply_control(vehicle, carla.VehicleControl(throttle=thr, brake=brk,
                                                            steer=steer))
            world.tick()
            try:
                cam_q.get(timeout=2.0)     # keep the sensor queue drained
            except Exception:
                pass
            env.update_spectator(world, vehicle)
            if step % 200 == 0:
                print(f"  {here:7.0f} m of {meta['length_m']:.0f}   "
                      f"|CTE| {abs(cte or 0)*C.M_TO_FT:.2f} ft", flush=True)
            if step > 100 and here > meta["length_m"] - 8:
                print(f"\n  lap complete at {here:.0f} m"); break
        print(f"  worst |CTE| over the lap: {worst*C.M_TO_FT:.2f} ft "
              f"(budget {C.CTE_BUDGET_FT:.2f} ft)")
    except KeyboardInterrupt:
        print("\n  stopped")
    finally:
        try:
            if camera:
                camera.destroy()
            if vehicle:
                vehicle.destroy()
        except Exception:
            pass
        world.apply_settings(original)
    return 0


if __name__ == "__main__":
    sys.exit(main())

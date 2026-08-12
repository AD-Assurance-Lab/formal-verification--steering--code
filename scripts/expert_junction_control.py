#!/usr/bin/env python3
"""Does the EXPERT deviate at the intersection too? The control for D-01/D-05.

Every marginal excursion tonight, and both departures, land inside the western
intersection at the end of the lap, where `route.py` follows a straightest-at-junction
policy and there is no painted centreline. That is an inference: the policies have no
visual cue there, so they drift.

Pure pursuit tests it directly. It steers geometrically toward a point on the reference
path and never looks at an image, so it has no perception to lose. If IT also deviates at
the same place, the reference path itself is the problem and the excursion is a property of
the route, not of any learned policy. If it tracks cleanly, the route is fine and the
drift really is the students losing their visual cue -- still a real finding, but a
different one.
"""
import sys
from pathlib import Path
import numpy as np
import carla

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C            # noqa: E402
import carla_env as env       # noqa: E402
from route import load_route, signed_cte_route, pure_pursuit_route  # noqa: E402

from carla_lock import carla_lock  # noqa: E402


def lap(world, vehicle, direction, route, max_steps=2200):
    env.teleport(vehicle, {"eastbound": C.SPAWN_EASTBOUND,
                           "westbound": C.SPAWN_WESTBOUND}[direction])
    for _ in range(10):
        world.tick()
    spd = env.SpeedController()
    start = vehicle.get_transform().location
    out, hint, left = [], None, False
    for _ in range(max_steps):
        world.tick()
        tf = vehicle.get_transform()
        loc = tf.location
        steer, _, hint = pure_pursuit_route(route, tf, hint)
        cte, hint2 = signed_cte_route(route, loc.x, loc.y, hint)
        if cte is not None:
            out.append((abs(cte), loc.x, loc.y))
        thr, brk = spd.control(vehicle)
        vehicle.apply_control(carla.VehicleControl(throttle=thr, brake=brk, steer=steer))
        d0 = loc.distance(start)
        if d0 > 50.0:
            left = True
        if left and d0 < 12.0:
            break
    return out


def main():
    with carla_lock(owner="expert junction control"):
        cl = carla.Client(C.HOST, C.PORT)
        cl.set_timeout(120.0)
        world = cl.get_world()
        orig = world.get_settings()
        s = world.get_settings()
        s.synchronous_mode = True
        s.fixed_delta_seconds = C.FIXED_DT
        world.apply_settings(s)
        v = None
        try:
            world.set_weather(env.weather_params("clear"))
            v = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
            for _ in range(30):
                world.tick()
            for direction in ("eastbound", "westbound"):
                route = load_route(direction)
                series = lap(world, v, direction, route)
                if not series:
                    print(f"{direction}: no data")
                    continue
                a = np.array(series)
                cte, xs = a[:, 0], a[:, 1]
                # the junction spans roughly x -360 .. -390
                inj = (xs > -392) & (xs < -358)
                out = ~inj
                print(f"\n{direction}: {len(a)} steps, budget {C.CTE_BUDGET_M:.3f} m")
                print(f"  OUTSIDE junction : max {cte[out].max()*3.28084:5.2f} ft  "
                      f"median {np.median(cte[out])*3.28084:5.2f} ft  "
                      f"over budget {100*(cte[out] > C.CTE_BUDGET_M).mean():.2f}%")
                if inj.any():
                    print(f"  INSIDE  junction : max {cte[inj].max()*3.28084:5.2f} ft  "
                          f"median {np.median(cte[inj])*3.28084:5.2f} ft  "
                          f"over budget {100*(cte[inj] > C.CTE_BUDGET_M).mean():.2f}%")
                i = int(cte.argmax())
                print(f"  worst overall    : {cte[i]*3.28084:.2f} ft at "
                      f"x {a[i,1]:.1f} y {a[i,2]:.1f}")
        finally:
            try:
                if v:
                    v.destroy()
            except Exception:
                pass
            world.apply_settings(orig)
    return 0


if __name__ == "__main__":
    sys.exit(main())

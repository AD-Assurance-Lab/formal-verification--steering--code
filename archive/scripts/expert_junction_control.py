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

# Where the students actually failed, from the ledger cells' max_cte_at fields.
FAILURE_POINTS = {
    "westbound": [("marginal x-374 y11.9", -374.0, 11.9),
                  ("marginal x-365.8 y11.7", -365.8, 11.7)],
    "eastbound": [("marginal x-370.5 y29.0", -370.5, 29.0),
                  ("DEPARTURE x-371 y3.8", -371.0, 3.8)],
}


def lap(world, vehicle, direction, route, max_steps=2200):
    env.teleport(vehicle, {"eastbound": C.SPAWN_EASTBOUND,
                           "westbound": C.SPAWN_WESTBOUND}[direction])
    for _ in range(10):
        world.tick()
    spd = env.SpeedController()
    # WITHOUT THIS THE CAR NEVER MOVES. The first version of this control omitted the
    # warm-up that closed_loop_ledger does, so the vehicle sat at spawn for all 2200
    # steps, reported a max CTE of 0.14 ft -- because it was parked exactly on the route --
    # and I read that as "the expert tracks the reference perfectly through the junction".
    # It had not driven anywhere near the junction. A control that does not exercise the
    # thing it controls for is worse than no control: it manufactures confidence.
    vehicle.set_autopilot(False)
    # warmup_to_speed wants a camera queue to drain; this control needs no images, so
    # accelerate to target speed inline instead.
    for _ in range(15):
        vehicle.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
        world.tick()
    for _ in range(80):
        if env.speed_mph(vehicle) >= C.TARGET_SPEED_MPH * 0.95:
            break
        tf0 = vehicle.get_transform()
        st, _, _ = pure_pursuit_route(route, tf0)
        thr, brk = spd.control(vehicle)
        vehicle.apply_control(carla.VehicleControl(throttle=thr, brake=brk, steer=st))
        world.tick()
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
                ys = a[:, 2]
                print(f"\n{direction}: {len(a)} steps, budget {C.CTE_BUDGET_M:.3f} m, "
                      f"x {xs.min():.0f}..{xs.max():.0f} (a real lap spans ~900 m)")
                print(f"  whole lap        : max {cte.max()*3.28084:5.2f} ft  "
                      f"median {np.median(cte)*3.28084:5.2f} ft  "
                      f"over budget {100*(cte > C.CTE_BUDGET_M).mean():.2f}%")
                # measure AT the observed student failure points, by 2-D proximity
                for label, fx, fy in FAILURE_POINTS.get(direction, []):
                    d2 = np.hypot(xs - fx, ys - fy)
                    near = d2 < 8.0
                    if near.any():
                        print(f"  near {label:22s}: {near.sum():4d} steps within 8 m, "
                              f"expert max {cte[near].max()*3.28084:5.2f} ft, "
                              f"over budget {100*(cte[near] > C.CTE_BUDGET_M).mean():.2f}%")
                    else:
                        print(f"  near {label:22s}: LAP NEVER CAME WITHIN 8 m "
                              f"(closest {d2.min():.1f} m) -- control does not cover it")
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

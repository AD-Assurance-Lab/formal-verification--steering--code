#!/usr/bin/env python3
"""Is the simulator fit to measure on? Drive the ORACLE and check it behaves.

WHY THIS EXISTS
---------------
A CARLA server that has been abused -- clients killed mid-run leaving synchronous mode
enabled with nothing ticking, or simply left up too long -- keeps answering, keeps
reporting plausible vehicle velocities, and silently stops advancing physics correctly.
Measured on a degraded server, the same section gave:

    path 78-555 m of a 552-894 m section (14-62%), at 1.3-5.6 m/s while
    speed_mph reported 20.0 throughout; and one run flung the car 190 m in 18 steps

On a freshly restarted server the same code drives 619.5 m of 622 m (99.6%) at 8.93 m/s
with an oracle max |CTE| of 0.50 ft.

None of that is visible in a result. The numbers look like driving failures, and an
entire evening was spent theorising about marginal stability, covariate shift and
per-section difficulty on top of them. So the server is not trusted, it is CHECKED,
before anything that will be reported.

The oracle is pure pursuit on the same route the policies follow. If IT cannot drive the
section at target speed, no policy measurement taken on that server means anything.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/carla_health_check.py
    exit 0 = fit to measure on, exit 1 = restart CARLA
"""
import argparse
import math
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", default=None, help="default: the shortest section")
    ap.add_argument("--weather", default="clear")
    ap.add_argument("--min-path-frac", type=float, default=0.95)
    ap.add_argument("--speed-tol", type=float, default=0.05)
    ap.add_argument("--max-oracle-cte-ft", type=float, default=1.0)
    args = ap.parse_args()

    import carla
    import carla_env as env
    from route import load_route, signed_cte_route, pure_pursuit_route

    sec = args.section or min(C.SECTIONS, key=lambda s: C.SECTION_LEN_M[s])
    route = load_route(sec)
    client = env.connect()
    world = env.load_town04(client, fresh=False)
    original = env.enable_sync_mode(world)
    v = cam = None
    try:
        v = env.spawn_vehicle(world, C.SPAWNS[sec])
        cam, q = env.spawn_camera(world, v)
        cam, q = env.set_condition(world, v, args.weather, cam)
        sc = env.SpeedController()
        env.warmup_to_speed(world, v, q, sc,
                            steer_fn=lambda veh: pure_pursuit_route(route, veh.get_transform())[0])
        prev = v.get_transform().location
        path, hint, mx = 0.0, None, 0.0
        n = C.steps_for(sec)
        for _ in range(n):
            f = world.tick()
            env.grab_frame(q, f)
            tf = v.get_transform()
            loc = tf.location
            cte, hint = signed_cte_route(route, loc.x, loc.y, hint)
            st, _, _ = pure_pursuit_route(route, tf, hint)
            th, br = sc.control(v)
            v.apply_control(carla.VehicleControl(throttle=th, brake=br, steer=st))
            path += math.dist((prev.x, prev.y), (loc.x, loc.y))
            prev = loc
            mx = max(mx, abs(cte))
    finally:
        env.cleanup([cam, v] if cam else [v] if v else [], world, original)

    scored = C.SECTION_LEN_M[sec]
    frac = path / scored
    speed = path / (n * C.FIXED_DT)
    cte_ft = mx * C.M_TO_FT
    print(f"oracle on {sec}/{args.weather}: path {path:.1f} m of {scored:.0f} m "
          f"({100*frac:.1f}%), {speed:.2f} m/s (target {C.TARGET_SPEED_MS:.2f}), "
          f"max|CTE| {cte_ft:.2f} ft")

    bad = []
    if frac < args.min_path_frac:
        bad.append(f"drove only {100*frac:.1f}% of the section (want >= "
                   f"{100*args.min_path_frac:.0f}%)")
    if abs(speed - C.TARGET_SPEED_MS) / C.TARGET_SPEED_MS > args.speed_tol:
        bad.append(f"mean speed {speed:.2f} m/s is off target {C.TARGET_SPEED_MS:.2f} "
                   f"by more than {100*args.speed_tol:.0f}%")
    if cte_ft > args.max_oracle_cte_ft:
        bad.append(f"oracle max|CTE| {cte_ft:.2f} ft exceeds {args.max_oracle_cte_ft:.2f}")
    if bad:
        print("\nSIMULATOR NOT FIT TO MEASURE ON:")
        for b in bad:
            print(f"  - {b}")
        print("\nRestart CARLA before measuring. Anything measured now will look like a "
              "driving failure and will not be one.")
        return 1
    print("simulator healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())

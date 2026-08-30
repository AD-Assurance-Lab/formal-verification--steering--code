#!/usr/bin/env python3
"""
Milestone-1, step 2: prove the PURE-PURSUIT ORACLE can drive both directions of
the Town04 figure-8 within the CTE budget. If the map-based oracle can't, no
learned policy can — and this isolates plumbing bugs (spawn/warmup/speed) from
model quality. No neural network involved.

Usage:
    python drive_expert.py --direction both --max-steps 2000
"""
import os
import sys
import csv
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import carla  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import config as C  # noqa: E402
import carla_env as env  # noqa: E402
from expert import nearest_waypoint  # noqa: E402
from metrics import summarize_cte  # noqa: E402
from route import load_route, signed_cte_route, pure_pursuit_route  # noqa: E402

# Sections, not a hardcoded pair: Town06 has six, Town04 has its two directions.
SPAWNS = C.SPAWNS


def drive_one(world, world_map, vehicle, img_queue, direction, max_steps):
    spawn = SPAWNS[direction]
    route = load_route(direction)
    hint = None
    speed_ctrl = env.SpeedController()
    env.teleport(vehicle, spawn)
    # Steer along the reference route while accelerating so recording starts on-center.
    env.warmup_to_speed(
        world, vehicle, img_queue, speed_ctrl,
        steer_fn=lambda veh: pure_pursuit_route(route, veh.get_transform())[0],
    )

    start = carla.Location(x=spawn["x"], y=spawn["y"], z=spawn["z"])
    print(f"\n=== {direction.upper()} === start=({spawn['x']}, {spawn['y']}) "
          f"speed={env.speed_mph(vehicle):.1f} mph")

    records, left_start, stalled, offroad = [], False, 0, 0
    for step in range(max_steps):
        env.update_spectator(world, vehicle)
        tf = vehicle.get_transform()
        loc = tf.location

        cte, hint = signed_cte_route(route, loc.x, loc.y, hint)
        steer, steer_rad, _ = pure_pursuit_route(route, tf, hint)
        thr, brk = speed_ctrl.control(vehicle)
        env.apply_control(vehicle, carla.VehicleControl(throttle=thr, brake=brk, steer=steer))

        spd = env.speed_mph(vehicle)
        records.append(dict(
            step=step, time_sec=round(step * C.FIXED_DT, 2),
            steer_norm=steer, steer_rad=steer_rad,
            cte_m=cte, cte_ft=(cte * C.M_TO_FT if cte is not None else None),
            speed_mph=spd, x=loc.x, y=loc.y, yaw=tf.rotation.yaw,
        ))

        # ── termination logic ──────────────────────────────────────────────
        dist_start = loc.distance(start)
        if dist_start > 50.0:
            left_start = True
        if left_start and dist_start < 12.0:
            print(f"  [step {step}] loop closed (returned near start)")
            break
        stalled = stalled + 1 if spd < 1.0 else 0
        if stalled >= 20:
            print(f"  [step {step}] STALLED (speed<1mph for 20 steps) at x={loc.x:.1f}")
            break
        offroad = offroad + 1 if (cte is not None and abs(cte) > 4.0) else 0
        if offroad >= 10:
            print(f"  [step {step}] OFF-ROAD (|CTE|>4m) at x={loc.x:.1f}")
            break

        world.tick()
        # the oracle never looks at the image; drain so the queue cannot grow
        env.drain_frame(img_queue)

    return records


def save_and_report(direction, records):
    os.makedirs(C.RESULTS_DIR, exist_ok=True)
    csv_path = os.path.join(C.RESULTS_DIR, f"oracle_{direction}.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        w.writeheader()
        w.writerows(records)

    stats = summarize_cte([r["cte_m"] for r in records])
    verdict = "PASS" if stats.get("passed") else "FAIL"
    print(f"  [{direction}] {verdict} | steps={stats['n']} "
          f"max|CTE|={stats['max_abs_cte_m']:.3f}m ({stats['max_abs_cte_m']*C.M_TO_FT:.2f}ft) "
          f"over-budget={stats['frac_over_budget']*100:.1f}%")

    # plot: trajectory + signed CTE vs step
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    xs = [r["x"] for r in records]
    ys = [r["y"] for r in records]
    ctes = [r["cte_ft"] for r in records]
    sc = ax1.scatter(xs, ys, c=[abs(c) for c in ctes], cmap="RdYlGn_r", s=8, vmin=0, vmax=C.CTE_BUDGET_FT * 2)
    ax1.set_title(f"{direction}: trajectory (color=|CTE| ft)")
    ax1.set_xlabel("x (m)"); ax1.set_ylabel("y (m)"); ax1.axis("equal")
    fig.colorbar(sc, ax=ax1, label="|CTE| (ft)")
    ax2.plot([r["step"] for r in records], ctes, lw=1)
    ax2.axhline(C.CTE_BUDGET_FT, ls="--", c="r"); ax2.axhline(-C.CTE_BUDGET_FT, ls="--", c="r")
    ax2.set_title(f"{direction}: signed CTE (budget ±{C.CTE_BUDGET_FT:.2f} ft)")
    ax2.set_xlabel("step"); ax2.set_ylabel("CTE (ft)")
    fig.tight_layout()
    png = os.path.join(C.RESULTS_DIR, f"oracle_{direction}.png")
    fig.savefig(png, dpi=110); plt.close(fig)
    print(f"  saved {csv_path} and {png}")
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--direction", default="both",
                    help="section name, or 'both'/'all' for every section")
    ap.add_argument("--max-steps", type=int, default=2000)
    args = ap.parse_args()

    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)
    env.set_clear_weather(world)
    world_map = world.get_map()

    # sanity re-check: lane width at the eastbound spawn
    wp0 = nearest_waypoint(world_map, carla.Location(**{k: C.SPAWN_EASTBOUND[k] for k in "xyz"}))
    print(f"lane_width at spawn = {wp0.lane_width:.3f} m (config assumes {C.LANE_WIDTH_M})")
    print(C.summary())

    # Spawn INSIDE the try: a failure here would otherwise skip the finally and leave
    # the server hung in synchronous mode with no ticking client (trap 3b).
    vehicle = camera = img_queue = None
    dirs = list(C.SECTIONS) if args.direction in ("both", "all") else [args.direction]
    results = {}
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
        camera, img_queue = env.spawn_camera(world, vehicle)
        for d in dirs:
            recs = drive_one(world, world_map, vehicle, img_queue, d, min(args.max_steps, C.steps_for(d)))
            results[d] = save_and_report(d, recs)
    finally:
        env.cleanup([camera, vehicle], world, original)

    print("\n" + "=" * 60)
    for d, s in results.items():
        print(f"{d:10s}: {'PASS' if s.get('passed') else 'FAIL'} "
              f"(max|CTE|={s.get('max_abs_cte_m', 0)*C.M_TO_FT:.2f} ft)")


if __name__ == "__main__":
    # One CARLA client per port. Two synchronous clients on one world interleave ticks
    # and silently corrupt each other -- see pipeline/carla_lock.py for the run this
    # cost. Every entry point that ticks the world takes the lock, in both directions:
    # it refuses to start over someone else's run, and its own run is visible to them.
    from carla_lock import carla_lock, CarlaBusy
    try:
        with carla_lock(owner=" ".join(sys.argv[:3])):
            main()
    except CarlaBusy as exc:
        raise SystemExit(str(exc))

#!/usr/bin/env python3
"""M4: fill a closed-loop ledger cell -- a failure RATE over repetitions, not one run.

Every closed-loop number in this study is a rate with a confidence interval. Near the
stability cliff a single run gives the wrong verdict roughly 1 in 8 times, so a single
pass or fail is not evidence and a "PASS" from one lap is how a marginal policy gets
promoted. This is constraint 5 and trap 4.

Writes results/ledger/<condition>__<student>__closed_loop.json, which
`python -m study.ledger` then checks against the pre-registered expectation.

    python scripts/closed_loop_ledger.py --student S_mixed_84x28 --condition night --reps 10
"""

import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))

import carla  # noqa: E402
import carla_env as env  # noqa: E402
import config as C  # noqa: E402
from route import load_route, signed_cte_route, pure_pursuit_route  # noqa: E402
from student import StudentNet, student_preprocess  # noqa: E402

LEDGER = REPO / "results" / "ledger"
SPAWNS = {"eastbound": C.SPAWN_EASTBOUND, "westbound": C.SPAWN_WESTBOUND}


def wilson(k, n, z=1.96):
    """Wilson score interval for a binomial proportion.

    Used rather than the normal approximation because it stays inside [0,1] and behaves
    at k=0 and k=n, which is exactly where these rates land.
    """
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def drive_once(world, vehicle, cam_queue, model, device, direction, max_steps):
    """One lap under policy control. Returns (max_abs_cte_m, frac_over_budget, departed)."""
    route = load_route(direction)
    hint = None
    speed_ctrl = env.SpeedController()
    env.teleport(vehicle, SPAWNS[direction])
    env.warmup_to_speed(
        world, vehicle, cam_queue, speed_ctrl,
        steer_fn=lambda veh: pure_pursuit_route(route, veh.get_transform())[0],
    )
    spawn = SPAWNS[direction]
    start = carla.Location(x=spawn["x"], y=spawn["y"], z=spawn["z"])

    # Track WHERE the worst excursion happens, not just how big it is. Three westbound
    # failures across two conditions all sat at 2.2-2.6 ft against a 2.19 ft budget, and
    # with only a scalar max there is no way to tell a recurring bad corner from bad luck
    # -- which is exactly the question D-01 turns on.
    ctes, poses, left, stalled, offroad, departed = [], [], False, 0, 0, False
    for _ in range(max_steps):
        # Keep the chase camera on the car. Omitting this leaves the spectator wherever
        # warmup left it while the vehicle drives off into the distance -- the view is
        # cosmetic, but a run you cannot watch is a run you cannot sanity-check by eye,
        # and eyeballing the render is what caught the fog-in-night preset bug.
        env.update_spectator(world, vehicle)
        frame = world.tick()
        image = env.grab_frame(cam_queue, frame)
        tf = vehicle.get_transform()
        loc = tf.location

        x = student_preprocess(env.raw_to_bgr(image), model.in_w, model.in_h)
        xin = torch.from_numpy(x).unsqueeze(0).to(device)
        with torch.no_grad():
            steer = max(-1.0, min(1.0, float(model(xin).item())))

        cte, hint = signed_cte_route(route, loc.x, loc.y, hint)
        if cte is not None:
            ctes.append(abs(cte))
            poses.append((float(loc.x), float(loc.y)))

        thr, brk = speed_ctrl.control(vehicle)
        vehicle.apply_control(carla.VehicleControl(throttle=thr, brake=brk, steer=steer))

        d0 = loc.distance(start)
        if d0 > 50.0:
            left = True
        if left and d0 < 12.0:
            break
        stalled = stalled + 1 if env.speed_mph(vehicle) < 1.0 else 0
        offroad = offroad + 1 if (cte is not None and abs(cte) > 6.0) else 0
        if stalled >= 20 or offroad >= 15:
            departed = True
            break

    if not ctes:
        return (float("inf"), 1.0, True, None)
    arr = np.array(ctes)
    i = int(arr.argmax())
    where = dict(step=i, x=poses[i][0], y=poses[i][1]) if i < len(poses) else None
    return (float(arr.max()), float((arr > C.CTE_BUDGET_M).mean()), departed, where)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--student", required=True)
    ap.add_argument("--condition", required=True)
    ap.add_argument("--reps", type=int, default=10,
                    help="repetitions PER DIRECTION. The ledger requires >= 10 total.")
    ap.add_argument("--max-steps", type=int, default=2000)
    ap.add_argument("--w", type=int, default=84)
    ap.add_argument("--h", type=int, default=28)
    ap.add_argument("--channels", default="8,16,16")
    ap.add_argument("--fc", type=int, default=32)
    ap.add_argument("--cell-name", default=None,
                    help="ledger student name, if it differs from the checkpoint "
                         "(e.g. --student S_mixed_84x28 --cell-name S_mixed)")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = StudentNet(args.h, args.w,
                       channels=tuple(int(v) for v in args.channels.split(",")),
                       fc=args.fc).to(device)
    model.load_state_dict(torch.load(
        os.path.join(C.CHECKPOINT_DIR, f"{args.student}.pth"), map_location=device))
    model.eval()   # StudentNet sets in_h/in_w from its constructor args

    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)
    vehicle = camera = None
    runs = []
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
        camera, cam_queue = env.set_condition(world, vehicle, args.condition)
        print(f"{args.student} under '{args.condition}' "
              f"(exposure shutter={C.exposure_for(args.condition)['shutter']:.0f})")
        print(f"budget {C.CTE_BUDGET_M:.3f} m ({C.CTE_BUDGET_FT:.2f} ft), "
              f"{args.reps} reps x 2 directions\n")

        for rep in range(args.reps):
            for d in ("eastbound", "westbound"):
                mx, frac, departed, where = drive_once(world, vehicle, cam_queue, model,
                                                device, d, args.max_steps)
                ok = (not departed) and mx <= C.CTE_BUDGET_M
                runs.append(dict(rep=rep, direction=d, max_cte_m=mx,
                                 frac_over_budget=frac, departed=departed, passed=ok,
                                 max_cte_at=where))
                print(f"  rep {rep} {d:10s} max|CTE|={mx * C.M_TO_FT:6.2f} ft "
                      f"over={frac * 100:5.1f}%  {'PASS' if ok else 'FAIL'}"
                      f"{'  (departed)' if departed else ''}")
    finally:
        # Cleanup must NEVER destroy results. CARLA died mid-cell once and
        # world.apply_settings() then raised out of this finally block, killing the
        # process before the JSON was written -- discarding ten repetitions that had
        # already been driven. Best-effort teardown, always.
        for label, fn in (("camera", lambda: camera and camera.destroy()),
                          ("vehicle", lambda: vehicle and vehicle.destroy()),
                          ("settings", lambda: world.apply_settings(original))):
            try:
                fn()
            except Exception as exc:
                print(f"  cleanup: {label} failed ({type(exc).__name__}); continuing")

    if not runs:
        print("no runs completed -- nothing to record")
        return 1
    n = len(runs)
    fails = sum(1 for r in runs if not r["passed"])
    rate = fails / n if n else 1.0
    lo, hi = wilson(fails, n)
    verdict = "FAIL" if lo > 0.0 else "PASS"

    print(f"\n{'=' * 64}")
    print(f"  failure rate {fails}/{n} = {rate:.1%}   95% Wilson [{lo:.1%}, {hi:.1%}]")
    print(f"  verdict: {verdict}")
    print("  (FAIL when the interval excludes zero -- a rate consistent with zero is")
    print("   not evidence of failure, and one bad lap out of ten is not a pass either)")
    if verdict == "PASS":
        print(f"\n  NOTE: a PASS at n={n} bounds the failure rate below {hi:.1%}, not to")
        print("  zero. Report it that way. Bounding below 5% would need n ~ 60.")
    print("=" * 64)

    LEDGER.mkdir(parents=True, exist_ok=True)
    cell = args.cell_name or args.student
    path = LEDGER / f"{args.condition}__{cell}__closed_loop.json"
    with open(path, "w") as fh:
        json.dump(dict(
            verdict=verdict, repetitions=n, failures=fails, failure_rate=rate,
            wilson_95=[lo, hi], student=args.student, condition=args.condition,
            exposure=C.exposure_for(args.condition),
            cte_budget_m=C.CTE_BUDGET_M, runs=runs,
        ), fh, indent=2)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    # One CARLA client per port. Two synchronous clients on one world interleave ticks
    # and silently corrupt each other -- see pipeline/carla_lock.py for the run this cost.
    from carla_lock import carla_lock, CarlaBusy
    try:
        with carla_lock(owner=" ".join(sys.argv[:3])):
            sys.exit(main())
    except CarlaBusy as exc:
        print(exc)
        sys.exit(4)

#!/usr/bin/env python3
"""
Closed-loop evaluation: drive the full Town04 loop (both directions) with the
NETWORK in control (camera -> steering), recording CTE. This is the real metric
for a BC/DAgger policy — covariate shift (compounding error) only shows up here,
not in offline val MSE.

Warmup uses pure-pursuit to reach cruising speed on-center (same starting
condition as data collection); the network then drives the evaluated loop.

    python evaluate.py --model steering_bc_baseline --direction both
"""
import os
import sys
import csv
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch  # noqa: E402
import carla  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import config as C  # noqa: E402
import carla_env as env  # noqa: E402
from imaging import preprocess_for_model  # noqa: E402
from student import student_preprocess  # noqa: E402
from expert import pure_pursuit_steer  # noqa: E402
from metrics import summarize_cte  # noqa: E402
from model import CarlaSteeringNet  # noqa: E402
from route import load_route, signed_cte_route, pure_pursuit_route  # noqa: E402

# Sections, not a hardcoded pair (Town06 has six; Town04 has its two directions).
SPAWNS = C.SPAWNS


def load_model(name, device, student=False, channels=(8, 16, 16), fc=32, h=28, w=84):
    """Load a teacher (CarlaSteeringNet) or, with student=True, a StudentNet.

    The students are what the certificate actually reasons about, so being able to
    DRIVE one here is what makes a clear-weather competence check possible without
    duplicating the closed-loop driving code.
    """
    if student:
        from student import StudentNet
        model = StudentNet(h, w, channels=tuple(channels), fc=fc).to(device)
    else:
        model = CarlaSteeringNet().to(device)
    model.load_state_dict(torch.load(os.path.join(C.CHECKPOINT_DIR, f"{name}.pth"),
                                     map_location=device))
    model.eval()
    return model


def drive_nn(world, world_map, vehicle, img_queue, model, device, direction, max_steps):
    spawn = SPAWNS[direction]
    route = load_route(direction)
    hint = None
    speed_ctrl = env.SpeedController()
    env.teleport(vehicle, spawn)
    env.warmup_to_speed(
        world, vehicle, img_queue, speed_ctrl,
        steer_fn=lambda veh: pure_pursuit_route(route, veh.get_transform())[0],
    )
    start = carla.Location(x=spawn["x"], y=spawn["y"], z=spawn["z"])
    print(f"\n=== {direction.upper()} (network in control) ===")

    records, left, stalled, offroad = [], False, 0, 0
    for step in range(max_steps):
        env.update_spectator(world, vehicle)
        frame = world.tick()
        image = env.grab_frame(img_queue, frame)
        tf = vehicle.get_transform()
        loc = tf.location

        # network steering from the camera frame
        # A StudentNet takes 84x28, the teacher 200x66. preprocess_for_model bakes in
        # the TEACHER size, so driving a student through it feeds the wrong tensor.
        bgr = env.raw_to_bgr(image)
        if hasattr(model, "in_w"):
            x = torch.from_numpy(student_preprocess(bgr, model.in_w, model.in_h)).unsqueeze(0).to(device)
        else:
            x = torch.from_numpy(preprocess_for_model(bgr)).unsqueeze(0).to(device)
        with torch.no_grad():
            nn_steer = float(model(x).item())
        nn_steer = max(-1.0, min(1.0, nn_steer))

        # CTE + expert reference against the FIXED route (immune to lane-snapping)
        cte, hint = signed_cte_route(route, loc.x, loc.y, hint)
        exp_steer, _, _ = pure_pursuit_route(route, tf, hint)

        thr, brk = speed_ctrl.control(vehicle)
        vehicle.apply_control(carla.VehicleControl(throttle=thr, brake=brk, steer=nn_steer))

        records.append(dict(
            step=step, time_sec=round(step * C.FIXED_DT, 2),
            nn_steer=nn_steer, expert_steer=exp_steer,
            cte_m=cte, cte_ft=(cte * C.M_TO_FT if cte is not None else None),
            speed_mph=env.speed_mph(vehicle), x=loc.x, y=loc.y, yaw=tf.rotation.yaw,
        ))

        d0 = loc.distance(start)
        if d0 > 50.0:
            left = True
        if left and d0 < 12.0:
            print(f"  loop closed at step {step}")
            break
        stalled = stalled + 1 if env.speed_mph(vehicle) < 1.0 else 0
        offroad = offroad + 1 if (cte is not None and abs(cte) > 4.0) else 0
        if stalled >= 20:
            print(f"  STALLED at step {step}, x={loc.x:.0f}"); break
        if offroad >= 10:
            print(f"  OFF-ROAD (departed lane) at step {step}, x={loc.x:.0f}"); break
    return records


def save_and_report(name, direction, records):
    os.makedirs(C.RESULTS_DIR, exist_ok=True)
    csv_path = os.path.join(C.RESULTS_DIR, f"eval_{name}_{direction}.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        w.writeheader(); w.writerows(records)

    stats = summarize_cte([r["cte_m"] for r in records])
    verdict = "PASS" if stats.get("passed") else "FAIL"
    print(f"  [{direction}] {verdict} | steps={stats['n']} "
          f"max|CTE|={stats['max_abs_cte_m']*C.M_TO_FT:.2f}ft "
          f"over-budget={stats['frac_over_budget']*100:.1f}%")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))
    xs = [r["x"] for r in records]; ys = [r["y"] for r in records]
    ctes = [r["cte_ft"] for r in records]
    sc = a1.scatter(xs, ys, c=[abs(c) for c in ctes], cmap="RdYlGn_r",
                    s=8, vmin=0, vmax=C.CTE_BUDGET_FT * 2)
    a1.set_title(f"{name} {direction}: trajectory (|CTE| ft)")
    a1.axis("equal"); a1.set_xlabel("x"); a1.set_ylabel("y")
    fig.colorbar(sc, ax=a1, label="|CTE| ft")
    a2.plot([r["step"] for r in records], ctes, lw=1, label="CTE")
    a2.axhline(C.CTE_BUDGET_FT, ls="--", c="r"); a2.axhline(-C.CTE_BUDGET_FT, ls="--", c="r")
    a2.set_title(f"{direction}: CTE (budget ±{C.CTE_BUDGET_FT:.2f} ft)")
    a2.set_xlabel("step"); a2.set_ylabel("CTE (ft)")
    fig.tight_layout()
    fig.savefig(os.path.join(C.RESULTS_DIR, f"eval_{name}_{direction}.png"), dpi=110)
    plt.close(fig)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="steering_bc_baseline")
    ap.add_argument("--student", action="store_true",
                    help="load a StudentNet instead of the PilotNet-class teacher")
    ap.add_argument("--channels", default="8,16,16", help="student conv widths")
    ap.add_argument("--fc", type=int, default=32, help="student FC width")
    ap.add_argument("--in-w", type=int, default=84)
    ap.add_argument("--in-h", type=int, default=28)
    ap.add_argument("--direction", default="both",
                    help="section name, or 'both'/'all' for every section")
    ap.add_argument("--max-steps", type=int, default=2000)
    ap.add_argument("--weather", default="clear",
                    choices=["clear", "fog", "rain", "night", "shadows"],
                    help="rendered CARLA condition; night switches the ego headlights on")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = load_model(args.model, device, student=args.student,
                       channels=tuple(int(v) for v in args.channels.split(",")),
                       fc=args.fc, h=args.in_h, w=args.in_w)

    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)
    world_map = world.get_map()
    # Spawn INSIDE the try: a failure here would otherwise skip the finally and leave
    # the server hung in synchronous mode with no ticking client (trap 3b).
    vehicle = camera = img_queue = None
    dirs = list(C.SECTIONS) if args.direction in ("both", "all") else [args.direction]
    results = {}
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
        camera, img_queue = env.spawn_camera(world, vehicle)
        # after spawn: lights need the vehicle, and exposure is declared per condition
        camera, img_queue = env.set_condition(world, vehicle, args.weather, camera)
        for d in dirs:
            recs = drive_nn(world, world_map, vehicle, img_queue, model, device, d, min(args.max_steps, C.steps_for(d)))
            results[d] = save_and_report(args.model, d, recs)
    finally:
        env.cleanup([camera, vehicle], world, original)

    print("\n" + "=" * 60)
    for d, s in results.items():
        print(f"{d:10s}: {'PASS' if s.get('passed') else 'FAIL'} "
              f"max|CTE|={s.get('max_abs_cte_m', 0)*C.M_TO_FT:.2f}ft "
              f"over-budget={s.get('frac_over_budget', 1)*100:.1f}%")


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

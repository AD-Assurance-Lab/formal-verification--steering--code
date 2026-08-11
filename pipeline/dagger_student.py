#!/usr/bin/env python3
"""
DAgger-polish the verifiable StudentNet. Each round: the current student drives
the full loop both directions; every visited frame is saved (its distillation
label is the TEACHER's output, computed at re-distill time). The frames are
aggregated and the student is re-distilled from scratch. The off-center states
the student wanders into (e.g. the westbound curve it overshoots) become the
targeted recovery data. Stops when the driven student meets budget.

    python dagger_student.py --student student_84x28 --w 84 --h 28 --rounds 3
"""
import os
import glob
import sys
import csv
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import torch
import carla

import config as C
import carla_env as env
from route import load_route, signed_cte_route, pure_pursuit_route
from metrics import summarize_cte
from student import StudentNet, student_preprocess
from distill import distill_student

SPAWNS = {"eastbound": C.SPAWN_EASTBOUND, "westbound": C.SPAWN_WESTBOUND}
FIELDS = ["image", "weather", "direction", "step", "steer", "steer_rad", "nn_steer",
          "cte_m", "speed_mph", "x", "y", "yaw"]


def load_student(name, w, h, device, channels=(8, 16, 16), fc=32):
    m = StudentNet(h, w, channels=channels, fc=fc).to(device)
    m.load_state_dict(torch.load(os.path.join(C.CHECKPOINT_DIR, f"{name}.pth"),
                                 map_location=device))
    m.eval()
    return m


def drive_collect(world, vehicle, img_queue, model, device, w, h, weather, direction, round_dir, max_steps):
    route = load_route(direction)
    hint = None
    sc = env.SpeedController()
    env.teleport(vehicle, SPAWNS[direction])
    env.warmup_to_speed(world, vehicle, img_queue, sc,
                        steer_fn=lambda v: pure_pursuit_route(route, v.get_transform())[0])
    seg = os.path.join(weather, direction)
    frames_dir = os.path.join(round_dir, seg, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    start = carla.Location(x=SPAWNS[direction]["x"], y=SPAWNS[direction]["y"], z=SPAWNS[direction]["z"])

    rows, left, stalled, offroad = [], False, 0, 0
    for step in range(max_steps):
        env.update_spectator(world, vehicle)
        world.tick()
        try:
            image = img_queue.get(timeout=2.0)
        except Exception:
            continue
        tf = vehicle.get_transform()
        loc = tf.location
        bgr = env.raw_to_bgr(image)
        xin = torch.from_numpy(student_preprocess(bgr, w, h)).unsqueeze(0).to(device)
        with torch.no_grad():
            nn_steer = max(-1.0, min(1.0, float(model(xin).item())))
        cte, hint = signed_cte_route(route, loc.x, loc.y, hint)
        exp_steer, exp_rad, _ = pure_pursuit_route(route, tf, hint)  # reference (label = teacher at distill)

        rel = os.path.join(seg, "frames", f"{step:05d}.png")
        cv2.imwrite(os.path.join(round_dir, rel), bgr)
        rows.append(dict(image=rel, weather=weather, direction=direction, step=step, steer=exp_steer,
                         steer_rad=exp_rad, nn_steer=nn_steer, cte_m=cte,
                         speed_mph=env.speed_mph(vehicle), x=loc.x, y=loc.y, yaw=tf.rotation.yaw))

        thr, brk = sc.control(vehicle)
        vehicle.apply_control(carla.VehicleControl(throttle=thr, brake=brk, steer=nn_steer))

        d0 = loc.distance(start)
        if d0 > 50:
            left = True
        if left and d0 < 12:
            break
        stalled = stalled + 1 if env.speed_mph(vehicle) < 1 else 0
        offroad = offroad + 1 if abs(cte) > 6 else 0
        if stalled >= 20 or offroad >= 15:
            print(f"    {direction}: aborted at step {step}")
            break
    return rows, summarize_cte([r["cte_m"] for r in rows])


def write_manifest(round_dir, rows):
    os.makedirs(round_dir, exist_ok=True)
    path = os.path.join(round_dir, "manifest.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--student", default="student_84x28")
    ap.add_argument("--w", type=int, default=84)
    ap.add_argument("--h", type=int, default=28)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--lr", type=float, default=5e-4,
                    help="LR for warm-start re-distill (gentle fine-tune from prior student)")
    ap.add_argument("--max-steps", type=int, default=2000)
    ap.add_argument("--weathers", default="clear",
                    help="conditions to drive/collect each round (e.g. clear,fog,night)")
    ap.add_argument("--dagger-dir", default="dagger_student",
                    help="subdir under data/ for this run's student-DAgger rounds")
    ap.add_argument("--teacher", default="steering_dagger_r02", help="teacher for re-distill labels")
    ap.add_argument("--base", default="clear", help="base BC dataset name for re-distill")
    ap.add_argument("--distill-dirs", default="dagger,dagger_student",
                    help="DAgger subdirs folded into re-distill (teacher rounds + this student dir)")
    ap.add_argument("--channels", default="8,16,16", help="conv widths (capacity lever; must match --student)")
    ap.add_argument("--fc", type=int, default=32, help="FC width (must match --student)")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    weathers = args.weathers.split(",")
    channels = tuple(int(x) for x in args.channels.split(","))
    dagger_student_dir = os.path.join(C.DATASET_DIR, args.dagger_dir)
    distill_dirs = tuple(args.distill_dirs.split(","))
    model = load_student(args.student, args.w, args.h, device, channels=channels, fc=args.fc)
    current = args.student

    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)
    vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
    camera, img_queue = env.spawn_camera(world, vehicle)

    history = []
    try:
        # Resume: rounds from earlier invocations are discovered so a long run can be
        # executed in batches without overwriting them (which would both lose their
        # frames and silently shrink the aggregated distillation set).
        _prior = sorted(glob.glob(os.path.join(dagger_student_dir, "round*", "manifest.csv")))
        _offset = (1 + max(int(os.path.basename(os.path.dirname(m))[5:]) for m in _prior)) if _prior else 0
        if _offset:
            print(f"resuming: found {len(_prior)} prior student round(s), continuing at round {_offset}",
                  flush=True)
        for r_local in range(args.rounds + 1):
            r = r_local + _offset
            round_dir = os.path.join(dagger_student_dir, f"round{r:02d}")
            print(f"\n{'#'*64}\n# student DAgger round {r} — policy '{current}'\n{'#'*64}", flush=True)
            rows, passed = [], True
            for weather in weathers:
                env.set_weather(world, weather, vehicle)   # headlights follow weather
                for d in ["eastbound", "westbound"]:
                    drows, st = drive_collect(world, vehicle, img_queue, model, device,
                                              args.w, args.h, weather, d, round_dir, args.max_steps)
                    rows += drows
                    ob = st.get("frac_over_budget", 1) * 100
                    mx = st.get("max_abs_cte_m", 0) * C.M_TO_FT
                    print(f"  [{weather}/{d}] over-budget={ob:5.1f}%  max|CTE|={mx:5.2f}ft  "
                          f"-> {'PASS' if st.get('passed') else 'FAIL'}", flush=True)
                    if not st.get("passed"):
                        passed = False
                    write_manifest(round_dir, rows)   # checkpoint per lap, not per round
            write_manifest(round_dir, rows)
            history.append((r, current, passed))
            if passed:
                print(f"\n*** student PASSED at round {r} with '{current}' ***", flush=True)
                break
            if r == args.rounds:
                print(f"\nExhausted {args.rounds} rounds (last '{current}').", flush=True)
                break
            new = f"{args.student}_dagger_r{r:02d}"
            print(f"  re-distilling (warm-start from '{current}') -> {new}", flush=True)
            distill_student(args.w, args.h, new, teacher_name=args.teacher, base=args.base,
                            dagger_dirs=distill_dirs, weathers=weathers, channels=channels, fc=args.fc,
                            init_from=current, lr=args.lr, epochs=args.epochs, quiet=True)
            model = load_student(new, args.w, args.h, device, channels=channels, fc=args.fc)
            current = new
    finally:
        env.cleanup([camera, vehicle], world, original)

    print("\n===== student DAgger summary =====")
    for r, name, passed in history:
        print(f"  round {r}: {name:28s} {'PASS' if passed else 'FAIL'}")


if __name__ == "__main__":
    main()

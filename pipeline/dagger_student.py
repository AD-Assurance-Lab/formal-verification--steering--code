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
import subprocess

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

# Sections, not a hardcoded pair (Town06 has six; Town04 has its two directions).
SPAWNS = C.SPAWNS
FIELDS = ["image", "weather", "direction", "step", "steer", "steer_rad", "nn_steer",
          "cte_m", "speed_mph", "x", "y", "yaw"]


def load_student(name, w, h, device, channels=(8, 16, 16), fc=32):
    m = StudentNet(h, w, channels=channels, fc=fc).to(device)
    m.load_state_dict(torch.load(os.path.join(C.CHECKPOINT_DIR, f"{name}.pth"),
                                 map_location=device))
    m.eval()
    return m


def drive_collect(world, vehicle, img_queue, model, device, w, h, weather, direction,
                  round_dir, max_steps, beta=0.0, collect=True, abort_on_departure=True):
    """Drive one lap, optionally recording frames.

    Ported from dagger.py, which had beta-mixing and recovery resets while this file did
    not. Trap 15: without them a weak policy departs immediately and the round collects
    almost nothing. MEASURED here at student-DAgger round 0 -- night aborted at step 32
    and step 30, so four rounds would have contributed ~120 night frames against 83,000,
    and student-DAgger could not have fixed night no matter how many rounds it ran.

    Evaluation and collection have incompatible requirements and must not share a pass
    when the policy is weak: evaluation needs pure policy control (beta=0) and an honest
    abort, collection needs the vehicle kept in a useful state distribution.
    """
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

    rows, left, stalled, offroad, n_recover = [], False, 0, 0, 0
    for step in range(max_steps):
        env.update_spectator(world, vehicle)
        frame = world.tick()
        image = env.grab_frame(img_queue, frame)
        tf = vehicle.get_transform()
        loc = tf.location
        bgr = env.raw_to_bgr(image)
        xin = torch.from_numpy(student_preprocess(bgr, w, h)).unsqueeze(0).to(device)
        with torch.no_grad():
            nn_steer = max(-1.0, min(1.0, float(model(xin).item())))
        cte, hint = signed_cte_route(route, loc.x, loc.y, hint)
        exp_steer, exp_rad, _ = pure_pursuit_route(route, tf, hint)  # reference (label = teacher at distill)

        rel = os.path.join(seg, "frames", f"{step:05d}.png")
        if collect:
            cv2.imwrite(os.path.join(round_dir, rel), bgr)
        rows.append(dict(image=rel, weather=weather, direction=direction, step=step, steer=exp_steer,
                         steer_rad=exp_rad, nn_steer=nn_steer, cte_m=cte,
                         speed_mph=env.speed_mph(vehicle), x=loc.x, y=loc.y, yaw=tf.rotation.yaw))

        # DAgger mixing: the expert assists with weight beta so the vehicle keeps
        # generating useful states. The recorded LABEL is unaffected.
        applied = (1.0 - beta) * nn_steer + beta * exp_steer
        thr, brk = sc.control(vehicle)
        env.apply_control(vehicle, carla.VehicleControl(throttle=thr, brake=brk,
                                                   steer=float(applied)))

        d0 = loc.distance(start)
        if d0 > 50:
            left = True
        if left and d0 < 12:
            break
        stalled = stalled + 1 if env.speed_mph(vehicle) < 1 else 0
        offroad = offroad + 1 if abs(cte) > 6 else 0
        if stalled >= 20 or offroad >= 15:
            if abort_on_departure:
                print(f"    {direction}: aborted at step {step}")
                break
            # collection pass: recover onto the route and keep gathering rather than
            # sitting off-road accumulating nothing
            n_recover += 1
            wp = world.get_map().get_waypoint(loc, project_to_road=True,
                                              lane_type=carla.LaneType.Driving)
            tfw = wp.transform
            tfw.location.z += 0.3
            vehicle.set_target_velocity(carla.Vector3D(0, 0, 0))
            vehicle.set_transform(tfw)
            for _ in range(6):
                env.update_spectator(world, vehicle)   # keep the view on the car
                world.tick()
            sc = env.SpeedController()
            env.warmup_to_speed(world, vehicle, img_queue, sc,
                                steer_fn=lambda v: pure_pursuit_route(route,
                                                                      v.get_transform())[0])
            stalled = offroad = 0
            hint = None
    if n_recover:
        print(f"    {direction}: {n_recover} recovery reset(s) during collection")
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
    ap.add_argument("--balance", action="store_true",
                    help="downsample near-straight frames on every re-distil; must match "
                         "the initial distillation or each round undoes it")
    ap.add_argument("--distill-dirs", default="dagger,dagger_student",
                    help="DAgger subdirs folded into re-distill (teacher rounds + this student dir)")
    ap.add_argument("--channels", default="8,16,16", help="conv widths (capacity lever; must match --student)")
    ap.add_argument("--fc", type=int, default=32, help="FC width (must match --student)")
    ap.add_argument("--beta0", type=float, default=0.0,
                    help="DAgger expert-mixing weight at round 0 (Ross et al. 2011). Raise "
                         "it when a policy departs so early that a round collects too few "
                         "frames -- measured here, night aborted at step 30 with beta=0")
    ap.add_argument("--beta-decay", type=float, default=0.5,
                    help="per-round multiplicative decay of the mixing weight")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    weathers = args.weathers.split(",")
    channels = tuple(int(x) for x in args.channels.split(","))
    dagger_student_dir = os.path.join(C.DATASET_DIR, args.dagger_dir)
    distill_dirs = tuple(args.distill_dirs.split(","))
    # Resume: rounds from earlier invocations are discovered so a long run can be
    # executed in batches without overwriting them (which would both lose their
    # frames and silently shrink the aggregated distillation set).
    _prior = sorted(glob.glob(os.path.join(dagger_student_dir, "round*", "manifest.csv")))
    _offset = (1 + max(int(os.path.basename(os.path.dirname(m))[5:]) for m in _prior)) if _prior else 0

    # RESUME MUST ADVANCE THE POLICY, NOT JUST THE ROUND COUNTER (same fix as
    # dagger.py, which measured the cost: a resume that reloads the original policy
    # re-evaluates a checkpoint already known to fail and silently discards every
    # completed round's improvement -- repeated behaviour cloning, trap 16).
    # Walk DOWN from the newest round to the highest checkpoint that actually exists;
    # an interrupted round can leave a manifest with no trained checkpoint.
    start_from = args.student
    if _prior:
        for _r in range(_offset - 1, -1, -1):
            _cand = f"{args.student}_dagger_r{_r:02d}"
            if os.path.isfile(os.path.join(C.CHECKPOINT_DIR, f"{_cand}.pth")):
                start_from = _cand
                print(f"resuming from '{start_from}', the newest policy this run "
                      f"actually trained (round {_r}); not '{args.student}'", flush=True)
                break
        else:
            print(f"WARNING: no {args.student}_dagger_r*.pth from this run; falling "
                  f"back to '{args.student}', discarding {_offset} round(s) of "
                  f"improvement", flush=True)
    model = load_student(start_from, args.w, args.h, device, channels=channels, fc=args.fc)
    current = start_from

    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)
    # Spawn INSIDE the try: an exception between enable_sync_mode and the first tick
    # would otherwise skip the finally and leave the server hung in synchronous mode
    # with no ticking client (trap 3b).
    vehicle = camera = img_queue = None
    history = []
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
        camera, img_queue = env.spawn_camera(world, vehicle)
        if _offset:
            print(f"resuming: found {len(_prior)} prior student round(s), continuing at round {_offset}",
                  flush=True)
        for r_local in range(args.rounds + 1):
            r = r_local + _offset
            # R-SIM-1: RESTART CARLA BEFORE EVERY ROUND.
            #
            # This loop drives 2 x len(weathers) times per round and retrains in between,
            # holding ONE server for the whole run. A server degrades silently under that
            # exposure -- it keeps answering and keeps reporting plausible velocities
            # while it stops advancing physics correctly. Measured here, and it voided a
            # complete six-round run: the SAME distilled checkpoint scored 3.8% / 0.0%
            # over budget on a freshly restarted server and 96.9% / 96.2% inside this
            # loop. Every round of that run reported a catastrophic failure that did not
            # exist. Nothing in the output reveals which server you were on.
            #
            # This is the same defect check_student_competence.py had before it was fixed,
            # and dagger.py's teacher loop should be looked at for the same reason.
            if r_local > 0:
                env.cleanup([camera, vehicle], world, original)
                # NEVER capture_output on a script that daemonises CARLA: the detached
                # child inherits the pipe and the call never returns.
                _rlog = os.path.join(C.REPO_ROOT, "results", "carla_restart_dagger_student.log")
                with open(_rlog, "a") as _fh:
                    subprocess.run(["bash", os.path.join(C.REPO_ROOT, "scripts", "carla_restart.sh")],
                                   stdout=_fh, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, timeout=600)
                client = env.connect()
                world = env.load_town04(client)
                original = env.enable_sync_mode(world)
                vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
                camera, img_queue = env.spawn_camera(world, vehicle)
                print(f"  [R-SIM-1] CARLA restarted before round {r}", flush=True)
            round_dir = os.path.join(dagger_student_dir, f"round{r:02d}")
            print(f"\n{'#'*64}\n# student DAgger round {r} — policy '{current}'\n{'#'*64}", flush=True)
            rows, passed = [], True
            beta = max(0.0, args.beta0 * (args.beta_decay ** r))
            for weather in weathers:
                # set_condition, NOT set_weather: exposure is declared per condition and
                # is a blueprint attribute, so the camera must be respawned. Using
                # set_weather captured every condition through the PREVIOUS condition's
                # exposure -- night through the daylight setting, silently.
                camera, img_queue = env.set_condition(world, vehicle, weather, camera)
                for d in C.SECTIONS:
                    if beta <= 0.0:
                        drows, st = drive_collect(world, vehicle, img_queue, model, device,
                                                  args.w, args.h, weather, d, round_dir,
                                                  min(args.max_steps, C.steps_for(d)), beta=0.0, collect=True,
                                                  abort_on_departure=True)
                    else:
                        # evaluate honestly under pure policy control, then collect with
                        # expert assistance so a weak policy still yields a full lap
                        _, st = drive_collect(world, vehicle, img_queue, model, device,
                                              args.w, args.h, weather, d, round_dir,
                                              min(args.max_steps, C.steps_for(d)), beta=0.0, collect=False,
                                              abort_on_departure=True)
                        drows, _ = drive_collect(world, vehicle, img_queue, model, device,
                                                 args.w, args.h, weather, d, round_dir,
                                                 min(args.max_steps, C.steps_for(d)), beta=beta, collect=True,
                                                 abort_on_departure=False)
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
                            init_from=current, lr=args.lr, epochs=args.epochs, quiet=True, balance=args.balance)
            model = load_student(new, args.w, args.h, device, channels=channels, fc=args.fc)
            current = new
    finally:
        env.cleanup([camera, vehicle], world, original)

    print("\n===== student DAgger summary =====")
    for r, name, passed in history:
        print(f"  round {r}: {name:28s} {'PASS' if passed else 'FAIL'}")


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

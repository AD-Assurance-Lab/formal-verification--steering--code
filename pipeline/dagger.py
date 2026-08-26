#!/usr/bin/env python3
"""
DAgger (Ross et al., 2011) for the steering policy.

Each round: the CURRENT policy drives the full loop both directions; EVERY frame
it visits is labeled with the route pure-pursuit recovery action (steer back to
the intended centerline) and saved. That aggregated data is added to the training
set and the model is retrained from scratch. The off-center states the policy
wanders into ARE the recovery data — no autopilot hand-over, no PID oscillations.

The same drive both (a) evaluates the current policy (route-based CTE) and
(b) collects the next round's data. Stops when the driven policy meets budget.

    python dagger.py --init steering_bc_baseline --rounds 6
"""
import os
import sys
import glob
import csv
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2  # noqa: E402
import torch  # noqa: E402
import carla  # noqa: E402

import config as C  # noqa: E402
import carla_env as env  # noqa: E402
from imaging import preprocess_for_model  # noqa: E402
from route import load_route, signed_cte_route, pure_pursuit_route  # noqa: E402
from metrics import summarize_cte  # noqa: E402
from model import CarlaSteeringNet  # noqa: E402
from train import train_model  # noqa: E402

# Sections, not a hardcoded pair (Town06 has six; Town04 has its two directions).
SPAWNS = C.SPAWNS
FIELDS = ["image", "weather", "direction", "step", "steer", "steer_rad", "nn_steer",
          "cte_m", "speed_mph", "x", "y", "yaw"]


def load_model(name, device):
    m = CarlaSteeringNet().to(device)
    m.load_state_dict(torch.load(os.path.join(C.CHECKPOINT_DIR, f"{name}.pth"),
                                 map_location=device))
    m.eval()
    return m


def drive_collect(world, vehicle, img_queue, model, device, weather, direction,
                  round_dir, max_steps, beta=0.0, collect=True, abort_on_departure=True):
    """Drive one lap, optionally recording expert-labelled frames.

    Two jobs that must NOT share a pass:

    * EVALUATION needs pure policy control (beta=0) and must abort on departure, so the
      pass/fail verdict is honest.
    * COLLECTION needs the vehicle to stay in a useful state distribution. With pure
      policy control an early-round policy leaves the road within seconds and yields a
      few dozen frames, which is far too little to learn recovery from.

    DAgger (Ross et al. 2011) handles this with a mixing schedule,
    pi_i = beta*pi_expert + (1-beta)*pi_policy, with beta decaying over rounds. The
    LABEL is always the pure-pursuit recovery action regardless of beta, so the data
    still teaches recovery; beta only controls how far the vehicle is allowed to stray
    while generating it.
    """
    route = load_route(direction)
    hint = None
    speed_ctrl = env.SpeedController()
    env.teleport(vehicle, SPAWNS[direction])
    # warm up on-center with the expert, then hand control to the policy
    env.warmup_to_speed(
        world, vehicle, img_queue, speed_ctrl,
        steer_fn=lambda veh: pure_pursuit_route(route, veh.get_transform())[0],
    )
    seg = os.path.join(weather, direction)
    frames_dir = os.path.join(round_dir, seg, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    start = carla.Location(x=SPAWNS[direction]["x"], y=SPAWNS[direction]["y"],
                           z=SPAWNS[direction]["z"])

    rows, left, stalled, offroad, n_recover = [], False, 0, 0, 0
    for step in range(max_steps):
        env.update_spectator(world, vehicle)
        frame = world.tick()
        image = env.grab_frame(img_queue, frame)
        tf = vehicle.get_transform()
        loc = tf.location

        bgr = env.raw_to_bgr(image)
        xin = torch.from_numpy(preprocess_for_model(bgr)).unsqueeze(0).to(device)
        with torch.no_grad():
            nn_steer = max(-1.0, min(1.0, float(model(xin).item())))

        cte, hint = signed_cte_route(route, loc.x, loc.y, hint)
        exp_steer, exp_rad, _ = pure_pursuit_route(route, tf, hint)   # LABEL

        rel = os.path.join(seg, "frames", f"{step:05d}.png")
        if collect:
            cv2.imwrite(os.path.join(round_dir, rel), bgr)
        rows.append(dict(
            image=rel, weather=weather, direction=direction, step=step,
            steer=exp_steer, steer_rad=exp_rad, nn_steer=nn_steer,
            cte_m=cte, speed_mph=env.speed_mph(vehicle), x=loc.x, y=loc.y, yaw=tf.rotation.yaw,
        ))

        # DAgger mixing: expert assists with weight beta so the vehicle keeps generating
        # useful states; the recorded LABEL is always the pure expert action.
        applied = (1.0 - beta) * nn_steer + beta * exp_steer
        thr, brk = speed_ctrl.control(vehicle)
        vehicle.apply_control(carla.VehicleControl(throttle=thr, brake=brk,
                                                   steer=float(applied)))

        d0 = loc.distance(start)
        if d0 > 50.0:
            left = True
        if left and d0 < 12.0:
            break
        stalled = stalled + 1 if env.speed_mph(vehicle) < 1.0 else 0
        offroad = offroad + 1 if abs(cte) > 6.0 else 0
        if stalled >= 20 or offroad >= 15:
            if abort_on_departure:
                print(f"    {direction}: aborted at step {step} (stall/offroad)")
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
            speed_ctrl = env.SpeedController()
            env.warmup_to_speed(world, vehicle, img_queue, speed_ctrl,
                                steer_fn=lambda veh: pure_pursuit_route(route,
                                                                        veh.get_transform())[0])
            stalled = offroad = 0
            hint = None
    if n_recover:
        print(f"    {direction}: {n_recover} recovery reset(s) during collection")
    return rows, summarize_cte([r["cte_m"] for r in rows])


def write_manifest(round_dir, rows):
    """Write (or rewrite) a round's manifest.

    Called after EVERY lap, not only at the end of a round. A round drives eight laps
    over roughly twenty minutes, and writing the manifest only at the end means any
    interruption discards every frame collected, since the resume logic keys on the
    manifest's existence. Rewriting incrementally makes a partial round salvageable and
    costs nothing measurable next to the driving.
    """
    os.makedirs(round_dir, exist_ok=True)
    path = os.path.join(round_dir, "manifest.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="clear",
                    help="base BC dataset name(s), COMMA-SEPARATED. A mixed-condition "
                         "run needs every base set it was collected into, e.g. "
                         "--base clear,mixed")
    ap.add_argument("--init", default="steering_bc_baseline", help="initial policy checkpoint")
    ap.add_argument("--rounds", type=int, default=6, help="max DAgger retrains")
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--lr", type=float, default=5e-4,
                    help="LR for warm-start retrains (gentle fine-tune from prior round)")
    ap.add_argument("--max-steps", type=int, default=2500)
    ap.add_argument("--out-prefix", default="steering_dagger")
    ap.add_argument("--weathers", default="clear",
                    help="comma-separated weather presets to drive/collect each round")
    ap.add_argument("--margin-frac", type=float, default=1.0,
                    help="a direction counts as passing only if max|CTE| stays below "
                         "margin-frac * CTE budget. Default 1.0 = the plain budget. Use "
                         "<1 to demand real margin: closed-loop CTE varies run to run on "
                         "marginal policies (teacher westbound spans 1.38-2.37 ft against "
                         "a 2.19 ft budget), so a single-run gate can stop on a lucky pass.")
    ap.add_argument("--beta0", type=float, default=0.0,
                    help="DAgger expert-mixing weight at round 0 (Ross et al. 2011). Default 0 "
                         "reproduces v1, which converged with these presets. Raise it if a "
                         "policy departs so early that a round collects too few frames.")
    ap.add_argument("--beta-decay", type=float, default=0.5,
                    help="per-round multiplicative decay of the mixing weight")
    ap.add_argument("--dagger-dir", default="dagger",
                    help="subdir under data/ for this run's rounds (use a distinct name "
                         "per model, e.g. dagger_mixed, so rounds don't collide)")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    weathers = args.weathers.split(",")
    dagger_dir = os.path.join(C.DATASET_DIR, args.dagger_dir)
    # DAgger aggregates: every prior round's data must stay in the training set. Rounds
    # from EARLIER INVOCATIONS are discovered here, so a long run can be executed in
    # batches without silently discarding what it already collected (which would quietly
    # turn DAgger back into repeated behaviour cloning).
    # `--base` takes a COMMA-SEPARATED list. It was a single name, which silently
    # dropped every base dataset but one: a mixed-condition run started from
    # `--base clear` would retrain on the clear base plus DAgger rounds and discard the
    # 20,348 fog/night/shadows frames, producing something called a mixed teacher that
    # had barely seen the conditions. Same shape as trap 18.
    base_names = [b.strip() for b in args.base.split(",") if b.strip()]
    manifests = [os.path.join(C.DATASET_DIR, b, "manifest.csv") for b in base_names]
    missing = [m for m in manifests if not os.path.exists(m)]
    if missing:
        raise SystemExit("missing base manifest(s): " + ", ".join(missing))
    print(f"base datasets: {base_names}")
    prior_rounds = sorted(glob.glob(os.path.join(dagger_dir, "round*", "manifest.csv")))
    manifests += prior_rounds
    round_offset = 0
    if prior_rounds:
        round_offset = 1 + max(int(os.path.basename(os.path.dirname(m))[5:])
                               for m in prior_rounds)
        print(f"resuming: found {len(prior_rounds)} prior DAgger round(s) in "
              f"{args.dagger_dir}, continuing at round {round_offset}")
    # RESUME MUST ADVANCE THE POLICY, NOT JUST THE ROUND COUNTER.
    #
    # This loaded `args.init` unconditionally, so resuming a run re-evaluated the ORIGINAL
    # policy at the resumed round number while aggregating all the prior rounds' data.
    # Measured: a resume at round 4 evaluated teacher_mixed_bc and scored 42.19 ft, having
    # already reached 3.15 ft at round 3 -- four rounds of policy improvement silently
    # discarded, and a full 8-lap round spent re-measuring a policy already known to fail.
    # It also drops the warm start that multi-condition DAgger needs (trap 14).
    # Derive the policy from THIS run's completed rounds, never from "whatever checkpoint
    # sorts last". Checkpoints from an earlier, superseded run can still be on disk --
    # r04 and r05 from a pre-recollection run were sitting there while this run had only
    # reached r03 -- and picking the highest-numbered file would silently resume from a
    # policy trained on retired data. That is trap 18 wearing a different hat.
    start_from = args.init
    if prior_rounds:
        # Walk DOWN from the most recent round to the highest checkpoint that actually
        # exists. A round can leave data on disk without a trained checkpoint -- an
        # interrupted round writes its per-lap manifest but never reaches the retrain --
        # so requiring an exact match drops all the way back to the initial policy and
        # silently discards every round of improvement.
        for r in range(round_offset - 1, -1, -1):
            cand = f"{args.out_prefix}_r{r:02d}"
            if os.path.isfile(os.path.join(C.CHECKPOINT_DIR, f"{cand}.pth")):
                start_from = cand
                print(f"resuming from '{start_from}', the newest policy this run "
                      f"actually trained (round {r}); not '{args.init}'")
                break
        else:
            print(f"WARNING: no {args.out_prefix}_r*.pth from this run; falling back to "
                  f"'{args.init}', discarding {round_offset} rounds of improvement")
    model = load_model(start_from, device)
    current = start_from

    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)
    # Spawn INSIDE the try: a failure here would otherwise skip the finally and leave
    # the server hung in synchronous mode with no ticking client (trap 3b).
    vehicle = camera = img_queue = None
    history = []
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
        camera, img_queue = env.spawn_camera(world, vehicle)
        for r_local in range(args.rounds + 1):
            r = r_local + round_offset
            round_dir = os.path.join(dagger_dir, f"round{r:02d}")
            print(f"\n{'#'*64}\n# DAgger round {r} — evaluating policy '{current}'\n{'#'*64}")
            # beta decays over rounds: heavy expert assistance early (when the policy
            # cannot hold the road and would otherwise yield a few dozen frames), none
            # by the end, so late rounds train on the policy's own state distribution.
            beta = max(0.0, args.beta0 * (args.beta_decay ** r))
            rows, passed = [], True
            for weather in weathers:
                camera, img_queue = env.set_condition(world, vehicle, weather, camera)
                for d in C.SECTIONS:
                    if beta <= 0.0:
                        # v1 behaviour, which demonstrably converged with these presets:
                        # ONE pass that both evaluates (pure policy, honest abort) and
                        # collects. Adequate here because the policy drives ~420 steps
                        # before departing, so a round still gathers thousands of frames.
                        drows, st = drive_collect(world, vehicle, img_queue, model, device,
                                                  weather, d, round_dir, min(args.max_steps, C.steps_for(d)),
                                                  beta=0.0, collect=True,
                                                  abort_on_departure=True)
                        rows += drows
                    else:
                        # beta > 0: evaluation and collection cannot share a pass, since
                        # one needs pure policy control and the other needs the vehicle
                        # kept in a useful state distribution.
                        _, st = drive_collect(world, vehicle, img_queue, model, device,
                                              weather, d, round_dir, min(args.max_steps, C.steps_for(d)),
                                              beta=0.0, collect=False,
                                              abort_on_departure=True)
                        drows, _ = drive_collect(world, vehicle, img_queue, model, device,
                                                 weather, d, round_dir, min(args.max_steps, C.steps_for(d)),
                                                 beta=beta, collect=True,
                                                 abort_on_departure=False)
                        rows += drows
                    ob = st.get("frac_over_budget", 1) * 100
                    mx = st.get("max_abs_cte_m", 0) * C.M_TO_FT
                    budget_ft = C.CTE_BUDGET_M * C.M_TO_FT
                    ok = bool(st.get("passed")) and mx <= args.margin_frac * budget_ft
                    print(f"  [{weather}/{d}] over-budget={ob:5.1f}%  max|CTE|={mx:5.2f}ft  "
                          f"(gate {args.margin_frac*budget_ft:.2f}ft) -> {'PASS' if ok else 'FAIL'}")
                    if not ok:
                        passed = False
                    write_manifest(round_dir, rows)   # checkpoint after every lap
            print(f"  collected {len(rows)} frames at beta={beta:.2f}")
            mpath = write_manifest(round_dir, rows)
            history.append((r, current, passed))

            if passed:
                print(f"\n*** PASSED at round {r} with policy '{current}' ***")
                break
            if r == args.rounds:
                print(f"\nExhausted {args.rounds} rounds without passing "
                      f"(last policy '{current}').")
                break

            manifests.append(mpath)
            new = f"{args.out_prefix}_r{r:02d}"
            print(f"  aggregating {len(manifests)} manifests, warm-start from '{current}' -> {new}")
            train_model(manifests, new, epochs=args.epochs, balance=True, quiet=True,
                        weathers=weathers, init_from=current, lr=args.lr)
            model = load_model(new, device)
            current = new
    finally:
        env.cleanup([camera, vehicle], world, original)

    print("\n===== DAgger summary =====")
    for r, name, passed in history:
        print(f"  round {r}: {name:24s} {'PASS' if passed else 'FAIL'}")


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

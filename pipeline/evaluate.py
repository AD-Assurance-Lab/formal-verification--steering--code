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
from pathlib import Path
import csv
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch  # noqa: E402

from gpu import require_cuda  # noqa: E402
import numpy as np
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
from route import lap_finished, arc_lengths  # noqa: E402

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

    # STOP AT THE SECTION'S END, MEASURED ALONG THE ROUTE.
    #
    # steps_for() caps STEPS, computed as length / (TARGET_SPEED * dt). That bounds
    # distance only if the vehicle holds target speed exactly. It runs slightly hot, so
    # runs overshot: fog failures on s02 peaked at 639 m and 634 m of a 628 m section,
    # 101-102% through, and night peaked at 94-101% on four sections. Past the boundary
    # the car is in the unclean road the section was CLIPPED TO EXCLUDE, and the
    # excursion it finds there was being recorded as that section's max |CTE|.
    #
    # steps_for's own docstring already names this failure mode -- "it fails there for
    # reasons that have nothing to do with the policy" -- and fixes it with a step cap.
    # A step cap is the wrong instrument for a distance bound. This is the right one.
    # route.arc_lengths takes x and y ONLY. This computed the norm over the whole route
    # array, and the Town06 lap's third column is yaw in DEGREES -- so seg_len averaged
    # 4.62 "m" per index instead of 2.00, travelled_m accrued 2.3x too fast, and the
    # scored-distance cap below stopped every run at 1,006 m of a 2,289 m lap. The
    # vehicle was on the road at 20 mph with 0.5 ft of CTE when the run ended, and the
    # competence gate read the truncated drive as a PASS.
    arc = arc_lengths(route)
    seg_len = np.diff(arc)
    scored_m = C.SECTION_LEN_M.get(direction) if getattr(C, "SECTION_BASED", False) else None

    prev_hint, travelled_m = None, 0.0
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

        # ── ODD BOUNDARY: pure pursuit bridges the intersections ────────────────
        #
        # The policy is a lane-follower. Through Town06's signalised intersections there
        # are no lane markings, so it has no input signal and its output there is not
        # wrong so much as undefined. The expert drives those spans and NOTHING in them is
        # scored -- which is what a real ADAS does at an ODD boundary, and it keeps the lap
        # one continuous drive instead of six teleports.
        #
        # A bridge is also not merely the geometric gap: it starts where the markings
        # leave the CAMERA's view, which is why these spans are ~85 m wide against the
        # map's 17-38 m junctions. Those boundaries were set by driving the route and
        # looking, not by the map's is_junction flag, which over-reports them 3x.
        in_bridge = False
        if getattr(C, "LAP_BASED", False) and hint is not None:
            here_m = hint * float(C.LAP_META.get("step_m", 2.0))
            in_bridge = any(a <= here_m <= b for a, b in C.BRIDGE_SPANS)

        # STOP AT THE END OF AN OPEN ROUTE, BEFORE RECORDING THIS STEP.
        #
        # The distance cap above bounds this by SECTION_LEN_M, which on the lap is the
        # route's geometry -- so it stops at roughly the right place rather than exactly
        # the right one, and "roughly" is what gate_teacher_lap.py measured as max|CTE|
        # 75 ft from a measurement running off the end of its own reference.
        if lap_finished(route, hint):
            break

        drive_steer = exp_steer if in_bridge else nn_steer
        thr, brk = speed_ctrl.control(vehicle)
        env.apply_control(vehicle, carla.VehicleControl(throttle=thr, brake=brk,
                                                        steer=drive_steer))

        records.append(dict(
            step=step, time_sec=round(step * C.FIXED_DT, 2),
            nn_steer=nn_steer, expert_steer=exp_steer,
            bridged=in_bridge,
            cte_m=cte, cte_ft=(cte * C.M_TO_FT if cte is not None else None),
            speed_mph=env.speed_mph(vehicle), x=loc.x, y=loc.y, yaw=tf.rotation.yaw,
        ))

        # PROGRESS ALONG THE ROUTE, accumulated from UNWRAPPED index deltas.
        #
        # Two earlier attempts at this were wrong and both failed the same way -- the run
        # stopped after a handful of steps and reported a tiny |CTE| as a PASS:
        #   1. comparing ABSOLUTE arc position assumed every spawn sits at route index 0;
        #   2. subtracting a start offset then "correcting" a negative result by one lap
        #      turned a one-index backward wobble near the seam into a full lap of credit.
        # Accumulating per-step deltas, each unwrapped to the shorter way round, is immune
        # to both: a wobble contributes its own small negative and cancels itself.
        if scored_m is not None and hint is not None:
            if prev_hint is not None:
                d_idx = hint - prev_hint
                if d_idx > len(route) // 2:
                    d_idx -= len(route)
                elif d_idx < -len(route) // 2:
                    d_idx += len(route)
                travelled_m += d_idx * float(np.mean(seg_len))
            prev_hint = hint
            if travelled_m >= scored_m:
                print(f"  reached the section's scored end ({scored_m:.0f} m) at step {step}")
                break

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

    # SCORE ONLY THE POLICY'S ROAD.
    #
    # Steps driven by pure pursuit across an intersection are outside the ODD and outside
    # the certificate, so including them would score the expert and compare a verdict
    # against road the certificate never covered. That mismatch -- drives covering more
    # than verification -- is exactly what made half of Town04's ledger runs take their
    # worst |CTE| beyond the scored prefix.
    scored_records = [r for r in records if not r.get("bridged")]
    n_bridged = len(records) - len(scored_records)
    if n_bridged:
        print(f"  {n_bridged} of {len(records)} steps were PPC-bridged and are NOT scored")
    stats = summarize_cte([r["cte_m"] for r in scored_records])
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
                    # "shadows" stays accepted: Town04's frozen artifacts and its
                    # drivers name it that, and canonical_condition maps it through.
                    choices=["clear", "fog", "rain", "night", "low_sun", "shadows"],
                    help="rendered CARLA condition; night switches the ego headlights on")
    args = ap.parse_args()

    device = require_cuda()
    model = load_model(args.model, device, student=args.student,
                       channels=tuple(int(v) for v in args.channels.split(",")),
                       fc=args.fc, h=args.in_h, w=args.in_w)

    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)

    # DETERMINISM PREFLIGHT (Town06 only). The launch flags that matter most -- texture
    # streaming and quality level -- are invisible over RPC, so a server someone started
    # by hand looks completely normal and quietly produces noisier results. This reads
    # the server's real command line and refuses rather than warns.
    #
    # Town04 is excluded deliberately: it is the published artifact and must keep
    # reproducing exactly until its own re-measurement is authorised.
    if C.STUDY_MAP == "Town06":
        import carla_determinism as cd  # noqa: E402
        cd.require_deterministic(C.PORT, world, fixed_dt=C.FIXED_DT,
                                 deterministic_control=C.DETERMINISTIC_CONTROL)

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
        # Confirm from a RENDERED FRAME that the requested condition is what is actually
        # being drawn. set_condition already reads the weather struct back, but the
        # struct is what we asked for, not what the camera sees -- exposure, headlights
        # and the sensor all sit between them. One frame, and it costs a few ticks.
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
        from condition_signature import assert_condition, identify  # noqa: E402
        for _ in range(6):
            f_ = world.tick()
        _img = env.grab_frame(img_queue, f_)
        # R-SIM-4: confirm from a RENDERED FRAME that the requested condition is what is
        # actually drawn. This is the Town04 fog-into-night failure and it stays ON for
        # every normal run.
        #
        # It is SKIPPED, and only skipped, when a disturbance override is deliberately
        # in force. An override renders an INTERMEDIATE point of the disturbance family
        # -- fog at density 17.5, say -- which by construction is not the preset, so
        # `identify` will not call it 'fog' and the assert would abort a run that is
        # doing exactly what was asked. The signature is still measured and printed, so
        # the rendered condition is on the record rather than merely unchecked.
        _sig_frame = student_preprocess(env.raw_to_bgr(_img), 168, 28)
        _ovr = {k: os.environ[k] for k in
                ("FOG_DENSITY_OVERRIDE", "SUN_ALTITUDE_OVERRIDE", "SUN_AZIMUTH_OVERRIDE",
                 "EXPOSURE_SHUTTER_OVERRIDE") if os.environ.get(k)}
        if _ovr:
            _got, _st = identify(_sig_frame)
            print(f"  OVERRIDE ACTIVE {_ovr}: preset assert skipped by design. "
                  f"Rendered signature: looks like '{_got}' "
                  f"(mean={_st['mean']:.4f} sigma={_st['sigma']:.4f} p01={_st['p01']:.4f})")
            # The signature was printed and NOT checked, and that cost a whole sweep
            # (T06-F35): sun altitude was swept with --weather night, so the DECLARED
            # EXPOSURE was night's shutter 200 against daylight's 800, and daylight
            # scenes were rendered through a night camera. Every run completed, every
            # CTE was plausible, every step count was normal, and the signature line
            # said 'clear' on a run labelled 'shadows' -- printed, and ignored.
            #
            # An override legitimately moves the condition off its preset, so this
            # cannot assert. But a signature that has crossed into a DIFFERENT named
            # condition is worth shouting about, because the usual cause is that the
            # exposure belongs to the wrong condition rather than that the override
            # went far enough to change the condition's character.
            if _got != args.weather:
                print(f"  *** WARNING: the rendered frame classifies as '{_got}' but this "
                      f"run is labelled '{args.weather}'. Check that --weather names the "
                      f"condition whose EXPOSURE you intend: exposure is per-condition "
                      f"(clear/fog/low-sun shutter "
                      f"{C.exposure_for('clear')['shutter']:.0f}, night "
                      f"{C.exposure_for('night')['shutter']:.0f}), so the wrong one "
                      f"silently rescales every frame. See T06-F35.")
        else:
            assert_condition(_sig_frame, args.weather)
        for d in dirs:
            recs = drive_nn(world, world_map, vehicle, img_queue, model, device, d, min(args.max_steps, C.steps_for(d)))
            results[d] = save_and_report(args.model, d, recs)
    finally:
        env.cleanup([camera, vehicle], world, original)

    print("\n" + "=" * 60)
    for d, s in results.items():
        # steps= belongs on the SUMMARY line too, not only the progress line: callers
        # parse this one, and R-SIM-6 says a run that ends far short of steps_for is void
        # rather than a pass. Without the step count they cannot tell.
        print(f"{d:10s}: {'PASS' if s.get('passed') else 'FAIL'} "
              f"steps={s.get('n', 0)} "
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

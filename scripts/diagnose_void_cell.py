#!/usr/bin/env python3
"""Why do three laps of one cell disagree? Measure the INITIAL CONDITION each run starts from.

    STUDY_MAP=Town06 python3 scripts/diagnose_void_cell.py \
        --checkpoint S_mixed_t06lap_168x56_w4_s3 --channels 32,64,64 --fc 128 \
        --weather fog --reps 4 --steps 60

PROTOCOL A-4: "if the three laps disagree, that is a BUG until proven otherwise, and more
laps are never the response ... a cell whose laps disagree is VOID, not uncertain, and it
stays void until the cause is found and written down."

fog/S_mixed_t06 is that cell:

    lap0  0.406 m  PASS        lap2  0.449 m  PASS
    lap1  1.601 m  FAIL        budget 0.668 m

Its provenance is identical across the three runs -- same weather struct, same determinism
config, same git SHA, same substepping, a clean server and the photometry gate green before
each. And laps 1 and 2 take their worst CTE at the SAME PLACE, step 23-26, about 45 m in,
where one reaches 1.60 m and the other 0.45 m.

A disagreement concentrated in the first thirty steps is not the D-7 render residual, which
needs hundreds of steps to grow. It points at what the scored run STARTS from:
`warmup_to_speed` accelerates and breaks the moment speed >= 0.98 * target, so the number
of warmup ticks -- and therefore the pose and speed at scored step 0 -- is not fixed.

This measures that directly: same checkpoint, same condition, a clean server per rep, and
it records the pose and speed the scored run begins at plus the early CTE trace. If the
start states differ and the early peak tracks them, the cause is the initial condition and
not the policy.

Writes nothing the study consumes. It is a diagnostic.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
os.environ.setdefault("CARLA_PORT", "3000")
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "scripts"))

import carla  # noqa: E402
import carla_determinism as cd  # noqa: E402
import carla_env as env  # noqa: E402
import config as C  # noqa: E402
import torch  # noqa: E402
from student import StudentNet, student_preprocess  # noqa: E402
from route import load_route, signed_cte_route, pure_pursuit_route  # noqa: E402


def one_run(ckpt, channels, fc, weather, steps):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = StudentNet(C.TOWN06_INPUT_H, C.TOWN06_INPUT_W, channels=channels, fc=fc).to(dev)
    net.load_state_dict(torch.load(Path(C.CHECKPOINT_DIR) / f"{ckpt}.pth",
                                   map_location=dev, weights_only=True))
    net.eval()

    client = cd.bind_client(carla.Client("127.0.0.1", C.PORT))
    client.set_timeout(120.0)
    world = env.load_study_map(client)
    original = world.get_settings()
    env.enable_sync_mode(world)
    route = load_route(C.SECTIONS[0])
    veh = cam = None
    try:
        veh = env.spawn_vehicle(world, C.SPAWNS[C.SECTIONS[0]])
        cam, q = env.set_condition(world, veh, weather)
        speed = env.SpeedController()
        env.warmup_to_speed(
            world, veh, q, speed,
            steer_fn=lambda v: pure_pursuit_route(route, v.get_transform())[0])
        tf = veh.get_transform()
        start = dict(x=float(tf.location.x), y=float(tf.location.y),
                     yaw=float(tf.rotation.yaw), speed_ms=float(env.speed_ms(veh)))
        hint, trace = None, []
        for i in range(steps):
            env.update_spectator(world, veh)
            frame = world.tick()
            image = env.grab_frame(q, frame)
            tf = veh.get_transform(); loc = tf.location
            x = torch.from_numpy(student_preprocess(env.raw_to_bgr(image),
                                                    C.TOWN06_INPUT_W, C.TOWN06_INPUT_H)
                                 ).unsqueeze(0).to(dev)
            with torch.no_grad():
                steer = max(-1.0, min(1.0, float(net(x).item())))
            cte, hint = signed_cte_route(route, loc.x, loc.y, hint)
            trace.append(float(cte) if cte is not None else float("nan"))
            thr, brk = speed.control(veh)
            env.apply_control(veh, carla.VehicleControl(throttle=thr, brake=brk, steer=steer))
        return start, trace
    finally:
        try:
            if cam: cam.destroy()
            if veh: veh.destroy()
        except Exception:
            pass
        world.apply_settings(original)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--channels", required=True)
    ap.add_argument("--fc", type=int, required=True)
    ap.add_argument("--weather", default="fog")
    # ONE REP PER PROCESS. Restarting CARLA in-process between reps dies with
    # "terminate called after throwing carla::client::TimeoutException" at teardown -- the
    # same crash the ledger, the teacher gate and both DAgger drivers all moved to a
    # process boundary to escape. The caller loops; this drives exactly one rep and appends.
    ap.add_argument("--rep", type=int, required=True)
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--out", default="results/town06/void_cell_diagnosis.json")
    args = ap.parse_args()
    ch = tuple(int(c) for c in args.channels.split(","))

    out = REPO / args.out
    runs = []
    if out.exists():
        runs = json.loads(out.read_text()).get("runs", [])
    runs = [r for r in runs if r.get("rep") != args.rep]

    start, trace = one_run(args.checkpoint, ch, args.fc, args.weather, args.steps)
    peak = float(np.nanmax(np.abs(trace)))
    runs.append(dict(rep=args.rep, start=start, peak_abs_cte_m=peak,
                     peak_step=int(np.nanargmax(np.abs(trace))), trace=trace))
    runs.sort(key=lambda r: r["rep"])
    print(f"  rep{args.rep}: start x={start['x']:.3f} y={start['y']:.3f} "
          f"yaw={start['yaw']:.3f} v={start['speed_ms']:.4f} m/s  ->  "
          f"peak |CTE| {peak:.3f} m at step {runs[-1]['peak_step']}", flush=True)

    xs = np.array([r["start"]["x"] for r in runs])
    ys = np.array([r["start"]["y"] for r in runs])
    vs = np.array([r["start"]["speed_ms"] for r in runs])
    pk = np.array([r["peak_abs_cte_m"] for r in runs])
    print(f"\n  start-pose spread : x {xs.max()-xs.min():.3f} m, y {ys.max()-ys.min():.3f} m")
    print(f"  start-speed spread: {vs.max()-vs.min():.4f} m/s")
    print(f"  peak |CTE| spread : {pk.min():.3f} .. {pk.max():.3f} m "
          f"(budget {C.CTE_BUDGET_M:.3f})")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(checkpoint=args.checkpoint, weather=args.weather,
                                   budget_m=C.CTE_BUDGET_M, runs=runs), indent=2))
    print(f"  -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

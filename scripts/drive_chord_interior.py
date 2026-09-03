#!/usr/bin/env python3
"""Drive INTERIOR points of the certificate's OWN family, in image space.

    STUDY_MAP=Town06 python3 scripts/drive_chord_interior.py \
        --checkpoint S_mixed_t06lap_168x56_w4_s3 --channels 32,64,64 --fc 128 \
        --condition night --s 0.25 0.5 0.75

WHY THIS AND NOT A SUN-ALTITUDE SWEEP.

certify_town06.py bounds the frozen family of PROTOCOL section 3:

    x(s) = x_clear + s * (x_cond - x_clear),  s in [0, 1]

built from two REAL captured frames at the SAME pose -- the clear capture and the
condition capture. It is a straight line in image space, and alpha-CROWN covers every
point of it at once. So "is the interior safe?" is a question about that line.

Re-rendering an intermediate in CARLA does NOT ask that question. Sweeping sun altitude
from 90 to -25 changes three things the chord does not: it introduces DIRECTIONAL SHADOWS
in the 20-45 degree band (T06-F35: a different disturbance class, out of scope), it
crosses the daylight/night exposure switch where interior points have no declared camera
(T06-F51: at 0 degrees with daylight exposure 98.5% of the frame is below 0.05, so the
policy drives blind), and T06-F34 measured that the chord and the physically rendered
condition are not the same image anyway.

This applies the certificate's own perturbation to the LIVE frame while driving in clear
weather:

    live_input(s) = live_clear_input + s * (captured_cond[k] - captured_clear[k])

where k is the captured pose nearest the vehicle. The difference term is the MEASURED
night-minus-clear (or fog-minus-clear) direction at that place on the road, so it carries
no shadows, needs no exposure decision, and is the same vector the bound is computed over.

The approximation, stated plainly: the live clear frame is not the captured clear frame,
because the vehicle is never at exactly the captured pose. The chord DIRECTION is taken
from the nearest capture and applied to what the camera actually sees. That is a
first-order stand-in for the family, not the family itself, and it is the closest a
closed-loop drive can get to what the certificate quantifies over.

Not a scored cell: writes to results/town06/chord_interior/ and nothing else reads it.
"""
import argparse
import json
import os
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
from route import (load_route, signed_cte_route, pure_pursuit_route,  # noqa: E402
                   lap_finished)


def load_chord(condition):
    """(pose_xy, delta) where delta[k] = captured_cond[k] - captured_clear[k]."""
    caps = REPO / "results" / "town06" / "captures"
    sec = C.SECTIONS[0]
    zc = np.load(caps / f"lap_{sec}_clear.npz", allow_pickle=True)
    zd = np.load(caps / f"lap_{sec}_{condition}.npz", allow_pickle=True)

    def nominal(z, cond):
        conds = [str(c) for c in z["conds"]]
        fr = z["frames"][conds.index(cond)]
        oi = int(np.argmin(np.abs(z["offsets"])))
        yi = int(np.argmin(np.abs(z["yaws"])))
        return fr[:, oi, yi]

    clr = nominal(zc, "clear").astype(np.float32)
    dis = nominal(zd, condition).astype(np.float32)
    if clr.shape != dis.shape:
        sys.exit(f"capture shape mismatch: {clr.shape} vs {dis.shape}")
    xy = np.stack([np.asarray(zc["pose_x"], float), np.asarray(zc["pose_y"], float)], 1)
    return xy, (dis - clr)


def drive(ckpt, channels, fc, s, xy, delta, max_steps):
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
        # CLEAR weather and the clear camera: the disturbance is applied to the image,
        # so the simulator must render the s = 0 anchor and nothing else.
        cam, q = env.set_condition(world, veh, "clear")
        speed = env.SpeedController()
        env.warmup_to_speed(
            world, veh, q, speed,
            steer_fn=lambda v: pure_pursuit_route(route, v.get_transform())[0])

        hint, ctes, bridged = None, [], 0
        n_route = len(route)
        for step in range(max_steps):
            env.update_spectator(world, veh)
            frame = world.tick()
            image = env.grab_frame(q, frame)
            tf = veh.get_transform(); loc = tf.location

            x = student_preprocess(env.raw_to_bgr(image),
                                   C.TOWN06_INPUT_W, C.TOWN06_INPUT_H)
            k = int(np.argmin((xy[:, 0] - loc.x) ** 2 + (xy[:, 1] - loc.y) ** 2))
            xin = np.clip(x + s * delta[k], 0.0, 1.0).astype(np.float32)

            with torch.no_grad():
                steer = max(-1.0, min(1.0,
                            float(net(torch.from_numpy(xin).unsqueeze(0).to(dev)).item())))
            cte, hint = signed_cte_route(route, loc.x, loc.y, hint)
            exp_steer, _, hint = pure_pursuit_route(route, tf, hint)

            in_bridge = False
            if getattr(C, "LAP_BASED", False) and hint is not None:
                here = hint * float(C.LAP_META.get("step_m", 2.0))
                in_bridge = any(a <= here <= b for a, b in C.BRIDGE_SPANS)
            if in_bridge:
                bridged += 1
            elif cte is not None:
                ctes.append(abs(cte))

            thr, brk = speed.control(veh)
            env.apply_control(veh, carla.VehicleControl(
                throttle=thr, brake=brk, steer=exp_steer if in_bridge else steer))
            if lap_finished(route, hint) or (hint is not None and hint >= n_route - 2):
                break
        mx = float(max(ctes)) if ctes else float("nan")
        return dict(s=s, max_cte_m=mx, max_cte_ft=mx * C.M_TO_FT,
                    frac_over=float(np.mean([c > C.CTE_BUDGET_M for c in ctes])) if ctes else 1.0,
                    scored_steps=len(ctes), bridged=bridged,
                    passed=bool(ctes) and mx <= C.CTE_BUDGET_M)
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
    ap.add_argument("--condition", default="night")
    ap.add_argument("--s", type=float, required=True)
    ap.add_argument("--max-steps", type=int, default=1400)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    ch = tuple(int(c) for c in args.channels.split(","))

    xy, delta = load_chord(args.condition)
    r = drive(args.checkpoint, ch, args.fc, args.s, xy, delta, args.max_steps)
    print(f"  s={args.s:.2f} {args.condition}: max|CTE| {r['max_cte_ft']:6.2f} ft "
          f"({100 * r['max_cte_ft'] / C.CTE_BUDGET_FT:4.0f}% of budget)  "
          f"over {100 * r['frac_over']:.1f}%  steps {r['scored_steps']}  "
          f"{'PASS' if r['passed'] else 'FAIL'}", flush=True)

    out = Path(REPO / (args.out or
                       f"results/town06/chord_interior/{args.condition}_s{args.s:.2f}.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    r.update(checkpoint=args.checkpoint, condition=args.condition,
             budget_ft=C.CTE_BUDGET_FT)
    out.write_text(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

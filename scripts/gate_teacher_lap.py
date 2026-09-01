#!/usr/bin/env python3
"""Drive ONE lap with a teacher checkpoint and record the result. One lap, one process.

The teacher's pass/fail decides whether the study distils from it, so under the standing
rule the laps that decide it get a clean server each -- and a restart inside the training
process is what has been dying with "terminate called" all afternoon. A process boundary
avoids that entirely: the shell restarts CARLA, this drives exactly one lap, the OS
reclaims the client.

DAgger's own per-round gate stays as a cheap progress signal. THIS is what decides.

    STUDY_MAP=Town06 python3 scripts/gate_teacher_lap.py \
        --checkpoint teacher_clear_t06lap_dagger_r05 --weather clear --lap 0
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
import carla                                                   # noqa: E402
import numpy as np                                             # noqa: E402
import torch                                                   # noqa: E402
import carla_determinism as cd                                 # noqa: E402
import carla_env as env                                        # noqa: E402
import config as C                                             # noqa: E402
from gpu import require_cuda                                   # noqa: E402
from evaluate import load_model                                # noqa: E402
from imaging import preprocess_for_model                       # noqa: E402
from route import load_route, signed_cte_route, pure_pursuit_route   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--weather", default="clear")
    ap.add_argument("--lap", type=int, required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cd.install_cleanup_handlers()
    device = require_cuda()
    model = load_model(args.checkpoint, device)
    model.eval()

    route = load_route(C.SECTIONS[0])
    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)
    vehicle = camera = None
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWNS[C.SECTIONS[0]])
        camera, q = env.set_condition(world, vehicle, args.weather)
        speed = env.SpeedController()
        env.warmup_to_speed(world, vehicle, q, speed,
                            steer_fn=lambda v: pure_pursuit_route(route, v.get_transform())[0])
        hint, ctes, bridged, departed = None, [], 0, False
        for step in range(C.steps_for(C.SECTIONS[0]) + 50):
            frame = world.tick()
            image = env.grab_frame(q, frame)
            tf = vehicle.get_transform(); loc = tf.location
            x = torch.from_numpy(preprocess_for_model(env.raw_to_bgr(image))
                                 ).unsqueeze(0).to(device)
            with torch.no_grad():
                nn_steer = max(-1.0, min(1.0, float(model(x).item())))
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
                if abs(cte) > 4.0:
                    departed = True
            thr, brk = speed.control(vehicle)
            env.apply_control(vehicle, carla.VehicleControl(
                throttle=thr, brake=brk, steer=exp_steer if in_bridge else nn_steer))
            if departed:
                break
        mx = float(max(ctes)) if ctes else float("nan")
        over = float(np.mean([c > C.CTE_BUDGET_M for c in ctes])) if ctes else 1.0
        ok = bool(ctes) and mx <= C.CTE_BUDGET_M and not departed
        out = Path(args.out or (Path(C.REPO_ROOT) / "results" / "town06_logs" /
                                f"gate_{args.checkpoint}_{args.weather}_lap{args.lap:02d}.json"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(
            checkpoint=args.checkpoint, weather=args.weather, lap=args.lap,
            max_cte_m=mx, max_cte_ft=mx * C.M_TO_FT, frac_over_budget=over,
            departed=departed, passed=ok, bridged_steps=bridged,
            scored_steps=len(ctes), budget_ft=C.CTE_BUDGET_FT), indent=2))
        print(f"  lap {args.lap} {args.weather}: max|CTE| {mx * C.M_TO_FT:6.2f} ft "
              f"(budget {C.CTE_BUDGET_FT:.2f}) over={over*100:.1f}% "
              f"bridged={bridged} -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        try:
            if camera:
                camera.destroy()
            if vehicle:
                vehicle.destroy()
        except Exception:
            pass
        world.apply_settings(original)


if __name__ == "__main__":
    sys.exit(main())

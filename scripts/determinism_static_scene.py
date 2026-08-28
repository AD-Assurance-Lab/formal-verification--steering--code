#!/usr/bin/env python3
"""Does a FROZEN scene render the same twice? The tightest isolation available.

Everything that could vary is removed: the vehicle is held on the brake and does not
move, the camera is rigidly attached and does not move, the weather is fixed, exposure
is manual. The world still ticks, so the renderer still produces a frame per tick.

If consecutive frames of a scene where NOTHING MOVES are not identical, the sensor image
is not a function of world state, and no amount of pinning physics or spawn or weather
can make a closed-loop run reproducible -- the entropy is generated inside the renderer
on every frame. That is a different problem from asset streaming, and it has different
remedies.

It also separates the two candidates that survive:
  - a WALL-CLOCK-driven effect (foliage sway, any material animating on real time)
    -> frames keep changing, and changing MORE when ticks are spaced further apart,
       which --tick-delay tests directly.
  - a FRAME-COUNTER-driven effect (temporal AA jitter walks a fixed sample sequence)
    -> frames change in a short repeating cycle and are indifferent to --tick-delay.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/determinism_static_scene.py
"""
import argparse
import hashlib
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))

import numpy as np  # noqa: E402
import carla  # noqa: E402
import config as C  # noqa: E402
import carla_env as env  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=40)
    ap.add_argument("--section", default="s02")
    ap.add_argument("--condition", default="clear")
    ap.add_argument("--settle", type=int, default=30,
                    help="ticks held on the brake before capture. If the residual is a "
                         "temporal-accumulation HISTORY that started from a slightly "
                         "different state, a longer settle should converge it away; if "
                         "it is generated fresh every frame, it will not.")
    ap.add_argument("--reps", type=int, default=3,
                    help="repeats of the whole frozen capture, compared FRAME INDEX BY "
                         "FRAME INDEX. Comparing frame N to frame N+1 inside one run "
                         "measures temporal ACCUMULATION (TAA, SSR and volumetric fog "
                         "all evolve for several frames on a scene that never moves) "
                         "and says nothing about determinism. Only frame N of run A "
                         "against frame N of run B does.")
    ap.add_argument("--tick-delay", type=float, default=0.0,
                    help="wall-clock seconds to wait between ticks; separates a "
                         "real-time-driven effect from a frame-counter-driven one")
    args = ap.parse_args()

    if C.MAP_NAME != "Town06":
        raise SystemExit(f"Town06 only; STUDY_MAP is {C.MAP_NAME}")

    reps = [capture(args) for _ in range(args.reps)]

    print(f"\n  frozen scene, {args.frames} frames, {args.reps} reps, "
          f"tick-delay {args.tick_delay}s")
    print(f"  vehicle moved at most "
          f"{max(r['moved'] for r in reps):.3e} (0 = truly frozen)")

    # WITHIN a run: expected to change. Temporal accumulation, not a defect.
    for i, r in enumerate(reps):
        print(f"  rep{i}: {len(set(r['shas']))} distinct frames of {args.frames} "
              f"(within-run temporal evolution -- expected, not a determinism result)")

    # ACROSS runs, same frame index: this is the determinism result.
    print("\n  ACROSS REPS, frame index by frame index:")
    for a in range(len(reps)):
        for b in range(a + 1, len(reps)):
            same = sum(1 for k in range(args.frames)
                       if reps[a]["shas"][k] == reps[b]["shas"][k])
            dmax, npx, roi = 0, 0, 0
            for k in range(args.frames):
                d = np.abs(reps[a]["frames"][k] - reps[b]["frames"][k])
                dmax = max(dmax, int(d.max()))
                m = d.max(axis=2) > 0
                npx = max(npx, int(m.sum()))
                roi = max(roi, int(m[240:450].sum()))
            print(f"    rep{a} vs rep{b}: {same}/{args.frames} frames bit-identical; "
                  f"worst frame {npx} px differ (max delta {dmax}), {roi} of them in ROI")
    return 0


def capture(args):
    client = env.connect()
    world = env.load_study_map(client)
    original = env.enable_sync_mode(world)
    vehicle = camera = None
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWNS[args.section])
        camera, q = env.spawn_camera(world, vehicle, condition=args.condition)
        env.set_weather(world, args.condition, vehicle)
        env.verify_condition(world, args.condition)

        # Settle: hold the brake until the chassis has stopped moving entirely.
        for _ in range(args.settle):
            env.apply_control(vehicle, carla.VehicleControl(throttle=0.0, brake=1.0))
            f = world.tick()
            try:
                env.grab_frame(q, f)
            except env.FrameDesync:
                pass

        shas, frames, poses = [], [], []
        for i in range(args.frames):
            env.apply_control(vehicle, carla.VehicleControl(throttle=0.0, brake=1.0))
            if args.tick_delay:
                time.sleep(args.tick_delay)
            f = world.tick()
            img = env.grab_frame(q, f)
            a = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
                C.CAM_HEIGHT, C.CAM_WIDTH, 4)[:, :, :3].astype(np.int16)
            frames.append(a)
            shas.append(hashlib.sha256(a.tobytes()).hexdigest()[:12])
            tf = vehicle.get_transform()
            poses.append((tf.location.x, tf.location.y, tf.rotation.yaw))
    finally:
        env.cleanup([camera, vehicle], world, original)

    moved = max(abs(p[k] - poses[0][k]) for p in poses for k in range(3))
    return dict(shas=shas, frames=frames, moved=moved)

if __name__ == "__main__":
    from carla_lock import carla_lock, CarlaBusy
    try:
        with carla_lock(owner="determinism_static_scene"):
            sys.exit(main())
    except CarlaBusy as exc:
        raise SystemExit(str(exc))

#!/usr/bin/env python3
"""Do all four conditions still render as themselves under the corrected harness?

`condition_signature.identify()` uses fixed thresholds derived from captures taken
BEFORE the determinism fixes (T06-F20/F22), and `evaluate.py` RAISES on a mismatch. If
`-notexturestreaming` shifted the image statistics enough to cross a threshold, every
run of the affected condition would abort -- and it would abort hours into an unattended
rebuild, not at the start.

So this checks all four in one short run, before the rebuild is launched. It also prints
the statistics next to the values the thresholds were derived from, because a condition
that still classifies correctly but has drifted close to a boundary is worth knowing
about before it starts failing intermittently.

It captures several frames per condition, at spaced poses, because one frame at one
pose is not evidence about a section.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/verify_conditions_render.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "scripts"))

import numpy as np  # noqa: E402
import carla  # noqa: E402
import config as C  # noqa: E402
import carla_env as env  # noqa: E402
from student import student_preprocess  # noqa: E402
from condition_signature import identify, stats  # noqa: E402

# The values the thresholds were derived from, for drift comparison (docstring of
# condition_signature.py). Not assertions -- context.
REFERENCE = {
    "clear":   dict(mean=0.3039, sigma=0.0636, p01=0.0471),
    "fog":     dict(mean=0.2803, sigma=0.0601, p01=0.1804),
    "night":   dict(mean=0.2002, sigma=0.1380, p01=0.0000),
    "shadows": dict(mean=0.1842, sigma=0.0559, p01=0.0157),
}
CONDITIONS = ("clear", "fog", "night", "shadows")


def main():
    if C.MAP_NAME != "Town06":
        raise SystemExit(f"Town06 only; STUDY_MAP is {C.MAP_NAME}")

    import carla_determinism as cd
    client = env.connect()
    world = env.load_study_map(client)
    original = env.enable_sync_mode(world)
    cd.require_deterministic(C.PORT, world, fixed_dt=C.FIXED_DT,
                             deterministic_control=C.DETERMINISTIC_CONTROL)

    vehicle = camera = None
    bad = []
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWNS["s02"])
        camera, q = env.spawn_camera(world, vehicle, condition="clear")
        print(f"  {'condition':9s} {'verdict':9s} {'mean':>8s} {'sigma':>8s} {'p01':>8s}"
              f"   {'(reference: mean/sigma/p01)':>34s}")
        for cond in CONDITIONS:
            camera, q = env.set_condition(world, vehicle, cond, camera)
            # Let the write land and the renderer settle before believing a frame.
            for _ in range(8):
                f = world.tick()
                try:
                    env.grab_frame(q, f)
                except env.FrameDesync:
                    pass
            got_all, st_all = [], []
            for _ in range(5):
                f = world.tick()
                img = env.grab_frame(q, f)
                pre = student_preprocess(env.raw_to_bgr(img), 168, 28)
                g, s = identify(pre)
                got_all.append(g)
                st_all.append(s)
            m = {k: float(np.mean([s[k] for s in st_all])) for k in ("mean", "sigma", "p01")}
            ok = all(g == cond for g in got_all)
            r = REFERENCE[cond]
            print(f"  {cond:9s} {'OK' if ok else 'MISMATCH':9s} "
                  f"{m['mean']:8.4f} {m['sigma']:8.4f} {m['p01']:8.4f}   "
                  f"({r['mean']:.4f} / {r['sigma']:.4f} / {r['p01']:.4f})"
                  + ("" if ok else f"  -> read as {sorted(set(got_all))}"))
            if not ok:
                bad.append(cond)
    finally:
        env.cleanup([camera, vehicle], world, original)

    if bad:
        print(f"\n  FAIL: {bad} do not classify as themselves under this harness.")
        print("  Do NOT start the rebuild: evaluate.py raises on a condition mismatch,")
        print("  so every run of these conditions would abort part-way through it.")
        return 1
    print("\n  All four conditions classify correctly. Safe to collect.")
    return 0


if __name__ == "__main__":
    from carla_lock import carla_lock, CarlaBusy
    try:
        with carla_lock(owner="verify_conditions_render"):
            sys.exit(main())
    except CarlaBusy as exc:
        raise SystemExit(str(exc))

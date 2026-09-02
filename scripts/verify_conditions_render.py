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
    "low_sun": dict(mean=0.1842, sigma=0.0559, p01=0.0157),
}
CONDITIONS = ("clear", "fog", "night", "low_sun")


def main(sections=None):
    # The function's own default must not disagree with the CLI's. A caller that imports
    # this module would otherwise silently get one section while the command line gets
    # every section -- the same defect in a second place.
    sections = tuple(sections) if sections else tuple(C.SECTIONS)
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
        vehicle = env.spawn_vehicle(world, C.SPAWNS[sections[0]])
        camera, q = env.spawn_camera(world, vehicle, condition="clear")
        print(f"  sections: {', '.join(sections)}")
        print(f"  {'condition':9s} {'verdict':9s} {'mean':>8s} {'sigma':>8s} {'p01':>8s}"
              f"   {'(reference: mean/sigma/p01)':>34s}")
        per_section = {c: {} for c in CONDITIONS}
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
            for sec in sections:
                # Sample the condition at each section's spawn. T06-F20 chose the low-sun
                # angle on brightness measured across the route, not at one pose, and the
                # per-section SPREAD was half its argument -- so one pose cannot re-derive
                # it. Teleport rather than drive: this is a photometric check, and driving
                # it would cost six sections of simulator time for no extra information.
                env.teleport(vehicle, C.SPAWNS[sec])
                for _ in range(6):
                    f = world.tick()
                    try:
                        env.grab_frame(q, f)
                    except env.FrameDesync:
                        pass
                sec_st = []
                for _ in range(3):
                    f = world.tick()
                    img = env.grab_frame(q, f)
                    pre = student_preprocess(env.raw_to_bgr(img), 168, 28)
                    g, s = identify(pre)
                    got_all.append(g)
                    st_all.append(s)
                    sec_st.append(s)
                per_section[cond][sec] = float(np.mean([x["mean"] for x in sec_st]))
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

    print("\n  per-section mean brightness of the network's own input:")
    print(f"    {'condition':9s} " + " ".join(f"{s:>7s}" for s in sections) + "     CV%")
    for cond in CONDITIONS:
        vals = [per_section[cond][s] for s in sections]
        cv = 100.0 * float(np.std(vals)) / float(np.mean(vals)) if np.mean(vals) else 0.0
        print(f"    {cond:9s} " + " ".join(f"{v:7.4f}" for v in vals) + f"   {cv:5.2f}")
    ls_mean = float(np.mean([per_section["shadows"][s] for s in sections]))
    print(f"\n  LOW SUN re-derivation (PROTOCOL A-2 clause). Town06 at "
          f"{C.STUDY_MAP and 5.0} deg under the corrected harness: mean {ls_mean:.4f}")
    print(f"    Town04 published reference: 0.1117 -> "
          f"{100.0*abs(ls_mean-0.1117)/0.1117:5.1f}% away "
          f"(T06-F20 accepted 5 deg at 9%; 15 deg was 65% away and read as night)")
    print(f"    night - low sun gap: "
          f"{float(np.mean([per_section['night'][s] for s in sections])) - ls_mean:.4f} "
          f"(Town04 published: 0.0958; the axis must stay ordered)")

    if bad:
        print(f"\n  FAIL: {bad} do not classify as themselves under this harness.")
        print("  Do NOT start the rebuild: evaluate.py raises on a condition mismatch,")
        print("  so every run of these conditions would abort part-way through it.")
        return 1
    print(f"\n  All four conditions classify correctly on "
          f"{len(sections)} section(s): {','.join(sections)}. Safe to collect.")
    return 0


if __name__ == "__main__":
    import argparse
    _ap = argparse.ArgumentParser()
    # EVERY SECTION BY DEFAULT. This defaulted to s02 alone and then printed "All four
    # conditions classify correctly. Safe to collect." -- a map-wide clearance from one
    # section of six. The docstring already argues that one pose is not evidence about a
    # section; one section is not evidence about a map for the same reason. Narrowing is
    # still available, but it has to be asked for (standing rule 7).
    _ap.add_argument("--sections", default="all",
                     help="comma-separated, or 'all' (default) for every section")
    _a = _ap.parse_args()
    _secs = tuple(C.SECTIONS) if _a.sections == "all" else tuple(_a.sections.split(","))

    from carla_lock import carla_lock, CarlaBusy
    try:
        with carla_lock(owner="verify_conditions_render"):
            sys.exit(main(_secs))
    except CarlaBusy as exc:
        raise SystemExit(str(exc))

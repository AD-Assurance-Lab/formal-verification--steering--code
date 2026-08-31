#!/usr/bin/env python3
"""Is the interior of the clear->night family a real operating point?

The night axis is the awkward one and was left unmeasured until a CERTIFIED verdict came
to depend on it: Town04's `S_mixed/night` certifies in BOTH directions, and a family whose
interior does not behave like a real render is a soundness risk for CERTIFIED verdicts
specifically -- an optimistic chord does not produce false alarms, it produces missed ones.

WHY IT IS AWKWARD. The chord runs from clear to night, and the two endpoints carry
DIFFERENT declared exposures: daylight shutter 800, night shutter 200. So a pixel chord
between them interpolates an exposure change as well as a lighting change, and there is no
single exposure at which to render an intermediate. Rendering the whole sweep at night's
exposure is what invalidated an earlier sun sweep (T06-F35): daylight scenes through a
night camera, overexposed and meaningless.

So each intermediate is rendered at the exposure THE STUDY WOULD DECLARE for that angle --
daylight above the horizon, night below it, since headlights_on() switches at 0 -- which is
the physically sensible path a vehicle would actually take through this family. If the
chord tracks that path the coverage claim holds; if it does not, the claim must be scoped
to the endpoints and the CERTIFIED night cells rest on a construct.

    STUDY_MAP=Town04 python3 scripts/interp_fidelity_night.py
"""
import os, sys, json
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
import numpy as np, torch                                    # noqa: E402
import config as C                                           # noqa: E402
from student import StudentNet                               # noqa: E402

DIAG = REPO / "results" / "diagnostic"
# angle -> the condition whose EXPOSURE the study declares at that angle
INTERMEDIATES = [(45.0, "shadows"), (20.0, "shadows"), (5.0, "shadows"), (-10.0, "night")]

MIN_COVERAGE = 0.80          # of the section's scored length


def check_coverage(path, sec):
    """Refuse a capture that covers a slice of the section. See interpolation_fidelity."""
    z = np.load(path, allow_pickle=True)
    x = np.asarray(z["pose_x"], float); y = np.asarray(z["pose_y"], float)
    span = float(np.sum(np.hypot(np.diff(x), np.diff(y))))
    expect = getattr(C, "SECTION_LEN_M", {}).get(sec)
    if expect is not None and span < MIN_COVERAGE * expect:
        print(f"\nREFUSING to measure fidelity from {Path(path).name}: it spans "
              f"{span:.0f} m of a {expect:.0f} m section ({100 * span / expect:.1f}%). "
              f"Recapture with scripts/capture_interp_fidelity.sh.", file=sys.stderr)
        sys.exit(2)
    return span


def frames(path, cond):
    z = np.load(path, allow_pickle=True)
    conds = [str(c) for c in z["conds"]]
    if cond not in conds:
        return None
    fr = z["frames"][conds.index(cond)]
    oi = int(np.argmin(np.abs(z["offsets"]))); yi = int(np.argmin(np.abs(z["yaws"])))
    return fr[:, oi, yi]


def steer(net, x, dev):
    with torch.no_grad():
        return net(torch.from_numpy(np.ascontiguousarray(x)).to(dev)).cpu().numpy().reshape(-1)


def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tol = C.CLOSED_LOOP_TOLERANCE
    # EVERY SECTION, not one. See interpolation_fidelity.py -- a single section is at
    # most 23% of the route, and the old output could not say which part it covered.
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sections", default=None,
                    help="comma-separated sections to pool over; default EVERY section")
    args = ap.parse_args()
    sections = args.sections.split(",") if args.sections else list(C.SECTIONS)

    ends = {}
    for sec in sections:
        e = DIAG / f"interp_night_{sec}_end.npz"
        if not e.exists():
            print(f"need {e} (clear + night at -25, same session). "
                  f"Run scripts/capture_interp_fidelity.sh {sec}", file=sys.stderr)
            return 2
        check_coverage(e, sec)
        ends[sec] = e
    total_span = sum(check_coverage(ends[s], s) for s in sections)

    clear = np.concatenate([frames(ends[s], "clear") for s in sections])
    full = np.concatenate([frames(ends[s], "night") for s in sections])
    n = len(clear)
    d_vec = (full - clear).reshape(n, -1)
    denom = np.einsum("ij,ij->i", d_vec, d_vec)

    students = C.TOWN06_STUDENTS if C.STUDY_MAP == "Town06" else C.STUDENTS
    in_h, in_w = ((C.TOWN06_INPUT_H, C.TOWN06_INPUT_W) if C.STUDY_MAP == "Town06" else (28, 84))
    print(f"\nNIGHT-AXIS INTERPOLATION FIDELITY -- {C.STUDY_MAP}, {n} poses, tol {tol:.4f}")
    print("  chord: clear (daylight exposure) -> night at -25 deg (night exposure)")
    print("  each intermediate rendered at the exposure the study declares for its angle\n")
    print(f"  scope: {len(sections)} sections ({','.join(sections)}), "
          f"{n} poses, {total_span:.0f} m of road\n")
    out = {"n_poses": int(n), "tolerance": tol, "sections": list(sections),
           "route_span_m": float(total_span), "cells": {}}
    for nm, ck_base, ch, fc in students:
        ck = C.final_student(ck_base)
        net = StudentNet(in_h, in_w, channels=ch, fc=fc).to(dev)
        net.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev,
                                       weights_only=True))
        net.eval()
        s_clear, s_full = steer(net, clear, dev), steer(net, full, dev)
        print(f"  {nm}  ({ck})   lap-mean bias at s=1: {np.mean(s_full - s_clear):+.5f} "
              f"= {np.mean(s_full - s_clear)/tol:+.2f}x tol")
        print(f"    {'sun':>6} {'exposure':>9} {'s*':>6} {'pixel err':>10} {'steer err':>10} {'x tol':>7}")
        cells = {}
        for ang, cond in INTERMEDIATES:
            paths = [DIAG / f"interp_night_{sec}_s{ang:g}.npz" for sec in sections]
            if not all(q.exists() for q in paths):
                print(f"    {ang:6g} {cond:>9} {'capture missing':>36}"); continue
            for sec, q in zip(sections, paths):
                check_coverage(q, sec)
            xr = np.concatenate([frames(q, cond) for q in paths])
            if xr is None or len(xr) != n:
                print(f"    {ang:6g} {cond:>9} {'length mismatch':>36}"); continue
            r = (xr - clear).reshape(n, -1)
            s_star = np.clip(np.einsum("ij,ij->i", r, d_vec) / np.maximum(denom, 1e-12), 0, 1)
            x_chord = clear + s_star[:, None, None, None] * (full - clear)
            pix = float(np.abs(x_chord - xr).mean())
            err = float(np.mean(steer(net, x_chord, dev) - steer(net, xr, dev)))
            print(f"    {ang:6g} {cond:>9} {s_star.mean():6.3f} {pix:10.5f} {err:+10.5f} {err/tol:+7.2f}")
            cells[str(ang)] = dict(exposure=cond, s_star=float(s_star.mean()),
                                   pixel_err=pix, steer_err=err, steer_err_x_tol=err/tol)
        out["cells"][nm] = cells
        print()
    # MAP-SCOPED FILENAME. This wrote one map-agnostic name, so running Town04 after
    # Town06 silently overwrote Town06's artifact -- same shape, same keys, different map,
    # and nothing downstream could tell. Caught because the saved file said
    # sections=[eastbound, westbound] minutes after the Town06 run reported six sections.
    _out = DIAG / f"interpolation_fidelity_night_{C.STUDY_MAP.lower()}.json"
    out["map"] = C.STUDY_MAP
    _out.write_text(json.dumps(out, indent=2))
    print(f"  -> {_out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

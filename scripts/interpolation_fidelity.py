#!/usr/bin/env python3
"""Does the INTERIOR of the disturbance family behave like a real render?

The certificate quantifies over

    x_p(s) = x_p^clear + s (x_p^cond - x_p^clear),   s in [0, 1]

but only s = 0 and s = 1 are rendered. Everything between is a pixel-space chord, and
the paper's coverage claim -- that the certificate covers intensities no closed-loop run
samples -- rests entirely on that chord meaning something.

This applies to our own family exactly the test that killed the analytic Koschmieder
model. That model was faithful to IMAGES (road-ROI R^2 0.848) and drove the policy
23.8x harder than the real condition, which is how we learned that image fidelity is not
the property that matters. Not running the same test on the replacement is a double
standard, and both blind reviewers said so independently.

METHOD. Render fog at intermediate densities. For each rendered intermediate x_render,
project it onto the chord to find the s it corresponds to,

    s* = <x_render - x_clear, x_cond - x_clear> / ||x_cond - x_clear||^2

then compare the two things that matter, in order of increasing relevance:

    pixel     ||x(s*) - x_render||        does the chord pass near the render?
    steering  |d(x(s*)) - d(x_render)|    does the policy AGREE at that point?

The second is the one the study cares about, and it is reported against the two
references that make it interpretable: CLOSED_LOOP_TOLERANCE, and the lap-mean bias the
certificate is comparing to that tolerance.

    python scripts/interpolation_fidelity.py
"""
import sys
import json
import glob
import re
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
from student import StudentNet  # noqa: E402

DIAG = REPO / "results" / "diagnostic"

# AXES. The test is the same for any one-parameter family; only the file naming, the
# condition held at the far endpoint, and which end of the swept parameter IS that
# endpoint differ. Fog runs 0 -> 70 (endpoint = the largest density); low sun runs
# 90 -> 5 degrees (endpoint = the SMALLEST angle), so `endpoint_is_max` carries that.
AXES = {
    "fog":    dict(glob="interp_fog_d*.npz",     pat=r"interp_fog_d([\d.]+)\.npz",
                   cond="fog",     endpoint=70.0, endpoint_is_max=True,  unit="density"),
    "lowsun": dict(glob="interp_lowsun_s*.npz",  pat=r"interp_lowsun_s([\d.]+)\.npz",
                   cond="shadows", endpoint=5.0,  endpoint_is_max=False, unit="sun deg"),
}
FULL_DENSITY = 70.0          # kept for the fog default


def frames(path, cond):
    z = np.load(path, allow_pickle=True)
    conds = [str(c) for c in z["conds"]]
    if cond not in conds:
        return None
    fr = z["frames"][conds.index(cond)]
    oi = int(np.argmin(np.abs(z["offsets"])))
    yi = int(np.argmin(np.abs(z["yaws"])))
    return fr[:, oi, yi]


def steer(net, x, dev):
    with torch.no_grad():
        return net(torch.from_numpy(np.ascontiguousarray(x)).to(dev)
                   ).cpu().numpy().reshape(-1)


def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tol = C.CLOSED_LOOP_TOLERANCE

    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--axis", default="fog", choices=sorted(AXES))
    args = ap.parse_args()
    ax = AXES[args.axis]

    caps = {}
    for p in sorted(glob.glob(str(DIAG / ax["glob"]))):
        m = re.search(ax["pat"], p)
        if m:
            caps[float(m.group(1))] = p
    end = ax["endpoint"]
    if end not in caps:
        print(f"need the endpoint capture for {end:g} {ax['unit']} in {DIAG}",
              file=sys.stderr)
        return 2
    inters = sorted((d for d in caps if d != end), reverse=not ax["endpoint_is_max"])
    if not inters:
        print("need at least one intermediate point", file=sys.stderr)
        return 2

    # The chord's endpoints come from the ENDPOINT capture, so both are same-session
    # (F43/F44: a cross-session baseline inverted the sign of a fog measurement).
    clear = frames(caps[end], "clear")
    full = frames(caps[end], ax["cond"])
    n = len(clear)
    d_vec = (full - clear).reshape(n, -1)
    denom = np.einsum("ij,ij->i", d_vec, d_vec)

    print(f"\nINTERPOLATION FIDELITY -- is the family's interior a real condition?")
    print(f"  axis '{args.axis}': clear -> {ax['cond']} at {end:g} {ax['unit']}")
    print(f"  chord endpoints from {Path(caps[end]).name} (same session)")
    print(f"  {n} poses, tolerance {tol:.4f}\n")

    out = {"n_poses": int(n), "tolerance": tol, "axis": args.axis,
           "endpoint": end, "unit": ax["unit"], "cells": {}}
    # MAP-AWARE, like the rest of the pipeline. This script was written for Town04 and
    # hardcoded its students and its 28x84 input; run unchanged under STUDY_MAP=Town06 it
    # would silently load Town04 checkpoints at the wrong resolution.
    students = C.TOWN06_STUDENTS if C.STUDY_MAP == "Town06" else C.STUDENTS
    in_h, in_w = ((C.TOWN06_INPUT_H, C.TOWN06_INPUT_W) if C.STUDY_MAP == "Town06"
                  else (28, 84))
    print(f"  map {C.STUDY_MAP}, students at {in_w}x{in_h}")
    for nm, ck, ch, fc in students:
        net = StudentNet(in_h, in_w, channels=ch, fc=fc).to(dev)
        net.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth",
                                       map_location=dev, weights_only=True))
        net.eval()
        s_clear = steer(net, clear, dev)
        s_full = steer(net, full, dev)
        print(f"  {nm}   (lap-mean bias at s=1: {np.mean(s_full - s_clear):+.5f}"
              f" = {np.mean(s_full - s_clear) / tol:+.2f}x tol)")
        print(f"    {ax['unit']:>8} {'s*':>6} {'pixel err':>10} {'steer err':>10}"
              f" {'x tol':>7} {'chord/render':>13}")
        for d in inters:
            xr = frames(caps[d], ax["cond"])
            # Project each pose's render onto that pose's chord.
            r = (xr - clear).reshape(n, -1)
            s_star = np.einsum("ij,ij->i", r, d_vec) / np.maximum(denom, 1e-12)
            s_cl = np.clip(s_star, 0.0, 1.0)
            x_chord = clear + s_cl[:, None, None, None] * (full - clear)

            pix = float(np.abs(x_chord - xr).mean())
            s_r = steer(net, xr, dev)
            s_c = steer(net, x_chord, dev)
            # The certificate's quantity is a LAP MEAN of a signed difference, so that is
            # the error that actually propagates into a verdict.
            mean_err = float(np.mean(s_c - s_r))
            bias_render = float(np.mean(s_r - s_clear))
            bias_chord = float(np.mean(s_c - s_clear))
            # The Koschmieder-comparable number: how much harder does the CHORD drive the
            # policy than the real render? That model scored 23.8x on this ratio.
            # Guard it: where the render's own bias is negligible the ratio divides by
            # nothing and is meaningless, so the absolute error is the honest statistic.
            weak = abs(bias_render) < 0.1 * tol
            ratio = float("nan") if weak else bias_chord / bias_render
            flag = "  (render bias ~0; ratio meaningless)" if weak else ""
            print(f"    {d:8.1f} {np.mean(s_cl):6.3f} {pix:10.5f} {mean_err:+10.5f}"
                  f" {mean_err / tol:+7.2f} {'' if weak else f'{ratio:9.2f}x'}{flag}")
            out["cells"].setdefault(nm, {})[str(d)] = dict(
                s_star_mean=float(np.mean(s_cl)), pixel_err=pix,
                steer_mean_err=mean_err, steer_err_x_tol=mean_err / tol,
                bias_render=bias_render, bias_chord=bias_chord,
                ratio_chord_over_render=None if weak else ratio,
                ratio_meaningful=not weak)
        print()

    outp = DIAG / f"interpolation_fidelity_{args.axis}.json"
    outp.write_text(json.dumps(out, indent=2))
    print(f"  -> {outp.relative_to(REPO)}")
    print("\n  READ IT THIS WAY. The steering error is what a verdict would inherit if the")
    print("  interior were treated as a real operating point. Compare it to the s=1 bias:")
    print("  small means the chord is behaviourally faithful and the coverage claim holds;")
    print("  comparable means the interior is a pixel construct and the claim must be")
    print("  scoped to the endpoints. Koschmieder failed this same test at 23.8x.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

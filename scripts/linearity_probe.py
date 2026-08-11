#!/usr/bin/env python3
"""M5's gating measurement: is each condition's disturbance model VERIFIABLE at all?

No CARLA, no GPU. Runs on collected frames.

A disturbance reaches the verifier as `x = clamp01(m(u) (*) x0 + a(u))` with `m` and `a`
affine in a low-dimensional `u`. If that affine model does not track the true physics
across the parameter interval, the residual has to be carried as a sound envelope, and a
large envelope makes the bounds vacuous no matter how good the physics is. So
`max_linearity_error` decides whether a condition can be certified before any calibration
effort is spent on it.

Two things measured per condition:

  1. The residual over the FULL declared interval -- can this be certified in one shot?
  2. How the residual scales as the interval is SPLIT -- the branch-and-bound claim in
     docs/DISTURBANCE_MATH.md is that it shrinks roughly quadratically with interval
     width. That has never been measured, and it is what makes a nonlinear
     reparameterization tractable at all.

Constants here are the previous generation's and are NOT calibrated (D4 recalibrates them
from depth). That is fine for this question: linearity is a property of the model's FORM
in its chosen parameterization, not of the constant values.

    python scripts/linearity_probe.py --frames 6
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
import verifiable_disturbance as vd  # noqa: E402

RESULTS = REPO / "results" / "linearity"

# Declared axes from STUDY.md, expressed in the parameterization each model is affine in.
CONDITIONS = {
    "fog":   dict(ranges=lambda lo, hi: {"mor": (lo, hi)}, axis=(2000.0, 60.0),
                  unit="m MOR"),
    "night": dict(ranges=lambda lo, hi: {"ambient": (lo, hi), "retro": (0.0, 3.0)},
                  axis=(0.50, 0.02), unit="ambient (rel. to peak headlight)"),
    "rain":  dict(ranges=lambda lo, hi: {"mor": (lo, hi), "wet": 0.30}, axis=(1500.0, 300.0),
                  unit="m MOR equiv."),
}


def clear_frames(n):
    """N clear frames from the collected dataset, spread across the route."""
    base = REPO / "pipeline" / "data" / "conditions"
    rows = [r for r in csv.DictReader(open(base / "manifest.csv"))
            if r["weather"] == "clear"]
    if not rows:
        raise SystemExit("no clear frames in data/conditions -- collect first")
    picks = rows[:: max(1, len(rows) // n)][:n]
    return [cv2.imread(str(base / r["image"])) for r in picks]


def probe(cond, frames, lo, hi):
    """Worst-case linearity residual over an interval, across frames."""
    spec = CONDITIONS[cond]
    worst, dims = 0.0, None
    for img in frames:
        W, b, blo, bhi, err = vd.linear_map_for(cond, img, spec["ranges"](lo, hi),
                                                w=84, h=28)
        worst = max(worst, err)
        dims = len(blo)
    return worst, dims


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frames", type=int, default=6)
    ap.add_argument("--splits", type=int, default=4,
                    help="how many times to halve the interval for the BaB scaling test")
    args = ap.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)

    frames = clear_frames(args.frames)
    print(f"{len(frames)} clear frames, students at 84x28\n")

    # A residual is only meaningful against the tolerance it has to fit inside.
    tol = C.CLOSED_LOOP_TOLERANCE
    print(f"closed-loop tolerance {tol:.4f} (network output units)")
    print("residual is in IMAGE units [0,1]; treat it as usable only if it is small")
    print("relative to the pixel changes the disturbance itself makes.\n")

    report = {}
    print(f"  {'condition':9s} {'dims':>5s} {'full-interval residual':>23s}  verdict")
    print("  " + "-" * 62)
    for cond, spec in CONDITIONS.items():
        a, b = spec["axis"]
        err, dims = probe(cond, frames, a, b)
        verdict = ("EXACT" if err < 1e-5 else
                   "usable" if err < 0.01 else
                   "MARGINAL" if err < 0.05 else "TOO NONLINEAR")
        print(f"  {cond:9s} {dims:5d} {err:23.6f}  {verdict}")
        report[cond] = {"dims": dims, "full_interval_residual": err,
                        "axis": [a, b], "unit": spec["unit"]}

    # --- BaB scaling: does splitting the interval shrink the residual? ----------
    print(f"\n  branch-and-bound scaling -- residual vs interval width")
    print(f"  {'condition':9s} " + "".join(f"{'1/'+str(2**k):>12s}" for k in range(args.splits + 1)))
    print("  " + "-" * 62)
    for cond, spec in CONDITIONS.items():
        a, b = spec["axis"]
        mid = 0.5 * (a + b)
        row, series = [], []
        for k in range(args.splits + 1):
            half = (b - a) / (2 ** (k + 1))
            lo_k, hi_k = mid - half, mid + half
            err, _ = probe(cond, frames, min(lo_k, hi_k), max(lo_k, hi_k))
            row.append(f"{err:12.6f}")
            series.append(err)
        print(f"  {cond:9s} " + "".join(row))
        report[cond]["bab_scaling"] = series
        if len(series) > 1 and series[0] > 1e-9:
            ratios = [series[i] / max(series[i + 1], 1e-12) for i in range(len(series) - 1)]
            report[cond]["halving_ratios"] = ratios
            print(f"  {'':9s} " + f"  shrink per halving: "
                  + ", ".join(f"{r:.1f}x" for r in ratios))

    print("\n  NOTE: quadratic shrinkage would be ~4x per halving. Linear would be ~2x.")
    print("  Anything near 1x means splitting does not help and BaB will not rescue")
    print("  that condition.")

    print("\n  SHADOWS: no disturbance model exists. It is a spatially-varying mask, not")
    print("  a photometric map, so it needs a new model (docs/DISTURBANCE_MATH.md) and")
    print("  cannot be probed here. That is a gap, not a pass.")

    path = RESULTS / "linearity_probe.json"
    with open(path, "w") as fh:
        json.dump(report, fh, indent=2)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    sys.exit(main())

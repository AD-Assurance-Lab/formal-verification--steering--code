#!/usr/bin/env python3
"""What does discarding the correlation between depth bands actually cost?

No CARLA. This is the measurement `scripts/linearity_probe.py` should have made.

Fog is driven by ONE physical scalar: the extinction coefficient beta, hence one
meteorological optical range. The inherited machinery hands the verifier a BOX over six
independent per-band transmissions, which is sound but permits band 1 to sit at MOR 60
while band 6 sits at MOR 2000 -- physically impossible, since a single beta sets them all.

`docs/DISTURBANCE_MATH.md` says not to do this ("a box permits pixel i at beta_lo while
pixel j sits at beta_hi... discarding that correlation is exactly what makes pixel-space
verification vacuous") and prescribes the rank-1 alternative: on a branch-and-bound cell,
write t_i = tbar_i + s * delta_i with a SINGLE scalar s in [-1, 1].

Both are sound. The box is an over-approximation of the rank-1 set. This measures the
price in certified bound width, which is the quantity that decides whether a condition can
be certified at all.

    python scripts/box_vs_rank1.py --mor-lo 60 --mor-hi 2000
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
import disturbance_models as dm  # noqa: E402
import verifiable_disturbance as vd  # noqa: E402
from student import StudentNet  # noqa: E402

from auto_LiRPA import BoundedModule, BoundedTensor, PerturbationLpNorm  # noqa: E402

RESULTS = REPO / "results" / "linearity"


def clear_frame(i=0):
    base = REPO / "pipeline" / "data" / "conditions"
    rows = [r for r in csv.DictReader(open(base / "manifest.csv"))
            if r["weather"] == "clear"]
    return cv2.imread(str(base / rows[i * (len(rows) // 8)]["image"]))


def render(xf, t_bands, edges, airlight, w, h):
    y = vd._apply_banded_veil(xf, t_bands, edges, airlight)
    return vd._project(y.astype(np.float32), w, h).reshape(-1)


def bound_width(W, b, lo, hi, student, device, shape):
    """alpha-CROWN output width for x(theta) = clamp(W theta + b) fed to the student."""
    dist = vd.LinearDisturbance(W, b, shape)
    net = nn.Sequential(dist, student).to(device).eval()
    centre = torch.zeros(1, W.shape[1], device=device)
    lo_t = torch.tensor(lo, dtype=torch.float32, device=device).unsqueeze(0)
    hi_t = torch.tensor(hi, dtype=torch.float32, device=device).unsqueeze(0)
    bounded = BoundedModule(net, torch.empty_like(centre), device=device)
    ptb = PerturbationLpNorm(norm=float("inf"), x_L=lo_t, x_U=hi_t)
    bt = BoundedTensor(centre, ptb)
    lb, ub = bounded.compute_bounds(x=(bt,), method="CROWN-Optimized")
    return float(lb.min()), float(ub.max())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mor-lo", type=float, default=60.0)
    ap.add_argument("--mor-hi", type=float, default=2000.0)
    ap.add_argument("--student", default="S_clear_84x28")
    ap.add_argument("--w", type=int, default=84)
    ap.add_argument("--h", type=int, default=28)
    ap.add_argument("--splits", type=int, default=3)
    args = ap.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    student = StudentNet(args.h, args.w).to(device)
    student.load_state_dict(torch.load(
        f"{C.CHECKPOINT_DIR}/{args.student}.pth", map_location=device))
    student.eval()

    img = clear_frame()
    xf = img.astype(np.float32) / 255.0
    H = xf.shape[0]
    A = (0.76, 0.78, 0.78)
    shape = (1, 3, args.h, args.w)
    tol = C.CLOSED_LOOP_TOLERANCE

    print(f"student {args.student}, {student.num_relu_neurons()} ReLU | device {device}")
    print(f"closed-loop tolerance {tol:.4f}\n")
    print(f"  {'MOR interval':>20s} {'dims':>5s} {'model':>7s} {'bound width':>13s} {'vs tol':>9s}")
    print("  " + "-" * 62)

    report = []
    for k in range(args.splits + 1):
        # progressively narrower sub-interval at the severe end, as BaB would produce
        n_cells = 2 ** k
        width = (args.mor_hi - args.mor_lo) / n_cells
        lo_m, hi_m = args.mor_lo, args.mor_lo + width

        t_lo, t_hi, edges = vd.banded_transmission_box(lo_m, hi_m, H)
        tbar, delta = 0.5 * (t_lo + t_hi), 0.5 * (t_hi - t_lo)

        # (a) BOX over 6 independent band transmissions -- what the inherited code does
        b_box = render(xf, tbar, edges, A, args.w, args.h)
        W_box = np.stack([
            (render(xf, tbar + np.eye(len(tbar))[i] * max(delta[i], 1e-6), edges, A,
                    args.w, args.h) - b_box) / max(delta[i], 1e-6)
            for i in range(len(tbar))], axis=1).astype(np.float32)
        lo_box, hi_box = -delta.astype(np.float32), delta.astype(np.float32)

        # (b) RANK-1: one scalar s in [-1,1] moves all bands together, as one beta does
        b_r1 = b_box
        W_r1 = (render(xf, tbar + delta, edges, A, args.w, args.h) - b_r1
                ).reshape(-1, 1).astype(np.float32)
        lo_r1, hi_r1 = np.array([-1.0], np.float32), np.array([1.0], np.float32)

        row = {"mor": [lo_m, hi_m], "cells": n_cells}
        for name, (W, b, lo, hi) in (("box", (W_box, b_box, lo_box, hi_box)),
                                     ("rank-1", (W_r1, b_r1, lo_r1, hi_r1))):
            l, u = bound_width(W, b, lo, hi, student, device, shape)
            wdt = u - l
            row[name] = wdt
            print(f"  {f'[{lo_m:.0f}, {hi_m:.0f}]':>20s} {W.shape[1]:5d} {name:>7s} "
                  f"{wdt:13.6f} {wdt / tol:8.1f}x")
        row["box_over_rank1"] = row["box"] / max(row["rank-1"], 1e-12)
        print(f"  {'':>20s} {'':>5s} {'ratio':>7s} {row['box_over_rank1']:13.1f}x\n")
        report.append(row)

    print("=" * 66)
    ratios = [r["box_over_rank1"] for r in report]
    print(f"  box costs {min(ratios):.1f}x to {max(ratios):.1f}x the bound width of rank-1")
    certifiable = [r for r in report if r["rank-1"] < C.CLOSED_LOOP_TOLERANCE]
    print(f"  sub-intervals certifiable under rank-1: {len(certifiable)}/{len(report)}")
    print(f"  sub-intervals certifiable under box   : "
          f"{len([r for r in report if r['box'] < C.CLOSED_LOOP_TOLERANCE])}/{len(report)}")
    print("=" * 66)

    path = RESULTS / "box_vs_rank1.json"
    with open(path, "w") as fh:
        json.dump({"student": args.student, "tolerance": tol, "rows": report}, fh, indent=2)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    sys.exit(main())

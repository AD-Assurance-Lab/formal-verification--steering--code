#!/usr/bin/env python3
"""Certify a student over the NIGHT axis. No CARLA. First test of BaB at d = 2.

Fog is one scalar. Night is two -- an illumination gain and a retroreflection amplitude --
so this is the first time the tractability argument is exercised above one dimension. The
claim in `docs/DISTURBANCE_MATH.md` is that branch-and-bound costs `k^d` rather than
`2^thousands`, and at d = 1 that claim is never actually tested.

The night map is EXACTLY affine in its parameterization `u = (g, a_retro)` -- residual at
float noise, see F8's note on why that is true by construction. So the linear map is
computed ONCE for the full box and branch-and-bound simply subdivides the box in u-space,
splitting the widest dimension. No re-probing per cell.

Corridor centred on clear-weather steering (trap 6).

Parameters are reported in the MODEL's space, not lux: the mapping from road illuminance
to `ambient` is part of the calibration that D4 has not done yet. The tractability and
tightness results do not depend on that mapping; the certified boundaries do.

    python scripts/certify_night.py --frames 10 --max-cells 64
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
import verifiable_disturbance as vd  # noqa: E402
from student import StudentNet  # noqa: E402

from auto_LiRPA import BoundedModule, BoundedTensor, PerturbationLpNorm  # noqa: E402

RESULTS = REPO / "results" / "certify"
# Declared night axis, in the model's affine parameterization.
AMBIENT = (0.02, 0.50)     # ambient road light relative to peak headlight
RETRO = (0.0, 3.0)         # retroreflection amplitude of lane markings


def clear_frames(n):
    base = REPO / "pipeline" / "data" / "conditions"
    with open(base / "manifest.csv") as fh:
        rows = [r for r in csv.DictReader(fh) if r["weather"] == "clear"]
    return [cv2.imread(str(base / r["image"])) for r in rows[:: max(1, len(rows) // n)][:n]]


def bound_box(net, lo, hi, device):
    """alpha-CROWN bound over one axis-aligned box in u-space."""
    k = len(lo)
    centre = torch.zeros(1, k, device=device)
    ptb = PerturbationLpNorm(
        norm=float("inf"),
        x_L=torch.tensor(lo, dtype=torch.float32, device=device).unsqueeze(0),
        x_U=torch.tensor(hi, dtype=torch.float32, device=device).unsqueeze(0))
    bounded = BoundedModule(net, torch.empty_like(centre), device=device)
    lb, ub = bounded.compute_bounds(x=(BoundedTensor(centre, ptb),),
                                    method="CROWN-Optimized")
    return float(lb.min()), float(ub.max())


def certify(img, student, device, w, h, tol, max_cells):
    W, b, lo0, hi0, resid = vd.linear_map_for(
        "night", img, {"ambient": AMBIENT, "retro": RETRO}, w=w, h=h)
    net = nn.Sequential(vd.LinearDisturbance(W, b, (1, 3, h, w)), student).to(device).eval()

    with torch.no_grad():
        clear = float(student(torch.from_numpy(
            vd._project(img.astype(np.float32) / 255.0, w, h)
            .reshape(1, 3, h, w).astype(np.float32)).to(device)).item())
    corridor = (clear - tol, clear + tol)

    # LARGEST-VOLUME-FIRST, not LIFO.
    #
    # This was `stack.pop()`, which is depth-first on the most recently pushed box -- i.e.
    # always the SMALLEST one. It descended into an ever-tinier corner, resolving
    # negligible volume while large undecided siblings sat untouched. Measured symptom:
    # raising the budget from 48 to 400 cells changed the resolved volume by nothing at
    # all, identical to three significant figures. Popping the largest box maximises
    # volume resolved per bound computed, which is the whole point of the budget.
    import heapq
    heap, n, cells = [], 0, []
    ctr = 0
    lo0a, hi0a = np.array(lo0, float), np.array(hi0, float)
    heapq.heappush(heap, (-float(np.prod(hi0a - lo0a)), ctr, lo0a, hi0a))
    while heap and n < max_cells:
        _, _, lo, hi = heapq.heappop(heap)
        l, u = bound_box(net, lo, hi, device)
        n += 1
        vol = float(np.prod(hi - lo))
        if l >= corridor[0] and u <= corridor[1]:
            cells.append(("CERTIFIED", vol))
        elif u < corridor[0] or l > corridor[1]:
            cells.append(("FALSIFIED", vol))
        else:
            d = int(np.argmax(hi - lo))          # split the widest dimension
            mid = 0.5 * (lo[d] + hi[d])
            a_hi = hi.copy(); a_hi[d] = mid
            b_lo = lo.copy(); b_lo[d] = mid
            for sub_lo, sub_hi in ((lo, a_hi), (b_lo, hi)):
                ctr += 1
                heapq.heappush(heap, (-float(np.prod(sub_hi - sub_lo)), ctr,
                                      sub_lo, sub_hi))
    for _, _, lo, hi in heap:                     # budget exhausted
        cells.append(("UNKNOWN", float(np.prod(hi - lo))))

    total = float(np.prod(np.array(hi0, float) - np.array(lo0, float)))
    frac = {v: sum(x for t, x in cells if t == v) / total
            for v in ("CERTIFIED", "FALSIFIED", "UNKNOWN")}
    return clear, resid, frac, n, len(cells)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--student", default="S_clear_84x28")
    ap.add_argument("--frames", type=int, default=10)
    ap.add_argument("--max-cells", type=int, default=64)
    ap.add_argument("--w", type=int, default=84)
    ap.add_argument("--h", type=int, default=28)
    args = ap.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    student = StudentNet(args.h, args.w).to(device)
    student.load_state_dict(torch.load(
        f"{C.CHECKPOINT_DIR}/{args.student}.pth", map_location=device))
    student.eval()
    tol = C.CLOSED_LOOP_TOLERANCE

    print(f"{args.student}, {student.num_relu_neurons()} ReLU | tolerance +/-{tol:.4f}")
    print(f"night axis: ambient {AMBIENT}, retro {RETRO}  (d = 2)")
    print(f"cell budget {args.max_cells} per frame\n")
    print(f"  {'frame':>5s} {'clear':>8s} {'resid':>9s} {'cert':>7s} {'fals':>7s} "
          f"{'unk':>7s} {'bounds':>7s}")
    print("  " + "-" * 56)

    rows = []
    for i, img in enumerate(clear_frames(args.frames)):
        clear, resid, frac, n, ncell = certify(img, student, device, args.w, args.h,
                                               tol, args.max_cells)
        print(f"  {i:5d} {clear:+8.4f} {resid:9.2e} {frac['CERTIFIED']:6.1%} "
              f"{frac['FALSIFIED']:6.1%} {frac['UNKNOWN']:6.1%} {n:7d}")
        rows.append({"frame": i, "clear": clear, "linearity_residual": resid,
                     "certified": frac["CERTIFIED"], "falsified": frac["FALSIFIED"],
                     "unknown": frac["UNKNOWN"], "bounds": n, "cells": ncell})

    cert = np.array([r["certified"] for r in rows])
    unk = np.array([r["unknown"] for r in rows])
    nb = np.array([r["bounds"] for r in rows])
    print("\n" + "=" * 58)
    print(f"  certified : median {np.median(cert):.1%}  mean {cert.mean():.1%}")
    print(f"  UNKNOWN   : median {np.median(unk):.2%}  max {unk.max():.2%}")
    print(f"  bounds    : median {np.median(nb):.0f}  max {nb.max():.0f}  "
          f"total {nb.sum():.0f}")
    print(f"  d = 2 against fog's d = 1: compare bounds/frame to see the k^d cost")
    print("=" * 58)

    path = RESULTS / f"night_{args.student}.json"
    with open(path, "w") as fh:
        json.dump({"student": args.student, "tolerance": tol,
                   "ambient": AMBIENT, "retro": RETRO, "frames": rows}, fh, indent=2)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    sys.exit(main())

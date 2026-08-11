#!/usr/bin/env python3
"""Certify a student over the fog axis by adaptive branch-and-bound. No CARLA.

This is the M6 machinery in miniature, on one condition and one frame.

The deliverable is NOT a single verdict over the whole visibility range -- the network
genuinely varies more than the tolerance across it, so no sound verifier could return one.
It is a **set of MOR sub-ranges** with a verdict each, which is the "bounded region of the
ODD" the study exists to produce.

Certification criterion, per trap 6: the corridor is centred on **clear-weather steering**,
not on the disturbed midpoint. Centring on the midpoint certifies only insensitivity to the
disturbance parameter while permitting an arbitrary systematic offset from what clear
weather would produce -- which is the actual hazard, and the bug that once made night read
100% certified while failing 85% of closed-loop frames.

    CERTIFIED  bound entirely inside [clear - tol, clear + tol]
    FALSIFIED  bound entirely outside            (a real violation exists)
    UNKNOWN    straddles the corridor edge       -> split, up to max depth

Transmission is per-pixel (per-row here), never banded -- see FINDINGS F8.

    python scripts/certify_fog.py --student S_clear_84x28 --max-depth 8
"""

import argparse
import csv
import json
import sys
from pathlib import Path

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

RESULTS = REPO / "results" / "certify"
AIRLIGHT = np.array([0.76, 0.78, 0.78], np.float32).reshape(1, 1, 3)


def frames(n):
    base = REPO / "pipeline" / "data" / "conditions"
    import cv2
    rows = [r for r in csv.DictReader(open(base / "manifest.csv"))
            if r["weather"] == "clear"]
    picks = rows[:: max(1, len(rows) // n)][:n]
    return [cv2.imread(str(base / r["image"])) for r in picks]


def veil_rows(xf, t_rows):
    return AIRLIGHT + t_rows.astype(np.float32).reshape(-1, 1, 1) * (xf - AIRLIGHT)


def proj(y, w, h):
    return vd._project(y.astype(np.float32), w, h).reshape(-1).astype(np.float32)


def cell_bound(xf, lo_m, hi_m, student, device, w, h):
    """alpha-CROWN bound on steering over one MOR sub-interval, rank-1 in one scalar."""
    H = xf.shape[0]
    t_lo = dm.transmission(H, lo_m, dm.CARLA_GEOM)
    t_hi = dm.transmission(H, hi_m, dm.CARLA_GEOM)
    tbar, delta = 0.5 * (t_lo + t_hi), 0.5 * (t_hi - t_lo)
    b = proj(veil_rows(xf, tbar), w, h)
    W = (proj(veil_rows(xf, tbar + delta), w, h) - b).reshape(-1, 1)

    net = nn.Sequential(vd.LinearDisturbance(W, b, (1, 3, h, w)), student).to(device).eval()
    centre = torch.zeros(1, 1, device=device)
    ptb = PerturbationLpNorm(norm=float("inf"),
                             x_L=torch.full((1, 1), -1.0, device=device),
                             x_U=torch.full((1, 1), 1.0, device=device))
    bounded = BoundedModule(net, torch.empty_like(centre), device=device)
    lb, ub = bounded.compute_bounds(x=(bounded_input := BoundedTensor(centre, ptb),),
                                    method="CROWN-Optimized")
    del bounded_input
    return float(lb.min()), float(ub.max())


def certify(xf, student, device, w, h, mor_lo, mor_hi, tol, max_depth):
    """Adaptive bisection. Returns (cells, n_bounds_computed)."""
    with torch.no_grad():
        clear = float(student(torch.from_numpy(
            proj(xf, w, h).reshape(1, 3, h, w)).to(device)).item())
    corridor = (clear - tol, clear + tol)

    cells, stack, n = [], [(mor_lo, mor_hi, 0)], 0
    while stack:
        lo_m, hi_m, depth = stack.pop()
        l, u = cell_bound(xf, lo_m, hi_m, student, device, w, h)
        n += 1
        if l >= corridor[0] and u <= corridor[1]:
            cells.append((lo_m, hi_m, "CERTIFIED", l, u))
        elif u < corridor[0] or l > corridor[1]:
            cells.append((lo_m, hi_m, "FALSIFIED", l, u))
        elif depth >= max_depth:
            cells.append((lo_m, hi_m, "UNKNOWN", l, u))
        else:
            mid = 0.5 * (lo_m + hi_m)
            stack += [(lo_m, mid, depth + 1), (mid, hi_m, depth + 1)]
    return clear, corridor, sorted(cells), n


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--student", default="S_clear_84x28")
    ap.add_argument("--frames", type=int, default=3)
    ap.add_argument("--mor-lo", type=float, default=60.0)
    ap.add_argument("--mor-hi", type=float, default=2000.0)
    ap.add_argument("--max-depth", type=int, default=7)
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
    print(f"fog axis {args.mor_hi:.0f} -> {args.mor_lo:.0f} m MOR, max depth {args.max_depth}\n")

    report = []
    for i, img in enumerate(frames(args.frames)):
        xf = img.astype(np.float32) / 255.0
        clear, corridor, cells, n = certify(xf, student, device, args.w, args.h,
                                            args.mor_lo, args.mor_hi, tol, args.max_depth)
        span = args.mor_hi - args.mor_lo
        cert = sum(hi - lo for lo, hi, v, _, _ in cells if v == "CERTIFIED") / span
        fals = sum(hi - lo for lo, hi, v, _, _ in cells if v == "FALSIFIED") / span
        unk = sum(hi - lo for lo, hi, v, _, _ in cells if v == "UNKNOWN") / span
        print(f"  frame {i}: clear steer {clear:+.4f} | {n} bounds, {len(cells)} cells")
        print(f"    certified {cert:6.1%}   falsified {fals:6.1%}   unknown {unk:6.1%}")
        # the certified sub-ranges ARE the deliverable
        certified = [(lo, hi) for lo, hi, v, _, _ in cells if v == "CERTIFIED"]
        if certified:
            merged = [list(certified[0])]
            for lo, hi in certified[1:]:
                if abs(lo - merged[-1][1]) < 1e-6:
                    merged[-1][1] = hi
                else:
                    merged.append([lo, hi])
            print("    certified MOR ranges: "
                  + ", ".join(f"[{a:.0f},{b:.0f}]" for a, b in merged[:6])
                  + (" ..." if len(merged) > 6 else ""))
        report.append({"frame": i, "clear": clear, "bounds_computed": n,
                       "cells": len(cells), "certified_frac": cert,
                       "falsified_frac": fals, "unknown_frac": unk,
                       "cells_detail": [[lo, hi, v, l, u] for lo, hi, v, l, u in cells]})
        print()

    mean_n = np.mean([r["bounds_computed"] for r in report])
    print("=" * 66)
    print(f"  mean {mean_n:.0f} bound computations per frame to resolve the axis")
    print("  Each is seconds. Localizing the same boundary by closed-loop sampling would")
    print("  need >= 10 repetitions per probe point at ~1 min per lap -- that ratio is the")
    print("  efficiency argument, and it is now measurable rather than asserted.")
    print("=" * 66)

    path = RESULTS / f"fog_{args.student}.json"
    with open(path, "w") as fh:
        json.dump({"student": args.student, "tolerance": tol,
                   "axis": [args.mor_lo, args.mor_hi], "frames": report}, fh, indent=2)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    sys.exit(main())

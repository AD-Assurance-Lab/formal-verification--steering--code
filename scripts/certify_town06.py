#!/usr/bin/env python3
"""Certify the Town06 students. BLIND: this tool has no truth table.

PROTOCOL R2. `certify_sustained_bound.py` carries a hardcoded TRUTH dict and prints an
agreement column, which is right for the Town04 discovery test, where the outcomes were
already known and the point was to score a criterion against them. It is exactly wrong
here. A held-out cell must not be scored by the tool that predicts it, so this script
cannot print agreement even if someone wants it to: there is nothing to compare against.

The bound math is IDENTICAL to the Town04 certifier, deliberately and line for line:
alpha-CROWN over the one-parameter family with `nsplit` branch-and-bound sub-intervals,
route-mean (sustained) bias, compared against config.CLOSED_LOOP_TOLERANCE. The frozen
constants come from PROTOCOL.md section 3 and this script refuses to run if the lock
has moved.

    STUDY_MAP=Town06 python3 scripts/certify_town06.py

Then COMMIT the output before any scored closed-loop run (PROTOCOL R1).
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "scripts"))

from check_protocol_lock import require_locked  # noqa: E402

import config as C  # noqa: E402
import certify_cell as cc  # noqa: E402
from student import StudentNet  # noqa: E402
from study import town06_design as D  # noqa: E402

# The Town06 students. Same shapes as the published pair; different weights.
STUDENTS = (("S_clear_t06", "S_clear_t06_84x28", (8, 16, 16), 32),
            ("S_mixed_t06", "S_mixed_t06_84x28_w3", (24, 48, 48), 96))

CAPTURES = REPO / "results" / "town06" / "captures"
OUT = REPO / D.CERT_ARTIFACT


def nominal(path, cond):
    z = np.load(path, allow_pickle=True)
    conds = [str(c) for c in z["conds"]]
    if cond not in conds:
        return None
    fr = z["frames"][conds.index(cond)]
    oi = int(np.argmin(np.abs(z["offsets"])))
    yi = int(np.argmin(np.abs(z["yaws"])))
    return fr[oi, yi]


def baseline_for(cond_path, fallback):
    """Paired clear baseline if the condition capture recorded its own, else foreign.

    F43: a clear baseline from a different session shifts the bound materially. Which
    one was used is printed and recorded, never chosen silently.
    """
    own = nominal(cond_path, "clear")
    return (own, "paired") if own is not None else (fallback, "foreign")


def git_head():
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stride", type=int, default=8, help="pose subsampling (frozen: 8)")
    ap.add_argument("--nsplit", type=int, default=16, help="BaB sub-intervals (frozen: 16)")
    ap.add_argument("--allow-missing", action="store_true")
    args = ap.parse_args()

    require_locked()
    if C.STUDY_MAP != "Town06":
        sys.exit("run with STUDY_MAP=Town06")
    if (args.stride, args.nsplit) != (8, 16):
        sys.exit(f"PROTOCOL section 3 freezes stride=8 and nsplit=16; "
                 f"got {args.stride}/{args.nsplit}. Changing either is an amendment.")

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tol = C.CLOSED_LOOP_TOLERANCE
    conds = ("fog", "night", "shadows")

    need = [f"lap_{d}_{c}.npz" for d in D.DIRECTIONS for c in conds]
    need += [f"lap_{d}_clear.npz" for d in D.DIRECTIONS]
    missing = [m for m in need if not (CAPTURES / m).exists()]
    if missing and not args.allow_missing:
        print(f"REFUSING TO RUN: {len(missing)} capture(s) absent from {CAPTURES}:",
              file=sys.stderr)
        for m in missing:
            print(f"    {m}", file=sys.stderr)
        return 2

    n_expected = len(D.DIRECTIONS) * len(conds) * len(STUDENTS)
    print(f"\nTOWN06 DEPLOYMENT-TEST CERTIFICATE (blind)   tolerance {tol:.6f}")
    print(f"  stride {args.stride}, {args.nsplit}-way BaB, {n_expected} cells expected")
    print(f"  T_CLOSED_LOOP_S = {C.T_CLOSED_LOOP_S} (frozen, inherited from Town04)\n")
    print(f"  {'dir':10s} {'model':12s} {'cond':9s} {'base':8s} {'bias bound':>22s}"
          f" {'x tol':>14s}  verdict")

    out, n = {}, 0
    for direction in D.DIRECTIONS:
        base = CAPTURES / f"lap_{direction}_clear.npz"
        if not base.exists():
            continue
        fallback = nominal(base, "clear")
        bl = {}
        for cond in conds:
            p = CAPTURES / f"lap_{direction}_{cond}.npz"
            if p.exists():
                bl[cond] = baseline_for(p, fallback)
        for nm, ck, ch, fc in STUDENTS:
            wpath = Path(C.CHECKPOINT_DIR) / f"{ck}.pth"
            if not wpath.exists():
                sys.exit(f"missing checkpoint {wpath}")
            net = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
            net.load_state_dict(torch.load(wpath, map_location=dev, weights_only=True))
            net.eval()
            bd = cc.Bounder(1, net, dev, 28, 84, method="CROWN")
            for cond in conds:
                p = CAPTURES / f"lap_{direction}_{cond}.npz"
                if not p.exists():
                    continue
                clr, origin = bl[cond]
                dis = nominal(p, cond)
                if dis is None or len(dis) != len(clr):
                    print(f"  {direction:10s} {nm:12s} {cond:9s} "
                          f"{'LENGTH MISMATCH':>22s}")
                    continue
                with torch.no_grad():
                    sc = net(torch.from_numpy(clr[::args.stride]).to(dev)
                             ).cpu().numpy().reshape(-1)
                los, his = [], []
                for i, k in enumerate(range(0, len(clr), args.stride)):
                    x0 = clr[k].reshape(-1).astype(np.float32)
                    x1 = dis[k].reshape(-1).astype(np.float32)
                    lo_i, hi_i = [], []
                    for j in range(args.nsplit):
                        a, b = j / args.nsplit, (j + 1) / args.nsplit
                        mid, half = 0.5 * (a + b), 0.5 * (b - a)
                        W = (half * (x1 - x0)).reshape(-1, 1)
                        l_, u_ = bd(W, x0 + mid * (x1 - x0),
                                    np.array([-1.0]), np.array([1.0]))
                        lo_i.append(l_)
                        hi_i.append(u_)
                    los.append(min(lo_i) - sc[i])
                    his.append(max(hi_i) - sc[i])
                blo, bhi = float(np.mean(los)), float(np.mean(his))
                # "Safe for EVERY intensity", so any violation declines the certificate.
                # NOT_CERTIFIED, never FALSIFIED: a sound over-approximation proves
                # safety and cannot prove danger.
                v = "CERTIFIED" if (bhi <= tol and blo >= -tol) else "NOT_CERTIFIED"
                n += 1
                out[f"{direction}/{nm}/{cond}"] = dict(
                    lo=blo, hi=bhi, lo_x_tol=blo / tol, hi_x_tol=bhi / tol,
                    verdict=v, baseline=origin)
                print(f"  {direction:10s} {nm:12s} {cond:9s} {origin:8s} "
                      f"[{blo:+.5f},{bhi:+.5f}] [{blo/tol:+6.2f},{bhi/tol:+6.2f}]"
                      f"  {v}", flush=True)

    print(f"\n  {n}/{n_expected} cells certified-or-not. NO agreement column: this is a "
          f"prediction,\n  and the closed-loop runs that test it have not happened yet.")
    if n != n_expected:
        print(f"  WARNING: {n_expected - n} cell(s) did not run.")

    out["_meta"] = dict(
        map=C.STUDY_MAP, nsplit=args.nsplit, stride=args.stride, tolerance=tol,
        t_closed_loop_s=C.T_CLOSED_LOOP_S, lane_width_m=C.LANE_WIDTH_M,
        cte_budget_m=C.CTE_BUDGET_M, lap_end_m=C.LAP_END_M,
        cells_expected=n_expected, cells_scored=n, git_commit=git_head(), device=dev,
        torch=torch.__version__, numpy=np.__version__,
        blind="no truth table; agreement is not computable by this tool")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\n  wrote {OUT.relative_to(REPO)}")
    print("  COMMIT THIS FILE before running any scored closed-loop cell (PROTOCOL R1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

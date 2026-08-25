#!/usr/bin/env python3
"""Certify a HELD-OUT condition, blind: verdicts only, no ground truth anywhere.

`certify_sustained_bound.py` carries a hardcoded TRUTH table so it can print an
agreement column. That is fine for the canonical cells, whose closed-loop outcomes were
already known when the criterion was chosen -- and it is exactly what must NOT happen
for a held-out cell.

This script therefore has no truth table, prints no agreement column, and cannot: the
verdicts it writes are a PREDICTION. The protocol is

    1. capture the condition, paired with its own clear (F43/D-11)
    2. run this, commit the verdicts to git
    3. only then drive the closed loop
    4. score

and `python -m study.ledger --check-order` verifies step 2 preceded step 3 against git
history. Every criterion in this project scored well in-sample and worse out-of-sample
(14/14 -> 2/6, 7/8 -> 3/7, 8/8 -> 6/10, 10/10 -> 2/4), so an in-sample number is not
evidence and this is the only kind of test that is.

The arithmetic is identical to the canonical certifier -- same bound, same statistic,
same NSPLIT -- so a difference in outcome cannot be blamed on a difference in method.

    python scripts/certify_heldout.py --condition <held-out condition>
"""
import sys
import json
import argparse
import subprocess
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
import certify_cell as cc  # noqa: E402
from student import StudentNet  # noqa: E402


def nominal(path, cond):
    z = np.load(path, allow_pickle=True)
    conds = [str(c) for c in z["conds"]]
    if cond not in conds:
        return None
    fr = z["frames"][conds.index(cond)]
    oi = int(np.argmin(np.abs(z["offsets"])))
    yi = int(np.argmin(np.abs(z["yaws"])))
    fr = fr[:, oi, yi]
    px, py = z["pose_x"], z["pose_y"]
    d = np.concatenate([[0], np.cumsum(np.hypot(np.diff(px), np.diff(py)))])
    return fr[:int(np.searchsorted(d, C.LAP_END_M))]


def git_head():
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--condition", required=True, help="held-out condition name")
    ap.add_argument("--stride", type=int, default=8)
    ap.add_argument("--nsplit", type=int, default=16)
    args = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tol = C.CLOSED_LOOP_TOLERANCE
    cal = REPO / "results" / "calibration"

    print(f"\nHELD-OUT CERTIFICATE -- {args.condition}   (BLIND: no ground truth loaded)")
    print(f"  tolerance {tol:.4f}, stride {args.stride}, {args.nsplit}-way BaB\n")
    print(f"  {'dir':10s} {'model':9s} {'base':8s} {'bias bound':>22s} {'x tol':>12s}"
          f"  verdict")

    out, n = {}, 0
    for direction in ("westbound", "eastbound"):
        p = cal / f"lap_{direction}_{args.condition}.npz"
        if not p.exists():
            print(f"  {direction:10s} capture missing: {p.name}")
            continue
        # Same-session baseline is mandatory here: a cross-session clear endpoint once
        # inverted the sign of a fog measurement (F43).
        clr = nominal(p, "clear")
        if clr is None:
            print(f"  {direction:10s} REFUSING: {p.name} has no internal clear baseline",
                  file=sys.stderr)
            return 2
        dis = nominal(p, args.condition)
        if dis is None or len(dis) != len(clr):
            print(f"  {direction:10s} REFUSING: condition frames absent or length-mismatched",
                  file=sys.stderr)
            return 2

        for nm, ck, ch, fc in C.STUDENTS:
            net = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
            net.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth",
                                           map_location=dev, weights_only=True))
            net.eval()
            bd = cc.Bounder(1, net, dev, 28, 84, method="CROWN")
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
                    l_, u_ = bd((half * (x1 - x0)).reshape(-1, 1), x0 + mid * (x1 - x0),
                                np.array([-1.0]), np.array([1.0]))
                    lo_i.append(l_)
                    hi_i.append(u_)
                los.append(min(lo_i) - sc[i])
                his.append(max(hi_i) - sc[i])
            blo, bhi = float(np.mean(los)), float(np.mean(his))
            v = "CERTIFIED" if (bhi <= tol and blo >= -tol) else "NOT CERTIFIED"
            out[f"{direction}/{nm}/{args.condition}"] = dict(
                lo=blo, hi=bhi, verdict=v, baseline="paired")
            n += 1
            print(f"  {direction:10s} {nm:9s} {'paired':8s} "
                  f"[{blo:+.5f},{bhi:+.5f}] [{blo/tol:+5.2f},{bhi/tol:+5.2f}]"
                  f"  {v}", flush=True)

    out["_meta"] = dict(condition=args.condition, nsplit=args.nsplit, stride=args.stride,
                        tolerance=tol, cells=n, git_commit=git_head(), device=dev,
                        blind=True, truth_loaded=False)
    dest = REPO / "results" / "predictions" / f"heldout_{args.condition}_verdicts.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"\n  -> {dest.relative_to(REPO)}")
    print("  COMMIT THIS BEFORE DRIVING. That commit is what makes it a prediction.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

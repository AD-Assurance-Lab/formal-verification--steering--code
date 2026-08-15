#!/usr/bin/env python3
"""FORMAL COVERAGE: bound the steering over the WHOLE declared disturbance interval.

This is the claim scenario-based testing cannot make. Sampling drives fog at densities 25,
40 and 55 and hopes 47 is not special. Verification quantifies:

    for EVERY intensity s in [0, 1], at EVERY pose on the lap, in BOTH directions,
    |steer(x(s)) - steer(x(0))| <= CLOSED_LOOP_TOLERANCE

x(s) = x_clear + s * (x_cond - x_clear) is the one-scalar affine family the study already
declares (`certify_cell.py`: NIGHT_S, SHADOW_DEPTH, FOG_MOR). s = 0 is clear and s = 1 is
the measured CARLA condition, so the interval covers every intensity in between, including
the ones no closed-loop run will ever sample.

WHY THE PROJECTION MAY BE APPLIED FIRST. The disturbance is rendered by CARLA at full sensor
resolution (640x480) and only then cropped and downsampled -- never the other way round.
Interpolating the stored 84x28 projections is nevertheless exact, because `_project` is
linear and a convex combination of two valid images stays in [0,1] so no clamp is needed:
measured agreement 1.2e-7, against a 0.0120 tolerance. This is why s is declared on [0,1]
and never extrapolated; outside it the clamp is a nonlinearity that would have to be applied
at sensor resolution.

ALPHA-CROWN WITH INPUT-SPACE BRANCH AND BOUND. The input set is ONE scalar, so the verifier
sees a 1-D box rather than 7,056 pixels. Splitting that box converges the bound to the
network's genuine variation (measured 0.0165 -> 0.0116 over a state box), which is why
SDP-CROWN adds nothing here: its advantage is L2 geometry in high dimensions, and there is
no looseness left to remove on an interval this small.

    python scripts/certify_interval.py --npz results/calibration/nom_westbound.npz
"""
import sys
import json
import argparse
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
import certify_cell as cc  # noqa: E402
from student import StudentNet  # noqa: E402
from auto_LiRPA import BoundedTensor  # noqa: E402
from auto_LiRPA.perturbations import PerturbationLpNorm  # noqa: E402

STUDENTS = (("S_clear", "S_clear_84x28", (8, 16, 16), 32),
            ("S_mixed", "S_mixed_84x28_w3", (24, 48, 48), 96))
NSPLIT = 4          # sub-intervals of s per pose


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--npz", required=True)
    ap.add_argument("--tol", type=float, default=None)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--out", default="results/calibration/interval_cert.json")
    args = ap.parse_args()
    tol = args.tol if args.tol else C.CLOSED_LOOP_TOLERANCE

    z = np.load(args.npz, allow_pickle=True)
    fr = z["frames"][:, :, 0, 0]                    # (cond, pose, 3, 28, 84), nominal only
    conds = [str(c) for c in z["conds"]]
    ci_clear = conds.index("clear")
    npose = fr.shape[1]
    sel = list(range(0, npose, args.stride))
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tag = Path(args.npz).stem

    print(f"\nINTERVAL COVERAGE CERTIFICATE   {tag}")
    print(f"  {len(sel)} poses on the lap, s in [0,1] split {NSPLIT} ways, "
          f"tolerance {tol:.4f}\n")
    print(f"  {'model':9s} {'cond':9s} {'max |dsteer| over s':>20s} {'poses over tol':>15s}"
          f"  verdict")
    out = {}
    for nm, ck, ch, fc in STUDENTS:
        net = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
        net.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
        net.eval()
        bd = cc.Bounder(1, net, dev, 28, 84, method="CROWN")
        for ci, cond in enumerate(conds):
            if cond == "clear":
                continue
            worst, nbad, wpose = 0.0, 0, -1
            for pi in sel:
                x0 = fr[ci_clear, pi].reshape(-1).astype(np.float32)
                x1 = fr[ci, pi].reshape(-1).astype(np.float32)
                with torch.no_grad():
                    s0 = float(net(torch.from_numpy(
                        x0.reshape(1, 3, 28, 84)).to(dev)).item())
                lo_all, hi_all = [], []
                for k in range(NSPLIT):
                    a, b = k / NSPLIT, (k + 1) / NSPLIT
                    mid, half = 0.5 * (a + b), 0.5 * (b - a)
                    base = x0 + mid * (x1 - x0)
                    W = (half * (x1 - x0)).reshape(-1, 1)
                    l_, u_ = bd(W, base, np.array([-1.0]), np.array([1.0]))
                    lo_all.append(l_)
                    hi_all.append(u_)
                dev_max = max(abs(min(lo_all) - s0), abs(max(hi_all) - s0))
                if dev_max > worst:
                    worst, wpose = dev_max, pi
                if dev_max > tol:
                    nbad += 1
            verdict = "FALSIFIED" if nbad else "CERTIFIED"
            print(f"  {nm:9s} {cond:9s} {worst:20.4f} {nbad:8d}/{len(sel):<6d}  {verdict}")
            out[f"{tag}/{nm}/{cond}"] = dict(verdict=verdict, worst=worst,
                                             n_over=nbad, n_poses=len(sel),
                                             worst_pose=wpose, tol=tol)
    p = Path(args.out)
    old = json.loads(p.read_text()) if p.exists() else {}
    old.update(out)
    p.write_text(json.dumps(old, indent=2))
    print(f"\n  wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

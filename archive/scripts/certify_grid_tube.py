#!/usr/bin/env python3
"""Reachable set as a UNION OF BOXES on a grid -- no wrapping, no single-set blow-up.

WHY NOT A ZONOTOPE. A single propagated set widens until it spans several captured offset
cells; taking min/max of the linear relations across those cells then weakens the effective
restoring gain and inflates the constant spread, which widens it further. Measured, that
runaway takes the tube from 0.05 m to 0.90 m in eleven steps and diverges, while the tube
CENTRE stays correctly within 0.05 m and a point rollout on the same data peaks at 0.29 m.
The blow-up is the abstraction, not the vehicle.

A union of small boxes has no such feedback: each box is bounded on its own, entirely inside
one captured cell, so the relaxation gap stays at its small-box value and cross-cell
disagreement is represented as separate reachable pieces rather than smeared into one wide
interval. This is standard discretized reachability, and the cost is grid resolution rather
than soundness -- successor boxes are rounded OUTWARD onto the grid.

Each box is bounded with the same 3-scalar input set as before (offset, heading, and the
lifted bilinear cross term, which makes the interpolation an over-approximation rather than
an approximation). The surrogate underneath was validated first:

    gate A  captured steer at (0,0) vs driven:  clear 0.006, shadows 0.010
    gate B  rollout departs at x=9.0 y=125.4;  real run departs at x=8.1 y=123.9

    python scripts/certify_grid_tube.py --student S_clear
"""
import sys
import json
import math
import argparse
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "scripts"))

import config as C  # noqa: E402
from student import StudentNet  # noqa: E402
import certify_cell as cc  # noqa: E402
from auto_LiRPA import BoundedTensor  # noqa: E402
from auto_LiRPA.perturbations import PerturbationLpNorm  # noqa: E402

NPZ = REPO / "results" / "calibration" / "oy_dense_shadow.npz"
STUDENTS = {"S_clear": ("S_clear_84x28", (8, 16, 16), 32),
            "S_mixed": ("S_mixed_84x28_w3", (24, 48, 48), 96)}
DO = 0.05                      # offset grid, m
DPSI = math.radians(0.5)       # heading grid, rad
MAXBOX = 400                   # occupancy cap; exceeded means the set has genuinely spread


class Bounder3:
    """Steer bounds over one (pose, offset-box, heading-box), cached on the grid."""

    def __init__(self, frames, off, yr, net, dev):
        self.fr, self.off, self.yr, self.dev = frames, off, yr, dev
        self.bd = cc.Bounder(3, net, dev, 28, 84, method="CROWN")
        self.cache = {}
        self.calls = 0

    def __call__(self, pi, io, jo):
        """io, jo are integer grid indices; the box is [io*DO,(io+1)*DO] x [jo*DPSI,...]."""
        key = (pi, io, jo)
        if key in self.cache:
            return self.cache[key]
        o0, o1 = io * DO, (io + 1) * DO
        y0, y1 = jo * DPSI, (jo + 1) * DPSI
        i = int(np.clip(np.searchsorted(self.off, 0.5 * (o0 + o1)) - 1,
                        0, len(self.off) - 2))
        j = int(np.clip(np.searchsorted(self.yr, 0.5 * (y0 + y1)) - 1,
                        0, len(self.yr) - 2))
        a = self.fr[pi, i, j].reshape(-1).astype(np.float32)
        b = self.fr[pi, i + 1, j].reshape(-1).astype(np.float32)
        c = self.fr[pi, i, j + 1].reshape(-1).astype(np.float32)
        d = self.fr[pi, i + 1, j + 1].reshape(-1).astype(np.float32)
        xc = 0.25 * (a + b + c + d)
        W = np.stack([0.25 * (b + d - a - c), 0.25 * (c + d - a - b),
                      0.25 * (d - b - c + a)], 1).astype(np.float32)
        self.bd._bind(W, xc)
        oc, oh = 0.5 * (self.off[i] + self.off[i + 1]), 0.5 * (self.off[i + 1] - self.off[i])
        yc, yh = 0.5 * (self.yr[j] + self.yr[j + 1]), 0.5 * (self.yr[j + 1] - self.yr[j])
        tlo = np.clip([(o0 - oc) / oh, (y0 - yc) / yh, -1.0], -1.0, 1.0).astype(np.float32)
        thi = np.clip([(o1 - oc) / oh, (y1 - yc) / yh, 1.0], -1.0, 1.0).astype(np.float32)
        ptb = PerturbationLpNorm(
            norm=float("inf"),
            x_L=torch.tensor(tlo, device=self.dev).unsqueeze(0),
            x_U=torch.tensor(thi, device=self.dev).unsqueeze(0))
        lb, ub = self.bd.bounded.compute_bounds(
            x=(BoundedTensor(self.bd.centre, ptb),), method="CROWN")
        out = (float(lb.min()), float(ub.max()))
        self.calls += 1
        self.cache[key] = out
        return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--student", default="S_clear", choices=list(STUDENTS))
    ap.add_argument("--out", default="results/calibration/grid_tube.json")
    args = ap.parse_args()

    z = np.load(NPZ, allow_pickle=True)
    frames, off, yaws = z["frames"], z["offsets"], np.radians(z["yaws"])
    conds = [str(c) for c in z["conds"]]
    px, py, pyaw = z["pose_x"], z["pose_y"], z["pose_yaw"]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    v, L, MS, dt = C.TARGET_SPEED_MS, C.WHEELBASE_M, C.MAX_STEER_RAD, C.FIXED_DT

    ck, ch, fc = STUDENTS[args.student]
    net = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
    net.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
    net.eval()

    print(f"\nGRID REACHABLE SET   {args.student}, {len(px)} poses, "
          f"budget {C.CTE_BUDGET_M:.3f} m")
    print(f"  grid {DO} m x {math.degrees(DPSI)} deg, successors rounded OUTWARD\n")
    print(f"  {'cond':9s} {'steps':>6s} {'peak |o| (m)':>13s} {'boxes':>6s} "
          f"{'bounds':>7s}  verdict")
    out = {}
    for ci, cond in enumerate(conds):
        bd = Bounder3(frames[ci], off, yaws, net, dev)
        occ = {(0, 0)}
        peak, steps, esc = 0.0, 0, False
        for pi in range(len(px) - 1):
            ya, yb = math.radians(float(pyaw[pi])), math.radians(float(pyaw[pi + 1]))
            dyaw = math.atan2(math.sin(yb - ya), math.cos(yb - ya))
            ds = float(np.hypot(px[pi + 1] - px[pi], py[pi + 1] - py[pi]))
            nst = max(1, int(round(ds / (v * dt))))
            for _ in range(nst):
                nxt = set()
                for (io, jo) in occ:
                    slo, shi = bd(pi, io, jo)
                    dlo = math.tan(max(-1.0, slo) * MS)
                    dhi = math.tan(min(1.0, shi) * MS)
                    y0, y1 = jo * DPSI, (jo + 1) * DPSI
                    o0, o1 = io * DO, (io + 1) * DO
                    ny0 = y0 + (v / L) * dlo * dt - dyaw / nst
                    ny1 = y1 + (v / L) * dhi * dt - dyaw / nst
                    no0 = o0 + v * y0 * dt
                    no1 = o1 + v * y1 * dt
                    for ii in range(int(math.floor(no0 / DO)),
                                    int(math.floor(no1 / DO)) + 1):
                        for jj in range(int(math.floor(ny0 / DPSI)),
                                        int(math.floor(ny1 / DPSI)) + 1):
                            nxt.add((ii, jj))
                occ = nxt
                if not occ:
                    break
                lo = min(i for i, _ in occ) * DO
                hi = (max(i for i, _ in occ) + 1) * DO
                peak = max(peak, abs(lo), abs(hi))
                if len(occ) > MAXBOX or peak > 2.0:
                    esc = True
                    break
            steps = pi + 1
            if esc:
                break
            if pi % 40 == 0:
                lo = min(i for i, _ in occ) * DO
                hi = (max(i for i, _ in occ) + 1) * DO
                print(f"      {cond} pose {pi:3d}  o=[{lo:+.2f},{hi:+.2f}]  "
                      f"{len(occ)} boxes", flush=True)
        verdict = "FAIL" if (esc or peak > C.CTE_BUDGET_M) else "PASS"
        tag = "  (set spread past the captured range)" if esc else ""
        print(f"  {cond:9s} {steps:6d} {peak:13.3f} {len(occ):6d} {bd.calls:7d}  "
              f"{verdict}{tag}")
        out[f"{args.student}/{cond}"] = dict(peak=peak, steps=steps, escaped=esc,
                                             verdict=verdict, bounds=bd.calls)
    p = Path(args.out)
    old = json.loads(p.read_text()) if p.exists() else {}
    old.update(out)
    p.write_text(json.dumps(old, indent=2))
    print(f"\n  wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

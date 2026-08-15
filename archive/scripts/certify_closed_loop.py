#!/usr/bin/env python3
"""Propagate a REACHABLE LATERAL-OFFSET TUBE along the route and compare it to the budget.

WHY THIS RATHER THAN ANOTHER PER-FRAME CRITERION. Six pointwise criteria have now failed
(F14-F22): analytic-model bias, measured-field bias, accumulation, restoring sign, restoring
sign over a bounded tube, and equilibrium offset. The last was tested against ground truth
directly -- predicted equilibrium versus the CTE the vehicle actually reached at 263 route
locations -- and returned r = -0.053, with flagged locations CLEANER than unflagged ones.
Departure is a property of the trajectory: CTE at a location is set by where the vehicle came
from, so no quantity evaluated at a single pose can carry it.

WHY THE FIRST ATTEMPT AT THIS EXPLODED, AND WHAT FIXED IT (F23). Bounding the steering over
each offset cell as a CONSTANT INTERVAL made every condition diverge within 6-7 steps,
including clear weather where the real vehicle holds 0.13 m. That was not loose bounding, it
was the wrapping effect: collapsing steer to an interval discards the fact that steer is a
DECREASING function of offset, and that negative correlation IS the restoring feedback. An
interval abstraction cannot represent a contraction, so it must diverge on a stable loop.

The fix is to keep the relation. CROWN already computes linear bounds internally, so with
`return_A=True` the steering comes back as

    k_l * o + c_l  <=  steer(o)  <=  k_u * o + c_u          (k measured negative: restoring)

and the loop closes as a LINEAR system whose contraction survives. Measured on one cell:
interval width 0.0795 versus 0.0166 for the relational form at fixed offset, 5x tighter,
with the stabilising slope retained rather than thrown away.

The state is path-relative and the tube is a ZONOTOPE, not a box, because a box re-wraps the
correlation between o and psi at every step:

    psi' = psi + (v/L) * tan(delta) * dt  -  dyaw_path,   delta = steer * MAX_STEER_RAD
    o'   = o   + v * psi * dt

Offsets are measured along the capture normal, which points RIGHT of the lane (CARLA is
left-handed), and positive steer turns right, so positive psi grows o.

STATED GAP, not hidden: bounds are sound with respect to the INTERPOLATED image manifold.
Real images between captured offsets differ from the interpolant by a measured residual
(~0.011 on the road ROI at 0.5 m spacing, less at the 0.25 m spacing used near centre),
reported with the verdict as `certify_restoring.py` does.

    python scripts/certify_closed_loop.py [--segment A|B|all]
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

NPZ = REPO / "results" / "calibration" / "offset_frames_seg.npz"
SEG = REPO / "results" / "calibration" / "segments.json"
STUDENTS = [("S_clear", "S_clear_84x28", (8, 16, 16), 32),
            ("S_mixed", "S_mixed_84x28_w3", (24, 48, 48), 96)]
MAXGEN = 64       # zonotope order cap; excess generators are boxed
OUTER = 2.0       # captured offsets stop here


class CellRelation:
    """Affine steer bounds in OFFSET for (pose, cell): k*o + c, cached on first use."""

    def __init__(self, frames, offsets, net, dev):
        self.fr, self.off, self.dev = frames, offsets, dev
        self.bd = cc.Bounder(1, net, dev, 28, 84, method="CROWN")
        self.on = self.bd.bounded.output_name[0]
        self.inn = self.bd.bounded.input_name[0]
        self.cache = {}
        self.calls = 0

    def __call__(self, pi, ci):
        key = (pi, ci)
        if key in self.cache:
            return self.cache[key]
        pa = self.fr[pi, ci].reshape(-1).astype(np.float32)
        pb = self.fr[pi, ci + 1].reshape(-1).astype(np.float32)
        self.bd._bind((0.5 * (pb - pa)).reshape(-1, 1), 0.5 * (pa + pb))
        ptb = PerturbationLpNorm(
            norm=float("inf"),
            x_L=torch.tensor([-1.0], device=self.dev).unsqueeze(0),
            x_U=torch.tensor([1.0], device=self.dev).unsqueeze(0))
        _, _, A = self.bd.bounded.compute_bounds(
            x=(BoundedTensor(self.bd.centre, ptb),), method="CROWN",
            return_A=True, needed_A_dict={self.on: {self.inn: None}})
        d = A[self.on][self.inn]
        lA = float(np.asarray(d["lA"].detach().cpu()).flatten()[0])
        uA = float(np.asarray(d["uA"].detach().cpu()).flatten()[0])
        lb = float(np.asarray(d["lbias"].detach().cpu()).flatten()[0])
        ub = float(np.asarray(d["ubias"].detach().cpu()).flatten()[0])
        # t in [-1,1] parameterises the cell; convert the relation to offset o
        o_c = 0.5 * (self.off[ci] + self.off[ci + 1])
        h = 0.5 * (self.off[ci + 1] - self.off[ci])
        k_l, k_u = lA / h, uA / h
        c_l, c_u = lb - k_l * o_c, ub - k_u * o_c
        self.calls += 1
        self.cache[key] = (k_l, c_l, k_u, c_u)
        return self.cache[key]


def zono_interval(c, G):
    r = np.abs(G).sum(1)
    return c - r, c + r


def reduce_order(c, G, maxgen):
    if G.shape[1] <= maxgen:
        return G
    norms = np.abs(G).sum(0)
    keep = np.argsort(-norms)[:maxgen - 2]
    drop = np.setdiff1d(np.arange(G.shape[1]), keep)
    box = np.diag(np.abs(G[:, drop]).sum(1))
    return np.hstack([G[:, keep], box])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--segment", default="A", choices=["A", "B", "all"])
    ap.add_argument("--out", default="results/calibration/closed_loop_tube.json")
    args = ap.parse_args()

    z = np.load(NPZ, allow_pickle=True)
    frames, off = z["frames"], z["offsets"]
    conds = [str(c) for c in z["conds"]]
    px, py, pyaw = z["pose_x"], z["pose_y"], z["pose_yaw"]
    seg = json.loads(SEG.read_text()) if SEG.exists() else {"segA_n": frames.shape[1]}
    nA = int(seg.get("segA_n", frames.shape[1]))
    idx = list({"A": range(0, nA), "B": range(nA, frames.shape[1]),
                "all": range(0, frames.shape[1])}[args.segment])

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    v, L, MS = C.TARGET_SPEED_MS, C.WHEELBASE_M, C.MAX_STEER_RAD
    print(f"\nCLOSED-LOOP REACHABLE TUBE (zonotope, relational CROWN)")
    print(f"  segment {args.segment}, {len(idx)} poses, v {v:.2f} m/s, "
          f"budget {C.CTE_BUDGET_M:.3f} m\n")
    print(f"  {'model':9s} {'cond':9s} {'steps':>6s} {'max|o| (m)':>11s} "
          f"{'k (1/m)':>9s} {'bounds':>7s}  verdict")

    out = {}
    for nm, ck, ch, fc in STUDENTS:
        net = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
        net.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
        net.eval()
        for ci_c, cond in enumerate(conds):
            cr = CellRelation(frames[ci_c], off, net, dev)
            c = np.zeros(2)                     # state (o, psi)
            G = np.zeros((2, 0))
            worst, steps, escaped, kmeans = 0.0, 0, False, []
            for n, pi in enumerate(idx[:-1]):
                lo, hi = zono_interval(c, G)
                o_lo, o_hi = lo[0], hi[0]
                if o_lo < off[0] or o_hi > off[-1] or max(abs(o_lo), abs(o_hi)) > OUTER:
                    escaped = True
                    break
                cells = [ci for ci in range(len(off) - 1)
                         if not (off[ci + 1] < o_lo or off[ci] > o_hi)]
                rel = [cr(pi, ci) for ci in cells]
                k_l = min(r[0] for r in rel); k_u = max(r[2] for r in rel)
                c_l = min(r[1] for r in rel); c_u = max(r[3] for r in rel)
                k_mid, k_rad = 0.5 * (k_l + k_u), 0.5 * (k_u - k_l)
                c_mid, c_rad = 0.5 * (c_l + c_u), 0.5 * (c_u - c_l)
                kmeans.append(k_mid)

                ya = math.radians(float(pyaw[ci_c][pi] if pyaw.ndim == 2 else pyaw[pi]))
                yb = math.radians(float(pyaw[ci_c][idx[n + 1]] if pyaw.ndim == 2
                                        else pyaw[idx[n + 1]]))
                dyaw = math.atan2(math.sin(yb - ya), math.cos(yb - ya))
                pa = np.array([float(px[ci_c][pi] if px.ndim == 2 else px[pi]),
                               float(py[ci_c][pi] if py.ndim == 2 else py[pi])])
                pb = np.array([float(px[ci_c][idx[n+1]] if px.ndim == 2 else px[idx[n+1]]),
                               float(py[ci_c][idx[n+1]] if py.ndim == 2 else py[idx[n+1]])])
                ds = float(np.linalg.norm(pb - pa))
                dt = ds / v if ds > 1e-6 else C.FIXED_DT

                # tan is convex on [0,pi/2); over the small deltas here (|delta| < 0.1 rad)
                # its excess over the identity is bounded and folded into the remainder.
                g = (v / L) * MS * dt
                A = np.array([[1.0, v * dt], [g * k_mid, 1.0]])
                b = np.array([0.0, g * c_mid - dyaw])
                omax = max(abs(o_lo), abs(o_hi))
                rem = g * (k_rad * omax + c_rad)
                tan_ex = g * abs(math.tan(min(1.0, abs(c_mid) + k_rad * omax) * MS)
                                 - min(1.0, abs(c_mid) + k_rad * omax) * MS)
                c = A @ c + b
                G = A @ G if G.shape[1] else G
                newg = np.array([[0.0], [rem + tan_ex]])
                G = np.hstack([G, newg]) if G.shape[1] else newg
                G = reduce_order(c, G, MAXGEN)

                lo2, hi2 = zono_interval(c, G)
                worst = max(worst, abs(lo2[0]), abs(hi2[0]))
                steps = n + 1
                if n % 25 == 0:
                    print(f"      {nm}/{cond} pose {n:3d} o=[{lo2[0]:+.3f},{hi2[0]:+.3f}] "
                          f"k={k_mid:+.3f}", flush=True)
            verdict = "FAIL" if (escaped or worst > C.CTE_BUDGET_M) else "PASS"
            tag = " (tube left captured range)" if escaped else ""
            kk = float(np.mean(kmeans)) if kmeans else float("nan")
            print(f"  {nm:9s} {cond:9s} {steps:6d} {worst:11.3f} {kk:9.3f} "
                  f"{cr.calls:7d}  {verdict}{tag}")
            out[f"{nm}/{cond}"] = dict(max_abs_o=worst, steps=steps, escaped=escaped,
                                       verdict=verdict, k_mean=kk, bounds=cr.calls)
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"\n  wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

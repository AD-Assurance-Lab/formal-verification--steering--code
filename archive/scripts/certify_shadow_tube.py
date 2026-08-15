#!/usr/bin/env python3
"""Sound reachable-tube certification on a VALIDATED measured surrogate.

WHAT MAKES THIS DIFFERENT FROM THE SEVEN RETIRED CRITERIA. Every earlier one reduced the
problem to a scalar per pose and then argued about aggregation. None was ever checked
against the question it claimed to answer. This one is bounded only AFTER the surrogate it
bounds is shown to reproduce the closed loop (`scripts/validate_surrogate.py`):

    gate A  captured steer at (0,0) vs the steer the vehicle actually used
            clear 0.006, shadows 0.010     (eastbound scored 0.208 and was rejected)
    gate B  a rollout on the measured surfaces reproduces the departure LOCATION
            shadows over budget at x=9.0 y=125.4; the real run departs at x=8.1 y=123.9

Bounds on a surrogate that fails those gates prove nothing about the vehicle.

THE INPUT SET IS THREE SCALARS, AND IT IS SOUND. Between four captured corners the image is
BILINEAR in (t_o, t_psi), not affine, so a rank-2 affine map would silently drop the cross
term. Lifting that term into its own input dimension restores soundness:

    x(t_o, t_psi) = x_c + t_o W_o + t_psi W_psi + t_x W_x,   t_o, t_psi, t_x in [-1, 1]

    W_x = (x_{i+1,j+1} - x_{i+1,j} - x_{i,j+1} + x_{i,j}) / 4

Because |t_o * t_psi| <= 1 for every point of the true bilinear patch, letting t_x range
freely over [-1, 1] OVER-approximates it. The verifier sees a 3-D box rather than 7,056
pixels, and the relaxation is conservative in the safe direction.

RELATIONAL, NOT INTERVAL. Collapsing steer to a constant interval per cell discards that it
decreases with offset -- the restoring feedback -- and an interval abstraction then cannot
represent a contraction, so it diverges on a stable loop (F23). CROWN's linear coefficients
are kept instead (`return_A`), giving

    k_o o + k_psi psi + c_l  <=  steer  <=  k_o' o + k_psi' psi + c_u

which closes the loop as a linear system whose contraction survives. The tube is a zonotope
because a box re-wraps the o-psi correlation at every step.

    python scripts/certify_shadow_tube.py [--cond shadows] [--student S_clear]
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
MAXGEN = 48
MINBOX = 1.0    # minimum input-box width in t units (half a cell)


class CellRel:
    """CROWN linear steer bounds in (o, psi) for one (pose, o-cell, psi-cell). Cached."""

    def __init__(self, frames, off, yr, net, dev):
        self.fr, self.off, self.yr, self.dev = frames, off, yr, dev
        self.bd = cc.Bounder(3, net, dev, 28, 84, method="CROWN")
        self.on = self.bd.bounded.output_name[0]
        self.inn = self.bd.bounded.input_name[0]
        self.cache = {}
        self.calls = 0

    def __call__(self, pi, i, j, obox=None, ybox=None):
        """Bound over the tube's ACTUAL extent within cell (i, j), not the whole cell.

        Bounding the full cell regardless of tube size costs a fixed relaxation gap of
        0.052-0.090 -- 4-7x the closed-loop tolerance -- which implies a steady-state tube
        near 1 m and fails every condition for the same trivial reason. The tube starts as a
        point and stays far smaller than a cell, so restricting the input box to the tube
        shrinks the gap with it. Cache keys therefore include the box, quantised."""
        if obox is None:
            obox = (self.off[i], self.off[i + 1])
        if ybox is None:
            ybox = (self.yr[j], self.yr[j + 1])
        key = (pi, i, j, round(obox[0], 4), round(obox[1], 4),
               round(ybox[0], 5), round(ybox[1], 5))
        if key in self.cache:
            return self.cache[key]
        a = self.fr[pi, i, j].reshape(-1).astype(np.float32)
        b = self.fr[pi, i + 1, j].reshape(-1).astype(np.float32)
        c = self.fr[pi, i, j + 1].reshape(-1).astype(np.float32)
        d = self.fr[pi, i + 1, j + 1].reshape(-1).astype(np.float32)
        xc = 0.25 * (a + b + c + d)
        W = np.stack([0.25 * (b + d - a - c),      # d/d t_o
                      0.25 * (c + d - a - b),      # d/d t_psi
                      0.25 * (d - b - c + a)], 1)  # cross term, lifted
        self.bd._bind(W.astype(np.float32), xc)
        # map the tube's box into this cell's t coordinates, clipped to the cell
        oc, oh = 0.5 * (self.off[i] + self.off[i + 1]), 0.5 * (self.off[i + 1] - self.off[i])
        yc, yh = 0.5 * (self.yr[j] + self.yr[j + 1]), 0.5 * (self.yr[j + 1] - self.yr[j])
        # EXPAND to a minimum width. Over a near-point box CROWN's linear coefficients are
        # unconstrained -- any line through the value is valid -- so the slope degenerates
        # (k_o -0.202 -> -0.091) and the modelled loop loses the damping that keeps it
        # stable. A wider box strictly CONTAINS the tube, so widening is sound; it trades a
        # slightly looser constant for a slope that actually reflects the restoring gain.
        tol_ = np.clip((np.array(obox) - oc) / oh, -1.0, 1.0)
        tyl_ = np.clip((np.array(ybox) - yc) / yh, -1.0, 1.0)
        for arr in (tol_, tyl_):
            mid = 0.5 * (arr[0] + arr[1])
            if arr[1] - arr[0] < MINBOX:
                arr[0], arr[1] = mid - MINBOX / 2, mid + MINBOX / 2
        tol_ = np.clip(tol_, -1.0, 1.0); tyl_ = np.clip(tyl_, -1.0, 1.0)
        lo = np.array([tol_[0], tyl_[0], -1.0], np.float32)
        hi = np.array([tol_[1], tyl_[1], 1.0], np.float32)
        ptb = PerturbationLpNorm(
            norm=float("inf"),
            x_L=torch.tensor(lo, device=self.dev).unsqueeze(0),
            x_U=torch.tensor(hi, device=self.dev).unsqueeze(0))
        _, _, A = self.bd.bounded.compute_bounds(
            x=(BoundedTensor(self.bd.centre, ptb),), method="CROWN",
            return_A=True, needed_A_dict={self.on: {self.inn: None}})
        g = A[self.on][self.inn]
        lA = np.asarray(g["lA"].detach().cpu()).reshape(-1)
        uA = np.asarray(g["uA"].detach().cpu()).reshape(-1)
        lb = float(np.asarray(g["lbias"].detach().cpu()).reshape(-1)[0])
        ub = float(np.asarray(g["ubias"].detach().cpu()).reshape(-1)[0])
        # cross dimension is not a state: absorb it into the constant, worst case
        lb -= abs(lA[2])
        ub += abs(uA[2])
        ko_l, kp_l = lA[0] / oh, lA[1] / yh
        ko_u, kp_u = uA[0] / oh, uA[1] / yh
        out = (ko_l, kp_l, lb - ko_l * oc - kp_l * yc,
               ko_u, kp_u, ub - ko_u * oc - kp_u * yc)
        self.calls += 1
        self.cache[key] = out
        return out


def interval(c, G):
    r = np.abs(G).sum(1)
    return c - r, c + r


def reduce_order(G, maxgen):
    if G.shape[1] <= maxgen:
        return G
    n = np.abs(G).sum(0)
    keep = np.argsort(-n)[:maxgen - 2]
    drop = np.setdiff1d(np.arange(G.shape[1]), keep)
    return np.hstack([G[:, keep], np.diag(np.abs(G[:, drop]).sum(1))])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--student", default="S_clear", choices=list(STUDENTS))
    ap.add_argument("--cond", default=None, help="default: every condition in the capture")
    ap.add_argument("--out", default="results/calibration/shadow_tube.json")
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

    print(f"\nSOUND REACHABLE TUBE   {args.student}, {len(px)} poses, budget "
          f"{C.CTE_BUDGET_M:.3f} m")
    print(f"  3-scalar input box per cell (offset, heading, lifted bilinear cross term)\n")
    print(f"  {'cond':9s} {'steps':>6s} {'peak |o| (m)':>13s} {'bounds':>7s}  verdict")
    out = {}
    for ci, cond in enumerate(conds):
        if args.cond and cond != args.cond:
            continue
        cr = CellRel(frames[ci], off, yaws, net, dev)
        c = np.zeros(2)
        G = np.zeros((2, 0))
        peak, steps, esc = 0.0, 0, False
        for pi in range(len(px) - 1):
            lo, hi = interval(c, G)
            if lo[0] < off[0] or hi[0] > off[-1] or max(abs(lo[0]), abs(hi[0])) > 2.0:
                esc = True
                break
            io = [i for i in range(len(off) - 1)
                  if not (off[i + 1] < lo[0] or off[i] > hi[0])]
            jp = [j for j in range(len(yaws) - 1)
                  if not (yaws[j + 1] < lo[1] or yaws[j] > hi[1])] or [len(yaws) // 2 - 1]
            rel = [cr(pi, i, j, (lo[0], hi[0]), (lo[1], hi[1]))
                   for i in io for j in jp]
            ko_l = min(r[0] for r in rel); ko_u = max(r[3] for r in rel)
            kp_l = min(r[1] for r in rel); kp_u = max(r[4] for r in rel)
            c_l = min(r[2] for r in rel); c_u = max(r[5] for r in rel)
            kom, kor = 0.5 * (ko_l + ko_u), 0.5 * (ko_u - ko_l)
            kpm, kpr = 0.5 * (kp_l + kp_u), 0.5 * (kp_u - kp_l)
            cm, crd = 0.5 * (c_l + c_u), 0.5 * (c_u - c_l)

            ya, yb = math.radians(float(pyaw[pi])), math.radians(float(pyaw[pi + 1]))
            dyaw = math.atan2(math.sin(yb - ya), math.cos(yb - ya))
            ds = float(np.hypot(px[pi + 1] - px[pi], py[pi + 1] - py[pi]))
            nst = max(1, int(round(ds / (v * dt))))
            for _ in range(nst):
                g = (v / L) * MS * dt
                A = np.array([[1.0, v * dt], [g * kom, 1.0 + g * kpm]])
                b = np.array([0.0, g * cm - dyaw / nst])
                lo2, hi2 = interval(c, G)
                rad = g * (kor * max(abs(lo2[0]), abs(hi2[0]))
                           + kpr * max(abs(lo2[1]), abs(hi2[1])) + crd)
                c = A @ c + b
                G = (A @ G) if G.shape[1] else G
                ng = np.array([[0.0], [rad]])
                G = np.hstack([G, ng]) if G.shape[1] else ng
                G = reduce_order(G, MAXGEN)
            lo3, hi3 = interval(c, G)
            peak = max(peak, abs(lo3[0]), abs(hi3[0]))
            steps = pi + 1
            if pi % 40 == 0:
                print(f"      {cond} pose {pi:3d}  o=[{lo3[0]:+.3f},{hi3[0]:+.3f}]  "
                      f"k_o={kom:+.3f}", flush=True)
        verdict = "FAIL" if (esc or peak > C.CTE_BUDGET_M) else "PASS"
        tag = "  (tube left captured range)" if esc else ""
        print(f"  {cond:9s} {steps:6d} {peak:13.3f} {cr.calls:7d}  {verdict}{tag}")
        out[f"{args.student}/{cond}"] = dict(peak=peak, steps=steps, escaped=esc,
                                             verdict=verdict, bounds=cr.calls)
    p = Path(args.out)
    old = json.loads(p.read_text()) if p.exists() else {}
    old.update(out)
    p.write_text(json.dumps(old, indent=2))
    print(f"\n  wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

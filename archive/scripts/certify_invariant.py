#!/usr/bin/env python3
"""Certify an INDUCTIVE INVARIANT inside the lane, instead of propagating a tube.

WHY NOT A TUBE. Three propagation schemes were built and all three blew up. An interval tube
diverged in 6 steps: collapsing steer to an interval discards the restoring correlation, so
the abstraction cannot represent a contraction and must diverge on a stable loop. A zonotope
tube diverged in 11 steps: as the set widens it spans more captured cells, and cross-cell
min/max weakens the effective gain, which widens it further -- a runaway partition, with the
tube CENTRE meanwhile staying correctly within 0.05 m. A grid of boxes reached 414 boxes and
0.700 m by step 20, because rounding successors outward injects error at every step.

The failure is structural, not a tooling problem: any 200-step propagation accumulates
abstraction error, and the vehicle's contraction is fighting an error source that never
stops. A point rollout on the SAME data behaves perfectly (clear peaks at 0.29 m, shadows
departs within 1.6 m of the real departure), which is what proves the surrogate is fine and
the abstraction is not.

The study does not need a trajectory. It needs to know whether the vehicle stays in its
lane, and that is an INVARIANCE property, which is inductive:

    S = { |o| <= o_max, |psi| <= psi_max }  is invariant  iff
    for every pose p and every (o, psi) in S,  successor(p, o, psi) in S

One step, quantified over the whole set and every pose along the route. Nothing accumulates.
If such an S exists inside the CTE budget the vehicle provably never leaves the lane; if no
S exists the property is falsified. This is the standard reason invariants are preferred to
bounded-horizon reachability when the horizon is long.

SOUNDNESS OF THE INPUT SET. Between four captured corners the image is BILINEAR in
(t_o, t_psi), so an affine map would silently drop the cross term. It is lifted into a third
input dimension ranging over [-1, 1], which contains the true bilinear patch because
|t_o * t_psi| <= 1. The verifier sees a 3-D box, not 7,056 pixels.

VALIDATED SURROGATE (this is what the seven retired criteria never had):
    gate A  captured steer at (0,0) vs driven:  clear 0.006, shadows 0.010
    gate B  rollout departs at x=9.0 y=125.4;  the real run departs at x=8.1 y=123.9

    python scripts/certify_invariant.py --student S_clear
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
NSPLIT = 3      # input-space BaB splits per dimension
STUDENTS = {"S_clear": ("S_clear_84x28", (8, 16, 16), 32),
            "S_mixed": ("S_mixed_84x28_w3", (24, 48, 48), 96)}


class BoxBounder:
    """alpha-CROWN steer bounds over an explicit (offset x heading) box at one pose."""

    def __init__(self, frames, off, yr, net, dev):
        self.fr, self.off, self.yr, self.dev = frames, off, yr, dev
        self.bd = cc.Bounder(3, net, dev, 28, 84, method="CROWN")
        self.cache = {}
        self.calls = 0

    def __call__(self, pi, o0, o1, y0, y1):
        key = (pi, round(o0, 4), round(o1, 4), round(y0, 5), round(y1, 5))
        if key in self.cache:
            return self.cache[key]
        # the captured cell containing the box centre; boxes are sized to sit inside one
        i = int(np.clip(np.searchsorted(self.off, 0.5 * (o0 + o1)) - 1, 0, len(self.off) - 2))
        j = int(np.clip(np.searchsorted(self.yr, 0.5 * (y0 + y1)) - 1, 0, len(self.yr) - 2))
        a = self.fr[pi, i, j].reshape(-1).astype(np.float32)
        b = self.fr[pi, i + 1, j].reshape(-1).astype(np.float32)
        c = self.fr[pi, i, j + 1].reshape(-1).astype(np.float32)
        d = self.fr[pi, i + 1, j + 1].reshape(-1).astype(np.float32)
        xc = 0.25 * (a + b + c + d)
        W = np.stack([0.25 * (b + d - a - c), 0.25 * (c + d - a - b),
                      0.25 * (d - b - c + a)], 1).astype(np.float32)
        self.bd._bind(W, xc)
        oc = 0.5 * (self.off[i] + self.off[i + 1])
        oh = 0.5 * (self.off[i + 1] - self.off[i])
        yc = 0.5 * (self.yr[j] + self.yr[j + 1])
        yh = 0.5 * (self.yr[j + 1] - self.yr[j])
        to0, to1 = np.clip([(o0 - oc) / oh, (o1 - oc) / oh], -1.0, 1.0)
        ty0, ty1 = np.clip([(y0 - yc) / yh, (y1 - yc) / yh], -1.0, 1.0)
        # The lifted cross term is t_o * t_psi, so it ranges over the PRODUCT interval of
        # this box -- not over [-1, 1]. Letting it span the whole cell regardless of box
        # size was costing a fixed steering uncertainty of 0.046-0.134 (the closed-loop
        # tolerance is 0.0120), which expanded a 1 deg heading box into 2.9-6.7 deg in a
        # single step and made every invariant set empty. For a small box centred near the
        # cell centre the product is near zero and the term almost vanishes, which is the
        # whole point of lifting it rather than dropping it.
        # INPUT-SPACE BRANCH AND BOUND, the technique CLAUDE.md prescribes. A single bound
        # over the box leaves a gap of 0.0165 against the 0.0120 closed-loop tolerance,
        # which inflates a 1 deg heading box to 2.2-4.7 deg in one step and leaves every
        # invariant set empty. Splitting converges to 0.0116, at which point the residual is
        # the network's GENUINE variation over the box rather than relaxation looseness, so
        # further splitting buys nothing and only a finer capture grid would:
        #     splits/dim    1      2      3      4      6
        #     gap      0.0165 0.0131 0.0122 0.0119 0.0116
        los, his = [], []
        for gi in range(NSPLIT):
            for gj in range(NSPLIT):
                a0 = to0 + (to1 - to0) * gi / NSPLIT
                a1 = to0 + (to1 - to0) * (gi + 1) / NSPLIT
                b0 = ty0 + (ty1 - ty0) * gj / NSPLIT
                b1 = ty0 + (ty1 - ty0) * (gj + 1) / NSPLIT
                q = [a0 * b0, a0 * b1, a1 * b0, a1 * b1]
                sl = np.array([a0, b0, min(q)], np.float32)
                su = np.array([a1, b1, max(q)], np.float32)
                ptb = PerturbationLpNorm(
                    norm=float("inf"),
                    x_L=torch.tensor(sl, device=self.dev).unsqueeze(0),
                    x_U=torch.tensor(su, device=self.dev).unsqueeze(0))
                lb, ub = self.bd.bounded.compute_bounds(
                    x=(BoundedTensor(self.bd.centre, ptb),), method="CROWN")
                los.append(float(lb.min()))
                his.append(float(ub.max()))
        out = (min(los), max(his))
        self.calls += 1
        self.cache[key] = out
        return out


def check(bd, px, py, pyaw, o_max, psi_max, nbo, nbp, v, L, MS, dt):
    """Is S = [-o_max,o_max] x [-psi_max,psi_max] closed under one step at every pose?

    Returns (invariant, worst_escape_m, pose_of_worst)."""
    eo = np.linspace(-o_max, o_max, nbo + 1)
    ey = np.linspace(-psi_max, psi_max, nbp + 1)
    worst, wpose, ok = -1e9, -1, True
    for pi in range(len(px) - 1):
        ya, yb = math.radians(float(pyaw[pi])), math.radians(float(pyaw[pi + 1]))
        dyaw = math.atan2(math.sin(yb - ya), math.cos(yb - ya))
        for a in range(nbo):
            for b in range(nbp):
                o0, o1, y0, y1 = eo[a], eo[a + 1], ey[b], ey[b + 1]
                slo, shi = bd(pi, o0, o1, y0, y1)
                ny0 = y0 + (v / L) * math.tan(max(-1.0, slo) * MS) * dt - dyaw
                ny1 = y1 + (v / L) * math.tan(min(1.0, shi) * MS) * dt - dyaw
                no0 = o0 + v * y0 * dt
                no1 = o1 + v * y1 * dt
                esc = max(max(abs(no0), abs(no1)) - o_max,
                          (max(abs(ny0), abs(ny1)) - psi_max) * (v * dt))
                if esc > worst:
                    worst, wpose = esc, pi
                if esc > 0:
                    ok = False
        if not ok:
            break
    return ok, worst, wpose


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--student", default="S_clear", choices=list(STUDENTS))
    ap.add_argument("--nbox-o", type=int, default=6)
    ap.add_argument("--nbox-psi", type=int, default=6)
    ap.add_argument("--poses", type=int, default=0, help="0 = all")
    ap.add_argument("--out", default="results/calibration/invariant.json")
    args = ap.parse_args()

    z = np.load(NPZ, allow_pickle=True)
    frames, off, yaws = z["frames"], z["offsets"], np.radians(z["yaws"])
    conds = [str(c) for c in z["conds"]]
    px, py, pyaw = z["pose_x"], z["pose_y"], z["pose_yaw"]
    if args.poses:
        px, py, pyaw = px[:args.poses], py[:args.poses], pyaw[:args.poses]
        frames = frames[:, :args.poses]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    v, L, MS, dt = C.TARGET_SPEED_MS, C.WHEELBASE_M, C.MAX_STEER_RAD, C.FIXED_DT

    ck, ch, fc = STUDENTS[args.student]
    net = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
    net.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
    net.eval()

    print(f"\nINDUCTIVE INVARIANT   {args.student}, {len(px)} poses, "
          f"budget {C.CTE_BUDGET_M:.3f} m")
    print(f"  S is invariant iff every state in S maps back into S at EVERY pose\n")
    print(f"  {'cond':9s} {'o_max':>6s} {'psi_max':>8s} {'invariant':>10s} "
          f"{'worst escape':>13s} {'at pose':>8s}")
    out = {}
    CAND = [(C.CTE_BUDGET_M, 6.0), (C.CTE_BUDGET_M, 4.0), (0.55, 4.0),
            (0.45, 4.0), (0.35, 3.0), (0.25, 3.0)]
    for ci, cond in enumerate(conds):
        bd = BoxBounder(frames[ci], off, yaws, net, dev)
        found = None
        for o_max, psid in CAND:
            ok, worst, wp = check(bd, px, py, pyaw, o_max, math.radians(psid),
                                  args.nbox_o, args.nbox_psi, v, L, MS, dt)
            print(f"  {cond:9s} {o_max:6.3f} {psid:8.1f} {('YES' if ok else 'no'):>10s} "
                  f"{worst:+13.4f} {wp:8d}", flush=True)
            if ok:
                found = (o_max, psid)
                break
        verdict = "PASS" if found else "FAIL"
        out[f"{args.student}/{cond}"] = dict(
            verdict=verdict, bounds=bd.calls,
            o_max=found[0] if found else None, psi_max_deg=found[1] if found else None)
        print(f"    -> {cond}: {verdict}   ({bd.calls} bounds)\n")
    p = Path(args.out)
    old = json.loads(p.read_text()) if p.exists() else {}
    old.update(out)
    p.write_text(json.dumps(old, indent=2))
    print(f"  wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

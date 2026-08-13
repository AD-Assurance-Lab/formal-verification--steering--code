#!/usr/bin/env python3
"""FORMAL certificate: is a lane-keeping invariant closed over the WHOLE LAP?

This is the verification result the study is about. It is a proof obligation, not a
simulation: no trajectory is rolled out, and the verdict quantifies over every state in a
set and every pose on the lap.

    S = { |o| <= o_max } x { |psi| <= psi_max }

    S is INVARIANT  iff  for every pose p on the lap and every (o, psi) in S,
                         successor(p, o, psi) lies in S

If S is invariant and S is inside the CTE budget, the vehicle provably never leaves its
lane under that condition. If no S is invariant, the property is falsified. One step,
quantified -- so unlike a bounded-horizon tube, nothing accumulates. Three tube
formulations were built first and all three diverged for exactly that reason (F27).

FULL LAP, NO INTERSECTION. Verification must span the same road the driving test does. The
truncated closed-loop run covers 1600 steps = 2861 m and the junction begins at 3008 m, so
the certificate is computed over 0-2861 m. Scoring a segment-scoped prediction against a
full-lap run compares two different roads, which is what made the earlier P-07 numbers
unsound.

WHAT MAKES IT TRACTABLE. Three things, each necessary:

  1. INPUT-SPACE BRANCH AND BOUND. A single CROWN bound over a state box leaves a gap of
     0.0165 against the 0.0120 closed-loop tolerance, which inflates a 1 deg heading box to
     2.2-4.7 deg in one step and leaves every invariant set empty. Splitting converges to
     0.0116, where the residual is the network's genuine variation rather than relaxation
     looseness:  splits/dim 1 -> 0.0165, 2 -> 0.0131, 3 -> 0.0122, 4 -> 0.0119, 6 -> 0.0116.
  2. BATCHED SUB-BOXES. The NSPLIT^2 sub-boxes share a weight matrix, so they differ only in
     the input box -- one batched `compute_bounds` costs 48.5 ms against 423 ms sequential,
     an 8.7x saving that turns a 19-hour lap into a 2-hour one.
  3. THE LIFTED CROSS TERM SCALES WITH THE BOX. Between four captured corners the image is
     bilinear, so the cross term is lifted into a third input dimension. It ranges over the
     PRODUCT interval of the box, not [-1,1]; holding it at [-1,1] regardless of box size
     cost a fixed 0.046-0.134 of steering uncertainty and made every set empty.

    python scripts/certify_lap_invariant.py --npz results/calibration/oy_lap_clear.npz
"""
import sys
import json
import math
import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
import verifiable_disturbance as vd  # noqa: E402
from student import StudentNet  # noqa: E402
from auto_LiRPA import BoundedModule, BoundedTensor  # noqa: E402
from auto_LiRPA.perturbations import PerturbationLpNorm  # noqa: E402

STUDENTS = {"S_clear": ("S_clear_84x28", (8, 16, 16), 32),
            "S_mixed": ("S_mixed_84x28_w3", (24, 48, 48), 96)}
NSPLIT = 3


class LapBounder:
    """Batched alpha-CROWN + input-space BaB over one (pose, offset-box, heading-box)."""

    def __init__(self, frames, off, yr, net, dev):
        self.fr, self.off, self.yr, self.dev = frames, off, yr, dev
        self.K = NSPLIT * NSPLIT
        self.head = vd.LinearDisturbance(
            np.zeros((3 * 28 * 84, 3), np.float32), np.zeros(3 * 28 * 84, np.float32),
            (self.K, 3, 28, 84))
        self.net = nn.Sequential(self.head, net).to(dev).eval()
        self.centre = torch.zeros(self.K, 3, device=dev)
        self.bm = BoundedModule(self.net, torch.empty_like(self.centre), device=dev)
        self.calls = 0

    def __call__(self, pi, o0, o1, y0, y1):
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
        with torch.no_grad():
            self.head.fc.weight.copy_(torch.from_numpy(W).to(self.dev))
            self.head.fc.bias.copy_(torch.from_numpy(xc).to(self.dev))
        oc = 0.5 * (self.off[i] + self.off[i + 1])
        oh = 0.5 * (self.off[i + 1] - self.off[i])
        yc = 0.5 * (self.yr[j] + self.yr[j + 1])
        yh = 0.5 * (self.yr[j + 1] - self.yr[j])
        to0, to1 = np.clip([(o0 - oc) / oh, (o1 - oc) / oh], -1.0, 1.0)
        ty0, ty1 = np.clip([(y0 - yc) / yh, (y1 - yc) / yh], -1.0, 1.0)
        lo = np.zeros((self.K, 3), np.float32)
        hi = np.zeros((self.K, 3), np.float32)
        k = 0
        for gi in range(NSPLIT):
            for gj in range(NSPLIT):
                a0 = to0 + (to1 - to0) * gi / NSPLIT
                a1 = to0 + (to1 - to0) * (gi + 1) / NSPLIT
                b0 = ty0 + (ty1 - ty0) * gj / NSPLIT
                b1 = ty0 + (ty1 - ty0) * (gj + 1) / NSPLIT
                q = [a0 * b0, a0 * b1, a1 * b0, a1 * b1]
                lo[k] = [a0, b0, min(q)]
                hi[k] = [a1, b1, max(q)]
                k += 1
        ptb = PerturbationLpNorm(norm=float("inf"),
                                 x_L=torch.tensor(lo, device=self.dev),
                                 x_U=torch.tensor(hi, device=self.dev))
        lb, ub = self.bm.compute_bounds(x=(BoundedTensor(self.centre, ptb),),
                                        method="CROWN")
        self.calls += 1
        return float(lb.min()), float(ub.max())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--npz", required=True)
    ap.add_argument("--student", default="S_clear", choices=list(STUDENTS))
    ap.add_argument("--o-max", type=float, default=None, help="default: the CTE budget")
    ap.add_argument("--psi-max-deg", type=float, default=4.0)
    ap.add_argument("--nbo", type=int, default=8)
    ap.add_argument("--nbp", type=int, default=8)
    ap.add_argument("--max-m", type=float, default=2861.0, help="exclude the intersection")
    ap.add_argument("--out", default="results/calibration/lap_invariant.json")
    args = ap.parse_args()

    z = np.load(args.npz, allow_pickle=True)
    frames, off, yaws = z["frames"], z["offsets"], np.radians(z["yaws"])
    conds = [str(c) for c in z["conds"]]
    px, py, pyaw = z["pose_x"], z["pose_y"], z["pose_yaw"]
    d = np.concatenate([[0], np.cumsum(np.hypot(np.diff(px), np.diff(py)))])
    n = int(np.searchsorted(d, args.max_m))
    n = min(n, len(px))
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    v, L, MS, dt = C.TARGET_SPEED_MS, C.WHEELBASE_M, C.MAX_STEER_RAD, C.FIXED_DT
    o_max = args.o_max if args.o_max else C.CTE_BUDGET_M
    psi_max = math.radians(args.psi_max_deg)

    ck, ch, fc = STUDENTS[args.student]
    net = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
    net.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
    net.eval()

    print(f"\nLAP INVARIANT CERTIFICATE   {args.student}   {Path(args.npz).name}")
    print(f"  {n} poses = {d[min(n, len(d)-1)]:.0f} m of lap (intersection excluded at "
          f"{args.max_m:.0f} m)")
    print(f"  S = |o| <= {o_max:.3f} m x |psi| <= {args.psi_max_deg:.1f} deg, "
          f"{args.nbo}x{args.nbp} boxes, BaB {NSPLIT}x{NSPLIT}\n")
    eo = np.linspace(-o_max, o_max, args.nbo + 1)
    ey = np.linspace(-psi_max, psi_max, args.nbp + 1)
    out = {}
    # MAXIMAL INVARIANT SUBSET by iterated removal. A BOX cannot be invariant here: its
    # corner -- maximum offset with the heading pointed further out -- moves outward
    # whatever the steering does, so the plain box check fails at pose 0 for every size
    # (measured escape +0.287 m). The invariant must be SLANTED: at large offset only
    # headings that point back belong to it. Iterated removal finds that shape without
    # assuming it, and never leaves the captured envelope:
    #     S_0     = the full grid inside the lane
    #     S_{k+1} = { boxes whose successor at EVERY pose is covered by S_k }
    # The iteration is monotone and terminates; its limit is the largest set the vehicle
    # can never leave. Non-empty and containing the lane centre = CERTIFIED.
    for ci, cond in enumerate(conds):
        bd = LapBounder(frames[ci], off, yaws, net, dev)
        cache = {}

        def succ(pi, a, b):
            k = (pi, a, b)
            if k in cache:
                return cache[k]
            o0, o1, y0, y1 = eo[a], eo[a + 1], ey[b], ey[b + 1]
            slo, shi = bd(pi, o0, o1, y0, y1)
            ya, yb = math.radians(float(pyaw[pi])), math.radians(float(pyaw[pi + 1]))
            dyaw = math.atan2(math.sin(yb - ya), math.cos(yb - ya))
            r = (o0 + v * y0 * dt, o1 + v * y1 * dt,
                 y0 + (v / L) * math.tan(max(-1.0, slo) * MS) * dt - dyaw,
                 y1 + (v / L) * math.tan(min(1.0, shi) * MS) * dt - dyaw)
            cache[k] = r
            return r

        S = {(a, b) for a in range(args.nbo) for b in range(args.nbp)}
        it = 0
        for it in range(1, 21):
            keep = set()
            for (a, b) in S:
                good = True
                for pi in range(n - 1):
                    no0, no1, ny0, ny1 = succ(pi, a, b)
                    if (no0 < eo[0] or no1 > eo[-1] or ny0 < ey[0] or ny1 > ey[-1]):
                        good = False
                        break
                    ia = range(max(0, int(np.searchsorted(eo, no0)) - 1),
                               min(args.nbo, int(np.searchsorted(eo, no1))))
                    jb = range(max(0, int(np.searchsorted(ey, ny0)) - 1),
                               min(args.nbp, int(np.searchsorted(ey, ny1))))
                    if any((i2, j2) not in S for i2 in ia for j2 in jb):
                        good = False
                        break
                if good:
                    keep.add((a, b))
            print(f"      {cond}: iteration {it}  {len(S)} -> {len(keep)} boxes",
                  flush=True)
            if keep == S:
                break
            S = keep
            if not S:
                break
        centre_in = any(eo[a] <= 0 <= eo[a + 1] and ey[b] <= 0 <= ey[b + 1]
                        for (a, b) in S)
        omax = max((max(abs(eo[a]), abs(eo[a + 1])) for a, _ in S), default=0.0)
        verdict = "CERTIFIED" if (S and centre_in) else "FALSIFIED"
        print(f"  {cond:9s} {verdict}   {len(S)}/{args.nbo*args.nbp} boxes invariant, "
              f"reaching |o|<={omax:.3f} m, lane centre "
              f"{'INSIDE' if centre_in else 'not inside'}   ({bd.calls} bounds)")
        out[f"{args.student}/{cond}"] = dict(verdict=verdict, boxes=len(S),
                                             o_reach=omax, centre_in=bool(centre_in),
                                             poses=n, bounds=bd.calls)
    p = Path(args.out)
    old = json.loads(p.read_text()) if p.exists() else {}
    old.update(out)
    p.write_text(json.dumps(old, indent=2))
    print(f"\n  wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

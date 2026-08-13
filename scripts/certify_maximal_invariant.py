#!/usr/bin/env python3
"""Compute the MAXIMAL INVARIANT SET inside the lane, by iterated removal.

WHY NOT A BOX, AND WHY NOT AN ELLIPSE. An axis-aligned box can never be invariant here: at
its corner -- maximum offset with the heading pointed outward -- one step moves outward
whatever the steering does, so the check fails at pose 0 for every candidate size. The
invariant set must be SLANTED, because at maximum offset the vehicle must already be heading
back. A Lyapunov ellipse from the measured loop has exactly that slant (at |o| = 0.668 m it
admits only psi = -17 deg) but reaches |psi| <= 22 deg, far outside the +-6 deg that was
captured, so it cannot be verified on measured data.

Iterated removal needs no assumed shape and never leaves the captured envelope:

    S_0     = { |o| <= CTE_BUDGET } x { |psi| <= captured range }
    S_{k+1} = { x in S_k : successor(x) is a subset of S_k }

The iteration is monotone decreasing and terminates. Its limit is the largest set inside the
lane that the vehicle can never leave. Non-empty and containing the lane centre means the
policy provably holds the lane; empty means no such set exists and the property is falsified.
Because each step is checked once against the current set, nothing accumulates -- which is
what defeated all three tube formulations (interval diverged in 6 steps, zonotope in 11, a
grid of boxes reached 414 boxes by step 20, while a point rollout on the same data was fine).

Successors are computed with alpha-CROWN over each box, on the 3-scalar input set used
throughout (offset, heading, and the lifted bilinear cross term that makes the image
interpolation an over-approximation), and rounded OUTWARD onto the grid.

    python scripts/certify_maximal_invariant.py --student S_clear
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
from certify_invariant import BoxBounder  # noqa: E402

NPZ = REPO / "results" / "calibration" / "oy_dense_shadow.npz"
STUDENTS = {"S_clear": ("S_clear_84x28", (8, 16, 16), 32),
            "S_mixed": ("S_mixed_84x28_w3", (24, 48, 48), 96)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--student", default="S_clear", choices=list(STUDENTS))
    ap.add_argument("--no", type=int, default=14, help="offset boxes across the lane")
    ap.add_argument("--npsi", type=int, default=12, help="heading boxes across the envelope")
    ap.add_argument("--poses", type=int, default=60)
    ap.add_argument("--out", default="results/calibration/maximal_invariant.json")
    args = ap.parse_args()

    z = np.load(NPZ, allow_pickle=True)
    frames, off, yaws = z["frames"], z["offsets"], np.radians(z["yaws"])
    conds = [str(c) for c in z["conds"]]
    px, py, pyaw = z["pose_x"], z["pose_y"], z["pose_yaw"]
    n = min(args.poses, len(px)) if args.poses else len(px)
    px, py, pyaw, frames = px[:n], py[:n], pyaw[:n], frames[:, :n]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    v, L, MS, dt = C.TARGET_SPEED_MS, C.WHEELBASE_M, C.MAX_STEER_RAD, C.FIXED_DT

    ck, ch, fc = STUDENTS[args.student]
    net = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
    net.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
    net.eval()

    eo = np.linspace(-C.CTE_BUDGET_M, C.CTE_BUDGET_M, args.no + 1)
    ey = np.linspace(yaws[0], yaws[-1], args.npsi + 1)
    print(f"\nMAXIMAL INVARIANT SET   {args.student}, {n} poses")
    print(f"  lane |o| <= {C.CTE_BUDGET_M:.3f} m in {args.no} boxes, "
          f"|psi| <= {math.degrees(yaws[-1]):.0f} deg in {args.npsi} boxes\n")
    out = {}
    for ci, cond in enumerate(conds):
        bd = BoxBounder(frames[ci], off, yaws, net, dev)
        S = {(a, b) for a in range(args.no) for b in range(args.npsi)}
        for it in range(12):
            keep = set()
            for (a, b) in S:
                o0, o1, y0, y1 = eo[a], eo[a + 1], ey[b], ey[b + 1]
                good = True
                for pi in range(n - 1):
                    ya = math.radians(float(pyaw[pi]))
                    yb = math.radians(float(pyaw[pi + 1]))
                    dyaw = math.atan2(math.sin(yb - ya), math.cos(yb - ya))
                    slo, shi = bd(pi, o0, o1, y0, y1)
                    ny0 = y0 + (v / L) * math.tan(max(-1.0, slo) * MS) * dt - dyaw
                    ny1 = y1 + (v / L) * math.tan(min(1.0, shi) * MS) * dt - dyaw
                    no0, no1 = o0 + v * y0 * dt, o1 + v * y1 * dt
                    ia = range(max(0, int(np.searchsorted(eo, no0) - 1)),
                               min(args.no, int(np.searchsorted(eo, no1))))
                    jb = range(max(0, int(np.searchsorted(ey, ny0) - 1)),
                               min(args.npsi, int(np.searchsorted(ey, ny1))))
                    if no0 < eo[0] or no1 > eo[-1] or ny0 < ey[0] or ny1 > ey[-1]:
                        good = False
                        break
                    if any((i2, j2) not in S for i2 in ia for j2 in jb):
                        good = False
                        break
                if good:
                    keep.add((a, b))
            if keep == S:
                break
            S = keep
            if not S:
                break
        centre_in = any(eo[a] <= 0 <= eo[a + 1] and ey[b] <= 0 <= ey[b + 1]
                        for (a, b) in S)
        omax = max((max(abs(eo[a]), abs(eo[a + 1])) for a, _ in S), default=0.0)
        verdict = "PASS" if (S and centre_in) else "FAIL"
        print(f"  {cond:9s} iterations {it+1:2d}  invariant boxes {len(S):4d}/"
              f"{args.no*args.npsi}  reaches |o|<={omax:.3f} m  "
              f"lane-centre {'in' if centre_in else 'NOT in'} set  -> {verdict}"
              f"   ({bd.calls} bounds)")
        out[f"{args.student}/{cond}"] = dict(verdict=verdict, boxes=len(S),
                                             o_reach=omax, centre_in=bool(centre_in),
                                             bounds=bd.calls)
    p = Path(args.out)
    old = json.loads(p.read_text()) if p.exists() else {}
    old.update(out)
    p.write_text(json.dumps(old, indent=2))
    print(f"\n  wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

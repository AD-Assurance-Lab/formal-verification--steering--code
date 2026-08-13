#!/usr/bin/env python3
"""Predict closed-loop outcome from the EQUILIBRIUM lateral offset, not from a sign test.

WHY THE SIGN TEST WAS NOT ENOUGH. The restoring-sign criterion reached 14/14 but scored the
corrected (intersection-excluded) ground truth 6/8, over-predicting failure on clear and fog.
Its violation intervals do not discriminate: `S_clear` violates exactly the same two
intervals under fog and under night, yet fog passes 0/10 and night fails 10/10. Every
violation sits either inside the 0.5 m dead-band or beyond the measured open-loop reach
(0.02-0.22 m), so sizing the tube by reachability certifies all four -- including night.
Sign is simply not the quantity that separates these outcomes.

WHAT DOES SEPARATE THEM. A lane-keeping policy settles where its steering equals the
steering that held the lane on the nominal path. Writing s_cond(o) for the mean steering at
lateral offset o under the disturbance,

    D(o) = s_cond(o) - s_clear(0)          equilibrium at D(o*) = 0

SIGN CONVENTION, fixed empirically rather than by reasoning about handedness. CARLA's
frame is left-handed, so the normal used at capture points RIGHT of the lane, and a
restoring policy answers a positive offset with LEFT (negative) steering. The check that
settles it: `S_clear` under clear weather drives the route without departing, so whatever
sign its gain takes IS the restoring sign -- measured at -0.187. Hence

    D decreasing through the root  =  restoring  =  a STABLE equilibrium

PER POSE, NOT POOLED. Averaging the 8 poses before solving cancels biases of opposite sign
at different points on the route and reports a policy as settled when it is not. The car
drives through every pose, so the equilibrium is solved at each and the FRACTION of poses
whose settling point lies outside the lane is what predicts departure.

    PASS   the car settles within the budget at (almost) every pose
    FAIL   at a meaningful fraction of poses it settles outside the lane, or not at all

This is a magnitude comparison against a budget the study already fixed (0.668 m), with no
threshold fitted to the closed-loop results it is scored against.

    python scripts/equilibrium_offset.py
"""
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
from student import StudentNet  # noqa: E402

NPZ = REPO / "results" / "calibration" / "offset_frames.npz"
STUDENTS = [("S_clear", "S_clear_84x28", (8, 16, 16), 32),
            ("S_mixed", "S_mixed_84x28_w3", (24, 48, 48), 96)]


def stable_root(off, d):
    """Smallest-|o| stable root of D, by linear interpolation between grid points.

    Stable means D DECREASES through the crossing (see the sign convention above). An
    unstable crossing is a divergence point, not a settling point, and must never be
    reported as an equilibrium -- that confusion is what the criterion exists to catch."""
    best = None
    for i in range(len(off) - 1):
        a, b = float(d[i]), float(d[i + 1])
        if a == 0.0:
            r = float(off[i])
            dec = (d[min(i + 1, len(d) - 1)] - d[max(i - 1, 0)]) < 0
        elif a * b < 0:
            r = float(off[i] + (off[i + 1] - off[i]) * (-a) / (b - a))
            dec = b < a
        else:
            continue
        if dec and (best is None or abs(r) < abs(best)):
            best = r
    return best


def main():
    if not NPZ.exists():
        print(f"missing {NPZ}\nrun: python scripts/capture_offset_frames.py")
        return 1
    z = np.load(NPZ, allow_pickle=True)
    frames, off, conds = z["frames"], z["offsets"], [str(c) for c in z["conds"]]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ci_clear = conds.index("clear")
    oi_zero = int(np.argmin(np.abs(off)))

    npose = frames.shape[1]
    print(f"\nEQUILIBRIUM OFFSET   {npose} poses, westbound, "
          f"CTE budget {C.CTE_BUDGET_M:.3f} m")
    print("  settling point of the disturbed policy, solved PER POSE;")
    print("  FAIL when it lies outside the lane at a meaningful fraction of poses\n")
    print(f"  {'model':9s} {'cond':9s} {'gain':>8s} {'median o*':>10s} "
          f"{'worst o*':>9s} {'poses out':>10s}  verdict")

    rows = []
    for nm, ck, ch, fc in STUDENTS:
        m = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
        m.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
        m.eval()
        with torch.no_grad():
            s = m(torch.from_numpy(frames.reshape(-1, 3, 28, 84)).to(dev)
                  ).cpu().numpy().reshape(frames.shape[:3])   # (cond, pose, offset)
        near = np.abs(off) <= 1.0
        for ci, cond in enumerate(conds):
            roots, gains, bad = [], [], 0
            for pi in range(npose):
                # the control that held THIS pose is its own clear-weather, centred steering
                d = s[ci, pi] - float(s[ci_clear, pi, oi_zero])
                gains.append(float(np.polyfit(off[near], d[near], 1)[0]))
                r = stable_root(off, d)
                if r is None or abs(r) > C.CTE_BUDGET_M:
                    bad += 1
                if r is not None:
                    roots.append(abs(r))
            frac = bad / npose
            med = float(np.median(roots)) if roots else float("nan")
            wor = float(np.max(roots)) if roots else float("nan")
            verdict = "PASS" if frac <= 0.25 else "FAIL"
            rows.append((nm, cond, float(np.mean(gains)), med, wor, frac, verdict))
            print(f"  {nm:9s} {cond:9s} {np.mean(gains):+8.4f} {med:10.3f} {wor:9.3f} "
                  f"{bad:5d}/{npose:<4d} {verdict}")

    truth = {("S_clear", "clear"): "PASS", ("S_clear", "fog"): "PASS",
             ("S_clear", "night"): "FAIL", ("S_clear", "shadows"): "FAIL",
             ("S_mixed", "clear"): "PASS", ("S_mixed", "fog"): "PASS",
             ("S_mixed", "night"): "PASS", ("S_mixed", "shadows"): "PASS"}
    print("\n  scored against OPEN-ROAD closed loop (intersection out of scope):")
    ok = n = 0
    for nm, cond, _, _, _, _, v in rows:
        t = truth.get((nm, cond))
        if t is None:
            print(f"    {nm:9s} {cond:9s} predicted {v.split()[0]:4s}   (no open-road "
                  f"ground truth yet)")
            continue
        good = v.startswith(t)
        ok += good
        n += 1
        print(f"    {nm:9s} {cond:9s} predicted {v.split()[0]:4s}  actual {t:4s}  "
              f"{'agree' if good else 'DISAGREE'}")
    print(f"\n  agreement: {ok}/{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

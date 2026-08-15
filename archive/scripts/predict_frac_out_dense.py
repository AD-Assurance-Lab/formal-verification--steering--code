#!/usr/bin/env python3
"""Fraction of lap out of lane, from densely-sampled equilibria with a RESPONSE-TIME filter.

WHY A FILTER. Solving the equilibrium at scattered poses and averaging gave the right
ranking (night 65.6% predicted against 58.7% measured, shadows 25.3% against 13.5%) on top
of a ~20% false-positive floor that put clear and fog over the line. The floor is not noise;
it is a missing piece of physics. The equilibrium is measured by teleporting the vehicle
with physics frozen, so a single adverse pose counts as a departure. A real vehicle cannot
translate laterally faster than its response allows: the study already fixed
T_CLOSED_LOOP_S = 1.85 s for exactly this reason, when the naive steering tolerance had to
shrink 3.42x. At 20 mph that is 16.5 m of road.

So an out-of-lane equilibrium only produces a departure if it PERSISTS over a contiguous
stretch at least that long. Isolated poses are transients the vehicle drives through.

    predicted frac out = fraction of route inside runs of adverse equilibrium >= 16.5 m

Dense along-route sampling (40 poses) is what makes runs measurable; the scattered captures
had no spatial ordering to run-length filter.

    python scripts/predict_frac_out_dense.py
"""
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "scripts"))

import config as C  # noqa: E402
from student import StudentNet  # noqa: E402
from equilibrium_helpers import stable_root  # noqa: E402

NPZ = REPO / "results" / "calibration" / "offset_frames.npz"
STUDENTS = [("S_clear", "S_clear_84x28", (8, 16, 16), 32),
            ("S_mixed", "S_mixed_84x28_w3", (24, 48, 48), 96)]
MEASURED = {("S_clear", "clear"): 0.0, ("S_clear", "fog"): 0.0,
            ("S_clear", "night"): 0.587, ("S_clear", "shadows"): 0.135,
            ("S_mixed", "clear"): 0.0, ("S_mixed", "fog"): 0.0,
            ("S_mixed", "night"): 0.0, ("S_mixed", "shadows"): 0.0}
SPEED_MS = C.TARGET_SPEED_MS if hasattr(C, "TARGET_SPEED_MS") else 8.94


def main():
    z = np.load(NPZ, allow_pickle=True)
    frames, off = z["frames"], z["offsets"]
    conds = [str(c) for c in z["conds"]]
    px, py = z["pose_x"], z["pose_y"]
    npose = frames.shape[1]
    oi_zero = int(np.argmin(np.abs(off)))
    ci_clear = conds.index("clear")
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    xy = np.stack([px[ci_clear], py[ci_clear]], 1)
    step = float(np.median(np.linalg.norm(np.diff(xy, axis=0), axis=1)))
    resp_m = 1.85 * SPEED_MS
    min_run = max(1, int(round(resp_m / step)))
    print(f"\nFRACTION OF LAP OUT OF LANE   {npose} poses, spacing {step:.1f} m")
    print(f"  response distance {resp_m:.1f} m at {SPEED_MS:.2f} m/s "
          f"-> a run must span {min_run} consecutive poses to depart the vehicle\n")
    print(f"  {'model':9s} {'cond':9s} {'raw':>7s} {'filtered':>9s} {'measured':>9s} "
          f" verdict actual")

    ok = n = 0
    for nm, ck, ch, fc in STUDENTS:
        m = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
        m.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
        m.eval()
        with torch.no_grad():
            s = m(torch.from_numpy(frames.reshape(-1, 3, 28, 84)).to(dev)
                  ).cpu().numpy().reshape(frames.shape[:3])
        for ci, cond in enumerate(conds):
            bad = np.zeros(npose, bool)
            for pi in range(npose):
                d = s[ci, pi] - float(s[ci_clear, pi, oi_zero])
                r = stable_root(off, d)
                bad[pi] = (r is None) or (abs(r) > C.CTE_BUDGET_M)
            # keep only runs long enough for the vehicle to actually translate out
            kept = np.zeros(npose, bool)
            i = 0
            while i < npose:
                if bad[i]:
                    j = i
                    while j < npose and bad[j]:
                        j += 1
                    if (j - i) >= min_run:
                        kept[i:j] = True
                    i = j
                else:
                    i += 1
            raw, filt = bad.mean(), kept.mean()
            meas = MEASURED[(nm, cond)]
            v = "FAIL" if filt > 0.05 else "PASS"
            a = "FAIL" if meas > 0.05 else "PASS"
            ok += (v == a)
            n += 1
            print(f"  {nm:9s} {cond:9s} {raw*100:6.1f}% {filt*100:8.1f}% "
                  f"{meas*100:8.1f}%  {v:6s} {a:6s} {'agree' if v==a else 'DISAGREE'}")
    print(f"\n  agreement: {ok}/{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

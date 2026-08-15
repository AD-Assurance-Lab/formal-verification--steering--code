#!/usr/bin/env python3
"""Predict the FRACTION OF LAP spent out of lane, not just a pass/fail bit.

WHY. Two pose samplings gave two different answers and both were defensible: uniform poses
scored 7/8 but missed the stretch where shadows actually fails (its poses sat at the 37th
percentile of shadow strength while 12.1% of the route was darker than any of them);
strength-stratified poses caught shadows and then over-predicted fog and `S_mixed`/shadows,
scoring 6/8. Neither is a sampling bug. They answer different questions -- "a typical pose"
versus "the worst pose" -- and the closed loop asks a third one. Its failure metric is
`frac_over_budget`: 58.7% of the lap for night, 13.5% for shadows, 0% for fog. A criterion
that emits one bit cannot be scored against a quantity that ranges over two orders of
magnitude, and picking a pose set is then an unconstrained knob.

WHAT THIS DOES INSTEAD. Stratified sampling estimates a population quantity only with
importance weights. Pooling both captures gives 16 poses per condition spanning the 0th to
99th percentile of disturbance strength, each labelled with whether the policy's equilibrium
there lies outside the lane. That is a function of strength, so it can be integrated over
the strength distribution the route actually presents:

    predicted frac out  =  E_{route}[ 1{ equilibrium out of lane at strength m } ]

estimated by binning the 16 poses on m and weighting each bin by its route frequency. The
prediction is then a NUMBER comparable with the measured `frac_over_budget`, with no pose
set to choose and no threshold to tune.

    python scripts/predict_frac_out.py
"""
import sys
import csv
from pathlib import Path

import cv2
import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
from student import StudentNet  # noqa: E402
from equilibrium_helpers import stable_root  # noqa: E402

CAL = REPO / "results" / "calibration"
STUDENTS = [("S_clear", "S_clear_84x28", (8, 16, 16), 32),
            ("S_mixed", "S_mixed_84x28_w3", (24, 48, 48), 96)]
MEASURED = {("S_clear", "clear"): 0.0, ("S_clear", "fog"): 0.0,
            ("S_clear", "night"): 0.587, ("S_clear", "shadows"): 0.135,
            ("S_mixed", "clear"): 0.0, ("S_mixed", "fog"): 0.0,
            ("S_mixed", "night"): 0.0, ("S_mixed", "shadows"): 0.0}


def route_strengths(cond, roi):
    """Road-ROI disturbance magnitude at every pose-matched frame on the route."""
    base = REPO / "pipeline" / "data" / "live_pairs"
    rows = list(csv.DictReader(open(base / "manifest.csv")))
    cr = [r for r in rows if r["weather"] == "clear" and r["direction"] == "westbound"]
    orr = [r for r in rows if r["weather"] == cond and r["direction"] == "westbound"]
    if not orr:
        return np.zeros(1), np.zeros((1, 2))
    cp = np.array([[float(r["x"]), float(r["y"])] for r in cr])
    op = np.array([[float(r["x"]), float(r["y"])] for r in orr])
    d = np.linalg.norm(cp[:, None, :] - op[None, :, :], axis=2)
    j = d.argmin(1)
    idx = np.flatnonzero(d[np.arange(len(cp)), j] < 0.10)[::3]
    mags, locs = [], []
    for i in idx:
        a = cv2.imread(str(base / cr[i]["image"])).astype(np.float32) / 255.0
        b = cv2.imread(str(base / orr[j[i]]["image"])).astype(np.float32) / 255.0
        mags.append(float(np.abs(a[roi] - b[roi]).mean()))
        locs.append(cp[i])
    return np.array(mags), np.array(locs)


def main():
    caps = [CAL / "offset_frames_uniform.npz", CAL / "offset_frames.npz"]
    caps = [p for p in caps if p.exists()]
    if not caps:
        print("no captures found; run scripts/capture_offset_frames.py")
        return 1
    roi = slice(*C.ROAD_ROI_ROWS)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    loaded = [np.load(p, allow_pickle=True) for p in caps]
    conds = [str(c) for c in loaded[0]["conds"]]
    off = loaded[0]["offsets"]
    oi_zero = int(np.argmin(np.abs(off)))
    ci_clear = conds.index("clear")

    # route strength distribution and per-pose strength, per condition
    route = {c: route_strengths(c, roi) for c in conds if c != "clear"}

    print(f"\nPREDICTED FRACTION OF LAP OUT OF LANE   pooled {len(caps)} captures, "
          f"budget {C.CTE_BUDGET_M:.3f} m")
    print("  equilibrium solved per pose, then integrated over the route's own")
    print("  disturbance-strength distribution\n")
    print(f"  {'model':9s} {'cond':9s} {'poses':>6s} {'predicted':>10s} "
          f"{'measured':>9s}  verdict  actual")

    ok = n = 0
    for nm, ck, ch, fc in STUDENTS:
        m = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
        m.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
        m.eval()
        for ci, cond in enumerate(conds):
            strengths, outs = [], []
            for z in loaded:
                fr = z["frames"]
                px, py = z["pose_x"], z["pose_y"]
                npose = fr.shape[1]
                with torch.no_grad():
                    s = m(torch.from_numpy(fr[ci].reshape(-1, 3, 28, 84)).to(dev)
                          ).cpu().numpy().reshape(npose, len(off))
                    sc = m(torch.from_numpy(fr[ci_clear].reshape(-1, 3, 28, 84)).to(dev)
                           ).cpu().numpy().reshape(npose, len(off))
                for pi in range(npose):
                    d = s[pi] - float(sc[pi, oi_zero])
                    r = stable_root(off, d)
                    outs.append(1.0 if (r is None or abs(r) > C.CTE_BUDGET_M) else 0.0)
                    if cond == "clear":
                        strengths.append(0.0)
                        continue
                    rm, rl = route[cond]
                    x = px[ci][pi] if px.ndim == 2 else px[pi]
                    y = py[ci][pi] if py.ndim == 2 else py[pi]
                    k = int(np.argmin(np.linalg.norm(rl - np.array([x, y]), axis=1)))
                    strengths.append(float(rm[k]))
            strengths = np.array(strengths)
            outs = np.array(outs)

            if cond == "clear":
                pred = float(outs.mean())
            else:
                rm, _ = route[cond]
                # bin on strength; weight each bin by how much of the route falls in it
                edges = np.quantile(strengths, [0, 0.34, 0.67, 1.0])
                edges[-1] += 1e-9
                pred = 0.0
                for a, b in zip(edges[:-1], edges[1:]):
                    sel = (strengths >= a) & (strengths < b)
                    if not sel.any():
                        continue
                    w = float(((rm >= a) & (rm < b)).mean())
                    pred += w * float(outs[sel].mean())
                tot = sum(float(((rm >= a) & (rm < b)).mean())
                          for a, b in zip(edges[:-1], edges[1:]))
                if tot > 0:
                    pred /= tot

            meas = MEASURED[(nm, cond)]
            v = "FAIL" if pred > 0.05 else "PASS"
            a = "FAIL" if meas > 0.05 else "PASS"
            ok += (v == a)
            n += 1
            print(f"  {nm:9s} {cond:9s} {len(outs):6d} {pred*100:9.1f}% "
                  f"{meas*100:8.1f}%  {v:7s} {a}  {'agree' if v==a else 'DISAGREE'}")
    print(f"\n  agreement: {ok}/{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

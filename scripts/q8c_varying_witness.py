#!/usr/bin/env python3
"""Q8c: exhibit a SPATIALLY VARYING witness for a NOT_CERTIFIED cell.

THE GAP THIS CLOSES. `falsify_witness.py` searches a single global intensity s and, for
the two Town06 cells that carry no witness, finds nothing -- fog peaks at 0.845x tolerance
at s = 0.697. Its own docstring says why that is not the end of the story:

    "The certifier bounds, per pose, the worst case over s, and THEN averages over poses
     -- so s is free to vary from pose to pose. That is deliberate and documented (it
     covers spatially varying disturbance, fog thicker in a hollow) and it is sound. But
     it quantifies over a strictly larger set than a single global intensity, so a
     NOT_CERTIFIED cell may have no witness at all: sound, undecided."

So the cell was called undecided because the witness search covers a NARROWER family than
the certificate. This searches the family the certificate actually quantifies over: one
intensity per pose, chosen independently.

WHAT A HIT MEANS. A profile s_1..s_n, one intensity per scored pose, all inside [0,1], is
a member of the declared disturbance family -- it is what spatially varying fog looks like.
If its lap-mean bias exceeds tolerance, the cell is FALSIFIED, not undecided, and the
witness is exhibited rather than inferred.

WHAT IT IS NOT. Still a lower bound: dense sampling per pose finds attained values, so a
miss means "no witness found", never "safe". And the profile is not claimed to be
physically plausible fog -- it is claimed to be inside the set the certificate quantifies
over, which is the only thing that makes a refusal correct or incorrect.

    STUDY_MAP=Town06 python3 scripts/q8c_varying_witness.py --student S_mixed_t06lap_168x56_w4_s3
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "scripts"))

import config as C  # noqa: E402
from gpu import require_cuda  # noqa: E402
from student import StudentNet  # noqa: E402
import certify_town06 as ct  # noqa: E402
from study import town06_design as D  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--student", default="S_mixed_t06lap_168x56_w4_s3")
    ap.add_argument("--channels", default="32,64,64")
    ap.add_argument("--fc", type=int, default=128)
    ap.add_argument("--conditions", default="fog,night,low_sun")
    ap.add_argument("--grid", type=int, default=401)
    ap.add_argument("--stride", type=int, default=8)
    ap.add_argument("--out", default="results/town06/beta/varying_witness.json")
    a = ap.parse_args()

    dev = require_cuda(tries=1, wait_s=0)
    tol = C.CLOSED_LOOP_TOLERANCE
    h, w = C.TOWN06_INPUT_H, C.TOWN06_INPUT_W
    ch = tuple(int(x) for x in a.channels.split(","))
    net = StudentNet(h, w, channels=ch, fc=a.fc).to(dev)
    net.load_state_dict(torch.load(Path(C.CHECKPOINT_DIR) / f"{a.student}.pth",
                                   map_location=dev, weights_only=True))
    net.eval()

    print(f"Q8c -- spatially varying witness search, {a.student}")
    print(f"  tolerance {tol:.6f}, {a.grid}-point grid per pose, stride {a.stride}\n")
    out = {"student": a.student, "grid": a.grid, "tolerance": tol, "cells": {}}

    for cond in a.conditions.split(","):
        s_hi, s_lo, dev_hi, dev_lo = [], [], [], []
        for sec in D.SECTIONS:
            p = ct.CAPTURES / f"lap_{sec}_{cond}.npz"
            base = ct.CAPTURES / f"lap_{sec}_clear.npz"
            if not p.exists() or not base.exists():
                continue
            mask = ct.scope_mask(p, "full")
            bmask = ct.scope_mask(base, "full")
            clr, _ = ct.baseline_for(p, ct.nominal(base, "clear", bmask), mask)
            dis = ct.nominal(p, cond, mask)
            if dis is None or len(dis) != len(clr):
                continue
            with torch.no_grad():
                sc = net(torch.from_numpy(clr[::a.stride]).to(dev)).cpu().numpy().reshape(-1)
            svals = np.linspace(0.0, 1.0, a.grid, dtype=np.float32)
            for i, k in enumerate(range(0, len(clr), a.stride)):
                x0 = torch.from_numpy(clr[k].astype(np.float32)).to(dev).unsqueeze(0)
                d1 = torch.from_numpy((dis[k] - clr[k]).astype(np.float32)).to(dev).unsqueeze(0)
                res = []
                with torch.no_grad():
                    for b in range(0, a.grid, 64):
                        ss = torch.from_numpy(svals[b:b + 64]).to(dev).view(-1, 1, 1, 1)
                        res.append(net(x0 + ss * d1).cpu().numpy().reshape(-1))
                o = np.concatenate(res) - sc[i]
                j_hi, j_lo = int(o.argmax()), int(o.argmin())
                s_hi.append(float(svals[j_hi])); dev_hi.append(float(o[j_hi]))
                s_lo.append(float(svals[j_lo])); dev_lo.append(float(o[j_lo]))

        bhi, blo = float(np.mean(dev_hi)), float(np.mean(dev_lo))
        hit_hi, hit_lo = bhi > tol, blo < -tol
        rec = dict(poses=len(dev_hi),
                   hi=bhi, hi_x_tol=bhi / tol, lo=blo, lo_x_tol=blo / tol,
                   witness_hi=bool(hit_hi), witness_lo=bool(hit_lo),
                   witness=bool(hit_hi or hit_lo),
                   s_profile_hi=s_hi, s_profile_lo=s_lo,
                   distinct_s_hi=len(set(s_hi)), distinct_s_lo=len(set(s_lo)))
        out["cells"][f"{a.student}/{cond}"] = rec
        verdict = "WITNESS" if rec["witness"] else "no witness found"
        print(f"  {cond:9s} {len(dev_hi):4d} poses   "
              f"lo {blo / tol:+7.3f}x  hi {bhi / tol:+7.3f}x   -> {verdict}"
              + (f"  (hi side)" if hit_hi else (f"  (lo side)" if hit_lo else "")))
        print(f"            distinct intensities used: {rec['distinct_s_hi']} (hi), "
              f"{rec['distinct_s_lo']} (lo)")

    dest = REPO / a.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {a.out}")
    print("\nA hit is a member of the DECLARED family -- one intensity per pose, all in")
    print("[0,1] -- whose lap-mean bias exceeds tolerance. That makes the cell FALSIFIED")
    print("under the quantification the certificate uses, not undecided.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Exhibit a SPATIALLY VARYING witness for a NOT_CERTIFIED cell.

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

    STUDY_MAP=Town06 python3 scripts/verify/q8c_varying_witness.py --student S_mixed_t06lap_168x56_w4_s3
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

# The root comes from the package, never from counting directories up from this
# file. Counting is what broke every entry point here when scripts/ was grouped
# into folders: each one silently resolved to <repo>/scripts and looked for the
# study's artifacts there.
from steering import REPO_ROOT

REPO = Path(REPO_ROOT)

from steering import config as C
from steering.gpu import require_cuda
from steering.networks.student import StudentNet
from steering.verify import captures as ct
from steering.study import town06_design as D


def short_name(student, highway):
    """The name witness_full.json files a policy under.

    That file uses the study's short name for a policy; this script is given the
    checkpoint that was loaded, and on one road they are not the same string because the
    shipped policy is a later DAgger round. Resolving through the same table both roads
    are declared in keeps the two files joinable instead of nearly joinable.
    """
    table = C.STUDENTS if highway else C.TOWN06_STUDENTS
    for nm, ck_base, *_ in table:
        if student in (ck_base, C.final_student(ck_base)):
            return nm
    return student


def per_pose(net, clr, dis, dev, grid, stride, s_hi, s_lo, dev_hi, dev_lo):
    """Accumulate the per-pose extremes for one capture pair into the four lists.

    One intensity per pose, chosen independently, which is the family the certificate
    actually quantifies over. Appends rather than returns so a road whose cell spans
    several captures pools them, exactly as the arterial's sections always did.
    """
    with torch.no_grad():
        sc = net(torch.from_numpy(clr[::stride]).to(dev)).cpu().numpy().reshape(-1)
    svals = np.linspace(0.0, 1.0, grid, dtype=np.float32)
    for i, k in enumerate(range(0, len(clr), stride)):
        x0 = torch.from_numpy(clr[k].astype(np.float32)).to(dev).unsqueeze(0)
        d1 = torch.from_numpy((dis[k] - clr[k]).astype(np.float32)).to(dev).unsqueeze(0)
        res = []
        with torch.no_grad():
            for b in range(0, grid, 64):
                ss = torch.from_numpy(svals[b:b + 64]).to(dev).view(-1, 1, 1, 1)
                res.append(net(x0 + ss * d1).cpu().numpy().reshape(-1))
        o = np.concatenate(res) - sc[i]
        j_hi, j_lo = int(o.argmax()), int(o.argmin())
        s_hi.append(float(svals[j_hi])); dev_hi.append(float(o[j_hi]))
        s_lo.append(float(svals[j_lo])); dev_lo.append(float(o[j_lo]))


def _highway_nominal(path, cond):
    """The highway pose selection, identical to the one its certifier uses.

    Truncated to the scored extent the certificate covers. A different slice here would
    make the witness and the bound statements about different stretches of road.
    """
    z = np.load(path, allow_pickle=True)
    conds = [str(c) for c in z["conds"]]
    if cond not in conds:
        return None
    fr = z["frames"][conds.index(cond)]
    oi = int(np.argmin(np.abs(z["offsets"])))
    yi = int(np.argmin(np.abs(z["yaws"])))
    fr = fr[:, oi, yi]
    px, py = z["pose_x"], z["pose_y"]
    d = np.concatenate([[0], np.cumsum(np.hypot(np.diff(px), np.diff(py)))])
    return fr[:int(np.searchsorted(d, 2861.0))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--student", default="S_mixed_t06lap_168x56_w4_s3")
    ap.add_argument("--channels", default="32,64,64")
    ap.add_argument("--fc", type=int, default=128)
    ap.add_argument("--conditions", default="fog,night,low_sun")
    ap.add_argument("--grid", type=int, default=401)
    ap.add_argument("--stride", type=int, default=8)
    ap.add_argument("--out", default=None,
                    help="defaults to the beta directory of whichever road STUDY_MAP "
                         "selects")
    ap.add_argument("--into", default=None,
                    help="also write pp_worst, pp_worst_x_tol and pp_witness into this "
                         "witness_full.json, matching cells by key")
    a = ap.parse_args()

    highway = C.STUDY_MAP == "Town04"
    if a.out is None:
        a.out = (f"results/{'highway' if highway else 'arterial'}"
                 f"/beta/varying_witness.json")

    dev = require_cuda(tries=1, wait_s=0)
    tol = C.CLOSED_LOOP_TOLERANCE
    # The two roads feed their students different input geometry, and reading the
    # arterial's size on the highway silently builds the wrong network rather than
    # failing: the checkpoint would refuse to load, but only after the run had started.
    h, w = (28, 84) if highway else (C.TOWN06_INPUT_H, C.TOWN06_INPUT_W)
    ch = tuple(int(x) for x in a.channels.split(","))
    net = StudentNet(h, w, channels=ch, fc=a.fc).to(dev)
    net.load_state_dict(torch.load(Path(C.CHECKPOINT_DIR) / f"{a.student}.pth",
                                   map_location=dev, weights_only=True))
    net.eval()

    print(f"spatially varying witness search, {a.student}")
    print(f"  tolerance {tol:.6f}, {a.grid}-point grid per pose, stride {a.stride}\n")
    out = {"student": a.student, "grid": a.grid, "tolerance": tol, "cells": {}}

    # A CELL IS WHATEVER THE CERTIFICATE CALLS A CELL, and the two roads disagree. The
    # arterial pools its sections into one lap-mean, so a cell is student/condition. The
    # highway certifies each direction separately, so a cell is direction/student/
    # condition and pooling the two would average over a boundary the certificate never
    # crosses. The keys below are the ones witness_full.json already uses on each road.
    nm = short_name(a.student, highway)
    if highway:
        units = [(f"{d}/{nm}/{c}", [(d, c)])
                 for c in a.conditions.split(",") for d in ("westbound", "eastbound")]
    else:
        units = [(f"{nm}/{c}", [(sec, c) for sec in D.SECTIONS])
                 for c in a.conditions.split(",")]

    for key, pairs in units:
        cond = pairs[0][1]
        s_hi, s_lo, dev_hi, dev_lo = [], [], [], []
        for sec, _c in pairs:
            if highway:
                cal = REPO / "results" / "highway" / "calibration"
                p, base = cal / f"lap_{sec}_{cond}.npz", cal / f"lap_{sec}_clear.npz"
                if not p.exists() or not base.exists():
                    continue
                clr, dis = _highway_nominal(base, "clear"), _highway_nominal(p, cond)
            else:
                p = ct.CAPTURES / f"lap_{sec}_{cond}.npz"
                base = ct.CAPTURES / f"lap_{sec}_clear.npz"
                if not p.exists() or not base.exists():
                    continue
                mask = ct.scope_mask(p, "full")
                bmask = ct.scope_mask(base, "full")
                clr, _ = ct.baseline_for(p, ct.nominal(base, "clear", bmask), mask)
                dis = ct.nominal(p, cond, mask)
            if dis is None or clr is None or len(dis) != len(clr):
                continue
            per_pose(net, clr, dis, dev, a.grid, a.stride, s_hi, s_lo, dev_hi, dev_lo)

        if not dev_hi:
            continue
        bhi, blo = float(np.mean(dev_hi)), float(np.mean(dev_lo))
        hit_hi, hit_lo = bhi > tol, blo < -tol
        rec = dict(poses=len(dev_hi),
                   hi=bhi, hi_x_tol=bhi / tol, lo=blo, lo_x_tol=blo / tol,
                   witness_hi=bool(hit_hi), witness_lo=bool(hit_lo),
                   witness=bool(hit_hi or hit_lo),
                   s_profile_hi=s_hi, s_profile_lo=s_lo,
                   distinct_s_hi=len(set(s_hi)), distinct_s_lo=len(set(s_lo)))
        out["cells"][key] = rec
        verdict = "WITNESS" if rec["witness"] else "no witness found"
        print(f"  {key:28s} {len(dev_hi):4d} poses   "
              f"lo {blo / tol:+7.3f}x  hi {bhi / tol:+7.3f}x   -> {verdict}"
              + ("  (hi side)" if hit_hi else ("  (lo side)" if hit_lo else "")))
        print(f"            distinct intensities used: {rec['distinct_s_hi']} (hi), "
              f"{rec['distinct_s_lo']} (lo)")

    if a.into:
        # THE GLOBAL SEARCH AND THIS ONE BELONG BESIDE EACH OTHER. A cell refused by the
        # bound with no global witness is only "sound but undecided" until the wider
        # family the certificate quantifies over has also been searched, and a reader
        # comparing the two should not have to join two files by hand.
        wf = REPO / a.into
        doc = json.loads(wf.read_text())
        wrote = []
        for key, rec in out["cells"].items():
            if key not in doc:
                print(f"  {key}: no such cell in {a.into}, not merged")
                continue
            worst = rec["hi"] if abs(rec["hi"]) >= abs(rec["lo"]) else rec["lo"]
            doc[key]["pp_worst"] = worst
            doc[key]["pp_worst_x_tol"] = worst / tol
            doc[key]["pp_witness"] = rec["witness"]
            wrote.append(key)
        wf.write_text(json.dumps(doc, indent=2) + "\n")
        print(f"\nmerged pp_worst, pp_worst_x_tol and pp_witness into {a.into} "
              f"for {len(wrote)} cell(s)")

    dest = REPO / a.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {a.out}")
    print("\nA hit is a member of the DECLARED family -- one intensity per pose, all in")
    print("[0,1] -- whose lap-mean bias exceeds tolerance. That makes the cell FALSIFIED")
    print("under the quantification the certificate uses, not undecided.")


if __name__ == "__main__":
    main()

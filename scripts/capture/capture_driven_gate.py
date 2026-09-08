#!/usr/bin/env python3
"""THE CAPTURE GATE: do captured frames reproduce what the vehicle actually commanded?

The paper states this as a precondition -- "Before any certificate is computed we require
captured steering to match the steering the vehicle actually commanded at the same
locations", full lap, mean |difference| 0.0137 against a 0.05 threshold. It is what
exposed the ride-height error that made one direction's captures unusable at 0.202 while
the other passed at 0.016 purely because its opening stretch is flat.

It was never run for either rebuild. Sound bounds computed on frames that do not
reproduce the system prove nothing about the system, so a certificate without this gate is
a number whose premise is unchecked -- which is exactly the shape of the 160 m capture
defect this script was written alongside.

Compares, per pose: the student's steering on the CAPTURED frame against the steering the
same student commanded while DRIVING, matched on position. No simulator needed; both
artifacts already exist.

    STUDY_MAP=Town04 python3 scripts/capture/capture_driven_gate.py \
        --captures results/highway/calibration --drives results/oracle
"""
import argparse
import glob
import json
import os
import sys
from pathlib import Path
# The root comes from the package, never from counting directories up from this
# file. Counting is what broke every entry point here when scripts/ was grouped
# into folders: each one silently resolved to <repo>/scripts and looked for the
# study's artifacts there.
from steering import REPO_ROOT

REPO = Path(REPO_ROOT)

from steering.gpu import require_cuda
import numpy as np
import torch
import csv
from steering import config as C
from steering.networks.student import StudentNet

THRESHOLD = 0.05          # the paper's stated gate


def nominal(path, cond):
    z = np.load(path, allow_pickle=True)
    conds = [str(c) for c in z["conds"]]
    if cond not in conds:
        return None, None, None
    fr = z["frames"][conds.index(cond)]
    oi = int(np.argmin(np.abs(z["offsets"]))); yi = int(np.argmin(np.abs(z["yaws"])))
    return fr[:, oi, yi], np.asarray(z["pose_x"], float), np.asarray(z["pose_y"], float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--captures", required=True)
    ap.add_argument("--drives", default="results/oracle")
    ap.add_argument("--cond", default="clear")
    ap.add_argument("--students", default=None,
                    help="override the student list: name:ck:c1,c2,c3:fc[;...]")
    ap.add_argument("--in-w", type=int, default=None, dest="in_w")
    ap.add_argument("--in-h", type=int, default=None, dest="in_h")
    args = ap.parse_args()
    # require_cuda, not is_available(): the flag is False while CARLA initialises on
    # the same device, and was True on a card the installed torch had no kernels for
    # (sm_120 vs an sm_90 build). Both end in a silent CPU run that still prints numbers.
    dev = require_cuda()
    # A capture set is gated for the STUDENT and INPUT SIZE it was captured at. A
    # 84x28 set cannot be gated against the study's 168x56 students -- the frames are a
    # different projection, so the comparison would be meaningless rather than merely
    # wrong. Both are therefore overridable together, and neither default moves.
    students = C.TOWN06_STUDENTS if C.STUDY_MAP == "Town06" else C.STUDENTS
    in_h, in_w = ((C.TOWN06_INPUT_H, C.TOWN06_INPUT_W) if C.STUDY_MAP == "Town06" else (28, 84))
    if args.students:
        students = tuple((f.split(":")[0], f.split(":")[1],
                          tuple(int(x) for x in f.split(":")[2].split(",")),
                          int(f.split(":")[3]))
                         for f in args.students.split(";") if f.strip())
    if (args.in_w is None) != (args.in_h is None):
        sys.exit("--in-w and --in-h must be given together: a capture set has ONE "
                 "projection and half of it is not a projection.")
    if args.in_w:
        in_h, in_w = args.in_h, args.in_w
    print(f"  students: {[n for n, *_ in students]}   projection {in_w}x{in_h}")

    print(f"\nCAPTURE GATE -- {C.STUDY_MAP}, condition '{args.cond}', threshold {THRESHOLD}")
    worst, rows = 0.0, []
    for nm, ck_base, ch, fc in students:
        ck = ck_base if args.students else C.final_student(ck_base)
        net = StudentNet(in_h, in_w, channels=ch, fc=fc).to(dev)
        net.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev,
                                       weights_only=True))
        net.eval()
        for cap in sorted(glob.glob(os.path.join(args.captures, f"lap_*_{args.cond}.npz"))):
            direction = Path(cap).stem.split("_")[1]
            fr, px, py = nominal(cap, args.cond)
            if fr is None:
                continue
            drv = os.path.join(args.drives, f"eval_{ck}_{direction}.csv")
            if not os.path.exists(drv):
                print(f"  {nm:9s} {direction:10s} no driven trace ({os.path.basename(drv)}) -- SKIP")
                continue
            d = list(csv.DictReader(open(drv)))
            dx = np.array([float(r["x"]) for r in d]); dy = np.array([float(r["y"]) for r in d])
            ds = np.array([float(r["nn_steer"]) for r in d])
            with torch.no_grad():
                cs = net(torch.from_numpy(np.ascontiguousarray(fr)).to(dev)).cpu().numpy().ravel()
            # match each captured pose to the nearest driven pose
            idx = [int(np.argmin((dx - x) ** 2 + (dy - y) ** 2)) for x, y in zip(px, py)]
            near = np.sqrt((dx[idx] - px) ** 2 + (dy[idx] - py) ** 2)
            keep = near < 2.0                       # only poses the drive actually visited
            if keep.sum() < 50:
                print(f"  {nm:9s} {direction:10s} only {keep.sum()} matched poses -- SKIP")
                continue
            diff = float(np.mean(np.abs(cs[keep] - ds[np.array(idx)[keep]])))
            worst = max(worst, diff)
            ok = diff <= THRESHOLD
            print(f"  {nm:9s} {direction:10s} mean|capture-driven| {diff:.4f}  "
                  f"({keep.sum()} poses)  {'PASS' if ok else 'FAIL'}")
            rows.append(dict(student=nm, checkpoint=ck, direction=direction,
                             cond=args.cond, mean_abs_diff=diff, poses=int(keep.sum()),
                             passed=bool(ok)))
    # A GATE THAT MEASURED NOTHING MUST NOT PASS.
    #
    # Every cell can SKIP -- no driven trace, too few matched poses -- and `worst` then
    # stays 0.0, which reads as a perfect pass. That is the same shape as every other
    # defect in this study: a result that looks complete because the thing it describes
    # was never measured. The expected cell count is known, so assert it.
    expected = len(students) * len(C.SECTIONS)
    if len(rows) != expected:
        print(f"\n  REFUSING to report a gate result: {len(rows)} of {expected} cells "
              f"were measured. A skipped cell is a missing driven trace, not a pass.\n"
              f"  Run scripts/capture/capture_gate_drives.py first.", file=sys.stderr)
        return 2

    out = Path(args.captures) / "capture_gate.json"
    out.write_text(json.dumps(dict(threshold=THRESHOLD, worst=worst, cells=rows,
                                   cells_expected=expected), indent=2))
    print(f"\n  worst {worst:.4f} against {THRESHOLD}  over {len(rows)}/{expected} cells"
          f"  -> {'PASS' if worst <= THRESHOLD else 'FAIL'}")
    print(f"  -> {out}")
    return 0 if worst <= THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())

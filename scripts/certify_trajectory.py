#!/usr/bin/env python3
"""Verify the frames the car ACTUALLY DROVE, not a sample of the dataset. No CARLA.

WHY THIS EXISTS
---------------
The first verification sweeps were unsound -- three cells CERTIFIED whose closed loop then
failed, twice with the vehicle leaving the road on every run. Two causes, both about which
images were verified rather than about the physics (F17, F18):

  SAMPLING. 12, then 60, frames sampled evenly from the dataset, against a ~1700-frame lap
    in which 34% of frames breach the corridor. An even sample can miss all of them, and it
    did. Verifying the frames that DO break the policy falsified 6 of 6 at 67-79% of the
    axis, so the model and the verifier were always capable.
  DOMAIN.   Verification read SAVED dataset frames while closed loop drove LIVE renders.
    Measured, those differ enough to move student steering past the certification tolerance
    on 40% of frames -- a larger effect than fog or shadows. The two instruments were not
    looking at the same images.

Both close if the frames come from `closed_loop_ledger.py --log-frames`: the trajectory is
complete, and the images are live renders by construction.

THE PROTOCOL THIS ENABLES, WHICH IS A REAL PREDICTION
-----------------------------------------------------
    1. drive the CLEAR lap with --log-frames          (no disturbance involved)
    2. apply a disturbance model to those frames and verify  <- THIS SCRIPT
    3. commit the verdict
    4. only then drive the disturbed lap and compare

Step 2 never sees the disturbed run, so step 4 tests a prediction -- on the real trajectory,
in the right image domain. That is stronger than anything in the ledger tonight except
night/S_clear, and it is what the disturbance models were built for: clear frame in,
disturbed behaviour out.

    python scripts/certify_trajectory.py --traj results/traj/clear_eastbound_rep00 \
        --student S_clear_84x28 --condition fog --channels 8,16,16 --fc 32
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
import verifiable_disturbance as vd  # noqa: E402
from student import StudentNet  # noqa: E402
from study import design  # noqa: E402
from scripts.certify_cell import (Bounder, fog_map_illum, night_map, shadow_map,
                                  sweep, clear_steer, FOG_CAL, FOG_CAL_FALLBACK)  # noqa: E402

OUT = REPO / "results" / "trajectory"


def load_fog_calibration(override=None):
    srcs = [q for q in (FOG_CAL, FOG_CAL_FALLBACK) if q.exists()]
    if not srcs:
        raise SystemExit("no fog calibration; run scripts/fit_operating_point.py first")
    ks, As = [], []
    for q in srcs:
        with open(q) as fh:
            cal = json.load(fh)
        if "densities" in cal:
            row = min(cal["densities"], key=lambda r: abs(r["fog_density"] - 70.0))
            As.append(row["airlight"]); ks.append(float(np.mean(row["k"])))
        else:
            As.append(cal["airlight_median"])
            if "k_median" in cal:
                ks.append(float(np.mean(cal["k_median"])))
    A = tuple(float(np.mean([a[c] for a in As])) for c in range(3))
    if override is not None:
        A = (override,) * 3
    k = (min(ks) * 0.9, max(ks) * 1.1) if ks else (0.60, 1.25)
    return A, k


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--traj", required=True, help="a --log-frames output directory")
    ap.add_argument("--student", required=True)
    ap.add_argument("--condition", required=True, choices=["fog", "night", "shadows"])
    ap.add_argument("--channels", default="8,16,16")
    ap.add_argument("--fc", type=int, default=32)
    ap.add_argument("--w", type=int, default=84)
    ap.add_argument("--h", type=int, default=28)
    ap.add_argument("--stride", type=int, default=1,
                    help="verify every Nth logged frame. 1 = the whole trajectory. Raising "
                         "this reintroduces sampling, so say so if you do.")
    ap.add_argument("--budget", type=int, default=design.VERIFY_CELL_BUDGET)
    ap.add_argument("--airlight", type=float, default=None)
    ap.add_argument("--shadow-mask", default=None,
                    help="npy mask for shadows; without a pose-paired counterpart per "
                         "logged frame there is no per-frame mask to measure")
    a = ap.parse_args()

    traj = Path(a.traj)
    with open(traj / "manifest.csv") as fh:
        rows = list(csv.DictReader(fh))
    rows = rows[:: a.stride]
    if not rows:
        raise SystemExit(f"no frames in {traj}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    student = StudentNet(a.h, a.w,
                         channels=tuple(int(v) for v in a.channels.split(",")),
                         fc=a.fc).to(device)
    student.load_state_dict(torch.load(
        f"{C.CHECKPOINT_DIR}/{a.student}.pth", map_location=device))
    student.eval()
    tol = C.CLOSED_LOOP_TOLERANCE

    fog_A = fog_k = None
    mask = None
    if a.condition == "fog":
        fog_A, fog_k = load_fog_calibration(a.airlight)
        print(f"  fog calibration A = [{fog_A[0]:.3f} {fog_A[1]:.3f} {fog_A[2]:.3f}], "
              f"k in [{fog_k[0]:.3f}, {fog_k[1]:.3f}]")
    elif a.condition == "shadows":
        if not a.shadow_mask:
            raise SystemExit(
                "shadows needs --shadow-mask. A logged trajectory has no pose-paired "
                "shadows counterpart, so the per-frame mask cannot be measured here; pass "
                "the pooled mask and note in the writeup that it understates spatial "
                "structure (F15).")
        mask = np.load(a.shadow_mask)

    print(f"{a.condition} on trajectory {traj.name}: {len(rows)} frames "
          f"(stride {a.stride}), tolerance {tol:.4f}, budget {a.budget}\n")

    per_frame, bounder = [], None
    for i, r in enumerate(rows):
        img = cv2.imread(str(traj / r["image"]))
        if img is None:
            continue
        xf = img.astype(np.float32) / 255.0
        if a.condition == "fog":
            build, lo, hi = fog_map_illum(xf, a.w, a.h, fog_A, fog_k)
        elif a.condition == "night":
            build, lo, hi = night_map(xf, a.w, a.h)
        else:
            build, lo, hi = shadow_map(xf, a.w, a.h, mask)

        if bounder is None:
            bounder = Bounder(build(lo, hi)[0].shape[1], student, device, a.h, a.w)
        cs = clear_steer(student, xf, device, a.w, a.h)
        frac, n, _ = sweep(build, lo, hi, bounder, (cs - tol, cs + tol), a.budget)
        per_frame.append({"step": int(r["step"]), "x": float(r["x"]), "y": float(r["y"]),
                          "certified": frac["CERTIFIED"], "falsified": frac["FALSIFIED"],
                          "unknown": frac["UNKNOWN"], "bounds": n})
        if i % 20 == 0:
            done = len(per_frame)
            viol = sum(1 for f in per_frame if f["falsified"] > 0)
            print(f"  {done:5d}/{len(rows)}  frames with a violation so far: "
                  f"{viol} ({viol/max(done,1):.0%})")

    cert = [f["certified"] for f in per_frame]
    fals = [f["falsified"] for f in per_frame]
    verdict = design.verify_verdict(cert, fals)
    viol = sum(1 for f in fals if f > 0)

    print("\n" + "=" * 62)
    print(f"  frames verified          {len(per_frame)}")
    print(f"  frames with a violation  {viol} ({viol/max(len(per_frame),1):.1%})")
    print(f"  median certified         {np.median(cert):.1%}")
    print(f"  VERDICT                  {verdict}")
    print("=" * 62)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{traj.name}__{a.condition}__{a.student}.json"
    with open(path, "w") as fh:
        json.dump({"trajectory": traj.name, "condition": a.condition,
                   "student": a.student, "stride": a.stride, "budget": a.budget,
                   "tolerance": tol, "verdict": verdict,
                   "frames": len(per_frame), "frames_with_violation": viol,
                   "per_frame": per_frame}, fh, indent=2)
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

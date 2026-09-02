#!/usr/bin/env python3
"""Where does the student diverge from its teacher? Split KD error BY CONDITION.

The mixed student drives clear 6/6 and fails night 9/12, while its teacher passes all 24
teacher-gate cells. So the gap is distillation, not the teacher -- but a single pooled KD
RMSE cannot say WHICH condition it comes from, and the pooled number (0.0370) looks fine.

Needs no CARLA and does not run the teacher: teacher outputs are already cached by
distill.teacher_targets, so this replays frames through the student only.

    STUDY_MAP=Town06 python3 scripts/kd_error_by_condition.py
"""
import os
import sys
from pathlib import Path

import numpy as np
import torch
import cv2

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402
from distill import aggregated_manifests  # noqa: E402
from dataset import load_manifests  # noqa: E402
from student import StudentNet, student_preprocess  # noqa: E402

CONDS = ["clear", "fog", "night", "low_sun", "shadows"]


def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    teacher = os.environ.get("TEACHER", "teacher_mixed_t06_dagger_r12")
    ck = os.environ.get("STUDENT", "S_mixed_t06_168x28_w2")
    ch = tuple(int(x) for x in os.environ.get("CHANNELS", "16,32,32").split(","))
    fc = int(os.environ.get("FC", "64"))
    w, h = C.TOWN06_INPUT_W, C.TOWN06_INPUT_H
    cap = int(os.environ.get("CAP", "3000"))

    _, rows = load_manifests(aggregated_manifests(
        base=os.environ.get("BASE", "mixed_t06"),
        dagger_dirs=os.environ.get("DAGGER_DIRS", "dagger_mixed_t06").split(",")))
    z = np.load(Path(C.DATASET_DIR) / f"teacher_targets_{teacher}.npz", allow_pickle=True)
    tgt = {str(p): float(s) for p, s in zip(z["paths"], z["steer"])}

    net = StudentNet(h, w, channels=ch, fc=fc).to(dev)
    net.load_state_dict(torch.load(Path(C.CHECKPOINT_DIR) / f"{ck}.pth",
                                   map_location=dev, weights_only=True))
    net.eval()
    print(f"{ck}  ({C.relu_count(ch, fc, h, w):,} ReLU)  vs  {teacher}")
    print(f"{len(rows):,} frames, {len(tgt):,} cached teacher targets\n")
    print(f"{'condition':10s} {'frames':>7s} {'KD RMSE':>9s} {'bias':>9s} "
          f"{'teacher|s|':>11s} {'student|s|':>11s} {'p99 |err|':>10s}")
    print("  " + "-" * 74)

    for cond in CONDS:
        sub = [r for r in rows if r.get("weather") == cond and r["image"] in tgt]
        if not sub:
            print(f"{cond:10s}   none")
            continue
        if len(sub) > cap:
            sub = [sub[i] for i in np.linspace(0, len(sub) - 1, cap).astype(int)]
        errs, tv = [], []
        for i in range(0, len(sub), 256):
            b = sub[i:i + 256]
            imgs = [(r, cv2.imread(r["image"])) for r in b]
            imgs = [(r, im) for r, im in imgs if im is not None]
            if not imgs:
                continue
            x = np.stack([student_preprocess(im, w, h) for _, im in imgs])
            t = np.array([tgt[r["image"]] for r, _ in imgs], np.float32)
            with torch.no_grad():
                s = net(torch.from_numpy(x).to(dev)).cpu().numpy().reshape(-1)
            errs.append(s - t); tv.append(t)
        e = np.concatenate(errs); t = np.concatenate(tv)
        print(f"{cond:10s} {len(e):7,} {np.sqrt((e ** 2).mean()):9.4f} {e.mean():+9.4f} "
              f"{np.abs(t).mean():11.4f} {np.abs(t + e).mean():11.4f} "
              f"{np.percentile(np.abs(e), 99):10.4f}")

    print(f"\n  steering tolerance delta_tol = {C.CLOSED_LOOP_TOLERANCE:.4f} "
          f"(normalised units), for scale")


if __name__ == "__main__":
    main()

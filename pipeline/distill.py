#!/usr/bin/env python3
"""
Knowledge distillation: train a small verifiable StudentNet to match the DAgger
teacher's steering output, over the aggregated DAgger dataset (which already
contains recovery states, so the student inherits recovery behavior).

Teacher targets are resolution-independent, so they're computed once and cached;
the resolution sweep then reuses them for each student input size.

    python distill.py --in-w 96 --in-h 42 --out student_096x42
"""
import os
import sys
import argparse
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import cv2
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

import config as C
from model import CarlaSteeringNet
from student import StudentNet, student_preprocess
from imaging import preprocess_for_model
from dataset import load_manifests, block_split, filter_conditions


def aggregated_manifests(base="clear", dagger_dirs=("dagger", "dagger_student")):
    """Base BC manifest + every DAgger round manifest under the given dirs.
    dagger_dirs selects which DAgger runs to fold in (e.g. the clear model uses
    dagger/dagger_student; the mixed model uses dagger_mixed) so distilling one
    model never silently pulls in the other model's recovery data."""
    # `base` accepts a comma-separated string or a sequence. It was a single name, which
    # silently dropped every base dataset but one -- a mixed-condition distill started
    # from base="clear" would never see the fog/night/shadows frames.
    names = [b.strip() for b in base.split(",")] if isinstance(base, str) else list(base)
    paths = [os.path.join(C.DATASET_DIR, b, "manifest.csv") for b in names if b]
    for sub in dagger_dirs:
        root = os.path.join(C.DATASET_DIR, sub)
        if os.path.isdir(root):
            for d in sorted(os.listdir(root)):
                m = os.path.join(root, d, "manifest.csv")
                if os.path.isfile(m):
                    paths.append(m)
    return paths


def teacher_targets(rows, teacher_name, device):
    """dict abs_image_path -> teacher steering. Cached; only NEW frames (e.g. from
    student-DAgger rounds) are computed on subsequent calls, not the whole set."""
    cache = os.path.join(C.DATASET_DIR, f"teacher_targets_{teacher_name}.npz")
    d = {}
    if os.path.isfile(cache):
        z = np.load(cache, allow_pickle=True)
        d = {str(p): float(s) for p, s in zip(z["paths"], z["steer"])}
    missing = [r for r in rows if r["image"] not in d]
    if not missing:
        print(f"all {len(rows)} teacher targets cached")
        return d
    print(f"computing teacher targets for {len(missing)} new frames with '{teacher_name}'...")
    teacher = CarlaSteeringNet().to(device)
    teacher.load_state_dict(torch.load(os.path.join(C.CHECKPOINT_DIR, f"{teacher_name}.pth"),
                                       map_location=device))
    teacher.eval()
    with torch.no_grad():
        for i, r in enumerate(missing):
            bgr = cv2.imread(r["image"])
            x = torch.from_numpy(preprocess_for_model(bgr)).unsqueeze(0).to(device)
            d[r["image"]] = float(teacher(x).item())
            if i % 2000 == 0:
                print(f"  {i}/{len(missing)}")
    paths = list(d.keys())
    np.savez(cache, paths=np.array(paths), steer=np.array([d[p] for p in paths], dtype=np.float32))
    return d


def _kd_decode(args):
    path, in_w, in_h = args
    return student_preprocess(cv2.imread(path), in_w, in_h)


class KDDataset(Dataset):
    def __init__(self, rows, indices, targets, in_w, in_h, preload=True):
        self.rows, self.indices, self.targets = rows, indices, targets
        self.in_w, self.in_h = in_w, in_h
        self.cache = None
        if preload:
            # Trap 17, second instance. dataset.SteeringDataset was parallelised and this
            # was not, so the trap-17 conformance test passed while the real bottleneck
            # sat here: a single-threaded decode of 83,567 frames on EVERY distill run,
            # silently outlasting the training it precedes.
            nproc = max(1, (os.cpu_count() or 4) - 2)
            work = [(rows[i]["image"], in_w, in_h) for i in indices]
            with ProcessPoolExecutor(max_workers=nproc) as ex:
                self.cache = list(ex.map(_kd_decode, work, chunksize=256))

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, k):
        i = self.indices[k]
        x = self.cache[k] if self.cache is not None else \
            student_preprocess(cv2.imread(self.rows[i]["image"]), self.in_w, self.in_h)
        return torch.from_numpy(x), torch.tensor([self.targets[self.rows[i]["image"]]],
                                                 dtype=torch.float32)


def _mse(model, loader, device):
    model.eval(); se = n = 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            se += nn.functional.mse_loss(model(x), y, reduction="sum").item(); n += y.numel()
    return se / n


def distill_student(in_w, in_h, out_name, teacher_name="steering_dagger_r02",
                    base="clear", dagger_dirs=("dagger", "dagger_student"),
                    weathers=None, channels=(8, 16, 16), fc=32, init_from=None,
                    epochs=120, batch_size=64, lr=1e-3, patience=20,
                    device=None, quiet=False):
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(0)
    # Seed the augmentation RNG too: dataset._shift draws from the global `random`,
    # and torch.manual_seed alone left retraining non-reproducible bit-for-bit.
    import random as _random
    _random.seed(0)
    np.random.seed(0)
    os.makedirs(C.CHECKPOINT_DIR, exist_ok=True)
    _, rows = load_manifests(aggregated_manifests(base, dagger_dirs))
    if weathers:
        # Trap 13: this WAS a second copy of the filter logic, which is exactly how the
        # previous generation's fix landed in train.py and missed distill.py. There is
        # now one implementation, in dataset.filter_conditions.
        n0 = len(rows)
        rows = filter_conditions(rows, keep=weathers)
        if not quiet:
            print(f"condition filter {sorted(set(weathers))}: kept {len(rows)}/{n0} frames")
    targets = teacher_targets(rows, teacher_name, device)
    tr_idx, va_idx = block_split(len(rows), val_frac=0.15, block=50, seed=0)

    tr = KDDataset(rows, tr_idx, targets, in_w, in_h)
    va = KDDataset(rows, va_idx, targets, in_w, in_h)
    tl = DataLoader(tr, batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=True)
    vl = DataLoader(va, batch_size=256, shuffle=False, num_workers=0, pin_memory=True)

    student = StudentNet(in_h, in_w, channels=channels, fc=fc).to(device)
    if init_from:  # warm-start (fine-tune) from a prior student; stabilizes multi-condition re-distill
        student.load_state_dict(torch.load(os.path.join(C.CHECKPOINT_DIR, f"{init_from}.pth"),
                                           map_location=device))
        if not quiet:
            print(f"warm-start from {init_from} (lr={lr})")
    nrelu = student.num_relu_neurons()
    if not quiet:
        print(f"student {in_w}x{in_h} channels={channels} fc={fc}: {nrelu} ReLU neurons, "
              f"{sum(p.numel() for p in student.parameters())} params | train={len(tr_idx)} val={len(va_idx)}")
    opt = torch.optim.Adam(student.parameters(), lr=lr, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5, patience=8)

    ckpt = os.path.join(C.CHECKPOINT_DIR, f"{out_name}.pth")
    best, bad = float("inf"), 0
    for ep in range(epochs):
        student.train()
        for x, y in tl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad(); loss = nn.functional.mse_loss(student(x), y)
            loss.backward(); opt.step()
        v = _mse(student, vl, device); sched.step(v)
        if v < best:
            best, bad = v, 0; torch.save(student.state_dict(), ckpt)
        else:
            bad += 1
        if not quiet and (ep % 10 == 0 or bad == 0):
            print(f"  epoch {ep:3d} | val KD-MSE {v:.3e} | rmse {np.sqrt(v):.4f}{' *' if bad==0 else ''}")
        if bad >= patience:
            break
    if not quiet:
        print(f"BEST KD val MSE={best:.3e} RMSE={np.sqrt(best):.4f} ({nrelu} neurons) -> {ckpt}")
    return {"best_val": best, "neurons": nrelu, "ckpt": ckpt}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-w", type=int, required=True)
    ap.add_argument("--in-h", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--teacher", default="steering_dagger_r02")
    ap.add_argument("--base", default="clear", help="base BC dataset name")
    ap.add_argument("--dagger-dirs", default="dagger,dagger_student",
                    help="comma-separated DAgger subdirs under data/ to fold in")
    ap.add_argument("--weathers", default=None,
                    help="restrict distillation to these conditions (e.g. clear,fog,night)")
    ap.add_argument("--channels", default="8,16,16",
                    help="conv channel widths (capacity lever at fixed resolution)")
    ap.add_argument("--fc", type=int, default=32, help="FC hidden width")
    ap.add_argument("--epochs", type=int, default=120)
    # These existed as function parameters but were never reachable from the CLI, so the
    # documented fix for multi-condition instability could not actually be applied.
    ap.add_argument("--init-from", default=None,
                    help="warm-start from a prior student checkpoint of the SAME "
                         "architecture; stabilizes multi-condition re-distill")
    ap.add_argument("--lr", type=float, default=1e-3,
                    help="use a reduced lr (5e-4) when warm-starting")
    ap.add_argument("--patience", type=int, default=20)
    args = ap.parse_args()
    distill_student(args.in_w, args.in_h, args.out, teacher_name=args.teacher,
                    base=args.base, dagger_dirs=tuple(args.dagger_dirs.split(",")),
                    weathers=(args.weathers.split(",") if args.weathers else None),
                    channels=tuple(int(x) for x in args.channels.split(",")), fc=args.fc,
                    epochs=args.epochs, init_from=args.init_from, lr=args.lr,
                    patience=args.patience)


if __name__ == "__main__":
    main()

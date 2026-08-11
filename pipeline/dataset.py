"""
Behavior-cloning dataset: reads a collection manifest (image path + expert steer)
and yields (model_input_tensor, steer). Uses the SAME preprocessing as inference
(imaging.preprocess_for_model). Optional straight-frame balancing and horizontal-
shift augmentation are OFF by default so the first run is a clean baseline.
"""
import os
from concurrent.futures import ProcessPoolExecutor
import csv
import random

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset

from imaging import preprocess_for_model


def load_manifest(manifest_path):
    base = os.path.dirname(manifest_path)
    with open(manifest_path) as f:
        rows = list(csv.DictReader(f))
    return base, rows


def load_manifests(manifest_paths):
    """Combine multiple manifests (base BC + DAgger rounds) into one row list with
    ABSOLUTE image paths, so DAgger can aggregate datasets living in different dirs.
    Returns (base="", rows) — base is empty because paths are already absolute."""
    rows = []
    for mp in manifest_paths:
        mbase = os.path.dirname(mp)
        with open(mp) as f:
            for r in csv.DictReader(f):
                r = dict(r)
                r["image"] = os.path.join(mbase, r["image"])
                rows.append(r)
    return "", rows


def filter_conditions(rows, keep=None):
    """Restrict rows to a set of conditions, keeping untagged rows.

    Trap 13. In the previous generation this logic was duplicated in `train.py` and
    `distill.py`; a fix was applied to one and missed in the other, and the naive form
    `r.get("condition") in keep` silently discarded 6,783 rows that predate condition
    tracking. It surfaced much later as an unrelated "Sample larger than population"
    crash.

    The structural fix is that this is now the ONLY filter site. Do not reimplement it
    at a call site.

    `keep=None` means keep everything. Reads either `condition` or the legacy
    `weather` key, so old manifests stay loadable.
    """
    if not keep:
        return list(rows)

    keep = set(keep)
    out = []
    for r in rows:
        tag = r.get("condition", r.get("weather"))
        # An untagged row predates condition tracking. It is clear-weather data and
        # dropping it silently is the bug this function exists to prevent.
        if tag in (None, ""):
            out.append(r)
        elif tag in keep:
            out.append(r)
    return out


def block_split(n, val_frac=0.15, block=50, seed=0):
    """
    Split indices into train/val by contiguous BLOCKS, not per-frame. Consecutive
    frames are near-identical, so a per-frame random split leaks train into val
    and makes val MSE meaninglessly low. Whole blocks go to one side.
    """
    rng = random.Random(seed)
    n_blocks = (n + block - 1) // block
    val_blocks = set(rng.sample(range(n_blocks), max(1, int(round(n_blocks * val_frac)))))
    train, val = [], []
    for i in range(n):
        (val if (i // block) in val_blocks else train).append(i)
    return train, val


def balance_straight(rows, indices, straight_thresh=0.01, ratio=0.6, seed=0):
    """Downsample near-straight frames to `ratio * max(n_left, n_right)`."""
    rng = random.Random(seed)
    straight, turn = [], []
    n_left = n_right = 0
    for i in indices:
        s = float(rows[i]["steer"])
        if abs(s) <= straight_thresh:
            straight.append(i)
        else:
            turn.append(i)
            n_left += s > 0
            n_right += s < 0
    keep_straight = int(ratio * max(n_left, n_right))
    if len(straight) > keep_straight:
        straight = rng.sample(straight, keep_straight)
    out = turn + straight
    rng.shuffle(out)
    return out


def _decode(path):
    """Module-level so a process pool can pickle it."""
    return preprocess_for_model(cv2.imread(path))


class SteeringDataset(Dataset):
    def __init__(self, base, rows, indices, augment=False,
                 shift_max_px=0, shift_k=0.0, preload=False):
        self.base = base
        self.rows = rows
        self.indices = indices
        self.augment = augment
        self.shift_max_px = shift_max_px
        self.shift_k = shift_k
        # In-RAM cache of preprocessed tensors (~0.16 MB/frame). Avoids re-decoding
        # PNGs every epoch. Disabled automatically when augmenting, since shift
        # needs the pre-resize image.
        #
        # Built in PARALLEL. DAgger aggregates every round, so this set grows without
        # bound: by round 5 it is ~67k frames, and a single-threaded decode takes over
        # ten minutes, which silently dominates (and can outlast) the training step
        # itself. Decoding is CPU-bound and embarrassingly parallel, so a process pool
        # turns that into well under a minute.
        self.cache = None
        if preload and not augment:
            paths = [os.path.join(base, rows[i]["image"]) for i in indices]
            if len(paths) < 2000:
                self.cache = [_decode(p) for p in paths]
            else:
                nproc = max(1, min(16, (os.cpu_count() or 4) - 2))
                with ProcessPoolExecutor(max_workers=nproc) as ex:
                    self.cache = list(ex.map(_decode, paths, chunksize=64))

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, idx):
        r = self.rows[self.indices[idx]]
        steer = float(r["steer"])
        if self.cache is not None:
            return torch.from_numpy(self.cache[idx]), torch.tensor([steer], dtype=torch.float32)
        bgr = cv2.imread(os.path.join(self.base, r["image"]))
        if self.augment and self.shift_max_px > 0:
            bgr, steer = self._shift(bgr, steer)
        x = preprocess_for_model(bgr)
        return torch.from_numpy(x), torch.tensor([steer], dtype=torch.float32)

    def _shift(self, bgr, steer):
        dx = random.randint(-self.shift_max_px, self.shift_max_px)
        h, w = bgr.shape[:2]
        M = np.float32([[1, 0, dx], [0, 1, 0]])
        bgr = cv2.warpAffine(bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        # a rightward image shift (dx>0) looks like the car is left of center,
        # so the corrective steer is to the right: additive correction.
        return bgr, steer + dx * self.shift_k

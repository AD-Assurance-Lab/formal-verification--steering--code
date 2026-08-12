#!/usr/bin/env python3
"""Measure the shadow mask S from POSE-PAIRED clear/shadows CARLA frames. No CARLA.

`docs/DISTURBANCE_MATH.md` gives the only verifiable shadow form:

    x' = x0 (*) (1 - s * S)         S in [0,1] per pixel, s the bounded depth

and notes that a mask which MOVES with solar elevation is not affine. So S is fixed and
only `s` is bounded. The question this script answers is where S comes from. A declared
mask would make the shadows verify cell an assumption dressed as a measurement.

WHY THIS IS POSSIBLE HERE AND WAS NOT BEFORE
--------------------------------------------
ACDC was rejected for exactly this kind of paired photometry: its condition pairs have no
pixel correspondence, which is what invalidated the previous generation's paired R^2. CARLA
does not have that problem -- the ego drives the same scripted route under each condition,
and the manifest records (x, y, yaw) per frame. Measured over this dataset:

    eastbound  median pose error 0.039 m, yaw 0.03 deg
    westbound  median pose error 0.129 m, yaw 0.04 deg

At 0.04 m longitudinal offset a point 5 m ahead moves by f*h/d^2 * dd = 0.6 px, and less
further out. So these ARE pixel-aligned pairs, and the ratio image is meaningful.

WHAT IS BEING MEASURED
----------------------
CARLA's "shadows" condition is sun_altitude_angle=15 against a clear baseline of 90. That
changes two things at once: the global illumination level, and the cast-shadow pattern. The
multiplicative form above absorbs BOTH, and S is simply the measured spatial pattern of the
resulting dimming. That is stated rather than hidden, because it means `s` sweeps a
combined elevation effect and not cast-shadow depth in isolation.

Per-channel, because a low sun is warmer as well as dimmer, and dropping that would model
a colour change as a pure luminance change.

    python scripts/measure_shadow_mask.py
"""

import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parent.parent
BASE = REPO / "pipeline" / "data" / "conditions"
OUT = REPO / "results" / "calibration"

MAX_POS_ERR_M = 0.15      # pairs looser than this are dropped
MAX_YAW_ERR_DEG = 0.30
N_PAIRS = 400             # sampled evenly along the route
FLOOR = 0.04              # ignore pixels this dark in clear; the ratio is meaningless there


def load(weather, direction):
    with open(BASE / "manifest.csv") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r["weather"] == weather and r["direction"] == direction]
    pose = np.array([[float(r["x"]), float(r["y"]), float(r["yaw"])] for r in rows])
    return rows, pose


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    num = None
    den = None
    used, dropped = 0, 0

    for direction in ("eastbound", "westbound"):
        c_rows, c_pose = load("clear", direction)
        s_rows, s_pose = load("shadows", direction)
        if not len(c_rows) or not len(s_rows):
            continue

        dist = np.linalg.norm(s_pose[:, None, :2] - c_pose[None, :, :2], axis=2)
        j = dist.argmin(1)
        dmin = dist[np.arange(len(s_pose)), j]
        dyaw = np.abs(((s_pose[:, 2] - c_pose[j, 2] + 180) % 360) - 180)
        ok = (dmin < MAX_POS_ERR_M) & (dyaw < MAX_YAW_ERR_DEG)
        idx = np.flatnonzero(ok)
        dropped += int((~ok).sum())
        if len(idx) == 0:
            continue
        idx = idx[:: max(1, len(idx) // (N_PAIRS // 2))][: N_PAIRS // 2]

        for i in idx:
            cimg = cv2.imread(str(BASE / c_rows[j[i]]["image"]))
            simg = cv2.imread(str(BASE / s_rows[i]["image"]))
            if cimg is None or simg is None:
                continue
            cf = cimg.astype(np.float32) / 255.0
            sf = simg.astype(np.float32) / 255.0
            valid = (cf > FLOOR).astype(np.float32)
            # Accumulate a WEIGHTED MEAN of the ratio: sum(s)/sum(c) per pixel over pairs,
            # which is the least-squares fit of a per-pixel multiplicative gain and is far
            # better behaved than averaging per-pair ratios (a single dark clear pixel
            # would otherwise dominate).
            num = (sf * valid) if num is None else num + sf * valid
            den = (cf * valid) if den is None else den + cf * valid
            used += 1

    if not used:
        print("no usable pairs")
        return 2

    ratio = np.divide(num, den, out=np.ones_like(num), where=den > 1e-6)
    drop = np.clip(1.0 - ratio, 0.0, 1.0)          # fractional dimming per pixel/channel

    # S is normalized to peak 1 so that `s` carries the amplitude, exactly as the model
    # x' = x0 * (1 - s*S) intends. The normalizer is the 99th percentile rather than the
    # max, so one saturated pixel cannot rescale the whole mask.
    peak = float(np.percentile(drop, 99.0))
    S = np.clip(drop / max(peak, 1e-6), 0.0, 1.0).astype(np.float32)

    np.save(OUT / "shadow_mask.npy", S)
    cv2.imwrite(str(OUT / "shadow_mask.png"), (S * 255).astype(np.uint8))

    sys.path.insert(0, str(REPO / "pipeline"))
    import config as C
    roi = slice(*C.ROAD_ROI_ROWS)
    meta = {
        "pairs_used": used, "pairs_dropped_pose": dropped,
        "max_pos_err_m": MAX_POS_ERR_M, "max_yaw_err_deg": MAX_YAW_ERR_DEG,
        "peak_dimming_p99": peak,
        "mean_dimming_road_roi": float(drop[roi].mean()),
        "mean_dimming_full": float(drop.mean()),
        "note": ("S is the measured per-pixel, per-channel multiplicative dimming from "
                 "CARLA sun_altitude 90 -> 15, normalized to peak 1 at the 99th "
                 "percentile. It absorbs BOTH the global illumination drop and the cast "
                 "shadow pattern, so the bounded depth s sweeps a combined solar-elevation "
                 "effect, not cast-shadow depth in isolation."),
    }
    json.dump(meta, open(OUT / "shadow_mask.json", "w"), indent=2)

    print(f"pairs used {used}, dropped for pose {dropped}")
    print(f"peak dimming (p99) {peak:.3f}")
    print(f"mean dimming: road ROI {drop[roi].mean():.3f}, full frame {drop.mean():.3f}")
    print(f"per-channel mean dimming B/G/R: "
          f"{drop[..., 0].mean():.3f} {drop[..., 1].mean():.3f} {drop[..., 2].mean():.3f}")
    print(f"\nwrote {OUT/'shadow_mask.npy'} and shadow_mask.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())

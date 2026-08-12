#!/usr/bin/env python3
"""Measure the night illumination field from pose-paired frames. No CARLA.

WHY. The analytic night model -- ambient dimming plus an assumed aimed-beam headlight
pattern plus a retroreflection term -- reproduces CARLA's night at road-ROI R^2 0.243,
against 0.870 for fog and 0.996 for shadows. Its verification consequently fails to
discriminate: it drives S_mixed's steering 27x further than CARLA does. Two specific things
were wrong:

  * the multiplicative form `x0*(1 - g*(1-L))` can only DIM. Measured, CARLA's headlight
    pool is 1.42x BRIGHTER than the overcast clear baseline at ~1.7 m, so the fit had no
    way to express the near field and contorted the retro term to -4.23 compensating.
  * the assumed beam shape L is not CARLA's beam shape.

Both vanish if the field is measured rather than assumed, which is exactly what "physical
disturbances characterized in CARLA" is supposed to mean.

WHY POOLING ACROSS POSES IS VALID HERE. The headlight pool is attached to the vehicle, so
it is FIXED in image coordinates and survives averaging over poses. Lane markings move
between poses and blur out, which is the one thing this field does not represent -- so it
captures illumination, not retroreflection, and that is stated rather than hidden.

Held out on frames not used to fit it: road-ROI R^2 +0.832, against +0.243 for the analytic
model. It is also PREDICTIVE -- applying it needs only the clear image.

    x'(s) = x0 * (1 + s*(G - 1))     s = 0 clear, s = 1 the measured CARLA night

d = 1, the same shape as shadows.

    python scripts/measure_night_gain.py
"""
import sys
import json
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402
from scripts.certify_cell import paired_frames  # noqa: E402

OUT = REPO / "results" / "calibration"
FLOOR = 0.03


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pairs = paired_frames(40, "night")
    n_train = int(len(pairs) * 0.75)
    train, test = pairs[:n_train], pairs[n_train:]
    roi = slice(*C.ROAD_ROI_ROWS)

    num = den = None
    for c_, n_, _ in train:
        x0 = c_.astype(np.float32) / 255.0
        y = n_.astype(np.float32) / 255.0
        v = (x0 > FLOOR).astype(np.float32)
        num = y * x0 * v if num is None else num + y * x0 * v
        den = x0 * x0 * v if den is None else den + x0 * x0 * v
    G = np.divide(num, den, out=np.ones_like(num), where=den > 1e-6).astype(np.float32)

    def r2(o, p):
        a = o[roi].reshape(-1); b = p[roi].reshape(-1)
        return 1.0 - ((a - b) ** 2).sum() / ((a - a.mean()) ** 2).sum()

    held = [r2(n_.astype(np.float32) / 255.0,
               np.clip((c_.astype(np.float32) / 255.0) * G, 0, 1))
            for c_, n_, _ in test]

    np.save(OUT / "night_gain.npy", G)
    meta = {"train_pairs": len(train), "test_pairs": len(test),
            "held_out_roi_r2_median": float(np.median(held)),
            "G_mean": float(G.mean()), "G_roi_mean": float(G[roi].mean()),
            "note": ("Per-pixel multiplicative night illumination field, least squares over "
                     "pose-paired clear/night frames. Captures ambient dimming AND the "
                     "headlight pool, which is fixed in image coordinates. Does NOT capture "
                     "retroreflection off lane markings, which move between poses and "
                     "average out.")}
    json.dump(meta, open(OUT / "night_gain.json", "w"), indent=2)

    print(f"train {len(train)} pairs, held out {len(test)}")
    print(f"  G mean {G.mean():.3f}, road-ROI mean {G[roi].mean():.3f}")
    print(f"  held-out road-ROI R^2 median {np.median(held):+.3f} "
          f"(analytic model was +0.243)")
    print(f"\nwrote {OUT/'night_gain.npy'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

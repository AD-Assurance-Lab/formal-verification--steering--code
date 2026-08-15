#!/usr/bin/env python3
"""Fit each disturbance as a MEASURED field from pose-paired frames, and gate it twice.

WHY MEASURED RATHER THAN ANALYTIC (F19). Analytic models reproduced CARLA's images
respectably -- fog at road-ROI R^2 0.848 -- and were still useless for verification,
because they drove `S_mixed`'s steering 23.8x further than real fog does while being
faithful (1.2x) for `S_clear`. `S_mixed` trained on CARLA's real fog and keys on exactly the
residual the analytic model omits, so the model was MOST wrong about the BEST policy. Fields
fitted from paired frames fixed it: fog R^2 0.950 with a behavioural ratio of 0.8x, night
0.243 -> 0.832 with exact discrimination at the operating point.

WHY TWO GATES. Image fidelity alone would have passed the analytic fog model. A disturbance
model is only usable if the policy responds to it as it responds to the real thing, so this
script reports both and neither is optional:

    image    held-out road-ROI R^2 >= 0.80
    behaviour  |dsteer(model)| / |dsteer(real)| within [0.5, 2.0], for EVERY student

FORMS, one per condition, all affine in a single scalar s with s=1 the measured condition:

    fog      x' = x0 + s*((a*x0 + b) - x0)   per-pixel affine, fog both veils and dims
    night    x' = x0 * (1 + s*(G - 1))       per-pixel gain: ambient + the headlight pool,
                                             which is fixed in image coordinates so it
                                             survives pooling across poses
    shadows  x' = x0 * (1 - s*S)             per-pixel dimming

Pooling across poses is what makes these PREDICTIVE -- applying them needs only a clear
frame. It also means they capture what is stationary in the image and not what moves:
lane-marking retroreflection averages out, and that is a stated limitation, not a hidden one.

    python scripts/fit_fields.py --dataset live_pairs
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

OUT = REPO / "results" / "calibration"
STUDENTS = [("S_clear", "S_clear_84x28", (8, 16, 16), 32),
            ("S_mixed", "S_mixed_84x28_w3", (24, 48, 48), 96)]


def pairs_from(base, cond, n, max_pos=0.15, max_yaw=0.30, directions=None):
    """Pose-matched (clear, condition) image pairs.

    `directions` restricts which laps are used. Independent laps only pair well if their
    frames happen to land at the same phase: measured on this capture, westbound matched to
    0.020 m with 1466 usable pairs while eastbound sat at 0.889 m -- half the 1.79 m frame
    spacing at 20 mph -- and yielded none. Fitting a field on whatever happens to pair, then
    applying it to both directions, is how a field ends up reproducing image statistics
    without reproducing the steering response."""
    with open(base / "manifest.csv") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for d in (directions or ("eastbound", "westbound")):
        cr = [r for r in rows if r["weather"] == "clear" and r["direction"] == d]
        orr = [r for r in rows if r["weather"] == cond and r["direction"] == d]
        if not cr or not orr:
            continue
        cp = np.array([[float(r["x"]), float(r["y"]), float(r["yaw"])] for r in cr])
        op = np.array([[float(r["x"]), float(r["y"]), float(r["yaw"])] for r in orr])
        dist = np.linalg.norm(cp[:, None, :2] - op[None, :, :2], axis=2)
        j = dist.argmin(1)
        dmin = dist[np.arange(len(cp)), j]
        dyaw = np.abs(((cp[:, 2] - op[j, 2] + 180) % 360) - 180)
        for i in np.flatnonzero((dmin < max_pos) & (dyaw < max_yaw)):
            out.append((cr[i]["image"], orr[j[i]]["image"]))
    return out[:: max(1, len(out) // n)][:n]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="live_pairs")
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--conditions", default="fog,night,shadows")
    ap.add_argument("--directions", default="westbound",
                    help="laps to fit from; eastbound did not frame-synchronise")
    args = ap.parse_args()

    base = REPO / "pipeline" / "data" / args.dataset
    OUT.mkdir(parents=True, exist_ok=True)
    roi = slice(*C.ROAD_ROI_ROWS)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    nets = {}
    for nm, ck, ch, fc in STUDENTS:
        m = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
        m.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
        m.eval()
        nets[nm] = m

    def steer(m, arr):
        with torch.no_grad():
            return float(m(torch.from_numpy(
                vd._project(arr, 84, 28).reshape(1, 3, 28, 84).astype(np.float32)
            ).to(dev)).item())

    summary = {}
    for cond in args.conditions.split(","):
        pr = pairs_from(base, cond, args.n,
                        directions=tuple(args.directions.split(",")))
        if len(pr) < 12:
            print(f"{cond}: only {len(pr)} pose-matched pairs, skipping")
            continue
        k = int(len(pr) * 0.75)
        train, test = pr[:k], pr[k:]

        acc = {}
        for cimg, oimg in train:
            x = cv2.imread(str(base / cimg)).astype(np.float32) / 255.0
            y = cv2.imread(str(base / oimg)).astype(np.float32) / 255.0
            v = (x > 0.03).astype(np.float32)
            for key, val in (("Sxx", x * x * v), ("Sx", x * v), ("Sxy", x * y * v),
                             ("Sy", y * v), ("N", v)):
                acc[key] = val if key not in acc else acc[key] + val

        if cond == "fog":
            den = acc["N"] * acc["Sxx"] - acc["Sx"] ** 2
            a = np.divide(acc["N"] * acc["Sxy"] - acc["Sx"] * acc["Sy"], den,
                          out=np.ones_like(den), where=np.abs(den) > 1e-8)
            b = np.divide(acc["Sy"] - a * acc["Sx"], np.maximum(acc["N"], 1e-6),
                          out=np.zeros_like(den), where=acc["N"] > 0)
            apply = lambda x: np.clip(a * x + b, 0, 1).astype(np.float32)
            np.save(OUT / "live_fog_a.npy", a.astype(np.float32))
            np.save(OUT / "live_fog_b.npy", b.astype(np.float32))
        else:
            G = np.divide(acc["Sxy"], acc["Sxx"], out=np.ones_like(acc["Sxy"]),
                          where=acc["Sxx"] > 1e-6).astype(np.float32)
            apply = lambda x, G=G: np.clip(x * G, 0, 1).astype(np.float32)
            np.save(OUT / f"live_{cond}_gain.npy", G)

        r2s = []
        beh = {nm: ([], []) for nm in nets}
        for cimg, oimg in test:
            x = cv2.imread(str(base / cimg)).astype(np.float32) / 255.0
            y = cv2.imread(str(base / oimg)).astype(np.float32) / 255.0
            p = apply(x)
            o = y[roi].reshape(-1); q = p[roi].reshape(-1)
            r2s.append(1 - ((o - q) ** 2).sum() / ((o - o.mean()) ** 2).sum())
            for nm, m in nets.items():
                s0 = steer(m, x)
                beh[nm][0].append(steer(m, y) - s0)      # SIGNED, not abs
                beh[nm][1].append(steer(m, p) - s0)

        r2 = float(np.median(r2s))
        rows = {}
        ok_beh = True
        for nm in nets:
            # SIGNED mean bias -- direction is what determines whether errors accumulate,
            # and a field can match |dsteer| while inverting the sign (measured: S_clear
            # night real -0.0588 against modelled +0.0208).
            real = float(np.mean(beh[nm][0])); mod = float(np.mean(beh[nm][1]))
            ratio = float(mod / real) if abs(real) > 1e-9 else float("inf")
            same_sign = np.sign(real) == np.sign(mod)
            rows[nm] = {"real": real, "model": mod, "ratio": ratio,
                        "same_sign": bool(same_sign)}
            if not (same_sign and 0.5 <= ratio <= 2.0):
                ok_beh = False
        gate = "PASS" if (r2 >= 0.80 and ok_beh) else "FAIL"
        summary[cond] = {"image_r2": r2, "behaviour": rows, "gate": gate,
                         "train": len(train), "test": len(test)}
        print(f"\n{cond}:  image R^2 {r2:+.3f} (need >=0.80)   GATE {gate}")
        for nm, v in rows.items():
            flag = ("ok" if (v["same_sign"] and 0.5 <= v["ratio"] <= 2.0)
                    else ("SIGN INVERTED" if not v["same_sign"] else "RATIO OUT OF RANGE"))
            print(f"    {nm:8s} real {v['real']:+.5f}  model {v['model']:+.5f}  "
                  f"ratio {v['ratio']:+6.2f}x  {flag}")

    json.dump(summary, open(OUT / "live_fields.json", "w"), indent=2)
    print(f"\nwrote {OUT/'live_fields.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

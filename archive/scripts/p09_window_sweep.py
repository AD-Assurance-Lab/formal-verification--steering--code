"""P-09 step 2: sweep window length on the CALIBRATION cells only.

Ground truth for the two calibration cells is now measured:
    sun +60  drives PASS 0/10   (max CTE 0.50-1.54 ft)
    sun +30  drives FAIL 10/10  (eastbound departs, 29-43 ft; westbound 3.3-4.1 ft)

The question step 2 exists to answer: is there ANY window length at which the
statistic orders these two cells correctly, i.e. max over passing cells < min over
failing cells? If not, no threshold repairs it and the window is not the free
parameter that was missing.

Held-out cells (+37, +15) are not loaded here.
"""
import sys

import numpy as np
import torch

R = "/home/za/ad-assurance--workspace/formal-verification--automated-driving--code/"
sys.path.insert(0, R)
sys.path.insert(0, R + "pipeline")

import config as C  # noqa: E402
from student import StudentNet  # noqa: E402

dev = "cuda"
CK, CH, FC = "S_mixed_84x28_w3", (24, 48, 48), 96
TRUTH = {60: "PASS", 30: "FAIL"}


def nominal(fn, cond=None):
    z = np.load(R + "results/calibration/" + fn, allow_pickle=True)
    conds = [str(c) for c in z["conds"]]
    i = conds.index(cond) if (cond and cond in conds) else (1 if len(conds) > 1 else 0)
    fr = z["frames"][i]
    oi = int(np.argmin(np.abs(z["offsets"])))
    yi = int(np.argmin(np.abs(z["yaws"])))
    px, py = z["pose_x"], z["pose_y"]
    d = np.concatenate([[0], np.cumsum(np.hypot(np.diff(px), np.diff(py)))])
    n = int(np.searchsorted(d, 2861.0))
    return fr[:n, oi, yi], d[:n]


def steer(m, fr):
    out = []
    with torch.no_grad():
        for k in range(0, len(fr), 3000):
            out.append(m(torch.from_numpy(fr[k:k + 3000]).to(dev)).cpu().numpy())
    torch.cuda.empty_cache()
    return np.concatenate(out).reshape(-1)


m = StudentNet(28, 84, channels=CH, fc=FC).to(dev)
m.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{CK}.pth", map_location=dev))
m.eval()

# deviation series for each calibration cell, each direction
series, step = {}, None
for d_ in ("westbound", "eastbound"):
    base, dist = nominal(f"lap_{d_}_clear.npz", "clear")
    step = float(np.median(np.diff(dist)))
    sb = steer(m, base)
    for alt in (60, 30):
        fr, _ = nominal(f"p09_{alt}_{d_}.npz")
        if len(fr) != len(base):
            print(f"  SKIP {d_} +{alt}: {len(fr)} vs {len(base)} poses")
            continue
        series[(d_, alt)] = steer(m, fr) - sb

print(f"  pose spacing {step:.2f} m;  {len(series)} calibration series\n")
print(f"  {'window':>9s} {'poses':>6s} {'max PASS':>9s} {'min FAIL':>9s} {'ratio':>7s}  separates?")
for W in (3, 5, 9, 15, 25, 40, 80, 200, 400, 800, 1590):
    p, f = [], []
    for (d_, alt), ds in series.items():
        v = float(np.abs(np.convolve(ds, np.ones(W) / W, mode="valid")).max())
        (p if TRUTH[alt] == "PASS" else f).append(v)
    mp, mf = max(p), min(f)
    print(f"  {W * step:8.1f}m {W:6d} {mp:9.5f} {mf:9.5f} {mf / mp:7.2f}  "
          f"{'YES' if mf > mp else 'no'}")

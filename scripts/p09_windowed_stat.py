"""P-09 step 2/3: windowed statistic against the feedback-derived tolerance.

Same criterion as F38, unmodified:
    statistic = max over the lap of |windowed mean of (steer(cell) - steer(clear))|
    tolerance = |k_o| * CTE_BUDGET_M          (policy-specific, measured not fitted)
    window    = T_CLOSED_LOOP_S * TARGET_SPEED_MS

Argument selects which cells are examined, so the calibration set can be inspected
without the held-out set ever being computed in the same run.

    python p09_stat.py calibration     -> +60, +30
    python p09_stat.py heldout         -> +37, +15
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
SPLIT = {"calibration": [60, 30], "heldout": [37, 15]}[sys.argv[1]]
CK, CH, FC = "S_mixed_84x28_w3", (24, 48, 48), 96
WIN_M = C.T_CLOSED_LOOP_S * C.TARGET_SPEED_MS


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

# k_o: restoring gain in steering per metre of lateral offset, at zero heading.
# Measured from the canonical offset x heading capture -- a property of the policy,
# identical for every cell, so it is not a per-cell free parameter.
z = np.load(R + "results/calibration/lap_westbound_clear.npz", allow_pickle=True)
off, yaws = z["offsets"], z["yaws"]
yz = int(np.argmin(np.abs(yaws)))
grid = z["frames"][0][::8]
with torch.no_grad():
    s = m(torch.from_numpy(grid.reshape(-1, 3, 28, 84)).to(dev)
          ).cpu().numpy().reshape(grid.shape[0], len(off), len(yaws))
torch.cuda.empty_cache()
ko = float(np.mean([abs(np.polyfit(off, s[p, :, yz], 1)[0]) for p in range(s.shape[0])]))
tol = ko * C.CTE_BUDGET_M
print(f"  S_mixed  k_o {ko:.4f}  ->  derived tolerance {tol:.4f}")

print(f"\n  {'dir':10s} {'cell':7s} {'windowed':>9s} {'lap mean':>9s} {'x tol':>7s} {'verdict':>8s}")
for d_ in ("westbound", "eastbound"):
    base, dist = nominal(f"lap_{d_}_clear.npz", "clear")
    W = max(1, int(round(WIN_M / float(np.median(np.diff(dist))))))
    sb = steer(m, base)
    for alt in SPLIT:
        fr, _ = nominal(f"p09_{alt}_{d_}.npz")
        if len(fr) != len(base):
            print(f"  {d_:10s} +{alt:<6d} pose-count mismatch {len(fr)} vs {len(base)} -- SKIP")
            continue
        ds = steer(m, fr) - sb
        win = float(np.abs(np.convolve(ds, np.ones(W) / W, mode="valid")).max())
        print(f"  {d_:10s} +{alt:<6d} {win:9.5f} {abs(ds.mean()):9.5f} {win / tol:7.2f} "
              f"{'FAIL' if win > tol else 'PASS':>8s}")
print(f"\n  window {WIN_M:.1f} m = {W} poses;  criterion unchanged from F38")

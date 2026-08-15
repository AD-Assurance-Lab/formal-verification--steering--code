"""Where does the departure happen, and what is the certificate saying THERE?

+30 eastbound departs reproducibly around (x=-20, y=100..240). +60 drives clean.
The lap-wide windowed statistic ranks +60 ABOVE +30, so if the certificate is
looking at the wrong thing, the local picture at the departure site should show it.

Signed, not absolute: a steering bias toward the inside of a curve is corrective,
the same magnitude outward is not, and |.| discards that.
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
W = 9
DEPART = (-20.0, 170.0)      # centre of the +30 eastbound departure cluster


def load(fn, cond=None):
    z = np.load(R + "results/calibration/" + fn, allow_pickle=True)
    conds = [str(c) for c in z["conds"]]
    i = conds.index(cond) if (cond and cond in conds) else (1 if len(conds) > 1 else 0)
    oi = int(np.argmin(np.abs(z["offsets"])))
    yi = int(np.argmin(np.abs(z["yaws"])))
    px, py = np.asarray(z["pose_x"]), np.asarray(z["pose_y"])
    d = np.concatenate([[0], np.cumsum(np.hypot(np.diff(px), np.diff(py)))])
    n = int(np.searchsorted(d, 2861.0))
    return z["frames"][i][:n, oi, yi], px[:n], py[:n], d[:n]


def steer(m, fr):
    out = []
    with torch.no_grad():
        for k in range(0, len(fr), 3000):
            out.append(m(torch.from_numpy(fr[k:k + 3000]).to(dev)).cpu().numpy())
    torch.cuda.empty_cache()
    return np.concatenate(out).reshape(-1)


m = StudentNet(28, 84, channels=(24, 48, 48), fc=96).to(dev)
m.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/S_mixed_84x28_w3.pth", map_location=dev))
m.eval()

base, px, py, dist = load("lap_eastbound_clear.npz", "clear")
sb = steer(m, base)
j = int(np.argmin(np.hypot(px - DEPART[0], py - DEPART[1])))
print(f"  departure site  ({px[j]:.1f}, {py[j]:.1f})  =  pose {j} of {len(px)}, "
      f"{dist[j]:.0f} m into the lap\n")

k = np.ones(W) / W
print(f"  {'cell':6s} {'signed win @ site':>18s} {'|win| @ site':>13s} "
      f"{'lap max |win|':>14s} {'argmax pose':>12s} {'site rank':>10s}")
for alt in (60, 30):
    fr, _, _, _ = load(f"p09_{alt}_eastbound.npz")
    if len(fr) != len(base):
        print(f"  +{alt}: pose mismatch"); continue
    ds = steer(m, fr) - sb
    win = np.convolve(ds, k, mode="same")          # signed, aligned to pose index
    aw = np.abs(win)
    # rank of the departure site among all poses by |windowed deviation|
    rank = int((aw > aw[j]).sum())
    print(f"  +{alt:<5d} {win[j]:18.5f} {aw[j]:13.5f} {aw.max():14.5f} "
          f"{int(np.argmax(aw)):12d} {rank:6d}/{len(aw)}")

print("\n  sign convention: positive steer turns the same way the training data labels it;\n"
      "  what matters is whether the two cells differ in SIGN at the departure site.")

"""Gate-A equivalent for the OFF-NOMINAL grid, with heading included.

The first pass evaluated the surface at the measured offset but ZERO heading error, so part
of the 0.00490 discrepancy was my omission rather than surface error. This uses both states:
heading error is the vehicle yaw minus the local path tangent, taken from the trace itself.

It also splits the error by |offset| band, because the traces of DEPARTING cells visit
offsets across the whole grid. That says where the captured surface can be trusted, which is
the precondition for any rollout.
"""
import csv
import sys

import numpy as np
import torch

R = "/home/za/ad-assurance--workspace/formal-verification--automated-driving--code/"
sys.path.insert(0, R)
sys.path.insert(0, R + "pipeline")

import config as C  # noqa: E402
from student import StudentNet  # noqa: E402

dev = "cuda"
CELLS = [("S_mixed", "S_mixed_84x28_w3", (24, 48, 48), 96, "fog"),
         ("S_clear", "S_clear_84x28", (8, 16, 16), 32, "night"),
         ("S_clear", "S_clear_84x28", (8, 16, 16), 32, "shadows")]


def trace(fn):
    with open(R + "results/traces/" + fn) as fh:
        rows = list(csv.DictReader(fh))
    return {k: np.array([float(r[k]) for r in rows]) for k in
            ("x", "y", "yaw", "steer", "cte_m")}


def surface(m, fn, cond):
    z = np.load(R + "results/calibration/" + fn, allow_pickle=True)
    cs = [str(c) for c in z["conds"]]
    i = cs.index(cond) if cond in cs else 0
    off = np.asarray(z["offsets"], dtype=np.float64)
    yaw = np.radians(np.asarray(z["yaws"], dtype=np.float64))
    fr = z["frames"][i]
    n = fr.shape[0]
    g = np.empty((n, len(off), len(yaw)))
    with torch.no_grad():
        for p in range(n):
            g[p] = m(torch.from_numpy(np.ascontiguousarray(fr[p]).reshape(-1, 3, 28, 84)
                                      ).to(dev)).cpu().numpy().reshape(len(off), len(yaw))
    torch.cuda.empty_cache()
    return g, off, yaw, np.asarray(z["pose_x"]), np.asarray(z["pose_y"]), np.asarray(z["pose_yaw"])


def interp(g, o, p, off, yaw):
    o = float(np.clip(o, off[0], off[-1]))
    p = float(np.clip(p, yaw[0], yaw[-1]))
    i = int(np.clip(np.searchsorted(off, o) - 1, 0, len(off) - 2))
    j = int(np.clip(np.searchsorted(yaw, p) - 1, 0, len(yaw) - 2))
    to = (o - off[i]) / (off[i + 1] - off[i])
    tp = (p - yaw[j]) / (yaw[j + 1] - yaw[j])
    return ((1 - to) * (1 - tp) * g[i, j] + to * (1 - tp) * g[i + 1, j]
            + (1 - to) * tp * g[i, j + 1] + to * tp * g[i + 1, j + 1])


def wrap(a):
    return (a + 180.0) % 360.0 - 180.0


print("  gate-A equivalent on the off-nominal grid: predicted steering at the vehicle's\n"
      "  measured (offset, heading) vs the steering it actually commanded.\n"
      "  gate A threshold on nominal captures was 0.05; nominal achieved 0.0137.\n")
for nm, ck, ch, fc, cond in CELLS:
    m = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
    m.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
    m.eval()
    try:
        g, off, yaw, px, py, pyaw = surface(m, f"lap_westbound_{cond}.npz", cond)
        tr = trace(f"{nm.replace('_','')}_{cond}_{cond}_westbound_rep00.csv")
    except FileNotFoundError as e:
        print(f"  {nm} / {cond}: missing ({e})")
        continue
    idx = np.array([int(np.argmin(np.hypot(px - x, py - y))) for x, y in zip(tr["x"], tr["y"])])
    # heading error = vehicle yaw - captured path yaw at the nearest pose
    he = np.radians(wrap(tr["yaw"] - pyaw[idx]))
    pred = np.array([interp(g[i], o, h, off, yaw) for i, o, h in zip(idx, tr["cte_m"], he)])
    err = np.abs(pred - tr["steer"])
    print(f"  {nm} / {cond}:  |cte| max {np.abs(tr['cte_m']).max():.2f} m, "
          f"|heading err| max {np.degrees(np.abs(he)).max():.1f} deg")
    print(f"    {'|offset| band':>16s} {'n':>6s} {'mean |err|':>11s} {'p95':>9s}")
    for lo, hi in ((0.0, 0.15), (0.15, 0.4), (0.4, 0.8), (0.8, 1.5), (1.5, 99.0)):
        s = (np.abs(tr["cte_m"]) >= lo) & (np.abs(tr["cte_m"]) < hi)
        if s.sum() < 5:
            continue
        print(f"    {lo:6.2f}-{hi:<8.2f} {int(s.sum()):6d} {err[s].mean():11.5f} "
              f"{np.percentile(err[s], 95):9.5f}")
    print()

"""Does a STATIC placement reproduce what the camera sees while actually driving?

F41 measured that the off-nominal surface mispredicts commanded steering by 0.021-0.048,
which is 4-5x the disturbance effect a rollout integrates. The named suspect is that
off-nominal frames come from teleporting the vehicle to an offset and settling it, whereas a
vehicle really at that offset is steering to correct and carries the suspension state that
produces.

This compares the two directly. For every logged driven frame whose measured (offset,
heading) lands near a grid node, it pulls the STATIC capture at that same pose and node and
compares them as images -- and, more decisively, as network outputs, since only the steering
difference matters.

Driven frames are projected with exactly the projection the captures used.
"""
import csv
import sys

import cv2
import numpy as np
import torch

R = "/home/za/ad-assurance--workspace/formal-verification--automated-driving--code/"
sys.path.insert(0, R)
sys.path.insert(0, R + "pipeline")

import config as C  # noqa: E402
import verifiable_disturbance as vd  # noqa: E402
from student import StudentNet  # noqa: E402

dev = "cuda"
ROOT = R + "results/framelog/Sclear_night6/"
OFF_TOL, YAW_TOL = 0.25, 3.0      # m, deg -- how near a grid node counts as "at" it


def wrap(a):
    return (a + 180.0) % 360.0 - 180.0


m = StudentNet(28, 84, channels=(8, 16, 16), fc=32).to(dev)
m.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/S_clear_84x28.pth", map_location=dev))
m.eval()

CAP = {}
for d_ in ("westbound", "eastbound"):
    zz = np.load(R + f"results/calibration/lap_{d_}_night.npz", allow_pickle=True)
    cs = [str(c) for c in zz["conds"]]
    CAP[d_] = (zz["frames"][cs.index("night") if "night" in cs else 0],
               np.asarray(zz["offsets"], dtype=np.float64),
               np.asarray(zz["yaws"], dtype=np.float64),
               np.asarray(zz["pose_x"]), np.asarray(zz["pose_y"]),
               np.asarray(zz["pose_yaw"]))

import os
rows = []
for sub in sorted(os.listdir(ROOT)):
    mf = os.path.join(ROOT, sub, "manifest.csv")
    if not os.path.exists(mf):
        continue
    d_ = "westbound" if "westbound" in sub else "eastbound"
    with open(mf) as fh:
        for r in csv.DictReader(fh):
            if r["cte_m"] != "":
                r["_dir"], r["_sub"] = d_, sub
                rows.append(r)
print(f"  {len(rows)} logged driven frames with a cross-track reading")

pairs = []
for r in rows:
    frames, off, yaws, px, py, pyaw = CAP[r["_dir"]]
    x, y = float(r["x"]), float(r["y"])
    i = int(np.argmin(np.hypot(px - x, py - y)))
    o = float(r["cte_m"])
    h = wrap(float(r["yaw"]) - pyaw[i])
    oi = int(np.argmin(np.abs(off - o)))
    yi = int(np.argmin(np.abs(yaws - h)))
    if abs(off[oi] - o) <= OFF_TOL and abs(yaws[yi] - h) <= YAW_TOL:
        pairs.append((ROOT + r["_sub"] + "/" + r["image"], i, oi, yi, o, h,
                      float(r["steer"]), r["_dir"]))

print(f"  {len(pairs)} of them sit within {OFF_TOL} m and {YAW_TOL} deg of a grid node\n")
if not pairs:
    sys.exit("  no comparable frames")

img_err, steer_static, steer_driven, bands = [], [], [], []
B = 512
for k in range(0, len(pairs), B):
    chunk = pairs[k:k + B]
    dv, st = [], []
    for img, i, oi, yi, o, h, s, d_ in chunk:
        full = cv2.imread(img).astype(np.float32) / 255.0
        dv.append(vd._project(full, 84, 28).reshape(3, 28, 84))
        st.append(CAP[d_][0][i, oi, yi])
    dv = np.asarray(dv, dtype=np.float32)
    st = np.asarray(st, dtype=np.float32)
    img_err.append(np.abs(dv - st).mean(axis=(1, 2, 3)))
    with torch.no_grad():
        sd = m(torch.from_numpy(dv).to(dev)).cpu().numpy().reshape(-1)
        ss = m(torch.from_numpy(st).to(dev)).cpu().numpy().reshape(-1)
        # first-order correction from the node to the driven state
        for t, (img, i, oi, yi, o, h, sdrv, d_) in enumerate(chunk):
            fr_, off_, yw_, *_ = CAP[d_]
            gnode = m(torch.from_numpy(
                np.ascontiguousarray(fr_[i]).reshape(-1, 3, 28, 84)).to(dev)
                ).cpu().numpy().reshape(len(off_), len(yw_))
            ko_ = np.polyfit(off_, gnode[:, yi], 1)[0]
            kp_ = np.polyfit(np.radians(yw_), gnode[oi, :], 1)[0]
            ss[t] += ko_ * (o - off_[oi]) + kp_ * np.radians(h - yw_[yi])
    torch.cuda.empty_cache()
    steer_driven.append(sd)
    steer_static.append(ss)
    bands.extend(abs(p[4]) for p in chunk)

img_err = np.concatenate(img_err)
sd = np.concatenate(steer_driven)
ss = np.concatenate(steer_static)
bands = np.asarray(bands)
d = np.abs(sd - ss)

print(f"  image difference   mean {img_err.mean():.4f} per pixel  (disturbance itself is "
      f"0.142 for night)")
print(f"  steering: static capture (gain-corrected to the driven state) vs driven frame")
print(f"    mean |diff| {d.mean():.5f}   p95 {np.percentile(d, 95):.5f}   "
      f"max {d.max():.5f}")
print(f"    for reference: nominal gate A 0.0137, disturbance driving term 0.0052\n")
print(f"    {'|offset| band':>16s} {'n':>6s} {'img err':>9s} {'steer diff':>11s}")
for lo, hi in ((0.0, 0.15), (0.15, 0.4), (0.4, 0.8), (0.8, 1.6)):
    s = (bands >= lo) & (bands < hi)
    if s.sum() < 3:
        continue
    print(f"    {lo:6.2f}-{hi:<8.2f} {int(s.sum()):6d} {img_err[s].mean():9.4f} "
          f"{d[s].mean():11.5f}")

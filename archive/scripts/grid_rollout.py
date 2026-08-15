"""Windowed rollout: integrate only as far as the measured grid supports.

The full-lap rollout scored 2/6 on the canonical cells and produced deviations of
17 km, which is not a physical claim -- it is the integrator extrapolating long after
the state left the +-1.5 m grid, where interp() clamps to the edge and the restoring
response no longer corresponds to where the vehicle actually is.

The fix is to respect that validity domain. Roll from rest over a window, take the max
deviation reached, then reset and start the next window. A cell FAILS if any window
leaves the budget. This also matches what the closed loop does physically: departures
develop over a few seconds, not over 2.8 km of accumulated integration.

A run is additionally marked as leaving the grid, so a window whose verdict rests on
extrapolated dynamics is visible rather than silently trusted.
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
v, dt, L, MS = C.TARGET_SPEED_MS, C.FIXED_DT, C.WHEELBASE_M, C.MAX_STEER_RAD
WIN = int(sys.argv[1]) if len(sys.argv) > 1 else 220
STRIDE = max(1, WIN // 4)
STUD = (("S_clear", "S_clear_84x28", (8, 16, 16), 32),
        ("S_mixed", "S_mixed_84x28_w3", (24, 48, 48), 96))
TRUTH = {("S_clear", "fog"): "PASS", ("S_clear", "night"): "FAIL",
         ("S_clear", "shadows"): "FAIL", ("S_mixed", "fog"): "PASS",
         ("S_mixed", "night"): "PASS", ("S_mixed", "shadows"): "PASS"}


def surface(m, fn, cond):
    z = np.load(R + "results/calibration/" + fn, allow_pickle=True)
    conds = [str(c) for c in z["conds"]]
    i = conds.index(cond) if cond in conds else 0
    off = np.asarray(z["offsets"], dtype=np.float64)
    yaw = np.radians(np.asarray(z["yaws"], dtype=np.float64))
    fr = z["frames"][i]
    n = fr.shape[0]
    g = np.empty((n, len(off), len(yaw)))
    with torch.no_grad():
        for p in range(n):
            b = np.ascontiguousarray(fr[p]).reshape(-1, 3, 28, 84)
            g[p] = m(torch.from_numpy(b).to(dev)).cpu().numpy().reshape(len(off), len(yaw))
    torch.cuda.empty_cache()
    return g, off, yaw


def interp(g, o, p, off, yaw):
    o = float(np.clip(o, off[0], off[-1]))
    p = float(np.clip(p, yaw[0], yaw[-1]))
    i = int(np.clip(np.searchsorted(off, o) - 1, 0, len(off) - 2))
    j = int(np.clip(np.searchsorted(yaw, p) - 1, 0, len(yaw) - 2))
    to = (o - off[i]) / (off[i + 1] - off[i])
    tp = (p - yaw[j]) / (yaw[j + 1] - yaw[j])
    return ((1 - to) * (1 - tp) * g[i, j] + to * (1 - tp) * g[i + 1, j]
            + (1 - to) * tp * g[i, j + 1] + to * tp * g[i + 1, j + 1])


def windowed(gc, gb, off, yaw, oz, yz):
    """max deviation over any window, integrating from rest at each window start"""
    n = len(gc)
    worst, left_grid = 0.0, False
    for s in range(0, max(1, n - WIN + 1), STRIDE):
        o = p = 0.0
        for i in range(s, min(s + WIN, n)):
            d = MS * (interp(gc[i], o, p, off, yaw) - gb[i][oz, yz])
            o = o + v * dt * p
            p = p + (v * dt / L) * d
            if abs(o) > off[-1]:
                left_grid = True
            worst = max(worst, abs(o))
            if abs(o) > 20.0:          # unambiguously departed; stop integrating
                break
    return worst, left_grid


print(f"  window {WIN} poses ({WIN*1.79:.0f} m), stride {STRIDE};  "
      f"budget {C.CTE_BUDGET_M:.3f} m\n")
print(f"  {'model':8s} {'cell':9s} {'max |o| (m)':>12s} {'x budget':>9s} {'grid?':>6s} "
      f"{'rollout':>8s} {'driven':>7s}  agree")
ok = tot = 0
for nm, ck, ch, fc in STUD:
    m = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
    m.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
    m.eval()
    gb, off, yaw = surface(m, "lap_westbound_clear.npz", "clear")
    oz = int(np.argmin(np.abs(off)))
    yz = int(np.argmin(np.abs(yaw)))
    for cond in ("fog", "night", "shadows"):
        gc, _, _ = surface(m, f"lap_westbound_{cond}.npz", cond)
        if len(gc) != len(gb):
            print(f"  {nm:8s} {cond:9s} pose mismatch"); continue
        mx, lg = windowed(gc, gb, off, yaw, oz, yz)
        vd = "FAIL" if mx > C.CTE_BUDGET_M else "PASS"
        t = TRUTH[(nm, cond)]
        ok += vd == t; tot += 1
        print(f"  {nm:8s} {cond:9s} {mx:12.3f} {mx/C.CTE_BUDGET_M:9.2f} "
              f"{'left' if lg else 'in':>6s} {vd:>8s} {t:>7s}  {'yes' if vd == t else 'NO'}")

# sun cells, eastbound, same window
SUN = {"+60": "PASS", "+30": "FAIL"}
m = StudentNet(28, 84, channels=(24, 48, 48), fc=96).to(dev)
m.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/S_mixed_84x28_w3.pth", map_location=dev))
m.eval()
try:
    gb, off, yaw = surface(m, "p09grid_clear_eastbound.npz", "clear")
    oz = int(np.argmin(np.abs(off)))
    yz = int(np.argmin(np.abs(yaw)))
    for lab, t in SUN.items():
        gc, _, _ = surface(m, f"p09grid_{lab.lstrip('+')}_eastbound.npz", "clear")
        mx, lg = windowed(gc, gb, off, yaw, oz, yz)
        vd = "FAIL" if mx > C.CTE_BUDGET_M else "PASS"
        ok += vd == t; tot += 1
        print(f"  {'S_mixed':8s} {'sun ' + lab:9s} {mx:12.3f} {mx/C.CTE_BUDGET_M:9.2f} "
              f"{'left' if lg else 'in':>6s} {vd:>8s} {t:>7s}  {'yes' if vd == t else 'NO'}")
except FileNotFoundError as e:
    print(f"  sun cells skipped: {e}")

print(f"\n  agreement: {ok}/{tot}")

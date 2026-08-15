#!/usr/bin/env python3
"""Roll the vehicle state forward on a surface fitted to DRIVEN frames (F42 follow-up).

The static (offset x heading) grid mispredicts driven steering by 0.0258 -- 5x the
disturbance term a rollout integrates -- so every rollout so far has been dominated by
capture error. This repeats the rollout on frames captured from a moving vehicle
(scripts/capture_driven_offsets.py) instead.

At each pose the driven samples give scattered (offset, heading, steering) triples rather
than a regular grid, so the local response is a least-squares plane

    steer(o, psi) ~ a + k_o o + k_psi psi

fitted from samples within a short window of arc length. The rollout is then the same
deviation dynamics used before, with the plane in place of the interpolated grid:

    o'   = o + v dt psi
    psi' = psi + (v dt / L) MAX_STEER_RAD ( steer_cond(o, psi) - steer_clear(0, 0) )

THE TEST THAT MATTERS is not +30 versus +60 -- the static grid already got those right.
It is whether the canonical cells stop false-alarming, which the static version failed 2/6.
Both are scored together here so the comparison is visible in one table.
"""
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
from student import StudentNet  # noqa: E402

dev = "cuda"
v, dt, L, MS = C.TARGET_SPEED_MS, C.FIXED_DT, C.WHEELBASE_M, C.MAX_STEER_RAD
CAL = REPO / "results" / "calibration"
WIN_M = 6.0          # arc-length window whose samples define one local plane
MIN_N = 8            # fewer samples than this and the pose is skipped, not guessed

STUD = {"S_clear": ("S_clear_84x28", (8, 16, 16), 32),
        "S_mixed": ("S_mixed_84x28_w3", (24, 48, 48), 96)}

# driven ground truth, eastbound
TRUTH = [("S_clear", "fog", "PASS"), ("S_clear", "night", "FAIL"),
         ("S_clear", "shadows", "FAIL"),
         ("S_mixed", "fog", "PASS"), ("S_mixed", "night", "PASS"),
         ("S_mixed", "shadows", "PASS"),
         ("S_mixed", "sun60", "PASS"), ("S_mixed", "sun30", "FAIL"),
         ("S_mixed", "sun37", "FAIL"), ("S_mixed", "sun15", "PASS")]


def load(name):
    z = np.load(CAL / f"driven_{name}_eastbound.npz", allow_pickle=True)
    return (z["frames"], z["offset"], np.radians(z["heading"]), z["x"], z["y"],
            z["phase"])


def steer_of(model, frames):
    out = []
    with torch.no_grad():
        for k in range(0, len(frames), 2048):
            out.append(model(torch.from_numpy(frames[k:k + 2048]).to(dev)
                             ).cpu().numpy().reshape(-1))
    torch.cuda.empty_cache()
    return np.concatenate(out)


def planes(s_samp, off, head, steer, edges):
    """least-squares plane per bin: returns (a, k_o, k_psi, n) arrays"""
    idx = np.digitize(s_samp, edges) - 1
    nb = len(edges) - 1
    A = np.full((nb, 4), np.nan)
    N = np.zeros(nb, dtype=int)
    RES = np.full(nb, np.nan)
    for b in range(nb):
        m = idx == b
        n = int(m.sum())
        N[b] = n
        if n < MIN_N + 1:
            continue
        ds = s_samp[m] - 0.5 * (edges[b] + edges[b + 1])
        M = np.column_stack([np.ones(n), ds, off[m], head[m]])
        try:
            A[b] = np.linalg.lstsq(M, steer[m], rcond=None)[0]
            RES[b] = float(np.abs(M @ A[b] - steer[m]).mean())
        except np.linalg.LinAlgError:
            pass
    return A, N, RES


def rollout(Ac, Ab):
    """integrate the deviation dynamics through the binned planes.

    A bin is WIN_M long but the control period covers only v*dt = 1.79 m, so each bin
    carries several integration steps. Stepping once per bin would under-integrate by
    WIN_M/(v*dt) and quietly make every cell look stable.
    """
    per_bin = max(1, int(round(WIN_M / (v * dt))))
    o = p = 0.0
    peak = 0.0
    for b in range(len(Ac)):
        if not np.isfinite(Ac[b]).all() or not np.isfinite(Ab[b]).all():
            continue
        s_base = Ab[b][0]                     # clear at the nominal state
        for _ in range(per_bin):
            s_cond = Ac[b][0] + Ac[b][2] * o + Ac[b][3] * p
            d = MS * (s_cond - s_base)
            o = o + v * dt * p
            p = p + (v * dt / L) * d
            peak = max(peak, abs(o))
            if peak > 20.0:
                return peak
    return peak


def main():
    fb, ob, hb, xb, yb, pb = load("clear")

    # The reference polyline must be ONE lap. The capture concatenates every phase, so
    # using all of it makes a ~17 km polyline whose arc length runs far past the bin
    # edges, and every bin then falls under MIN_N and is skipped -- which reads as a
    # clean sweep of PASS verdicts rather than as the failure it is.
    first = pb == pb[0]
    rx, ry = xb[first], yb[first]
    ref = np.column_stack([rx, ry])
    s_ref = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(rx), np.diff(ry)))])
    total = float(s_ref[-1])
    edges = np.arange(0.0, total + WIN_M, WIN_M)

    def project(x, y):
        out = np.empty(len(x))
        for k in range(len(x)):
            j = int(np.argmin((ref[:, 0] - x[k]) ** 2 + (ref[:, 1] - y[k]) ** 2))
            out[k] = s_ref[j]
        return out

    print(f"  window {WIN_M} m, min {MIN_N} samples per bin, "
          f"{len(edges)-1} bins over {total:.0f} m")
    print(f"  budget {C.CTE_BUDGET_M:.3f} m ({C.CTE_BUDGET_FT:.2f} ft)\n")
    print(f"  {'model':8s} {'cell':9s} {'bins used':>10s} {'max |o| (m)':>12s} "
          f"{'x budget':>9s} {'rollout':>8s} {'driven':>7s}  agree")

    cache = {}
    ok = tot = 0
    for nm, (ck, ch, fc) in STUD.items():
        model = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
        model.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
        model.eval()
        sb = steer_of(model, fb)
        s_base = project(xb, yb)
        Ab, Nb, Rb = planes(s_base, ob, hb, sb, edges)
        for m2, cell, truth in TRUTH:
            if m2 != nm:
                continue
            try:
                fc_, oc, hc, xc, yc, _pc = cache.get(cell) or load(cell)
            except FileNotFoundError:
                print(f"  {nm:8s} {cell:9s}  capture missing")
                continue
            cache[cell] = (fc_, oc, hc, xc, yc, _pc)
            sc = steer_of(model, fc_)
            Ac, Nc, Rc = planes(project(xc, yc), oc, hc, sc, edges)
            used = int((np.isfinite(Ac).all(1) & np.isfinite(Ab).all(1)).sum())
            mx = rollout(Ac, Ab)
            vd_ = "FAIL" if mx > C.CTE_BUDGET_M else "PASS"
            ok += vd_ == truth
            tot += 1
            res = float(np.nanmean(Rc))
            print(f"  {nm:8s} {cell:9s} {used:10d} {mx:12.3f} {mx/C.CTE_BUDGET_M:9.2f} "
                  f"{vd_:>8s} {truth:>7s}  {'yes' if vd_ == truth else 'NO':>3s}"
                  f"   fit resid {res:.5f}")
    print(f"\n  A verdict is only meaningful if the plane-fit residual is well BELOW the\n"
          f"  disturbance term the rollout integrates (~0.0052 normalised). Static captures\n"
          f"  failed exactly that test at 0.0258.")
    print(f"\n  agreement: {ok}/{tot}   (static-grid rollout scored 2/6 on the canonical "
          f"cells and 2/2 on the sun cells)")


if __name__ == "__main__":
    main()

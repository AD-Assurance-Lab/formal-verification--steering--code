#!/usr/bin/env python3
"""Does the CLEAR baseline have to come from the same capture session as the condition?

The sustained-bias certificate is computed on the segment

    x_p(s) = x_p^clear + s * (x_p^cond - x_p^clear),   s in [0, 1]

so the s = 0 endpoint is as much a part of the disturbance definition as s = 1.
`certify_sustained_bound.py` takes the two endpoints from DIFFERENT files:

    clear      <- results/calibration/lap_{dir}_clear.npz
    condition  <- results/calibration/lap_{dir}_{cond}.npz

which are separate CARLA sessions recorded hours apart. If anything global drifted
between them -- sun altitude, exposure, a weather field left set by the previous run --
that drift is inside (x_cond - x_clear) and the certificate bounds it as though it were
part of the weather.

`lap_eastbound_fog.npz` is the one capture that carries its OWN clear frames alongside
its fog frames, at identical poses. That makes it the only cell in the study where the
question can be MEASURED rather than argued: certify eastbound fog twice, once against
each baseline, and compare.

    python scripts/baseline_pairing_probe.py [stride]
"""
import sys
import json
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
import certify_cell as cc  # noqa: E402
from student import StudentNet  # noqa: E402

STUDENTS = (("S_clear", "S_clear_84x28", (8, 16, 16), 32),
            ("S_mixed", "S_mixed_84x28_w3", (24, 48, 48), 96))
NSPLIT = 16
CAL = REPO / "results" / "calibration"


def nominal(path, cond):
    """Centre-of-grid frames for one condition, truncated at the lap end (2861 m)."""
    z = np.load(path, allow_pickle=True)
    conds = [str(c) for c in z["conds"]]
    if cond not in conds:
        return None
    fr = z["frames"][conds.index(cond)]
    oi = int(np.argmin(np.abs(z["offsets"])))
    yi = int(np.argmin(np.abs(z["yaws"])))
    fr = fr[:, oi, yi]
    px, py = z["pose_x"], z["pose_y"]
    d = np.concatenate([[0], np.cumsum(np.hypot(np.diff(px), np.diff(py)))])
    return fr[:int(np.searchsorted(d, 2861.0))]


def bound_cell(net, bd, clr, dis, stride, dev):
    """Sustained-bias bound over s in [0,1], identical arithmetic to the certifier."""
    with torch.no_grad():
        sc = net(torch.from_numpy(clr[::stride]).to(dev)).cpu().numpy().reshape(-1)
    los, his = [], []
    for i, k in enumerate(range(0, len(clr), stride)):
        x0 = clr[k].reshape(-1).astype(np.float32)
        x1 = dis[k].reshape(-1).astype(np.float32)
        lo_i, hi_i = [], []
        for j in range(NSPLIT):
            a, b = j / NSPLIT, (j + 1) / NSPLIT
            mid, half = 0.5 * (a + b), 0.5 * (b - a)
            W = (half * (x1 - x0)).reshape(-1, 1)
            l_, u_ = bd(W, x0 + mid * (x1 - x0),
                        np.array([-1.0]), np.array([1.0]))
            lo_i.append(l_)
            hi_i.append(u_)
        los.append(min(lo_i) - sc[i])
        his.append(max(hi_i) - sc[i])
    return float(np.mean(los)), float(np.mean(his))


def measured_bias(net, clr, dis, stride, dev):
    """F34's statistic: mean over poses of (steer(cond) - steer(clear)). No bounding."""
    with torch.no_grad():
        a = net(torch.from_numpy(clr[::stride]).to(dev)).cpu().numpy().reshape(-1)
        b = net(torch.from_numpy(dis[::stride]).to(dev)).cpu().numpy().reshape(-1)
    return float(np.mean(b - a))


def main():
    stride = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tol = C.CLOSED_LOOP_TOLERANCE

    fog_npz = CAL / "lap_eastbound_fog.npz"
    clr_npz = CAL / "lap_eastbound_clear.npz"
    internal = nominal(fog_npz, "clear")      # same session as the fog frames
    external = nominal(clr_npz, "clear")      # what the certifier actually uses
    fog = nominal(fog_npz, "fog")
    n = min(len(internal), len(external), len(fog))
    internal, external, fog = internal[:n], external[:n], fog[:n]

    d = internal - external
    print(f"\nBASELINE PAIRING PROBE -- eastbound fog, stride {stride}, "
          f"tolerance {tol:.4f}\n")
    print("  the two CLEAR captures, same poses, different sessions")
    print(f"    signed mean   {d.mean():+.5f}     (a uniform offset, not noise)")
    print(f"    abs mean      {np.abs(d).mean():.5f}")
    print(f"    std           {d.std():.5f}")
    print(f"    fog's own disturbance |fog - internal clear|  "
          f"{np.abs(fog - internal).mean():.5f}")
    print(f"    baseline error as a fraction of it            "
          f"{np.abs(d).mean() / np.abs(fog - internal).mean():.1%}\n")

    print(f"  {'model':9s} {'baseline':10s} {'measured bias':>14s} {'x tol':>7s}"
          f" {'bound':>20s} {'x tol':>14s}  verdict")
    out = {}
    for nm, ck, ch, fc in STUDENTS:
        net = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
        net.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth",
                                       map_location=dev, weights_only=True))
        net.eval()
        bd = cc.Bounder(1, net, dev, 28, 84, method="CROWN")
        for tag, base in (("external", external), ("internal", internal)):
            mb = measured_bias(net, base, fog, stride, dev)
            lo, hi = bound_cell(net, bd, base, fog, stride, dev)
            v = "CERTIFIED" if (hi <= tol and lo >= -tol) else "FALSIFIED"
            out[f"{nm}/{tag}"] = dict(measured=mb, lo=lo, hi=hi, verdict=v)
            print(f"  {nm:9s} {tag:10s} {mb:+14.5f} {mb/tol:+7.2f}"
                  f" [{lo:+.5f},{hi:+.5f}] [{lo/tol:+5.2f},{hi/tol:+5.2f}]  {v}",
                  flush=True)

    out["_pixels"] = dict(signed_mean=float(d.mean()), abs_mean=float(np.abs(d).mean()),
                          std=float(d.std()),
                          fog_disturbance=float(np.abs(fog - internal).mean()),
                          stride=stride)
    (REPO / "results" / "diagnostic" / "baseline_pairing.json").write_text(
        json.dumps(out, indent=2))
    print("\n  -> results/diagnostic/baseline_pairing.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

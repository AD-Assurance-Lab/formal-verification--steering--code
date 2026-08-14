#!/usr/bin/env python3
"""Per-frame verification against the SUSTAINED steering tolerance.

WHY THIS AND NOT THE MAXIMUM (corrects F30). `CLOSED_LOOP_TOLERANCE` is defined as the
steering error which, SUSTAINED for T_CLOSED_LOOP_S = 1.85 s, carries the vehicle to the
edge of its lane. F30 compared it against the MAXIMUM steering deviation, which is
dimensionally the wrong quantity: the maximum is dominated by transients that reverse sign
and integrate to nothing, and every cell was falsified at 6-34x the threshold while four of
six drove cleanly. Worse, the ordering was wrong -- `S_mixed` deviates MORE under shadows
(0.2494) than `S_clear` does (0.2275) and passes while `S_clear` fails 10/10 -- so no choice
of threshold could have rescued it.

The MEAN deviation is the sustained component, which is what the threshold describes:

    persistent bias = mean over the lap of ( steer(disturbed) - steer(clear) )
    FAIL  iff  |persistent bias| > CLOSED_LOOP_TOLERANCE

Nothing here is fitted. The tolerance comes from lane width, vehicle width, wheelbase, speed
and a closed-loop time constant measured long before this criterion existed; the statistic is
an unweighted mean over every pose on the lap.

This is a PER-FRAME criterion -- no vehicle dynamics are simulated and no trajectory is
rolled out. It is the cheapest form of the idea that the physically meaningful quantity is
the integral of the steering error rather than its peak.

    python scripts/certify_sustained.py
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
from student import StudentNet  # noqa: E402

STUDENTS = (("S_clear", "S_clear_84x28", (8, 16, 16), 32),
            ("S_mixed", "S_mixed_84x28_w3", (24, 48, 48), 96))
TRUTH = {("S_clear", "clear"): "PASS", ("S_clear", "fog"): "PASS",
         ("S_clear", "night"): "FAIL", ("S_clear", "shadows"): "FAIL",
         ("S_mixed", "clear"): "PASS", ("S_mixed", "fog"): "PASS",
         ("S_mixed", "night"): "PASS", ("S_mixed", "shadows"): "PASS"}


def load(path, cond):
    """Nominal-path frames for one condition from a full-lap capture."""
    z = np.load(path, allow_pickle=True)
    conds = [str(c) for c in z["conds"]]
    if cond not in conds:
        return None, None
    fr = z["frames"][conds.index(cond)]          # (pose, offset, yaw, 3, 28, 84)
    # The NOMINAL path is the CENTRE of the offset/heading grid. Indexing [:, 0, 0] takes
    # the corner instead -- -1.5 m off centre and -6 deg of heading -- which is a state the
    # vehicle never occupies. Nominal-only captures have a 1x1 grid, so the corner and the
    # centre coincide there and the error only appears on the full grid.
    oi = np.argmin(np.abs(z["offsets"]))
    yi = np.argmin(np.abs(z["yaws"]))
    fr = fr[:, oi, yi]
    px, py = z["pose_x"], z["pose_y"]
    d = np.concatenate([[0], np.cumsum(np.hypot(np.diff(px), np.diff(py)))])
    n = int(np.searchsorted(d, 2861.0))
    return fr[:n], d[:n]


def steer_of(m, fr, dev, chunk=3000):
    outs = []
    with torch.no_grad():
        for k in range(0, len(fr), chunk):
            outs.append(m(torch.from_numpy(fr[k:k + chunk]).to(dev)).cpu().numpy())
    torch.cuda.empty_cache()
    return np.concatenate(outs).reshape(-1)


def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tol = C.CLOSED_LOOP_TOLERANCE
    cal = REPO / "results" / "calibration"
    print(f"\nSUSTAINED-BIAS CERTIFICATE   tolerance {tol:.4f} "
          f"(pre-registered, T={C.T_CLOSED_LOOP_S}s)")
    print(f"  |mean steering deviation from clear| over the full lap, per frame,")
    print(f"  no vehicle dynamics simulated\n")
    print(f"  {'direction':10s} {'model':9s} {'cond':9s} {'persistent bias':>16s} "
          f"{'x tol':>7s} {'verdict':>8s} {'drive':>6s}")
    ok = n = 0
    out = {}
    for direction in ("westbound", "eastbound"):
        base = cal / f"lap_{direction}_clear.npz"
        if not base.exists():
            continue
        for nm, ck, ch, fc in STUDENTS:
            m = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
            m.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
            m.eval()
            frc, _ = load(base, "clear")
            sc = steer_of(m, frc, dev)
            for cond in ("clear", "fog", "night", "shadows"):
                p = cal / f"lap_{direction}_{cond}.npz"
                if not p.exists():
                    print(f"  {direction:10s} {nm:9s} {cond:9s} "
                          f"{'capture missing':>16s}")
                    continue
                frd, _ = load(p, cond)
                if frd is None or len(frd) != len(frc):
                    continue
                sd = steer_of(m, frd, dev)
                bias = float(np.mean(sd - sc))
                v = "FAIL" if abs(bias) > tol else "PASS"
                t = TRUTH[(nm, cond)]
                ok += v == t
                n += 1
                out[f"{direction}/{nm}/{cond}"] = dict(bias=bias, verdict=v, truth=t)
                print(f"  {direction:10s} {nm:9s} {cond:9s} {bias:+16.5f} "
                      f"{abs(bias)/tol:7.2f} {v:>8s} {t:>6s}  "
                      f"{'agree' if v == t else 'DISAGREE'}")
    print(f"\n  agreement: {ok}/{n}")
    (cal / "sustained_cert.json").write_text(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

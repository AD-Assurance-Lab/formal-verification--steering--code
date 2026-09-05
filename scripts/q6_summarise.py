#!/usr/bin/env python3
"""Summarise Q6 -- where the distillation dispersion comes from.

The analysis declared in docs/Q6_PREREGISTRATION.md (with amendment A-1):

  Q6a   SD and CV of fog p99 for `init` (initialisation alone), `data` (minibatch order
        alone) and `both` (tied), all on the opt-in seed path so one variable moves.
        Reported with BOOTSTRAP 95% INTERVALS on the CV -- a variance comparison at n = 8
        is itself noisy, and a bare ratio of SDs would repeat the mistake Q6 exists to
        characterise.
  Q6b   the same CV at TRAIN_FRAC 1.0 / 0.5 / 0.25.
  Q6c   read from q6c_ensemble.json, written by scripts/q6_ensemble.py.

Q1's un-opted `lr3e4` seeds are printed alongside as a reference. They are NOT pooled into
any arm: amendment A-1 records that the opt-in path draws minibatches from a separate
generator, so the un-opted seeds differ from the tied `both` arm in exactly the variable
being decomposed.

    python3 scripts/q6_summarise.py
"""
import json
import pathlib
import statistics as st

import numpy as np

REPO = pathlib.Path(__file__).resolve().parent.parent
VAR = REPO / "results/town06/variance"
ARMS = ["init", "data", "both", "f50", "f25"]
SEEDS = range(8)
BOOT, BOOT_SEED = 10000, 20260905


def vals(arm, cond="fog", field="p99_abs_err"):
    out = []
    for s in SEEDS:
        p = VAR / f"kd_{arm}_s{s}.json"
        if p.exists():
            v = json.loads(p.read_text())["conditions"].get(cond, {}).get(field)
            if v is not None:
                out.append(v)
    return out


def cv_ci(v):
    """CV with a bootstrap 95% interval. Fixed seed: the interval must not move between
    two readings of the same data."""
    if len(v) < 3:
        return None, None, None
    rng = np.random.RandomState(BOOT_SEED)
    a = np.array(v)
    cvs = []
    for _ in range(BOOT):
        r = rng.choice(a, len(a), replace=True)
        m = r.mean()
        if m:
            cvs.append(r.std(ddof=1) / m)
    return a.std(ddof=1) / a.mean(), float(np.percentile(cvs, 2.5)), \
        float(np.percentile(cvs, 97.5))


def row(name, v):
    if not v:
        return f"{name:>7s}  {'no cells yet':>12s}"
    if len(v) < 2:
        return f"{name:>7s}  n= 1  median {v[0]:.4f}  (SD needs n >= 2)"
    cv, lo, hi = cv_ci(v)
    s = (f"{name:>7s}  n={len(v):2d}  median {st.median(v):.4f}  "
         f"SD {np.std(v, ddof=1):.4f}")
    if cv is not None:
        s += f"  CV {cv*100:5.1f}%  95% CI [{lo*100:.1f}%, {hi*100:.1f}%]"
    return s


def q1_reference():
    """Q1's lr3e4 fog KD p99, for context only -- never pooled."""
    out = []
    for s in range(15):
        if s < 6:
            p = REPO / f"results/town06/depth/kd_d3lr3_s{s}.json"
        else:
            p = REPO / f"results/town06/lr_confirm/kd_lr3e4_s{s}.json"
        if p.exists():
            out.append(json.loads(p.read_text())["conditions"]["fog"]["p99_abs_err"])
    return out


def main():
    print("Q6 -- the distillation dispersion. fog KD p99 |err|, tolerance 0.0120.")
    print("All arms on the OPT-IN seed path (amendment A-1), lr 3e-4, kernels pinned.\n")

    print("=== Q6a: initialisation or data order? ===")
    for arm in ("init", "data", "both"):
        print(" ", row(arm, vals(arm)))
    print()

    vi, vd, vb = vals("init"), vals("data"), vals("both")
    if len(vi) > 2 and len(vd) > 2:
        si, sd = np.std(vi, ddof=1), np.std(vd, ddof=1)
        ratio = si / sd if sd else float("inf")
        print(f"  Q6a-P1  SD(init) >= 2x SD(data): {si:.4f} / {sd:.4f} = {ratio:.2f}x "
              f"-> {'HELD' if ratio >= 2 else 'FALSIFIED'}")
        if len(vb) > 2:
            sb = np.std(vb, ddof=1)
            comp = (si ** 2 + sd ** 2)
            f = sb ** 2 / comp if comp else float("inf")
            print(f"  Q6a-P2  SD(both)^2 within 2x of SD(init)^2+SD(data)^2: "
                  f"{sb**2:.6f} vs {comp:.6f} = {f:.2f}x "
                  f"-> {'HELD' if 0.5 <= f <= 2 else 'FALSIFIED'}")
    print()

    print("=== Q6b: does the dispersion grow as the pool shrinks? ===")
    for arm, frac in (("both", "1.00"), ("f50", "0.50"), ("f25", "0.25")):
        v = vals(arm)
        print(f"  frac {frac}  {row(arm, v)[9:]}")
    cvs = []
    for arm in ("both", "f50", "f25"):
        v = vals(arm)
        cvs.append(cv_ci(v)[0] if len(v) > 2 else None)
    if all(c is not None for c in cvs):
        mono = cvs[0] <= cvs[1] <= cvs[2]
        print(f"\n  Q6b-P1  CV grows monotonically as the pool shrinks: "
              f"{cvs[0]*100:.1f}% -> {cvs[1]*100:.1f}% -> {cvs[2]*100:.1f}% "
              f"-> {'HELD' if mono else 'FALSIFIED'}")
        r = cvs[2] / cvs[0] if cvs[0] else float("inf")
        print(f"  Q6b-P2  CV at 0.25 < 2x CV at 1.00: {r:.2f}x "
              f"-> {'HELD' if r < 2 else 'FALSIFIED'}")
    print()

    print("=== reference: Q1's lr3e4 arm, UN-OPTED path (context only, never pooled) ===")
    print(" ", row("q1", q1_reference()))
    vb2 = vals("both")
    if vb2 and len(vb2) > 2:
        q = q1_reference()
        print(f"  the un-opted and tied-opt-in arms differ in minibatch STREAM only: "
              f"median {st.median(q):.4f} vs {st.median(vb2):.4f}")
    print()

    p = VAR / "q6c_ensemble.json"
    if not p.exists():
        print("=== Q6c: not run yet (scripts/q6_ensemble.py) ===")
        return
    d = json.loads(p.read_text())
    print("=== Q6c: does combining seeds beat the median seed? (fog p99) ===")
    s = d["singles"]["fog"]
    print(f"  single seeds  median {s['median']:.4f}  best {s['best']:.4f}  "
          f"worst {s['worst']:.4f}")
    for kind in ("output", "weights"):
        for k in ("2", "4", "8"):
            e = d.get(kind, {}).get("fog", {}).get(k)
            if e:
                print(f"  {kind:7s} k={k}  median {e['median']:.4f}")
    o4 = d.get("output", {}).get("fog", {}).get("4", {}).get("median")
    o8 = d.get("output", {}).get("fog", {}).get("8", {}).get("median")
    w2 = d.get("weights", {}).get("fog", {}).get("2", {}).get("median")
    if o4 and o8:
        p1 = o4 < s["median"] and o8 < s["best"]
        print(f"\n  Q6c-P1  output beats median at k=4 AND best at k=8 -> "
              f"{'HELD' if p1 else 'FALSIFIED'}")
    if w2:
        print(f"  Q6c-P2  weight average worse than the worst single seed at k=2: "
              f"{w2:.4f} vs {s['worst']:.4f} -> "
              f"{'HELD' if w2 > s['worst'] else 'FALSIFIED'}")
    print(f"\n  CAVEAT: {d['caveat']}")


if __name__ == "__main__":
    main()

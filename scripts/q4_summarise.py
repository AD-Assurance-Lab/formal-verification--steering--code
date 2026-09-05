#!/usr/bin/env python3
"""Summarise Q4 -- does label balancing survive twelve seeds?

The analysis declared in docs/Q4_PREREGISTRATION.md, and the primary endpoint is
deliberately NOT the median:

  primary     seeds holding fog 3/3 under the 2.19 ft budget, per arm, against the raw
              control. Fisher exact, two-sided. E6-F1 is explicit that balancing did not
              move the typical student, it REMOVED THE FAILURES -- raw's median was
              flattered by a distribution containing a 37.65 ft departure while `bal`
              produced none. Pre-registering the median would test a claim nobody makes.
  secondary   fog median and Hodges-Lehmann shift vs control; clear median and holding
              count (E6-F2 found clear IMPROVING, which is what made it a falsification);
              fog KD p99 median; and VOID counts, which E6 saw four of across these arms.

The CONTROL is free: Q1's `lr3e4` arm at n = 15 is the same architecture, same lr, same
pinned kernels, raw labels. Q4 drives no control laps of its own.

Seeds 0-5 of both arms are folded in from E6 and were validated bit-exactly by SHA-256
against S_mixed_bal_bal_s0 and S_mixed_bal_curv_s0 before use.

    python3 scripts/q4_summarise.py
"""
import json
import pathlib
import statistics as st

REPO = pathlib.Path(__file__).resolve().parent.parent
BAL = REPO / "results/town06/balancing"
DEPTH = REPO / "results/town06/depth"
NEW = REPO / "results/town06/lr_confirm"

BUDGET, MARGIN_GATE, VOID_REL = 2.19, 1.095, 0.25
ARM_SEEDS = range(12)
CTRL_SEEDS = range(15)


def _cell(path):
    if not path.exists():
        return None
    laps = [l for l in list(json.loads(path.read_text())["results"].values())[0]
            if not l.get("error")]
    if not laps:
        return {"state": "NO_LAPS"}
    v = [l["max_cte_ft"] for l in laps]
    if max(v) > 0 and (max(v) - min(v)) / max(v) > VOID_REL:
        return {"state": "VOID"}
    return {"state": "OK", "hi": max(v), "n": len(laps),
            "held": sum(1 for x in v if x <= BUDGET),
            "gate": sum(1 for x in v if x <= MARGIN_GATE),
            "dep": sum(1 for l in laps if l.get("departed"))}


def cell(arm, s, c):
    if arm == "raw":                                  # Q1's lr3e4 arm, the control
        p = (DEPTH / f"drive_d3lr3_s{s}_{c}.json" if s < 6
             else NEW / f"drive_lr3e4_s{s}_{c}.json")
    else:
        p = BAL / f"drive_{arm}_s{s}_{c}.json"
    return _cell(p)


def kd(arm, s, c="fog"):
    if arm == "raw":
        p = (DEPTH / f"kd_d3lr3_s{s}.json" if s < 6
             else NEW / f"kd_lr3e4_s{s}.json")
    else:
        p = BAL / f"kd_{arm}_s{s}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())["conditions"].get(c, {}).get("p99_abs_err")


def seeds_for(arm):
    return CTRL_SEEDS if arm == "raw" else ARM_SEEDS


def counts(arm, c="fog"):
    held = gate = n = void = 0
    for s in seeds_for(arm):
        x = cell(arm, s, c)
        if x is None:
            continue
        if x["state"] != "OK":
            void += x["state"] == "VOID"
            continue
        n += 1
        held += x["held"] == x["n"]
        gate += x["gate"] == x["n"]
    return held, gate, n, void


def vals(arm, c="fog"):
    return [x["hi"] for s in seeds_for(arm)
            if (x := cell(arm, s, c)) and x.get("state") == "OK"]


def table(c):
    print(f"=== {c}, worst-of-3 max|CTE| (ft) ===")
    width = max(len(list(seeds_for(a))) for a in ("raw", "bal", "curv"))
    print(f"{'arm':>5s}  " + "".join(f"{'s'+str(s):>8s}" for s in range(width)) +
          f"{'median':>9s}{'held':>8s}{'VOID':>6s}")
    for arm in ("raw", "bal", "curv"):
        row = ""
        for s in range(width):
            if s not in seeds_for(arm):
                row += f"{'':>8s}"
                continue
            x = cell(arm, s, c)
            if x is None:
                row += f"{'--':>8s}"
            elif x["state"] != "OK":
                row += f"{x['state']:>8s}"
            else:
                row += f"{x['hi']:7.2f}{'D' if x['dep'] else ' '}"
        v = vals(arm, c)
        held, _, n, void = counts(arm, c)
        med = f"{st.median(v):9.2f}" if v else f"{'--':>9s}"
        print(f"{arm:>5s}  {row}{med}{held:>5d}/{n}{void:>6d}")
    print()


def hodges_lehmann(x, y, alpha=0.05):
    from scipy.stats import norm
    d = sorted(a - b for a in x for b in y)
    m, n = len(x), len(y)
    if not d:
        return None, None, None
    z = norm.ppf(1 - alpha / 2)
    k = int(round(m * n / 2 - z * ((m * n * (m + n + 1) / 12) ** 0.5)))
    k = max(1, min(k, m * n))
    return st.median(d), d[k - 1], d[m * n - k]


def main():
    from scipy.stats import fisher_exact, mannwhitneyu
    print("Q4 -- label balancing at n = 12. budget 2.19 ft. "
          "control = Q1's lr3e4 arm (raw, n = 15)\n")
    for c in ("fog", "clear"):
        table(c)

    print("=== fog KD p99 |err| (tolerance 0.0120), no simulator ===")
    for arm in ("raw", "bal", "curv"):
        v = [x for x in (kd(arm, s) for s in seeds_for(arm)) if x is not None]
        if v:
            print(f"{arm:>5s}  n={len(v):2d}  median {st.median(v):.4f}")
    print()

    hr, _, nr, vr = counts("raw")
    if nr < 2:
        print("control not available yet")
        return
    print("=== PRIMARY: seeds holding fog 3/3 under budget (Fisher exact) ===")
    for arm in ("bal", "curv"):
        h, _, n, _ = counts(arm)
        if n < 2:
            print(f"  {arm}: not enough measured cells yet")
            continue
        p = fisher_exact([[h, n - h], [hr, nr - hr]])[1]
        print(f"  {arm:>4s} {h}/{n}  vs raw {hr}/{nr}   Fisher p = {p:.4f}")
    print()

    print("=== SECONDARY ===")
    raw_fog = vals("raw")
    for arm in ("bal", "curv"):
        v = vals(arm)
        if len(v) < 2:
            continue
        hl, lo, hi = hodges_lehmann(raw_fog, v)
        mw = mannwhitneyu(raw_fog, v, alternative="two-sided")[1]
        print(f"  {arm:>4s} fog median {st.median(v):.2f} vs raw {st.median(raw_fog):.2f} ft"
              f"   HL {hl:+.2f} [{lo:+.2f}, {hi:+.2f}]   MW p = {mw:.4f}")
    rc = vals("raw", "clear")
    for arm in ("bal", "curv"):
        v = vals(arm, "clear")
        if v:
            h, _, n, _ = counts(arm, "clear")
            print(f"  {arm:>4s} clear median {st.median(v):.2f} vs raw "
                  f"{st.median(rc):.2f} ft   held {h}/{n}")
    print("\n  VOID counts (declared endpoint: an arm unmeasurable more often is worse)")
    for arm in ("raw", "bal", "curv"):
        vf = counts(arm, "fog")[3]
        vc = counts(arm, "clear")[3]
        print(f"    {arm:>4s}  fog {vf}  clear {vc}  total {vf + vc}")

    print("\n=== against the pre-registration ===")
    hb, _, nb, _ = counts("bal")
    if nb >= 2:
        # The prediction is a COUNT OF HOLDERS out of the 12 seeds attempted, not a
        # fraction of the measured ones. VOID cells are excluded from the denominator by
        # design (standing rule 3), so requiring 12 measured cells would score a VOID as
        # a falsification -- penalising the arm for a harness outcome and, worse, making
        # the prediction unfalsifiable-in-the-good-direction: an arm could hold every
        # seed it measured and still be marked FALSIFIED.
        n_attempted = len(list(ARM_SEEDS))
        p1 = hb >= 10
        print(f"  Q4-P1 bal holds fog 3/3 in >=10 of {n_attempted} seeds : "
              f"{hb} held, {nb} measured, {n_attempted - nb} VOID -> "
              f"{'HELD' if p1 else 'FALSIFIED'}")
        pb = fisher_exact([[hb, nb - hb], [hr, nr - hr]])[1]
        print(f"  Q4-P2 Fisher p < 0.05 vs control      : p = {pb:.4f} -> "
              f"{'HELD' if pb < 0.05 else 'FALSIFIED'}")
        bc, rcv = vals("bal", "clear"), rc
        if bc and rcv:
            ok = st.median(bc) <= st.median(rcv)
            print(f"  Q4-P3 bal clear median <= raw's       : {st.median(bc):.2f} vs "
                  f"{st.median(rcv):.2f} -> {'HELD' if ok else 'FALSIFIED'}")
        hc, _, nc, _ = counts("curv")
        if nc >= 2:
            ok = not (hc / nc > hb / nb)
            print(f"  Q4-P4 curv does not beat bal          : curv {hc}/{nc} vs bal "
                  f"{hb}/{nb} -> {'HELD' if ok else 'FALSIFIED'}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Summarise E2 (tail-sensitive distillation loss) against docs/E2_PREREGISTRATION.md.

Primary endpoint is fog p99 |err|, UNPAIRED (Mann-Whitney). Amendment A-1: re-distilling
the same seed with the same objective moved fog p99 by +38.9%, so seed matching carries no
information and the paired test assumes something known to be false. The paired result is
printed anyway, labelled, because the pre-registration promised it.

Cells whose 3 laps disagree by >25% are VOID (standing rule 3) and are excluded rather
than averaged -- E1b established what those cells are.
"""
import json
import pathlib
import statistics as st

import os
# E2_DIR selects which run to summarise: the original unpinned sweep, or the
# deterministic paired re-run (amendment A-2). Defaults to the original.
D = (pathlib.Path(__file__).resolve().parent.parent /
     os.environ.get("E2_DIR", "results/town06/tail_loss"))
ALPHAS = ["0.0", "2.0", "8.0"]
SEEDS = [0, 1, 2, 3, 4, 5]
BUDGET = 2.19
VOID_REL = 0.25


def tag(a):
    return a.replace(".", "p")


def kd(a, s, cond, field="p99_abs_err"):
    p = D / f"kd_a{tag(a)}_s{s}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    return d["conditions"].get(cond, {}).get(field)


def cell(a, s, cond):
    p = D / f"e2_a{tag(a)}_s{s}_{cond}.json"
    if not p.exists():
        return None
    laps = [l for l in list(json.loads(p.read_text())["results"].values())[0]
            if not l.get("error")]
    if not laps:
        return {"state": "NO_LAPS"}
    v = [l["max_cte_ft"] for l in laps]
    lo, hi = min(v), max(v)
    if hi > 0 and (hi - lo) / hi > VOID_REL:
        return {"state": "VOID"}
    return {"state": "OK", "hi": hi, "n": len(laps),
            "held": sum(1 for x in v if x <= BUDGET),
            "departed": sum(1 for l in laps if l.get("departed"))}


def col(vals):
    return "  ".join(f"{v:6.4f}" if v is not None else "   --  " for v in vals)


def main():
    try:
        from scipy.stats import mannwhitneyu, wilcoxon
    except Exception:
        mannwhitneyu = wilcoxon = None

    print("E2 -- tail-sensitive distillation loss\n")
    for cond in ("fog", "clear"):
        print(f"=== KD p99 |err|, {cond} (tolerance 0.0120) ===")
        print(f"{'alpha':>6s}  " + "  ".join(f"{'s'+str(s):>6s}" for s in SEEDS) +
              f"  {'median':>8s}")
        for a in ALPHAS:
            v = [kd(a, s, cond) for s in SEEDS]
            got = [x for x in v if x is not None]
            med = f"{st.median(got):8.4f}" if got else f"{'--':>8s}"
            print(f"{a:>6s}  {col(v)}  {med}")
        print()

    print("=== closed loop, worst-of-3 max|CTE| (budget 2.19 ft) ===")
    for cond in ("fog", "clear"):
        print(f"  {cond}")
        print(f"{'alpha':>6s}  " + "  ".join(f"{'s'+str(s):>7s}" for s in SEEDS) +
              f"  {'held':>6s}")
        for a in ALPHAS:
            row, held, n = "", 0, 0
            for s in SEEDS:
                c = cell(a, s, cond)
                if c is None:
                    row += f"{'--':>9s}"
                elif c["state"] != "OK":
                    row += f"{c['state']:>9s}"
                else:
                    row += f"{c['hi']:8.2f}{'D' if c['departed'] else ' '}"
                    n += 1
                    held += 1 if c["held"] == c["n"] else 0
            print(f"{a:>6s}  {row}  {held:>3d}/{n}")
        print()

    print("=== against the pre-registration ===")
    base = [x for x in (kd("0.0", s, "fog") for s in SEEDS) if x is not None]
    for a in ("2.0", "8.0"):
        arm = [x for x in (kd(a, s, "fog") for s in SEEDS) if x is not None]
        if not (base and arm):
            print(f"C1 alpha {a}: incomplete")
            continue
        line = (f"C1 fog p99: baseline median {st.median(base):.4f} -> "
                f"alpha {a} median {st.median(arm):.4f} "
                f"({(st.median(arm)-st.median(base))/st.median(base)*100:+.1f}%)")
        if mannwhitneyu and len(base) >= 3 and len(arm) >= 3:
            u, p = mannwhitneyu(arm, base, alternative="two-sided")
            line += f"   Mann-Whitney p={p:.3f}"
        print(line)
        # paired, reported because promised, and labelled
        pairs = [(kd(a, s, "fog"), kd("0.0", s, "fog")) for s in SEEDS]
        pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
        if wilcoxon and len(pairs) >= 5:
            try:
                _, pw = wilcoxon([x - y for x, y in pairs])
                better = sum(1 for x, y in pairs if x < y)
                print(f"   [paired, ASSUMPTION KNOWN FALSE per amendment A-1] "
                      f"{better}/{len(pairs)} seeds improved, Wilcoxon p={pw:.3f}")
            except Exception:
                pass

    held = {}
    for a in ALPHAS:
        cs = [cell(a, s, "fog") for s in SEEDS]
        held[a] = sum(1 for c in cs if c and c.get("state") == "OK"
                      and c["held"] == c["n"])
    print(f"\nC2 seeds holding fog 3/3: " +
          ", ".join(f"alpha {a} = {held[a]}" for a in ALPHAS))
    if held["0.0"] is not None:
        gain = max(held[a] for a in ("2.0", "8.0")) - held["0.0"]
        print(f"   best arm gains {gain:+d} over baseline -> C2 (predicting <= +1) "
              f"{'held' if gain <= 1 else 'FALSIFIED'}")
        print("   NOTE: underpowered by design and pre-registered as such "
              "(2/6 vs 4/6 is Fisher p~0.57).")

    b_clear = [x for x in (kd("0.0", s, "clear") for s in SEEDS) if x is not None]
    a8 = [x for x in (kd("8.0", s, "clear") for s in SEEDS) if x is not None]
    if b_clear and a8:
        worse = sum(1 for x, y in zip(a8, b_clear) if x > y)
        print(f"\nC3 clear p99 worse at alpha 8.0 in {worse}/{min(len(a8),len(b_clear))} "
              f"seeds -> C3 {'held' if worse > len(b_clear)/2 else 'FALSIFIED'}")

    spreads, meds = {}, {}
    for a in ALPHAS:
        v = [c["hi"] for s in SEEDS if (c := cell(a, s, "fog")) and c.get("state") == "OK"]
        if v:
            spreads[a] = max(v) - min(v)
            meds[a] = st.median(v)
    if len(meds) >= 2:
        between = max(meds.values()) - min(meds.values())
        within = max(spreads.values())
        print(f"\nC4 largest within-alpha seed spread {within:.2f} ft vs "
              f"between-alpha median difference {between:.2f} ft "
              f"-> C4 {'held' if within > between else 'FALSIFIED'}")


if __name__ == "__main__":
    main()

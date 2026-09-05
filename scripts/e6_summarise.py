#!/usr/bin/env python3
"""Summarise E6 (label balancing) against docs/E6_PREREGISTRATION.md, amendment A-1.

Arms, all at lr 3e-4 with kernels pinned:
  raw   plain MSE                        (E4's d3lr3 arm, results/town06/depth)
  bal   --balance downsampling           (results/town06/balancing)
  curv  DISTILL_CURV_BETA=4.0 weighting  (results/town06/balancing)

VOID cells (>25% lap disagreement) are excluded, not averaged (standing rule 3).
"""
import json
import pathlib
import statistics as st

REPO = pathlib.Path(__file__).resolve().parent.parent
BAL = REPO / "results/town06/balancing"
DEPTH = REPO / "results/town06/depth"
BUDGET, GATE, VOID_REL = 2.19, 1.095, 0.25
SEEDS = range(6)
ARMS = [("raw", DEPTH, "drive_d3lr3_s{s}_{c}.json", "kd_d3lr3_s{s}.json"),
        ("bal", BAL, "drive_bal_s{s}_{c}.json", "kd_bal_s{s}.json"),
        ("curv", BAL, "drive_curv_s{s}_{c}.json", "kd_curv_s{s}.json")]


def cell(d, pat, s, c):
    p = d / pat.format(s=s, c=c)
    if not p.exists():
        return None
    laps = [l for l in list(json.loads(p.read_text())["results"].values())[0]
            if not l.get("error")]
    if not laps:
        return {"state": "NO_LAPS"}
    v = [l["max_cte_ft"] for l in laps]
    if max(v) > 0 and (max(v) - min(v)) / max(v) > VOID_REL:
        return {"state": "VOID"}
    return {"state": "OK", "hi": max(v), "n": len(laps),
            "held": sum(1 for x in v if x <= BUDGET),
            "gate": sum(1 for x in v if x <= GATE),
            "dep": sum(1 for l in laps if l.get("departed"))}


def main():
    print("E6 -- label balancing at lr 3e-4. budget 2.19 ft, margin gate 1.095 ft\n")
    meds = {}
    for c in ("fog", "clear"):
        print(f"=== {c}, worst-of-3 max|CTE| ===")
        print(f"{'arm':>5s}  " + "".join(f"{'s'+str(s):>9s}" for s in SEEDS) +
              f"{'median':>9s}{'held':>7s}{'gate':>6s}")
        for name, d, dp, _ in ARMS:
            row, vals, held, gate, n = "", [], 0, 0, 0
            for s in SEEDS:
                x = cell(d, dp, s, c)
                if x is None:
                    row += f"{'--':>9s}"
                elif x["state"] != "OK":
                    row += f"{x['state']:>9s}"
                else:
                    row += f"{x['hi']:8.2f}{'D' if x['dep'] else ' '}"
                    vals.append(x["hi"]); n += 1
                    held += x["held"] == x["n"]; gate += x["gate"] == x["n"]
            med = f"{st.median(vals):9.2f}" if vals else f"{'--':>9s}"
            if c == "fog":
                meds[name] = (st.median(vals) if vals else None, held, n, vals)
            print(f"{name:>5s}  {row}{med}{held:>4d}/{n}{gate:>4d}/{n}")
        print()

    print("=== against the pre-registration ===")
    raw = meds.get("raw", (None,))[0]
    for a in ("bal", "curv"):
        m, held, n, vals = meds.get(a, (None, 0, 0, []))
        if m is None or raw is None:
            print(f"  {a}: incomplete"); continue
        print(f"  {a}: fog median {m:.2f} ft vs raw {raw:.2f} ({(m-raw)/raw*100:+.0f}%), "
              f"held {held}/{n} vs raw {meds['raw'][1]}/{meds['raw'][2]}")
    g1 = meds.get("bal", (None,))[0]
    if g1 and raw:
        print(f"  G1 (bal does not improve fog by >25%): "
              f"{'FALSIFIED' if g1 < raw * 0.75 else 'held'}")
    try:
        from scipy.stats import mannwhitneyu
        for a in ("bal", "curv"):
            if meds.get(a, (None,))[3] and meds["raw"][3]:
                p = mannwhitneyu(meds[a][3], meds["raw"][3], alternative="two-sided")[1]
                print(f"     {a} vs raw: Mann-Whitney p = {p:.3f}")
    except Exception:
        pass
    print("\n  G5 reference: the learning rate moved the fog median 11.79 -> 1.91 ft (9.88 ft).")


if __name__ == "__main__":
    main()

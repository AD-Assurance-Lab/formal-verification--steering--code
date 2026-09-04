#!/usr/bin/env python3
"""Summarise E4 (depth, and the learning rate found while getting there).

Three arms, per docs/E4_PREREGISTRATION.md amendment A-2:
  d3@1e-3  the shipped recipe   (results/town06/tail_loss_det, E2's alpha 0.0 arm)
  d3@3e-4  the tuned recipe, same architecture   (results/town06/depth, d3lr3)
  d5@1e-4  depth, at its own best recipe          (results/town06/depth, d5lr1)

VOID cells (>25% lap disagreement) are excluded rather than averaged -- standing rule 3,
and E1b established what those cells are.
"""
import json
import pathlib
import statistics as st

REPO = pathlib.Path(__file__).resolve().parent.parent
DEPTH = REPO / "results/town06/depth"
BASE = REPO / "results/town06/tail_loss_det"
BUDGET, MARGIN_GATE, VOID_REL = 2.19, 1.095, 0.25
SEEDS = range(6)
ARMS = [("d3@1e-3", BASE, "e2_a0p0_s{s}_{c}.json", "kd_a0p0_s{s}.json"),
        ("d3@3e-4", DEPTH, "drive_d3lr3_s{s}_{c}.json", "kd_d3lr3_s{s}.json"),
        ("d5@1e-4", DEPTH, "drive_d5lr1_s{s}_{c}.json", "kd_d5lr1_s{s}.json")]


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
            "gate": sum(1 for x in v if x <= MARGIN_GATE),
            "dep": sum(1 for l in laps if l.get("departed"))}


def kd(d, pat, s, c="fog"):
    p = d / pat.format(s=s)
    if not p.exists():
        return None
    return json.loads(p.read_text())["conditions"].get(c, {}).get("p99_abs_err")


def main():
    print("E4 -- depth, and the learning rate. budget 2.19 ft; pass-3 margin gate 1.095 ft\n")
    for c in ("fog", "clear"):
        print(f"=== {c}, worst-of-3 max|CTE| ===")
        print(f"{'arm':>9s}  " + "".join(f"{'s'+str(s):>9s}" for s in SEEDS) +
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
                    held += x["held"] == x["n"]
                    gate += x["gate"] == x["n"]
            med = f"{st.median(vals):9.2f}" if vals else f"{'--':>9s}"
            print(f"{name:>9s}  {row}{med}{held:>4d}/{n}{gate:>4d}/{n}")
        print()

    print("=== fog KD p99 |err| (tolerance 0.0120) ===")
    for name, d, _, kp in ARMS:
        v = [x for x in (kd(d, kp, s) for s in SEEDS) if x is not None]
        if v:
            print(f"{name:>9s}  " + "  ".join(f"{x:.4f}" for x in v) +
                  f"   median {st.median(v):.4f}")

    print("\n=== against the pre-registration ===")
    def fogvals(d, dp):
        return [x["hi"] for s in SEEDS
                if (x := cell(d, dp, s, "fog")) and x.get("state") == "OK"]
    a = {n: fogvals(d, dp) for n, d, dp, _ in ARMS}
    if all(a.values()):
        m = {k: st.median(v) for k, v in a.items()}
        print(f"  fog median: shipped {m['d3@1e-3']:.2f} | tuned {m['d3@3e-4']:.2f} "
              f"| deeper {m['d5@1e-4']:.2f} ft")
        lr_effect = m["d3@1e-3"] - m["d3@3e-4"]
        depth_effect = m["d3@3e-4"] - m["d5@1e-4"]
        print(f"  F5: learning-rate effect {lr_effect:+.2f} ft vs depth effect "
              f"{depth_effect:+.2f} ft -> F5 "
              f"{'held' if abs(lr_effect) > abs(depth_effect) else 'FALSIFIED'}")
        try:
            from scipy.stats import mannwhitneyu
            for x, y in (("d3@1e-3", "d3@3e-4"), ("d3@3e-4", "d5@1e-4")):
                p = mannwhitneyu(a[x], a[y], alternative="two-sided")[1]
                print(f"     {x} vs {y}: Mann-Whitney p = {p:.3f}")
        except Exception:
            pass


if __name__ == "__main__":
    main()

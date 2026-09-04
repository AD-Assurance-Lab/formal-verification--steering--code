#!/usr/bin/env python3
"""Summarise the E1 resolution ablation and score it against its pre-registration.

    python3 scripts/e1_summarise.py

Reads results/town06/res_ablation/e1_<WxH>_s<seed>_<cond>.json and reports every seed,
never just the best one. docs/E1_PREREGISTRATION.md holds P1-P4; this prints the evidence
for each and does not decide them for you.

Two rules from the workspace standing rules are enforced here rather than left to the
reader:

  * a cell whose laps DISAGREE is VOID, not uncertain (rule 3). It is not averaged into a
    rate, because that turns an identified defect into a plausible failure rate and loses
    it. VOID cells are excluded from best/worst and counted separately.
  * a run that ends in far fewer steps than the lap is a BUG, not a pass (R-SIM-6). Short
    laps are flagged; a "pass" built on one is not a pass.
"""
import json
import pathlib
import sys

D = pathlib.Path(__file__).resolve().parent.parent / "results" / "town06" / "res_ablation"
RESOLUTIONS = ["84x28", "168x28", "168x56", "252x84"]
SEEDS = [0, 1, 2, 3, 4, 5]
CONDS = ["fog", "clear"]
BUDGET = 2.19

# Laps of one cell disagreeing by more than this (relative) makes the cell VOID. The
# corrected harness measured 0/48 rep-to-rep verdict disagreement, so genuine spread
# within a cell means something is wrong, not that the model is marginal.
VOID_REL = 0.25
SHORT_LAP_FRAC = 0.80          # of full_steps; below this the lap did not finish


def cell(wh, seed, cond):
    p = D / f"e1_{wh}_s{seed}_{cond}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    laps = [l for l in list(d["results"].values())[0] if not l.get("error")]
    if not laps:
        return {"state": "NO_LAPS"}
    cte = [l["max_cte_ft"] for l in laps]
    # A short lap that DEPARTED is a real failure -- the run ended because the car left
    # the road, which is the outcome being measured. A short lap that did NOT depart is
    # the R-SIM-6 bug: three separate attempts at the section-end distance cap ended runs
    # after 3-5 steps and reported a tiny |CTE| as a PASS. Only the second is suspicious,
    # and conflating them flags every genuine departure as a possible harness fault.
    short = [l for l in laps
             if l.get("full_steps") and l["steps"] < SHORT_LAP_FRAC * l["full_steps"]
             and not l.get("departed")]
    departed = [l for l in laps if l.get("departed")]
    lo, hi = min(cte), max(cte)
    void = hi > 0 and (hi - lo) / max(hi, 1e-9) > VOID_REL
    return {"state": "VOID" if void else "OK", "n": len(laps), "lo": lo, "hi": hi,
            "held": sum(1 for l in laps if l["max_cte_ft"] <= BUDGET),
            "short": len(short), "departed": len(departed)}


def main():
    if not D.exists():
        sys.exit(f"no results at {D}")
    print(f"E1 resolution ablation -- budget {BUDGET} ft, worst-of-3 laps per cell")
    print("   D = the car departed the road (a real failure); "
          "! = lap ended short WITHOUT departing (suspect, R-SIM-6)\n")
    summary = {}
    for cond in CONDS:
        print(f"=== {cond} ===")
        print(f"{'input':>8s} " + "".join(f"{'s'+str(s):>10s}" for s in SEEDS) +
              f"{'best':>9s}{'worst':>9s}{'held':>7s}")
        for wh in RESOLUTIONS:
            cells = {s: cell(wh, s, cond) for s in SEEDS}
            row = ""
            vals = []
            held = 0
            for s in SEEDS:
                c = cells[s]
                if c is None:
                    row += f"{'--':>10s}"
                elif c["state"] != "OK":
                    row += f"{c['state']:>10s}"
                else:
                    # ! = short WITHOUT departing (suspect, R-SIM-6); D = departed.
                    flag = "!" if c["short"] else ("D" if c["departed"] else "")
                    row += f"{c['hi']:>9.2f}{flag:<1s}"
                    vals.append(c["hi"])
                    held += 1 if c["held"] == c["n"] else 0
            best = f"{min(vals):9.2f}" if vals else f"{'--':>9s}"
            worst = f"{max(vals):9.2f}" if vals else f"{'--':>9s}"
            print(f"{wh:>8s} {row}{best}{worst}{held:>5d}/{len(vals) if vals else 0}")
            summary[(cond, wh)] = vals
        print()

    print("=== against the pre-registration ===")
    fog = {wh: summary.get(("fog", wh), []) for wh in RESOLUTIONS}
    clear = {wh: summary.get(("clear", wh), []) for wh in RESOLUTIONS}

    have = [wh for wh in RESOLUTIONS if fog[wh]]
    if len(have) == len(RESOLUTIONS):
        order = [min(fog[wh]) for wh in RESOLUTIONS]
        mono = all(order[i] < order[i + 1] for i in range(len(order) - 1))
        print(f"P1 monotone fog (best-of-seeds, low->high res): {[f'{o:.2f}' for o in order]}")
        print(f"   ordered increasing with resolution: {mono}  "
              f"-> P1 (predicting NOT monotone) {'FALSIFIED' if mono else 'held'}")
        b = min(fog['84x28'])
        print(f"   84x28 best-of-seeds fog {b:.2f} ft "
              f"{'>' if b > BUDGET else '<='} budget {BUDGET} "
              f"-> D-14 transfer {'refuted' if b > BUDGET else 'SUPPORTED'}")
    else:
        print(f"P1: incomplete -- fog measured at {have}")

    # A verdict on partial data is worse than no verdict: it reads as a result. Every
    # check below refuses until it has the cells it needs.
    n_fog_cells = sum(len(fog[wh]) for wh in RESOLUTIONS)
    if n_fog_cells >= len(RESOLUTIONS) * len(SEEDS):
        n_hold = sum(1 for wh in RESOLUTIONS for s in SEEDS
                     if (c := cell(wh, s, "fog")) and c.get("state") == "OK"
                     and c["held"] == c["n"])
        print(f"P2 cells holding fog 3/3 under budget: {n_hold} "
              f"-> P2 (predicting none) {'held' if n_hold == 0 else 'FALSIFIED'}")
    else:
        n_hold = sum(1 for wh in RESOLUTIONS for s_ in SEEDS
                     if (c := cell(wh, s_, "fog")) and c.get("state") == "OK"
                     and c["held"] == c["n"])
        print(f"P2: incomplete ({n_fog_cells} fog cells so far); "
              f"{n_hold} holding 3/3 -- P2 already FALSIFIED" if n_hold else
              f"P2: incomplete ({n_fog_cells} fog cells so far), none holding 3/3 yet")

    if len(clear["84x28"]) >= 3 and len(clear["168x56"]) >= 3:
        a, b = min(clear["84x28"]), min(clear["168x56"])
        print(f"P3 clear best-of-seeds: 84x28 {a:.2f} ft vs 168x56 {b:.2f} ft "
              f"-> P3 (predicting 84x28 worse) {'held' if a > b else 'FALSIFIED'}")

    spreads = {wh: (max(fog[wh]) / min(fog[wh])) for wh in RESOLUTIONS
               if len(fog[wh]) >= 3 and min(fog[wh]) > 0}
    if not spreads:
        print("P4: incomplete -- needs >=3 seeds at some resolution")
    else:
        w, r = max(spreads.items(), key=lambda kv: kv[1])
        done = all(len(fog[wh]) >= len(SEEDS) for wh in RESOLUTIONS)
        print(f"P4 largest within-resolution seed spread: {r:.2f}x at {w} "
              f"-> P4 (predicting >2x somewhere) "
              f"{'held' if r > 2 else ('FALSIFIED' if done else 'not yet, sweep incomplete')}")

    voids = [(wh, s, c) for wh in RESOLUTIONS for s in SEEDS for c in CONDS
             if (x := cell(wh, s, c)) and x.get("state") not in ("OK", None)]
    if voids:
        print(f"\nVOID/unmeasured cells ({len(voids)}) -- these are BUGS to chase, "
              f"not uncertainty to average away:")
        for wh, s, c in voids:
            print(f"    {wh} s{s} {c}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Summarise Q2 -- the pass-3 gate, unchanged, at the tuned recipe.

docs/Q2_PREREGISTRATION.md declares the analysis:

  primary     per candidate, how many of the 12 gate laps (4 conditions x 3) are at or
              under 1.095 ft (0.5 x the 2.19 ft budget), and whether it passes outright.
  secondary   per-condition worst-of-3, and WHICH condition stops each failing candidate.

The gate is pass 3's, run by the same committed driver with the same MARGIN_FRAC=0.5.
Only the candidate changes -- a gate that moved with the candidate would prove nothing.

`select_student_seed.sh` screens on ONE lap per condition at the full budget before
spending three, and breaks out of the screen at the first condition a candidate cannot
hold. So a candidate rejected at the screen has NO gate laps, and this reports it as
"screened out at <condition>" rather than as 0/12 -- an unmeasured lap is not a failing
lap (standing rule 8).

    python3 scripts/q2_summarise.py
"""
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT = REPO / "results/town06/tuned_gate"
BUDGET, GATE = 2.1916011199999996, 1.0958005599999998
CONDS = ["clear", "fog", "night", "low_sun"]
VOID_REL = 0.25

# The five Q1 candidates, in the declared ascending-seed order, with the checkpoint each
# resolves to. Seeds 0-5 came from E4's arm, 6-14 from Q1's own sweep.
CANDIDATES = [(0, "S_mixed_depth_d3lr3_s0"), (3, "S_mixed_depth_d3lr3_s3"),
              (5, "S_mixed_depth_d3lr3_s5"), (7, "S_mixed_lr_lr3e4_s7"),
              (12, "S_mixed_lr_lr3e4_s12")]


def laps(kind, ck, cond):
    p = OUT / f"seed_{kind}_{ck}_{cond}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    return [l for l in list(d["results"].values())[0] if not l.get("error")]


def worst(ls):
    return max(l["max_cte_ft"] for l in ls) if ls else None


def void(ls):
    if not ls or len(ls) < 2:
        return False
    v = [l["max_cte_ft"] for l in ls]
    return max(v) > 0 and (max(v) - min(v)) / max(v) > VOID_REL


def main():
    print("Q2 -- pass 3's gate at the tuned recipe (lr 3e-4).")
    print(f"budget {BUDGET:.2f} ft; GATE = 0.5 x budget = {GATE:.4f} ft; 3 laps x 4 conditions\n")

    print(f"{'seed':>5s} {'checkpoint':>24s}  " +
          "".join(f"{c:>10s}" for c in CONDS) + f"{'gate':>8s}{'verdict':>22s}")
    any_pass = False
    # Which conditions fail the margin gate, per CONDITION. NOT "the first failing
    # condition per candidate": CONDS is iterated in a fixed order, so recording only
    # the first would systematically credit whichever condition is listed first (here
    # `clear`) and could report fog as no longer the stopper while fog was failing every
    # single candidate. That is precisely the question Q2-P3 asks, so getting it from
    # list order would have answered it backwards.
    fails = {c: [] for c in CONDS}
    for seed, ck in CANDIDATES:
        cells, held, total, screened_out = [], 0, 0, None
        for c in CONDS:
            g = laps("gate", ck, c)
            if g is None:
                s = laps("screen", ck, c)
                if s is None:
                    cells.append(f"{'--':>10s}")
                    continue
                w = worst(s)
                cells.append(f"{w:9.2f}s")          # s = screen lap, not a gate lap
                if w is not None and w > BUDGET and screened_out is None:
                    screened_out = c
                continue
            w = worst(g)
            n = sum(1 for l in g if l["max_cte_ft"] <= GATE)
            held += n
            total += len(g)
            mark = "V" if void(g) else " "
            cells.append(f"{w:9.2f}{mark}")
            if n < len(g):
                fails[c].append(seed)
        if screened_out:
            verdict = f"screened out at {screened_out}"
        elif total == 0:
            verdict = "not run"
        elif held == total == 12:
            verdict = "*** PASSES THE GATE ***"
            any_pass = True
        else:
            verdict = "fails"
        print(f"{seed:>5d} {ck:>24s}  " + "".join(cells) +
              f"{held:>5d}/{total:<3d}{verdict:>22s}")

    print("\n  s = screen lap (1 lap at full budget), V = VOID (>25% lap disagreement)")

    print("\n=== against the pre-registration ===")
    # Q2-P1: at least one candidate holds fog 3/3 under the MARGIN.
    fog_ok = []
    for seed, ck in CANDIDATES:
        g = laps("gate", ck, "fog")
        if g and all(l["max_cte_ft"] <= GATE for l in g):
            fog_ok.append(seed)
    ran = any(laps("gate", ck, c) for _, ck in CANDIDATES for c in CONDS)
    if not ran:
        print("  no gate laps recorded yet -- nothing to score")
        return
    print(f"  Q2-P1 >=1 candidate holds fog 3/3 under {GATE:.3f} ft : "
          f"{fog_ok if fog_ok else 'none'} -> {'HELD' if fog_ok else 'FALSIFIED'}")
    print(f"  Q2-P2 no candidate passes all four 12/12          : "
          f"{'FALSIFIED -- REPORT IMMEDIATELY' if any_pass else 'HELD'}")
    gated = [s_ for s_, ck in CANDIDATES if laps("gate", ck, "fog") is not None]
    if gated:
        n = len(gated)
        detail = ", ".join(f"{c} {len(fails[c])}/{n}" for c in CONDS)
        # P3 predicted fog would stop a MINORITY. It is falsified if fog still fails
        # more candidates than any other condition.
        worst_c = max(CONDS, key=lambda c: len(fails[c]))
        print(f"  Q2-P3 fog is NOT the stopping condition for most : {detail} -> "
              f"{'FALSIFIED' if worst_c == 'fog' else 'HELD'}")
        universal = [c for c in CONDS if len(fails[c]) == n]
        if universal:
            print(f"        conditions failing EVERY gated candidate: {universal}")
        # Margin vs budget: a gate failure at 50% of budget is not a departure.
        under_budget = all(
            l["max_cte_ft"] <= BUDGET
            for _, ck in CANDIDATES for c in CONDS
            for l in (laps("gate", ck, c) or []))
        print(f"        every gated lap within the {BUDGET:.2f} ft BUDGET: {under_budget}")
    else:
        print("  Q2-P3 no failing gate cells recorded yet")


if __name__ == "__main__":
    main()

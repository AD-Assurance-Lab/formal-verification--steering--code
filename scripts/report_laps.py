#!/usr/bin/env python3
"""Report a ledger at LAP granularity (PROTOCOL A-4), with margins.

A lap is one traversal of all the unique scored road -- Town04's is eastbound +
westbound, Town06's is the loop -- and a lap FAILS if any scored span departs. The
ledger's per-run artifacts are the raw material; this reassembles them into laps.

Two things it reports that a pass/fail bit cannot:

  margin   how close the worst span came to the budget, as a percentage of it. A cell
           that passes with every span far below budget and one that passes at 1% of
           budget are different results, and a cell with no margin is a finding.
  agree    whether the three laps agreed with each other. Under an enforced harness they
           do (0 of 48 section-pairs disagreed when this was measured). Disagreement is a
           BUG until proven otherwise and VOIDS the cell -- it is never answered with
           more laps.

    STUDY_MAP=Town04 TOWN04_REDO=1 python3 scripts/report_laps.py
"""
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
import config as C                                            # noqa: E402

STANDARD_LAPS = 3


def main():
    led = Path(C.LEDGER_DIR)
    budget_ft = C.CTE_BUDGET_M * C.M_TO_FT
    runs = defaultdict(lambda: defaultdict(dict))
    for f in glob.glob(str(led / "runs" / "*.json")):
        d = json.load(open(f)); r = d["run"]
        runs[(d["condition"], d["student"])][r["rep"]][r["direction"]] = r
    if not runs:
        print(f"no per-run artifacts in {led/'runs'}", file=sys.stderr)
        return 2

    print(f"\n{C.STUDY_MAP} LEDGER -- LAPS (PROTOCOL A-4)")
    print(f"  a lap is one traversal of all the scored road, and fails if any part of it "
          f"departs")
    print(f"  budget {budget_ft:.2f} ft;  standard is {STANDARD_LAPS} laps\n")
    print(f"  {'condition':9s} {'student':26s} {'laps failed':>12s} {'verdict':8s} "
          f"{'worst':>8s} {'margin':>8s}")
    print("  " + "-" * 80)
    out = {}
    for (cond, stu) in sorted(runs):
        laps = []
        for rep in sorted(runs[(cond, stu)]):
            spans = runs[(cond, stu)][rep]
            if len(spans) < len(C.SECTIONS):
                continue                      # incomplete lap: not a lap
            worst = max(s["max_cte_m"] for s in spans.values()) * C.M_TO_FT
            ok = all(s["passed"] for s in spans.values())
            laps.append((rep, ok, worst))
        if not laps:
            continue
        n = len(laps)
        fails = sum(1 for _, ok, _ in laps if not ok)
        verdict = "FAIL" if fails else "PASS"
        worst_overall = max(w for _, _, w in laps)
        margin = (budget_ft - worst_overall) / budget_ft
        agree = len({ok for _, ok, _ in laps}) == 1
        first = {ok for _, ok, _ in laps[:STANDARD_LAPS]}
        first_same = (len(first) == 1) and (("FAIL" if not first.pop() else "PASS") == verdict)
        flag = ""
        if not agree:
            flag = "  <-- LAPS DISAGREE: cell is VOID, find the bug (A-4)"
        elif 0 <= margin < 0.10:
            flag = "  <-- NO MARGIN: a finding in itself"
        print(f"  {cond:9s} {stu:26s} {fails:6d} of {n:2d} {verdict:8s} "
              f"{worst_overall:6.2f} ft {margin*100:7.1f}%{flag}")
        out[f"{cond}/{stu}"] = dict(laps=n, failed=fails, verdict=verdict,
                                    worst_span_ft=worst_overall, margin_frac=margin,
                                    laps_agree=agree, first3_same_verdict=first_same)
    (led / "lap_report.json").write_text(json.dumps(out, indent=2))
    print(f"\n  -> {led/'lap_report.json'}")
    print("  worst  = the largest |CTE| anywhere in the worst lap")
    print("  margin = how far that stayed below budget; negative means it exceeded it.")
    print("  Span-level detail is in the artifact, for when a specific nuance needs it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Build a ledger CELL from the per-run artifacts written by one-process-per-run drives.

Each run is now its own process with its own CARLA server (R-SIM-1 at the granularity the
rule states) and its own vehicle, so no run can inherit a socket, a thread or a physics
state from the one before. That independence is exactly what the Wilson interval assumes
and what the previous ledger did not have: it restarted per CELL and reused one vehicle
for all twelve runs, making the twelve repetitions two chains of six.

This reassembles the cell without changing what a cell means -- same verdict rule (FAIL
when the interval excludes zero), same fields -- so a rebuilt cell is comparable to the
one it replaces.

    STUDY_MAP=Town06 python3 scripts/aggregate_ledger_runs.py \
        --condition clear --cell S_clear_t06_168x28_w2 --expect 12
"""
import argparse
import datetime
import glob
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "scripts"))
import config as C                                            # noqa: E402
from closed_loop_ledger import wilson, LEDGER                 # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", required=True)
    ap.add_argument("--cell", required=True)
    ap.add_argument("--expect", type=int, required=True,
                    help="RUN artifacts expected (laps x spans). The cell is REFUSED if "
                         "fewer are present: a verdict over a partial set of laps reads "
                         "exactly like the real one")
    args = ap.parse_args()

    pat = str(LEDGER / "runs" / f"{args.condition}__{args.cell}__*.json")
    files = sorted(glob.glob(pat))
    if len(files) != args.expect:
        print(f"REFUSING to write a cell: {len(files)} run artifact(s) for "
              f"{args.condition}/{args.cell}, expected {args.expect}.\n"
              f"  A failure rate over a partial set reads exactly like the real one.",
              file=sys.stderr)
        return 2

    runs, prov, ck, student = [], None, None, None
    for f in files:
        d = json.load(open(f))
        runs.append(d["run"])
        prov = prov or d.get("provenance", {})
        ck = ck or d.get("checkpoint")
        student = student or d.get("student")
    runs.sort(key=lambda r: (r.get("rep", 0), str(r.get("direction"))))

    # THE LAP IS THE UNIT (PROTOCOL A-4).
    #
    # This counted RUNS and put a Wilson interval over them, which is the framing A-4
    # replaced: runs are different pieces of road, so a rate over them pools unlike units
    # and reads misleadingly -- two cells once reported "2/12 = 17%" when the same span
    # failed in both passes, which is every attempt failing.
    #
    # A lap fails if any part of it departs. Three laps is a reproducibility check, so the
    # cell verdict is what the laps AGREE on; if they disagree the cell is VOID until the
    # cause is found, and is never resolved by driving more laps.
    spans = sorted({str(r["direction"]) for r in runs})
    by_lap = {}
    for r in runs:
        by_lap.setdefault(r["rep"], {})[str(r["direction"])] = r
    laps = []
    for rep in sorted(by_lap):
        if sorted(by_lap[rep]) != spans:
            continue                     # a partial lap is not a lap
        laps.append(dict(lap=rep,
                         passed=all(x["passed"] for x in by_lap[rep].values()),
                         worst_cte_m=max(x["max_cte_m"] for x in by_lap[rep].values())))
    n = len(laps)
    fails = sum(1 for l in laps if not l["passed"])
    rate = fails / n if n else 0.0
    lo, hi = wilson(fails, n)
    if n and len({l["passed"] for l in laps}) > 1:
        verdict = "VOID"                 # laps disagree: a bug until proven otherwise
    else:
        verdict = "FAIL" if fails else "PASS"

    prov = dict(prov or {})
    prov["independent_runs"] = True
    prov["restart_granularity"] = "per_run_process"
    prov["aggregated_at"] = datetime.datetime.now().astimezone().isoformat(
        timespec="seconds")

    LEDGER.mkdir(parents=True, exist_ok=True)
    path = LEDGER / f"{args.condition}__{args.cell}__closed_loop.json"
    worst = max((l["worst_cte_m"] for l in laps), default=float("nan"))
    margin = (C.CTE_BUDGET_M - worst) / C.CTE_BUDGET_M if laps else float("nan")
    path.write_text(json.dumps(dict(
        verdict=verdict, laps=n, laps_failed=fails, lap_failure_rate=rate,
        wilson_95=[lo, hi], worst_cte_m=worst, margin_frac=margin,
        lap_spans=spans, laps_detail=laps,
        student=student, checkpoint=ck,
        condition=args.condition, exposure=C.exposure_for(args.condition),
        cte_budget_m=C.CTE_BUDGET_M, provenance=prov, runs=runs), indent=2))
    print(f"  {args.condition}/{args.cell}: {fails} of {n} laps failed -> {verdict}"
          f"   worst {worst*C.M_TO_FT:.2f} ft, margin {margin*100:.1f}%")
    print(f"  wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

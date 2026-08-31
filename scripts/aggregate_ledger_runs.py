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
                    help="runs expected; the cell is REFUSED if fewer are present, "
                         "because a rate over a partial set is not the rate claimed")
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

    n = len(runs)
    fails = sum(1 for r in runs if not r["passed"])
    rate = fails / n if n else 0.0
    lo, hi = wilson(fails, n)
    verdict = "FAIL" if lo > 0.0 else "PASS"

    prov = dict(prov or {})
    prov["independent_runs"] = True
    prov["restart_granularity"] = "per_run_process"
    prov["aggregated_at"] = datetime.datetime.now().astimezone().isoformat(
        timespec="seconds")

    LEDGER.mkdir(parents=True, exist_ok=True)
    path = LEDGER / f"{args.condition}__{args.cell}__closed_loop.json"
    path.write_text(json.dumps(dict(
        verdict=verdict, repetitions=n, failures=fails, failure_rate=rate,
        wilson_95=[lo, hi], student=student, checkpoint=ck,
        condition=args.condition, exposure=C.exposure_for(args.condition),
        cte_budget_m=C.CTE_BUDGET_M, provenance=prov, runs=runs), indent=2))
    print(f"  {args.condition}/{args.cell}: {fails}/{n} = {rate:.1%} "
          f"Wilson [{lo:.1%}, {hi:.1%}] -> {verdict}")
    print(f"  wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

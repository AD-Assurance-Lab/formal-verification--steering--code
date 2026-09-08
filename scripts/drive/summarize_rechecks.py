#!/usr/bin/env python3
"""Fold the re-check campaigns into the one file that says what happened to the void cell.

The committed ledger has a void cell: the mixed student under fog, whose three laps were
1.33, 5.25 and 1.47 ft against a 2.19 ft budget. One lap over, none departing, and laps
that disagree make a cell void rather than passed or failed.

Four campaigns were driven afterwards to find the cause, which is what lifting a void
requires. They are the primary record of that work, and without them the ledger says
"void" and nothing says why. Rather than publish four directories of per-lap files, this
folds them into one artifact carrying every lap, so the evidence is complete in a single
file a reader can open.

It does NOT touch the committed ledger. The published passes stand as collected; this
sits beside them and says what was learned after.

    python3 scripts/drive/summarize_rechecks.py
"""
import glob
import json
import os
import re
import sys

from steering import REPO_ROOT

M_TO_FT = 3.280839895013123
BUDGET_FT = 2.1916011199999996

# Each campaign, in the order it was driven, with what it was for. The directories are
# working output and are not themselves published; this file is what carries them.
CAMPAIGNS = (
    ("fog_24_laps", "void_fog",
     "The void cell alone, 24 laps, one process and one fresh server each, to find out "
     "whether the 5.25 ft lap was a mode of this cell or a one-off."),
    ("all_cells_v1", "hw_recheck",
     "Every ledger cell re-driven on the current card, to test whether the committed "
     "verdicts depend on the machine that produced them."),
    ("all_cells_v2", "hw_recheck2",
     "The same eight cells again after the driver gained its frame-level condition "
     "check, so the re-check is not resting on one driver configuration."),
    ("tuned_policy", "best",
     "The best policy this pipeline knows how to build, driven on the same cells."),
)


def fold(subdir):
    """(cells, provenance) for one campaign, read from its per-lap records."""
    root = os.path.join(REPO_ROOT, "results", "arterial", subdir, "ledger", "runs")
    paths = sorted(glob.glob(os.path.join(root, "*.json")))
    if not paths:
        return None, None
    cells, prov = {}, None
    for p in paths:
        m = re.match(r"(\w+?)__(S_\w+?)__(\w+?)__rep(\d+)\.json", os.path.basename(p))
        if not m:
            continue
        j = json.load(open(p))
        run = j.get("run", j)
        if prov is None:
            pr = j["provenance"]
            det = pr.get("determinism", {})
            prov = {"run_started": pr["run_started"], "git_sha": pr["git_sha"],
                    "map": pr["map"], "fixed_delta_seconds": pr["fixed_delta_seconds"],
                    "deterministic_control": det.get("deterministic_control"),
                    "notexturestreaming": det.get("notexturestreaming"),
                    "quality_level": det.get("quality_level")}
        key = f"{m.group(1)}__{j['checkpoint']}"
        cells.setdefault(key, {"condition": m.group(1), "checkpoint": j["checkpoint"],
                               "laps": []})
        cells[key]["laps"].append({"rep": int(m.group(4)), "direction": m.group(3),
                                   "max_cte_ft": round(run["max_cte_m"] * M_TO_FT, 4),
                                   "passed": bool(run["passed"]),
                                   "departed": bool(run["departed"])})
    for c in cells.values():
        c["laps"].sort(key=lambda r: (r["direction"], r["rep"]))
        failed = [r for r in c["laps"] if not r["passed"]]
        c["n_laps"] = len(c["laps"])
        c["n_failed"] = len(failed)
        c["worst_cte_ft"] = round(max(r["max_cte_ft"] for r in c["laps"]), 4)
        # Same rule the ledger uses: laps that disagree void the cell.
        c["verdict"] = ("PASS" if not failed
                        else "FAIL" if len(failed) == len(c["laps"]) else "VOID")
    return cells, prov


def main():
    out = {
        "what_this_is":
            "Re-check campaigns driven after the committed ledger, to find the cause of "
            "its one void cell. Every lap is recorded here; the working directories they "
            "were folded from are not published.",
        "does_not_replace":
            "results/arterial/ledger and results/arterial/ledger_pass2 are the study's "
            "reported numbers and are unchanged. Nothing here was driven into them.",
        "the_void_cell":
            "fog / S_mixed_t06lap_168x56_w4_s3. Committed pass 1: 1.33, 5.25, 1.47 ft. "
            "Committed pass 2: 1.07, 1.08, 3.28 ft. Budget 2.19 ft. One lap over in each "
            "pass, none departing, so the laps disagree and the cell is void.",
        "cte_budget_ft": round(BUDGET_FT, 4),
        "campaigns": {},
    }
    missing = []
    for name, subdir, why in CAMPAIGNS:
        cells, prov = fold(subdir)
        if cells is None:
            missing.append(subdir)
            continue
        out["campaigns"][name] = {"purpose": why, "provenance": prov,
                                  "n_laps": sum(c["n_laps"] for c in cells.values()),
                                  "cells": cells}
    if missing:
        print(f"no per-lap records for: {', '.join(missing)}", file=sys.stderr)
        print("These are working directories and exist only where the campaigns were "
              "driven. Nothing to fold.", file=sys.stderr)
        return 1
    path = os.path.join(REPO_ROOT, "results", "arterial", "hardware_recheck.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    for name, c in out["campaigns"].items():
        verdicts = {k: v["verdict"] for k, v in c["cells"].items()}
        n_pass = sum(1 for v in verdicts.values() if v == "PASS")
        print(f"  {name:14s} {c['n_laps']:3d} laps, {len(verdicts)} cells, "
              f"{n_pass} PASS")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

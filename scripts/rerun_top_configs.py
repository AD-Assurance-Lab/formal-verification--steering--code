#!/usr/bin/env python3
"""Re-drive the sweep's shortlisted configs with REPETITIONS, and decide.

The sweep drives each section ONCE, which is enough to rank configs coarsely and not
enough to choose between them: the same checkpoint scored 5/6, 6/6 and 5/6 on three
consecutive gates earlier, and single-run CTE near the budget is a coin flip
(standing rule 3). This re-drives the shortlist REPS times per section and reports the
worst case over reps, which is the number a competence decision should rest on.

It reuses the sweep's checkpoints; nothing is re-distilled, so the comparison is between
the same weights the sweep scored.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/rerun_top_configs.py --reps 3
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402

SWEEP = REPO / "results" / "town06" / "arch_sweep.json"
OUT = REPO / "results" / "town06" / "arch_rerun.json"
LOGD = REPO / "results" / "town06_logs"

# Longest unbroken dead-straight run per section, for reading the result by mechanism
# rather than by aggregate. Town04's own maximum is 200-258 m, for reference.
STRAIGHT_M = {"s00": 166, "s01": 558, "s02": 404, "s03": 620, "s04": 264, "s05": 232}


def parse(out):
    res = {}
    for line in out.splitlines():
        t = line.strip()
        for sec in C.SECTIONS:
            if t.startswith(f"{sec} ") and ("PASS" in t or "FAIL" in t):
                cte = None
                if "max|CTE|=" in t:
                    try:
                        cte = float(t.split("max|CTE|=")[1].split("ft")[0])
                    except Exception:
                        pass
                res[sec] = dict(passed="PASS" in t, max_cte_ft=cte)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--top", type=int, default=4, help="how many configs to re-drive")
    args = ap.parse_args()

    sweep = json.loads(SWEEP.read_text())
    scored = [(k, v) for k, v in sweep.items() if "sections" in v]
    # Rank by sections held, then by worst CTE on the two longest straights, since that
    # is the mechanism under test rather than the aggregate.
    def key(kv):
        k, v = kv
        s = v["sections"]
        straights = [s.get(x, {}).get("max_cte_ft") or 99 for x in ("s03", "s01")]
        return (-v["n_pass"], max(straights))
    shortlist = [k for k, _ in sorted(scored, key=key)][:args.top]
    print(f"shortlist (by sections held, then worst straight): {shortlist}\n", flush=True)

    results = json.loads(OUT.read_text()) if OUT.exists() else {}
    for label in shortlist:
        if label in results:
            print(f"SKIP {label}", flush=True)
            continue
        cfg = sweep[label]
        per_rep = []
        for rep in range(args.reps):
            p = subprocess.run(
                [sys.executable, "evaluate.py", "--model", f"sweep_{label}", "--student",
                 "--channels", cfg["channels"], "--fc", str(cfg["fc"]),
                 "--in-w", str(cfg["in_w"]), "--in-h", str(cfg["in_h"]),
                 "--direction", "all", "--weather", "clear", "--max-steps", "2000"],
                cwd=str(REPO / "pipeline"), capture_output=True, text=True,
                env=dict(os.environ, STUDY_MAP="Town06", PYTHONUNBUFFERED="1"))
            r = parse(p.stdout + p.stderr)
            if r:
                per_rep.append(r)
            with open(LOGD / f"rerun_{label}.log", "a") as f:
                f.write(f"\n===== rep {rep} =====\n" + p.stdout + p.stderr)
        secs = {}
        for sec in C.SECTIONS:
            got = [rp[sec] for rp in per_rep if sec in rp]
            if not got:
                continue
            secs[sec] = dict(
                held=sum(1 for g in got if g["passed"]), reps=len(got),
                worst_cte_ft=max((g["max_cte_ft"] or 0.0) for g in got),
                straight_m=STRAIGHT_M.get(sec))
        results[label] = dict(**{k: cfg[k] for k in ("in_w", "in_h", "channels", "fc")},
                              sections=secs,
                              all_held=sum(1 for v in secs.values() if v["held"] == v["reps"]),
                              n=len(secs))
        OUT.write_text(json.dumps(results, indent=2))
        print(f"{label}: {results[label]['all_held']}/{len(secs)} sections held on ALL "
              f"{args.reps} reps", flush=True)

    print("\n===== REPEATED-DRIVE RESULT (worst |CTE| ft over reps) =====", flush=True)
    order = sorted(C.SECTIONS, key=lambda s: -STRAIGHT_M.get(s, 0))
    hdr = f"{'config':12s} {'ReLU':>7s} {'held':>6s} " + " ".join(
        f"{s}/{STRAIGHT_M[s]}m".rjust(11) for s in order)
    print(hdr, flush=True)
    for label in shortlist:
        r = results.get(label)
        if not r:
            continue
        ch = tuple(int(x) for x in r["channels"].split(","))
        n = C.relu_count(ch, r["fc"], r["in_h"], r["in_w"])
        row = " ".join(
            (f"{r['sections'][s]['worst_cte_ft']:7.2f}"
             f"({r['sections'][s]['held']}/{r['sections'][s]['reps']})").rjust(11)
            if s in r["sections"] else " " * 11 for s in order)
        print(f"{label:12s} {n:7,} {r['all_held']}/{r['n']:<4} {row}", flush=True)
    print(f"\nbudget {C.CTE_BUDGET_FT:.2f} ft; a section counts as held only if it holds "
          f"on every rep", flush=True)


if __name__ == "__main__":
    main()

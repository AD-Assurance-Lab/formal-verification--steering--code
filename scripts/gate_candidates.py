#!/usr/bin/env python3
"""3-rep clear-weather gate over an EXPLICIT list of checkpoints, for comparison.

WHY
---
check_student_competence.py gates whatever the registry names. This gates candidates
side by side in one CARLA session, which is what a decision between training procedures
needs: same server, same session, same route, three repetitions each.

The question it exists to answer: does student DAgger help or hurt at 168x28? Every
prior reading of that was single-pass, and single-pass cannot tell improvement from
run-to-run variance -- the same checkpoint scored 6/6 and 5/6 on consecutive passes
earlier tonight, which is why standing rule 3 requires a rate.

Clear weather only. That is the s=0 anchor of the disturbance family, not a disturbance
condition, so this reveals nothing about fog, night or low sun and does not weaken the
blind protocol (PROTOCOL R3).

    STUDY_MAP=Town06 python3 scripts/gate_candidates.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402

OUT = REPO / "results" / "town06" / "gate_candidates.json"
STRAIGHT_M = {"s00": 166, "s01": 558, "s02": 404, "s03": 620, "s04": 264, "s05": 232}

# (label, checkpoint, channels, fc, note)
CANDIDATES = [
    ("clear w2 base",    "S_clear_t06_168x28_w2",              "16,32,32", 64,
     "distilled only"),
    ("clear w2 +DAgger", "S_clear_t06_168x28_w2_dagger_r02",   "16,32,32", 64,
     "3 student-DAgger rounds"),
    ("mixed w2 base",    "S_mixed_t06_168x28_w2",              "16,32,32", 64,
     "distilled only"),
    ("mixed w2 +DAgger", "S_mixed_t06_168x28_w2_dagger_r03",   "16,32,32", 64,
     "4 student-DAgger rounds"),
    ("mixed w3 base",    "S_mixed_t06_168x28_w3",              "24,48,48", 96,
     "distilled only, widened"),
    ("clear w2 (sweep seed)", "sweep_168x28_w2",               "16,32,32", 64,
     "distilled only, different seed -- for the seed-variance record, NOT for selection"),
]


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
    reps = int(os.environ.get("REPS", "3"))
    # An unset CARLA_PORT sends every drive to the default port, where there is no
    # server. Every candidate then scores 0/0, which looks like data.
    if "CARLA_PORT" not in os.environ:
        sys.exit("set CARLA_PORT (the lab server is on a non-default port)")
    results = json.loads(OUT.read_text()) if OUT.exists() else {}
    for label, ckpt, ch, fc, note in CANDIDATES:
        if label in results:
            print(f"SKIP {label}", flush=True)
            continue
        w = Path(C.CHECKPOINT_DIR) / f"{ckpt}.pth"
        if not w.exists():
            print(f"  {label}: MISSING {w.name}", flush=True)
            continue
        print(f"\n=== {label}  ({ckpt}, {note}) ===", flush=True)
        per_rep = []
        for _ in range(reps):
            p = subprocess.run(
                [sys.executable, "evaluate.py", "--model", ckpt, "--student",
                 "--channels", ch, "--fc", str(fc),
                 "--in-w", str(C.TOWN06_INPUT_W), "--in-h", str(C.TOWN06_INPUT_H),
                 "--direction", "all", "--weather", "clear", "--max-steps", "2000"],
                cwd=str(REPO / "pipeline"), capture_output=True, text=True,
                env=dict(os.environ, STUDY_MAP="Town06", PYTHONUNBUFFERED="1"))
            r = parse(p.stdout + p.stderr)
            if r:
                per_rep.append(r)
            else:
                # Silence here once looked like "0/0 sections held", which reads as a
                # result rather than a failed run. It was a missing CARLA_PORT.
                print(f"  !! no per-section output (rc={p.returncode}). Last stderr:",
                      flush=True)
                for ln in (p.stderr or p.stdout).strip().splitlines()[-6:]:
                    print(f"     {ln}", flush=True)
        secs = {}
        for sec in C.SECTIONS:
            got = [rp[sec] for rp in per_rep if sec in rp]
            if not got:
                continue
            secs[sec] = dict(held=sum(1 for g in got if g["passed"]), reps=len(got),
                             worst_cte_ft=max((g["max_cte_ft"] or 0.0) for g in got),
                             straight_m=STRAIGHT_M.get(sec))
        results[label] = dict(checkpoint=ckpt, channels=ch, fc=fc, note=note,
                              relu=C.relu_count(tuple(int(x) for x in ch.split(",")), fc,
                                                C.TOWN06_INPUT_H, C.TOWN06_INPUT_W),
                              sections=secs,
                              all_held=sum(1 for v in secs.values() if v["held"] == v["reps"]),
                              n=len(secs))
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(results, indent=2))
        print(f"  -> {results[label]['all_held']}/{len(secs)} sections held on ALL "
              f"{reps} reps", flush=True)

    print(f"\n===== 3-REP CLEAR GATE (a section counts only if it holds on EVERY rep) =====",
          flush=True)
    order = sorted(C.SECTIONS, key=lambda s: -STRAIGHT_M.get(s, 0))
    print(f"{'candidate':24s} {'ReLU':>7s} {'held':>6s} " +
          " ".join(f"{s}/{STRAIGHT_M[s]}m".rjust(11) for s in order), flush=True)
    for label, _, _, _, _ in CANDIDATES:
        r = results.get(label)
        if not r:
            continue
        row = " ".join(
            (f"{r['sections'][s]['worst_cte_ft']:7.2f}"
             f"({r['sections'][s]['held']}/{r['sections'][s]['reps']})").rjust(11)
            if s in r["sections"] else " " * 11 for s in order)
        print(f"{label:24s} {r['relu']:7,} {r['all_held']}/{r['n']:<4} {row}", flush=True)
    print(f"\nbudget {C.CTE_BUDGET_FT:.2f} ft", flush=True)


if __name__ == "__main__":
    main()

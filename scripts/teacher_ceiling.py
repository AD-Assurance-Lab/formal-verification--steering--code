#!/usr/bin/env python3
"""What is the TEACHER's failure rate under repetition? The ceiling every student is
measured against.

The teacher gate scored one pass per (condition, section) and reported 0/24. That is a
single-pass number, and standing rule 3 exists because single-pass numbers cannot tell a
solid pass from a lucky one -- three separate conclusions tonight were built on
single-pass evidence and had to be withdrawn.

Every claim of the form "the teacher is perfect so the whole gap is distillation" rests
on that 0/24. This re-measures it at 12 runs per condition, the same way students are
scored, so the comparison is like for like.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/teacher_ceiling.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402

OUT = REPO / "results" / "town06" / "teacher_ceiling.json"
CONDS = ["clear", "fog", "night", "shadows"]
TEACHER = os.environ.get("TEACHER", "teacher_mixed_t06_dagger_r12")


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
    if "CARLA_PORT" not in os.environ:
        sys.exit("set CARLA_PORT")
    reps = int(os.environ.get("REPS", "2"))
    per, total_f, total_n = {}, 0, 0
    print(f"teacher {TEACHER}, {reps} reps x 6 sections per condition\n")
    for cond in CONDS:
        runs, worst = [], 0.0
        for _ in range(reps):
            p = subprocess.run(
                [sys.executable, "evaluate.py", "--model", TEACHER,
                 "--direction", "all", "--weather", cond, "--max-steps", "2000"],
                cwd=str(REPO / "pipeline"), capture_output=True, text=True,
                env=dict(os.environ, STUDY_MAP="Town06", PYTHONUNBUFFERED="1"))
            r = parse(p.stdout + p.stderr)
            if not r:
                print(f"  !! {cond}: no output (rc={p.returncode})", flush=True)
                for ln in (p.stderr or p.stdout).strip().splitlines()[-4:]:
                    print(f"     {ln}", flush=True)
                continue
            runs += [v["passed"] for v in r.values()]
            worst = max(worst, max((v["max_cte_ft"] or 0.0) for v in r.values()))
        f = sum(1 for x in runs if not x)
        per[cond] = dict(fails=f, n=len(runs), worst_cte_ft=worst)
        total_f += f
        total_n += len(runs)
        print(f"  {cond:9s} {f:2d}/{len(runs):2d} failures, worst |CTE| {worst:6.2f} ft",
              flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(teacher=TEACHER, reps=reps, conditions=per,
                                   total_fails=total_f, total_n=total_n), indent=2))
    print(f"\n  TEACHER CEILING: {total_f}/{total_n} failures under repetition")
    print(f"  (the teacher gate reported 0/24 on a SINGLE pass per cell)")
    print(f"  best student so far, 320x64 w3 at 172,848 ReLU: 5/48")


if __name__ == "__main__":
    main()

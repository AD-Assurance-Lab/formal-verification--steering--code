#!/usr/bin/env python3
"""EXPLORE PHASE 2: can ON-POLICY data break the 14/48 floor?

Under PROTOCOL amendment A-1 (R1 suspended). Nothing here is a blind prediction.

THE FLOOR
---------
Every non-overfit architecture lands in the same place, scored 12 runs per condition:

    config        ReLU    clear  fog  night  shadows   total
    168x28 w2   21,408      0     5     8      1       14/48
    168x28 w3   32,112      2     4     5      4       15/48
    224x64 w2   79,904      2     1     6      6       15/48

A 4x increase in ReLU and a 5x increase in input pixels move failures BETWEEN conditions
and never below the floor. That is not the signature of a capacity or resolution limit.
The teacher, meanwhile, is 0/24.

WHY ON-POLICY DATA IS THE CANDIDATE
-----------------------------------
The failure mode is drift, not departure: every failing night run has departed=False
while exceeding budget by 21-35 ft, wandering across lanes of a wide highway. That is
textbook covariate shift. The student is behaviour-cloned on TEACHER-visited states,
which sit near the lane centre, so it never learns to recover from its own errors -- and
its own errors are what it meets when it drives.

Supporting evidence from tonight: borrowing off-nominal frames from the mixed teacher's
DAgger set took the CLEAR student's s03 from 0/3 at 3.10 ft to 3/3 at 2.17 ft. Those were
another policy's off-nominal states, not the student's, and still helped.

WHAT MAKES THIS DIFFERENT FROM T06-F14
--------------------------------------
T06-F14 withdrew student DAgger, and that was correct for what it measured: single-pass
drives, clear weather only, at 168x28. "Student DAgger degrades CLEAR" is a different
claim from "on-policy correction cannot break a four-condition floor". This scores every
round on all four conditions at 12 runs each, and keeps the whole trajectory rather than
the last round -- DAgger rounds are not monotone, and `final_student` returning the
NEWEST round is exactly how a degraded checkpoint got certified earlier.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/explore_student_dagger.py --rounds 4
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

OUT = REPO / "results" / "town06" / "explore_student_dagger.json"
LOGD = REPO / "results" / "town06_logs"
CONDS = ["clear", "fog", "night", "shadows"]
TEACHER = "teacher_mixed_t06_dagger_r12"


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


def score(ck, ch, fc, iw, ih, reps):
    per = {}
    for cond in CONDS:
        runs, worst = [], 0.0
        for _ in range(reps):
            p = subprocess.run(
                [sys.executable, "evaluate.py", "--model", ck, "--student",
                 "--channels", ch, "--fc", str(fc), "--in-w", str(iw), "--in-h", str(ih),
                 "--direction", "all", "--weather", cond, "--max-steps", "2000"],
                cwd=str(REPO / "pipeline"), capture_output=True, text=True,
                env=dict(os.environ, STUDY_MAP="Town06", PYTHONUNBUFFERED="1"))
            r = parse(p.stdout + p.stderr)
            if not r:
                print(f"    !! {cond}: no output (rc={p.returncode})", flush=True)
                for ln in (p.stderr or p.stdout).strip().splitlines()[-4:]:
                    print(f"       {ln}", flush=True)
                continue
            runs += [v["passed"] for v in r.values()]
            worst = max(worst, max((v["max_cte_ft"] or 0.0) for v in r.values()))
        per[cond] = dict(fails=sum(1 for x in runs if not x), n=len(runs),
                         worst_cte_ft=worst)
        print(f"    {cond:9s} {per[cond]['fails']:2d}/{per[cond]['n']:2d}  "
              f"worst {worst:6.2f} ft", flush=True)
    return per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--student", default="S_mixed_t06_168x28_w2")
    ap.add_argument("--channels", default="16,32,32")
    ap.add_argument("--fc", type=int, default=64)
    ap.add_argument("--in-w", type=int, default=168)
    ap.add_argument("--in-h", type=int, default=28)
    args = ap.parse_args()
    if "CARLA_PORT" not in os.environ:
        sys.exit("set CARLA_PORT")

    results = json.loads(OUT.read_text()) if OUT.exists() else {}
    LOGD.mkdir(parents=True, exist_ok=True)
    ddir = "dagger_student_explore"

    # Round 0 is the starting student, so the trajectory has its own baseline rather
    # than borrowing one measured in a different CARLA session.
    if "round00" not in results:
        print(f"\n=== round 0: {args.student} (no on-policy data yet) ===", flush=True)
        per = score(args.student, args.channels, args.fc, args.in_w, args.in_h, args.reps)
        results["round00"] = dict(checkpoint=args.student, conditions=per,
                                  total_fails=sum(v["fails"] for v in per.values()),
                                  total_n=sum(v["n"] for v in per.values()))
        OUT.write_text(json.dumps(results, indent=2))
        print(f"  -> {results['round00']['total_fails']}/"
              f"{results['round00']['total_n']}", flush=True)

    current = args.student
    for r in range(args.rounds):
        key = f"round{r + 1:02d}"
        if key in results:
            current = results[key]["checkpoint"]
            print(f"SKIP {key}", flush=True)
            continue
        print(f"\n=== {key}: one student-DAgger round from {current} ===", flush=True)
        with open(LOGD / f"explore_sd_{key}.log", "w") as f:
            rc = subprocess.run(
                [sys.executable, "dagger_student.py", "--student", current,
                 "--w", str(args.in_w), "--h", str(args.in_h), "--rounds", "1",
                 "--weathers", ",".join(CONDS), "--dagger-dir", ddir,
                 "--teacher", TEACHER, "--base", "mixed_t06",
                 "--channels", args.channels, "--fc", str(args.fc),
                 "--distill-dirs", f"dagger_mixed_t06,{ddir}"],
                cwd=str(REPO / "pipeline"), stdout=f, stderr=subprocess.STDOUT,
                env=dict(os.environ, STUDY_MAP="Town06",
                         PYTHONUNBUFFERED="1")).returncode
        if rc != 0:
            print(f"  dagger_student exited {rc}; stopping", flush=True)
            break
        # dagger_student writes <student>_dagger_rNN; take the newest THIS round made.
        made = sorted(Path(C.CHECKPOINT_DIR).glob(f"{current}_dagger_r*.pth"))
        if not made:
            print("  no new checkpoint written; stopping", flush=True)
            break
        nxt = made[-1].stem
        print(f"  new checkpoint {nxt}", flush=True)
        per = score(nxt, args.channels, args.fc, args.in_w, args.in_h, args.reps)
        results[key] = dict(checkpoint=nxt, conditions=per,
                            total_fails=sum(v["fails"] for v in per.values()),
                            total_n=sum(v["n"] for v in per.values()))
        OUT.write_text(json.dumps(results, indent=2))
        print(f"  -> {results[key]['total_fails']}/{results[key]['total_n']}", flush=True)
        current = nxt

    print("\n===== STUDENT-DAgger TRAJECTORY (failures / runs) =====", flush=True)
    print(f"{'round':8s} {'checkpoint':44s} " + " ".join(f"{c:>8s}" for c in CONDS)
          + f" {'total':>8s}", flush=True)
    for k in sorted(results):
        v = results[k]
        row = " ".join(f"{v['conditions'][c]['fails']:2d}/{v['conditions'][c]['n']:<2d}".rjust(8)
                       for c in CONDS if c in v["conditions"])
        print(f"{k:8s} {v['checkpoint'][:44]:44s} {row} "
              f"{v['total_fails']:3d}/{v['total_n']:<4d}", flush=True)
    print("\n  the floor to beat is 14/48. Rounds are NOT monotone -- read the whole "
          "trajectory, not the last row.", flush=True)


if __name__ == "__main__":
    main()

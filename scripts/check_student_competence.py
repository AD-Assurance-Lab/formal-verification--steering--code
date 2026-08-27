#!/usr/bin/env python3
"""Verify each student is COMPETENT in clear weather before anything is certified.

WHY THIS EXISTS
---------------
The certificate bounds  Delta_p(s) = delta_p(s) - delta_p(0)  -- the change the
disturbance induces, measured against the model's OWN clear-weather output. It never
asks whether delta_p(0) is any good.

Follow that to its limit: a network that ignores its input and emits a constant
steering angle has Delta_p(s) identically zero and is perfectly CERTIFIED under every
condition, while driving straight off the road. The certificate cannot tell robustness
from indifference.

So clear-weather competence is a PRECONDITION for the certificate meaning anything, not
something the certificate establishes. That matters most exactly where this study is
now: distillation can produce a student without the capacity to fit its teacher's task,
and a student that is uniformly wrong in a way that is STABLE across s is rewarded by a
criterion that measures stability.

The published Town04 study half-encodes this already -- the clear cell is driven, and
its certificate is recorded as vacuous, "Delta_p = 0 by construction" -- but the
assumption is never named. This makes it a gate.

REPETITIONS
-----------
Standing rule 3: every closed-loop number is a RATE over repetitions, never a single
run, because CARLA pass/fail varies run to run near the cliff. This gate broke that
rule and paid for it -- the SAME checkpoint (S_clear ..._dagger_r02) scored 4/6
sections on one pass and 2/6 on the next, with worst |CTE| 8.57 ft and 7.86 ft. A
single pass per section cannot tell a marginal student from an unlucky one.

So each section is driven REPS times and must hold on EVERY one. That is a deliberately
strict bar: a student that only sometimes holds clear weather is not a competent
student, and the published Town04 clear cell is 0/10 failures, not a coin flip.

WHAT THIS IS NOT
----------------
Not a scored ledger cell. It is a single evaluation pass per section in CLEAR weather,
which is the s=0 anchor of the disturbance family, not one of the disturbance
conditions. It reveals nothing about fog, night or low sun, so it does not weaken the
blind protocol (PROTOCOL R3, section 5). It is the same kind of precondition check as
the teacher gate.

    STUDY_MAP=Town06 python3 scripts/check_student_competence.py
    STUDY_MAP=Town06 python3 scripts/check_student_competence.py --require   # gate mode
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402

OUT = REPO / "results" / "town06" / "competence_clear.json"

# One definition, in config. Four scripts previously named checkpoints independently
# and drifted apart.
STUDENTS = tuple((nm, ck, ",".join(str(c) for c in ch), fc)
                 for nm, ck, ch, fc in C.TOWN06_STUDENTS)


def run_eval(ckpt, channels, fc):
    """One pass over every section in clear weather. Returns per-section CTE."""
    env = dict(os.environ, STUDY_MAP=C.STUDY_MAP, PYTHONUNBUFFERED="1")
    cmd = [sys.executable, "evaluate.py", "--model", ckpt, "--direction", "all",
           "--weather", "clear", "--max-steps", "2000",
           "--channels", channels, "--fc", str(fc), "--student",
           "--in-w", str(C.TOWN06_INPUT_W), "--in-h", str(C.TOWN06_INPUT_H)]
    p = subprocess.run(cmd, cwd=str(REPO / "pipeline"), env=env,
                       capture_output=True, text=True)
    return p.stdout + p.stderr


def parse(out):
    """Pull the per-section summary lines evaluate.py prints."""
    res = {}
    for line in out.splitlines():
        t = line.strip()
        for sec in C.SECTIONS:
            if t.startswith(f"{sec} ") and ("PASS" in t or "FAIL" in t):
                ok = "PASS" in t
                cte = None
                if "max|CTE|=" in t:
                    try:
                        cte = float(t.split("max|CTE|=")[1].split("ft")[0])
                    except Exception:
                        pass
                res[sec] = dict(passed=ok, max_cte_ft=cte)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3,
                    help="passes per section; a section must hold on EVERY one")
    ap.add_argument("--require", action="store_true",
                    help="exit non-zero unless every student passes every section")
    args = ap.parse_args()

    print("CLEAR-WEATHER COMPETENCE GATE")
    print("  The certificate bounds deviation FROM clear. A model that is wrong in clear")
    print("  weather, or that ignores its input entirely, certifies perfectly and drives")
    print("  off the road. Competence is assumed by the certificate, so check it here.\n")

    report, all_ok = {}, True
    for name, base, channels, fc in STUDENTS:
        # The distilled checkpoint is an intermediate; the student is the newest
        # student-DAgger round. Testing the base tested a model nobody ships.
        ckpt = C.final_student(base)
        if ckpt != base:
            print(f"  {name}: using {ckpt} (student-DAgger), not the distilled {base}")
        w = Path(C.CHECKPOINT_DIR) / f"{ckpt}.pth"
        if not w.exists():
            print(f"  {name}: checkpoint missing ({w.name})")
            report[name] = dict(error="checkpoint missing")
            all_ok = False
            continue
        # Repetitions, per standing rule 3. A section must hold on every one.
        per_rep = []
        for _ in range(args.reps):
            out = run_eval(ckpt, channels, fc)
            r = parse(out)
            if r:
                per_rep.append(r)
            else:
                # An empty run is a FAILED run, not a failing student. This once
                # recorded "evaluation produced no per-section result" for both
                # students after 12 minutes of driving against a CARLA that was
                # listening but not yet serving, which reads as a verdict on the
                # models. Show what actually happened.
                print("      !! no per-section output; last lines of that run:")
                for ln in out.strip().splitlines()[-5:]:
                    print(f"         {ln}")
        res = {}
        for sec in C.SECTIONS:
            got = [rp[sec] for rp in per_rep if sec in rp]
            if not got:
                continue
            res[sec] = dict(passed=all(g["passed"] for g in got),
                            n_pass=sum(1 for g in got if g["passed"]),
                            reps=len(got),
                            max_cte_ft=max((g["max_cte_ft"] or 0.0) for g in got))
        if not res:
            print(f"  {name}: evaluation produced no per-section result")
            report[name] = dict(error="no result parsed")
            all_ok = False
            continue
        ok = all(v["passed"] for v in res.values())
        all_ok &= ok
        report[name] = dict(checkpoint=ckpt, sections=res, competent=ok)
        worst = max((v["max_cte_ft"] or 0.0) for v in res.values())
        n_ok = sum(1 for v in res.values() if v["passed"])
        print(f"  {name}: {n_ok}/{len(res)} sections within budget, "
              f"worst max|CTE| {worst:.2f} ft (gate {C.CTE_BUDGET_FT:.2f} ft)  "
              f"-> {'COMPETENT' if ok else 'NOT COMPETENT'}")
        for sec, v in sorted(res.items()):
            if not v["passed"]:
                print(f"      {sec}: held {v['n_pass']}/{v['reps']} reps, "
                      f"worst max|CTE| {v['max_cte_ft']} ft")

    try:
        head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        head = None
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(map=C.STUDY_MAP, students=report,
                                   all_competent=all_ok,
                                   cte_budget_ft=C.CTE_BUDGET_FT,
                                   git_commit=head,
                                   reps=args.reps,
                                   note="clear weather only; s=0 anchor, not a "
                                        "disturbance cell, not a scored ledger cell; "
                                        "every section must hold on every rep"),
                              indent=2))
    print(f"\n  wrote {OUT.relative_to(REPO)}")
    if not all_ok:
        print("\n  A student is NOT competent in clear weather. Certifying it would")
        print("  produce a bound on deviation from an output that is already wrong.")
        print("  Fix the student (capacity, distillation, more student-DAgger rounds)")
        print("  BEFORE certifying.")
    return 0 if (all_ok or not args.require) else 1


if __name__ == "__main__":
    sys.exit(main())

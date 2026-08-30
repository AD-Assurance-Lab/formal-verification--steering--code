#!/usr/bin/env python3
"""EXPLORE PHASE 2: size the mixed student against ALL FOUR conditions.

Runs under PROTOCOL amendment A-1, which suspends the blind ordering rule R1. Nothing
produced here is a blind prediction and none of it may be presented as one.

WHY THIS EXISTS
---------------
The mixed student's architecture was chosen on the clear-weather competence gate. That
gate is the s=0 anchor of the disturbance family and says NOTHING about fog, night or
low sun -- by construction. So when w3 measured worse than w2 and was withdrawn
(T06-F14), what had actually been measured was "worse in CLEAR", for a model whose whole
job is four conditions. It was never driven at night.

Meanwhile the teacher passes all 24 teacher-gate cells and the student fails night 9/12,
and the per-condition KD split shows why the gap hides in a pooled number:

    condition   KD RMSE   x tolerance    teacher |steer|
    clear        0.0116      0.97           0.0207
    shadows      0.0203      1.69           0.0236
    fog          0.0227      1.89           0.0267
    night        0.0344      2.86           0.0525

Night error is nearly 3x the entire steering tolerance, and the teacher steers 2.5x
harder there -- a larger-magnitude function to imitate, from darker images. The training
set is NOT the cause: it is 24-25% per condition, so this is not sampling.

Standing rule 3 still applies: 6 sections x REPS runs per condition, >= 10.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/explore_mixed_arch.py
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402

OUT = REPO / "results" / "town06" / "explore_mixed_arch.json"
LOGD = REPO / "results" / "town06_logs"
CONDS = ["clear", "fog", "night", "shadows"]

# (label, channels, fc). Resolution stays 168x28: T06-F11 settled it and 224x28 measured
# worse on both students (T06-F14 note).
CONFIGS = [
    ("w2", "16,32,32", 64),      # current; drives clear 6/6, fails night 9/12
    ("w3", "24,48,48", 96),      # Town04's mixed ratio, never driven at night here
    ("w4", "32,64,64", 128),
]
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


def main():
    if "CARLA_PORT" not in os.environ:
        sys.exit("set CARLA_PORT")
    reps = int(os.environ.get("REPS", "2"))
    results = json.loads(OUT.read_text()) if OUT.exists() else {}
    LOGD.mkdir(parents=True, exist_ok=True)

    for label, ch, fc in CONFIGS:
        ck = f"S_mixed_t06_168x28_{label}"
        relu = C.relu_count(tuple(int(x) for x in ch.split(",")), fc,
                            C.TOWN06_INPUT_H, C.TOWN06_INPUT_W)
        if label in results:
            print(f"SKIP {label}", flush=True)
            continue
        w = Path(C.CHECKPOINT_DIR) / f"{ck}.pth"
        if not w.exists():
            print(f"\n=== {label}: distilling {ck} ({relu:,} ReLU) ===", flush=True)
            with open(LOGD / f"explore_distill_{label}.log", "w") as f:
                rc = subprocess.run(
                    [sys.executable, "distill.py", "--in-w", str(C.TOWN06_INPUT_W),
                     "--in-h", str(C.TOWN06_INPUT_H), "--out", ck, "--teacher", TEACHER,
                     "--base", "mixed_t06", "--dagger-dirs", "dagger_mixed_t06",
                     "--channels", ch, "--fc", str(fc)],
                    cwd=str(REPO / "pipeline"), stdout=f, stderr=subprocess.STDOUT,
                    env=dict(os.environ, STUDY_MAP="Town06",
                             PYTHONUNBUFFERED="1")).returncode
            if rc != 0:
                print(f"  distil FAILED rc={rc}", flush=True)
                continue

        print(f"\n=== {label} ({relu:,} ReLU): driving all four conditions, "
              f"{reps} reps ===", flush=True)
        per_cond = {}
        for cond in CONDS:
            runs, worst = [], 0.0
            for _ in range(reps):
                p = subprocess.run(
                    [sys.executable, "evaluate.py", "--model", ck, "--student",
                     "--channels", ch, "--fc", str(fc),
                     "--in-w", str(C.TOWN06_INPUT_W), "--in-h", str(C.TOWN06_INPUT_H),
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
            fails = sum(1 for x in runs if not x)
            per_cond[cond] = dict(fails=fails, n=len(runs), worst_cte_ft=worst)
            print(f"  {cond:9s} {fails:2d}/{len(runs):2d} failures, "
                  f"worst |CTE| {worst:6.2f} ft", flush=True)
        results[label] = dict(checkpoint=ck, channels=ch, fc=fc, relu=relu,
                              conditions=per_cond)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(results, indent=2))

    print("\n===== EXPLORE PHASE 2: mixed student vs conditions "
          "(failures / runs) =====", flush=True)
    print(f"{'config':7s} {'ReLU':>7s} " + " ".join(f"{c:>14s}" for c in CONDS),
          flush=True)
    for label, _, _ in CONFIGS:
        r = results.get(label)
        if not r:
            continue
        row = " ".join(
            f"{r['conditions'][c]['fails']:2d}/{r['conditions'][c]['n']:<2d}"
            f" {r['conditions'][c]['worst_cte_ft']:6.2f}ft".rjust(14)
            if c in r["conditions"] else " " * 14 for c in CONDS)
        print(f"{label:7s} {r['relu']:7,} {row}", flush=True)
    print(f"\nbudget {C.CTE_BUDGET_FT:.2f} ft; a config is usable only if every "
          f"condition is 0 failures", flush=True)


if __name__ == "__main__":
    main()

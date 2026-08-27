#!/usr/bin/env python3
"""Re-measure the policies that matter, on the FIXED harness.

Every closed-loop number before this was taken with runs that overshot the section's
clean window (see evaluate.py, "stop at the section's scored end"). On the case that
exposed it, s02 in fog, max |CTE| fell from 25.00 ft to 2.29 ft once the run stopped at
628 m. The overshoot hit fog and night hardest, which is exactly where the architecture
conclusions were drawn, so those conclusions do not stand until re-measured.

12 runs per condition, 6 sections x 2 reps, standing rule 3.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/remeasure_configs.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402

OUT = REPO / "results" / "town06" / "remeasured.json"
CONDS = ["clear", "fog", "night", "shadows"]

# (label, checkpoint, channels, fc, in_w, in_h, is_student)  -- prior figure in comment
CONFIGS = [
    ("teacher",     "teacher_mixed_t06_dagger_r12", None,       None, None, None, False),   # was 2/48
    ("168x28_w2",   "S_mixed_t06_168x28_w2",        "16,32,32",   64,  168,   28, True),    # was 14/48
    ("320x64_w3",   "S_mixed_t06_320x64_w3",        "24,48,48",   96,  320,   64, True),    # was 5-6/48
    ("224x64_w2",   "S_mixed_t06_224x64_w2",        "16,32,32",   64,  224,   64, True),    # was 15/48
    ("168x28_w3",   "S_mixed_t06_168x28_w3",        "24,48,48",   96,  168,   28, True),    # was 15/48
]
PRIOR = {"teacher": "2/48", "168x28_w2": "14/48", "320x64_w3": "5-6/48",
         "224x64_w2": "15/48", "168x28_w3": "15/48"}


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
                steps = None
                if "steps=" in t:
                    try:
                        steps = int(t.split("steps=")[1].split()[0])
                    except Exception:
                        pass
                res[sec] = dict(passed="PASS" in t, max_cte_ft=cte, steps=steps)
    return res


def restart_carla():
    """R-SIM-1: fresh server before every cell. R-SIM-2: SIGTERM before SIGKILL."""
    subprocess.run(["bash", str(REPO / "scripts" / "carla_restart.sh")],
                   capture_output=True, text=True,
                   env=dict(os.environ, CARLA_PORT=os.environ.get("CARLA_PORT", "3000")))


def main():
    if "CARLA_PORT" not in os.environ:
        sys.exit("set CARLA_PORT")
    reps = int(os.environ.get("REPS", "2"))
    results = json.loads(OUT.read_text()) if OUT.exists() else {}

    for label, ck, ch, fc, iw, ih, is_student in CONFIGS:
        if label in results:
            print(f"SKIP {label}", flush=True)
            continue
        if not (Path(C.CHECKPOINT_DIR) / f"{ck}.pth").exists():
            print(f"  {label}: checkpoint missing ({ck})", flush=True)
            continue
        relu = (C.relu_count(tuple(int(x) for x in ch.split(",")), fc, ih, iw)
                if is_student else None)
        print(f"\n=== {label} ({ck}"
              + (f", {relu:,} ReLU" if relu else "") + f") -- was {PRIOR[label]} ===",
              flush=True)
        per = {}
        for cond in CONDS:
            runs, worst, short = [], 0.0, 0
            for _ in range(reps):
                restart_carla()          # R-SIM-1, every single run
                cmd = [sys.executable, "evaluate.py", "--model", ck,
                       "--direction", "all", "--weather", cond, "--max-steps", "2000"]
                if is_student:
                    cmd += ["--student", "--channels", ch, "--fc", str(fc),
                            "--in-w", str(iw), "--in-h", str(ih)]
                p = subprocess.run(cmd, cwd=str(REPO / "pipeline"), capture_output=True,
                                   text=True, env=dict(os.environ, STUDY_MAP="Town06",
                                                       PYTHONUNBUFFERED="1"))
                r = parse(p.stdout + p.stderr)
                if not r:
                    print(f"  !! {cond}: no output (rc={p.returncode})", flush=True)
                    for ln in (p.stderr or p.stdout).strip().splitlines()[-4:]:
                        print(f"     {ln}", flush=True)
                    continue
                runs += [v["passed"] for v in r.values()]
                worst = max(worst, max((v["max_cte_ft"] or 0.0) for v in r.values()))
                short += sum(1 for s, v in r.items()
                             if v.get("steps") is not None
                             and v["steps"] < 0.8 * C.steps_for(s))
            per[cond] = dict(fails=sum(1 for x in runs if not x), n=len(runs),
                             worst_cte_ft=worst, short_runs=short)
            if short:
                print(f"  !! {cond}: {short} run(s) ended far short of steps_for -- "
                      f"VOID, not a pass (R-SIM-6)", flush=True)
            print(f"  {cond:9s} {per[cond]['fails']:2d}/{per[cond]['n']:2d} failures, "
                  f"worst |CTE| {worst:6.2f} ft", flush=True)
        results[label] = dict(checkpoint=ck, relu=relu, conditions=per,
                              total_fails=sum(v["fails"] for v in per.values()),
                              total_n=sum(v["n"] for v in per.values()),
                              prior_figure=PRIOR[label])
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(results, indent=2))
        print(f"  -> {results[label]['total_fails']}/{results[label]['total_n']} "
              f"(was {PRIOR[label]} on the overshooting harness)", flush=True)

    print("\n===== RE-MEASURED ON THE FIXED HARNESS =====", flush=True)
    print(f"{'config':12s} {'ReLU':>9s} " + " ".join(f"{c:>9s}" for c in CONDS)
          + f" {'total':>8s} {'was':>8s}", flush=True)
    for label, _, _, _, _, _, _ in CONFIGS:
        r = results.get(label)
        if not r:
            continue
        row = " ".join(f"{r['conditions'][c]['fails']:2d}/{r['conditions'][c]['n']:<2d}".rjust(9)
                       for c in CONDS if c in r["conditions"])
        relu_s = f"{r['relu']:,}" if r.get("relu") else "--"
        print(f"{label:12s} {relu_s:>9s} {row} {r['total_fails']:3d}/{r['total_n']:<4d} "
              f"{r['prior_figure']:>8s}", flush=True)


if __name__ == "__main__":
    main()

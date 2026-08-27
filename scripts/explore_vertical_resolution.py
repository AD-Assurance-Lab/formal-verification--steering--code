#!/usr/bin/env python3
"""EXPLORE PHASE 2: does the mixed student need VERTICAL resolution for night?

Under PROTOCOL amendment A-1 (R1 suspended). Nothing here is a blind prediction.

THE ASYMMETRY
-------------
student_preprocess crops rows 240:450 (210 rows) x 640 columns and resizes to 28 x 168:

    vertical    210 -> 28   = 7.5x downsample
    horizontal  640 -> 168  = 3.8x downsample

Vertical detail is thrown away twice as hard, and the TEACHER -- which passes night 6/6
through the identical camera -- keeps 66 rows to the student's 28.

WHY THAT SHOULD MATTER AT NIGHT SPECIFICALLY
--------------------------------------------
Night is not "dark". Measured over the training set, SHADOWS is darker (mean 0.184) than
night (0.200) and drives perfectly. What separates night is CONTRAST: sigma 0.138 against
0.056-0.064 everywhere else, 13.8% of pixels crushed near black, and the highest p99. The
usable signal is concentrated in the headlight-lit near field -- a horizontal BAND low in
the crop -- plus lit pools. A band is exactly what 7.5x vertical downsampling destroys.

This is the opposite of what clear weather wanted. T06-F11 found horizontal resolution
was the lever on long straights, because the error there is LATERAL and sub-pixel. If
clear wants width and night wants height, one architecture chosen on clear-weather
evidence will always be wrong for night -- which is how the current student was picked.

COST-MATCHED, the same design that settled F11:
    168x28 w2 = 21,408 ReLU   (budget spent on WIDTH)
    168x56 w1 = 25,472 ReLU   (budget spent on VERTICAL RESOLUTION)

If vertical resolution is the lever at night, the second wins there and the first does
not, at near-identical cost.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/explore_vertical_resolution.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402

OUT = REPO / "results" / "town06" / "explore_vertical.json"
LOGD = REPO / "results" / "town06_logs"
CONDS = ["clear", "fog", "night", "shadows"]

# (label, in_w, in_h, channels, fc)
CONFIGS = [
    ("168x56_w1", 168, 56, "8,16,16", 32),    # cost-matched to the baseline, on HEIGHT
    ("168x56_w2", 168, 56, "16,32,32", 64),   # height AND width
    ("112x56_w2", 112, 56, "16,32,32", 64),   # height, trading horizontal away
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

    for label, iw, ih, ch, fc in CONFIGS:
        if label in results:
            print(f"SKIP {label}", flush=True)
            continue
        ck = f"S_mixed_t06_{label}"
        relu = C.relu_count(tuple(int(x) for x in ch.split(",")), fc, ih, iw)
        if not (Path(C.CHECKPOINT_DIR) / f"{ck}.pth").exists():
            print(f"\n=== {label}: distilling ({iw}x{ih}, {relu:,} ReLU) ===", flush=True)
            with open(LOGD / f"explore_vert_{label}.log", "w") as f:
                rc = subprocess.run(
                    [sys.executable, "distill.py", "--in-w", str(iw), "--in-h", str(ih),
                     "--out", ck, "--teacher", TEACHER, "--base", "mixed_t06",
                     "--dagger-dirs", "dagger_mixed_t06", "--channels", ch,
                     "--fc", str(fc)],
                    cwd=str(REPO / "pipeline"), stdout=f, stderr=subprocess.STDOUT,
                    env=dict(os.environ, STUDY_MAP="Town06",
                             PYTHONUNBUFFERED="1")).returncode
            if rc != 0:
                print(f"  distil FAILED rc={rc}", flush=True)
                continue

        print(f"\n=== {label} ({iw}x{ih}, {relu:,} ReLU): all four conditions ===",
              flush=True)
        per = {}
        for cond in CONDS:
            runs, worst = [], 0.0
            for _ in range(reps):
                p = subprocess.run(
                    [sys.executable, "evaluate.py", "--model", ck, "--student",
                     "--channels", ch, "--fc", str(fc), "--in-w", str(iw),
                     "--in-h", str(ih), "--direction", "all", "--weather", cond,
                     "--max-steps", "2000"],
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
            per[cond] = dict(fails=sum(1 for x in runs if not x), n=len(runs),
                             worst_cte_ft=worst)
            print(f"  {cond:9s} {per[cond]['fails']:2d}/{per[cond]['n']:2d} failures, "
                  f"worst |CTE| {worst:6.2f} ft", flush=True)
        results[label] = dict(checkpoint=ck, in_w=iw, in_h=ih, channels=ch, fc=fc,
                              relu=relu, conditions=per,
                              total_fails=sum(v["fails"] for v in per.values()),
                              total_n=sum(v["n"] for v in per.values()))
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(results, indent=2))
        print(f"  -> {results[label]['total_fails']}/{results[label]['total_n']} "
              f"failures overall", flush=True)

    print("\n===== VERTICAL RESOLUTION vs CONDITIONS (failures / runs) =====", flush=True)
    print(f"{'config':12s} {'ReLU':>7s} " + " ".join(f"{c:>10s}" for c in CONDS)
          + f" {'total':>8s}", flush=True)
    for label, _, _, _, _ in CONFIGS:
        r = results.get(label)
        if not r:
            continue
        row = " ".join(f"{r['conditions'][c]['fails']:2d}/{r['conditions'][c]['n']:<2d}".rjust(10)
                       if c in r["conditions"] else " " * 10 for c in CONDS)
        print(f"{label:12s} {r['relu']:7,} {row} {r['total_fails']:3d}/{r['total_n']:<4d}",
              flush=True)
    print("\n  baseline for comparison: 168x28 w2, 21,408 ReLU, "
          "clear 0/12 fog 5/12 night 8/12 shadows 1/12 = 14/48", flush=True)


if __name__ == "__main__":
    main()

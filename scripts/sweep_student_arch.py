#!/usr/bin/env python3
"""Width x input-resolution sweep for the Town06 student, scored CLOSED LOOP.

WHY REOPEN RESOLUTION
---------------------
F11 (4badcfa) swept width and resolution on Town04 and concluded "width is the capacity
lever; resolution loses on both axes", rejecting 112x38. Two things make that verdict
not binding here:

  1. It was scored on KD RMSE. F7 (5be6862) then established that KD RMSE is a poor
     proxy -- "width materially helps closed loop while barely moving KD RMSE ... it was
     leaned on too long". This sweep scores CLOSED LOOP instead.
  2. It was measured on Town04, whose longest dead-straight run is 200-258 m. Town06 has
     four sections exceeding that, s03 being a single 620 m straight, and failures track
     straight length almost exactly (s03 and s01 fail 3 gates each, s05 zero).

F11 also recorded, correctly, that resolution does NOT inflate the perturbation
dimension -- the verifier's input is the one-dimensional physical parameter, not the
image -- so this is a ReLU-cost question, not a verifiability one.

THE PHYSICAL ARGUMENT
---------------------
At 84 px input width the whole 0.668 m CTE budget spans 1.79 px of horizontal image
shift at 20 m lookahead, and a 0.1 m error spans 0.27 px. On a curve this is irrelevant:
the road bends across many pixels whatever the vehicle's offset. On a 620 m straight it
is the ONLY cue, and it is sub-pixel. That predicts HORIZONTAL resolution specifically,
since the error is lateral -- and widening one axis costs ReLU linearly rather than k^2,
which is what made F11's 112x38 expensive for what it bought.

THE CONTROLLED COMPARISON
-------------------------
  84x28 w2 = 10,304 ReLU   (budget spent on width)
 168x28 w1 = 10,704 ReLU   (budget spent on horizontal resolution)

Near-identical cost. If resolution is the lever on straights, the second wins on s01/s03
and the first does not.

    CARLA_PORT=3000 STUDY_MAP=Town06 python3 scripts/sweep_student_arch.py
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

OUT = REPO / "results" / "town06" / "arch_sweep.json"
LOGD = REPO / "results" / "town06_logs"

# (label, in_w, in_h, channels, fc)
CONFIGS = [
    ("84x28_w1",  84, 28, "8,16,16",   32),   # baseline, the published clear student
    ("84x28_w2",  84, 28, "16,32,32",  64),   # matched cost, spent on WIDTH
    ("168x28_w1", 168, 28, "8,16,16",  32),   # matched cost, spent on RESOLUTION
    ("84x28_w3",  84, 28, "24,48,48",  96),   # F11's Town04 winner
    ("224x28_w1", 224, 28, "8,16,16",  32),   # more resolution, still cheap
    ("168x28_w2", 168, 28, "16,32,32", 64),   # both
    ("112x38_w2", 112, 38, "16,32,32", 64),   # F11's rejected config, as control
]

TEACHER = "teacher_clear_t06_dagger_r05"
DATASET = "clear_t06"
DAGGER_DIR = "dagger_clear_t06"


def sh(cmd, log, cwd):
    with open(log, "a") as f:
        return subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT).returncode


def parse_sections(out):
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
    LOGD.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    results = {}
    if OUT.exists():
        results = json.loads(OUT.read_text())

    for label, in_w, in_h, ch, fc in CONFIGS:
        if label in results:
            print(f"SKIP {label} (already swept)", flush=True)
            continue
        ckpt = f"sweep_{label}"
        t0 = time.time()
        print(f"\n=== {label}: distilling ({in_w}x{in_h}, channels {ch}, fc {fc}) ===",
              flush=True)
        rc = sh([sys.executable, "distill.py", "--in-w", str(in_w), "--in-h", str(in_h),
                 "--out", ckpt, "--teacher", TEACHER, "--base", DATASET,
                 "--dagger-dirs", DAGGER_DIR, "--channels", ch, "--fc", str(fc),
                 "--epochs", "120"],
                LOGD / f"sweep_{label}_distill.log", str(REPO / "pipeline"))
        if rc != 0:
            print(f"  distil FAILED rc={rc}", flush=True)
            results[label] = dict(error=f"distill rc={rc}")
            OUT.write_text(json.dumps(results, indent=2))
            continue

        print(f"  driving all sections...", flush=True)
        p = subprocess.run(
            [sys.executable, "evaluate.py", "--model", ckpt, "--student",
             "--channels", ch, "--fc", str(fc), "--in-w", str(in_w), "--in-h", str(in_h),
             "--direction", "all", "--weather", "clear", "--max-steps", "2000"],
            cwd=str(REPO / "pipeline"), capture_output=True, text=True,
            env=dict(os.environ, STUDY_MAP="Town06", PYTHONUNBUFFERED="1"))
        secs = parse_sections(p.stdout + p.stderr)
        with open(LOGD / f"sweep_{label}_drive.log", "w") as f:
            f.write(p.stdout + p.stderr)

        n_ok = sum(1 for v in secs.values() if v["passed"])
        worst = max((v["max_cte_ft"] or 0.0) for v in secs.values()) if secs else None
        results[label] = dict(in_w=in_w, in_h=in_h, channels=ch, fc=fc,
                              sections=secs, n_pass=n_ok, n=len(secs),
                              worst_cte_ft=worst, minutes=round((time.time() - t0) / 60, 1))
        OUT.write_text(json.dumps(results, indent=2))
        straights = {s: secs.get(s, {}).get("max_cte_ft") for s in ("s01", "s03")}
        print(f"  {label}: {n_ok}/{len(secs)} sections, worst {worst} ft, "
              f"straights(s01,s03)={straights}  [{results[label]['minutes']} min]",
              flush=True)

    print("\n===== SWEEP SUMMARY (distilled only, no student DAgger) =====", flush=True)
    print(f"{'config':12s} {'ReLU':>7s} {'pass':>6s} {'worst_ft':>9s} "
          f"{'s01_ft':>8s} {'s03_ft':>8s}", flush=True)
    for label, _, _, ch, fc in CONFIGS:
        r = results.get(label)
        if not r or "sections" not in r:
            continue
        chs = tuple(int(x) for x in r["channels"].split(","))
        n = C.relu_count(chs, r["fc"], r["in_h"], r["in_w"])
        s01 = r["sections"].get("s01", {}).get("max_cte_ft")
        s03 = r["sections"].get("s03", {}).get("max_cte_ft")
        print(f"{label:12s} {n:7,} {r['n_pass']}/{r['n']:<4} {r['worst_cte_ft']:9} "
              f"{s01:8} {s03:8}", flush=True)
    print(f"\nwrote {OUT}", flush=True)


if __name__ == "__main__":
    main()

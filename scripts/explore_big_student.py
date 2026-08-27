#!/usr/bin/env python3
"""EXPLORE PHASE 2: make the mixed student WORK. Size is not being minimised.

Under PROTOCOL amendment A-1 (R1 suspended). Nothing here is a blind prediction.

The only hard constraint is that the student stay formally verifiable on this GPU, even
slowly. Measured ceiling (random weights, CARLA down, full card free):

    ReLU      s/pose   GPU mem   bound width   245 poses x 6 cells
     21,408    1.92     218 M      0.1 x tol       0.78 h
     68,640    1.67     1.2 G      0.2 x tol       0.68 h
    119,856    1.79     2.1 G      0.0 x tol       0.73 h
    230,464    2.36     4.7 G      0.2 x tol       0.96 h
    324,672    3.69     7.8 G      0.5 x tol       1.51 h
    507,968      --      OOM           --            --

So the ceiling is ~325k ReLU, set by MEMORY, not by time and not by bound looseness --
widths stay well inside tolerance the whole way up. Everything below sits under it.

WHY AUGMENTATION IS IN THIS SWEEP. Capacity stopped helping because KD had no
regulariser at all: the w4 student (246k params, 122k frames) hit its best validation at
epoch 19 and overfit, so it fit WORSE than a model half its size. Scaling up without a
regulariser would repeat that at every rung. The first rung isolates it -- same
architecture as the current student, augmentation the only change -- because if jitter
alone fixes night, no larger model is needed.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/explore_big_student.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402

OUT = REPO / "results" / "town06" / "explore_big_student.json"
LOGD = REPO / "results" / "town06_logs"
CONDS = ["clear", "fog", "night", "shadows"]

# (label, in_w, in_h, channels, fc, augment)
CONFIGS = [
    ("168x28_w2_aug", 168, 28, "16,32,32", 64, 0.30),   # isolates AUGMENTATION alone
    ("224x64_w2_aug", 224, 64, "16,32,32", 64, 0.30),   # ~ the teacher's own 200x66
    ("320x64_w3_aug", 320, 64, "24,48,48", 96, 0.30),   # bigger both ways
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


def carla_ready():
    return subprocess.run([sys.executable, str(REPO / "scripts" / "wait_carla_ready.py"),
                           "--timeout", "240"]).returncode == 0


def main():
    if "CARLA_PORT" not in os.environ:
        sys.exit("set CARLA_PORT")
    reps = int(os.environ.get("REPS", "2"))
    results = json.loads(OUT.read_text()) if OUT.exists() else {}
    LOGD.mkdir(parents=True, exist_ok=True)

    for label, iw, ih, ch, fc, aug in CONFIGS:
        if label in results:
            print(f"SKIP {label}", flush=True)
            continue
        ck = f"S_mixed_t06_{label}"
        relu = C.relu_count(tuple(int(x) for x in ch.split(",")), fc, ih, iw)
        if not (Path(C.CHECKPOINT_DIR) / f"{ck}.pth").exists():
            # Distillation is GPU work and needs no simulator. CARLA resident has killed
            # a distil already (T06-F12), and the big inputs here need the whole card.
            subprocess.run(["pkill", "-f", "[C]arlaUE4-Linux-Shipping"])
            import time as _t
            _t.sleep(10)
            print(f"\n=== {label}: distilling {iw}x{ih}, {relu:,} ReLU, augment {aug} ===",
                  flush=True)
            with open(LOGD / f"big_{label}.log", "w") as f:
                rc = subprocess.run(
                    [sys.executable, "distill.py", "--in-w", str(iw), "--in-h", str(ih),
                     "--out", ck, "--teacher", TEACHER, "--base", "mixed_t06",
                     "--dagger-dirs", "dagger_mixed_t06", "--channels", ch,
                     "--fc", str(fc), "--augment", str(aug), "--epochs", "200"],
                    cwd=str(REPO / "pipeline"), stdout=f, stderr=subprocess.STDOUT,
                    env=dict(os.environ, STUDY_MAP="Town06",
                             PYTHONUNBUFFERED="1")).returncode
            if rc != 0:
                print(f"  distil FAILED rc={rc} (see big_{label}.log)", flush=True)
                results[label] = dict(error=f"distill rc={rc}", relu=relu)
                OUT.write_text(json.dumps(results, indent=2))
                continue
            for ln in open(LOGD / f"big_{label}.log"):
                if "BEST KD" in ln:
                    print("  " + ln.strip(), flush=True)

        if not carla_ready():
            subprocess.Popen(
                ["setsid", "nohup", "./CarlaUE4.sh", f"-carla-rpc-port={os.environ['CARLA_PORT']}",
                 "-RenderOffScreen", "-quality-level=Epic"],
                cwd=os.path.expanduser("~/carla"),
                stdout=open(LOGD / "carla.log", "a"), stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, start_new_session=True)
            if not carla_ready():
                sys.exit("CARLA did not become ready")
        Path("/tmp/carla-locks/carla-3000.lock").unlink(missing_ok=True)

        print(f"\n=== {label} ({relu:,} ReLU): all four conditions ===", flush=True)
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
                              augment=aug, relu=relu, conditions=per,
                              total_fails=sum(v["fails"] for v in per.values()),
                              total_n=sum(v["n"] for v in per.values()))
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(results, indent=2))
        print(f"  -> {results[label]['total_fails']}/{results[label]['total_n']} "
              f"failures overall", flush=True)

    print("\n===== BIG STUDENT SWEEP (failures / runs) =====", flush=True)
    print(f"{'config':16s} {'ReLU':>9s} {'aug':>5s} " +
          " ".join(f"{c:>9s}" for c in CONDS) + f" {'total':>8s}", flush=True)
    for label, _, _, _, _, aug in CONFIGS:
        r = results.get(label)
        if not r or "conditions" not in r:
            continue
        row = " ".join(f"{r['conditions'][c]['fails']:2d}/{r['conditions'][c]['n']:<2d}".rjust(9)
                       for c in CONDS if c in r["conditions"])
        print(f"{label:16s} {r['relu']:9,} {aug:5.2f} {row} "
              f"{r['total_fails']:3d}/{r['total_n']:<4d}", flush=True)
    print("\n  baseline 168x28 w2, no augment, 21,408 ReLU: "
          "clear 0/12 fog 5/12 night 8/12 shadows 1/12 = 14/48", flush=True)


if __name__ == "__main__":
    main()

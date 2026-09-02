#!/usr/bin/env python3
"""Drive named STUDENT checkpoints over the same laps and report them side by side.

    STUDY_MAP=Town06 python3 scripts/compare_student_variants.py \
        --checkpoints S_mixed_t06lap_168x28_w3 S_mixed_t06lap_168x28_w3_dagger_r02 \
        --channels 24,48,48 --fc 96 --reps 3

WHY THIS EXISTS. Two questions about the students have been argued from evidence that was
later discarded, and neither has ever been measured on the corrected harness:

  * T06-F14 removed student DAgger after measuring it as HARMFUL at 168x28
    ("mixed w2 distilled only 6/6, after 4 DAgger rounds 3/6"). T06-F25 pointed out that
    A-2 discarded the data that finding rests on, and restored the stage -- explicitly
    asking for the comparison to be re-run on the corrected harness. Nobody ran it.
  * distill.py's straight-frame balancing is OFF by default, and its own comment predicts
    the consequence on this map: 83.8% of the Town06 lap needs |steer| <= 0.01, so "a
    student learns to emit ~0 with a small offset and the straight sections then integrate
    that offset into a departure. The teachers absorb the imbalance because they have
    ~107k ReLU; a 5-15k ReLU student does not."

Both are one-line changes to the pipeline whose effect is a driven measurement, so the
answer has to be driven. This is that instrument: same route, same conditions, a clean
server before EVERY lap (A-4), one process per lap, and the variants differ only in the
checkpoint named.

It writes nothing to the ledger and reads no certificate. It is training telemetry under
PROTOCOL section 5, not a scored result.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.environ.setdefault("CARLA_PORT", "3000")
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402


def restart_carla(log):
    """A clean server before every lap (A-4). Never capture_output: carla_restart.sh
    daemonises CARLA and the detached child inherits the pipe, so the call never returns.
    """
    with open(log, "a") as fh:
        for cmd, lim in ((["bash", str(REPO / "scripts" / "carla_restart.sh")], 420),
                         ([sys.executable, str(REPO / "scripts" / "wait_carla_ready.py"),
                           "--timeout", "200"], 240)):
            try:
                subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL, timeout=lim,
                               env=dict(os.environ))
            except subprocess.TimeoutExpired:
                print(f"      !! restart step exceeded {lim}s; continuing", flush=True)


def drive(ckpt, channels, fc, in_w, in_h, weather):
    """One lap. Returns (max_cte_ft, over_budget_frac, steps) or None if the run failed."""
    cmd = [sys.executable, "evaluate.py", "--model", ckpt, "--direction", "all",
           "--weather", weather, "--max-steps", "2000", "--channels", channels,
           "--fc", str(fc), "--student", "--in-w", str(in_w), "--in-h", str(in_h)]
    p = subprocess.run(cmd, cwd=str(REPO / "pipeline"), capture_output=True, text=True,
                       env=dict(os.environ, STUDY_MAP=C.STUDY_MAP, PYTHONUNBUFFERED="1"))
    out = p.stdout + p.stderr
    for line in out.splitlines():
        t = line.strip()
        for sec in C.SECTIONS:
            if t.startswith(f"{sec} ") and ("PASS" in t or "FAIL" in t):
                cte = over = steps = None
                if "max|CTE|=" in t:
                    cte = float(t.split("max|CTE|=")[1].split("ft")[0])
                # evaluate.py prints "over-budget=", not "over=". Searching for the
                # shorter string silently matched nothing and reported 0.0% over budget
                # next to a 12.46 ft peak -- a contradiction that looks like a result.
                if "over-budget=" in t:
                    over = float(t.split("over-budget=")[1].split("%")[0]) / 100.0
                if "steps=" in t:
                    steps = int(t.split("steps=")[1].split()[0].strip(","))
                # R-SIM-6: a run that ends far short of its step budget is a DEPARTURE,
                # and reporting only |CTE| hides that. steps_for is the full lap.
                full = C.steps_for(sec)
                return dict(max_cte_ft=cte, over=over, steps=steps, full_steps=full,
                            departed=bool(steps is not None and steps < 0.9 * full),
                            passed="PASS" in t)
    # A run that produced no summary line is a FAILED RUN, not a failing student.
    return dict(error=True, tail=out.strip().splitlines()[-4:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoints", nargs="+", required=True)
    ap.add_argument("--channels", required=True, help="e.g. 24,48,48")
    ap.add_argument("--fc", type=int, required=True)
    ap.add_argument("--reps", type=int, default=3, help="laps per checkpoint (A-4: 3)")
    ap.add_argument("--weather", default="clear")
    ap.add_argument("--in-w", type=int, default=None)
    ap.add_argument("--in-h", type=int, default=None)
    ap.add_argument("--out", default="results/town06/student_variants.json")
    args = ap.parse_args()
    in_w = args.in_w or C.TOWN06_INPUT_W
    in_h = args.in_h or C.TOWN06_INPUT_H

    log = REPO / "results" / "town06_logs" / "student_variants_restart.log"
    log.parent.mkdir(parents=True, exist_ok=True)

    missing = [c for c in args.checkpoints
               if not (Path(C.CHECKPOINT_DIR) / f"{c}.pth").exists()]
    if missing:
        sys.exit(f"missing checkpoint(s): {', '.join(missing)}")

    print(f"\nSTUDENT VARIANT COMPARISON -- {args.weather}, {args.reps} lap(s) each, "
          f"clean server before every lap")
    print(f"  budget {C.CTE_BUDGET_FT:.2f} ft\n")
    results = {}
    for ck in args.checkpoints:
        laps = []
        for rep in range(args.reps):
            restart_carla(log)
            t0 = time.time()
            r = drive(ck, args.channels, args.fc, in_w, in_h, args.weather)
            r["rep"] = rep
            r["sec"] = round(time.time() - t0, 1)
            laps.append(r)
            if r.get("error"):
                print(f"  {ck:44s} lap{rep}  RUN FAILED")
                for ln in r["tail"]:
                    print(f"      {ln}")
            else:
                ov = "  n/a" if r["over"] is None else f"{100 * r['over']:5.1f}%"
                print(f"  {ck:44s} lap{rep}  max|CTE| {r['max_cte_ft']:7.2f} ft "
                      f"over {ov}  steps {r['steps']}/{r['full_steps']}"
                      f"{'  DEPARTED' if r['departed'] else ''}  "
                      f"{'PASS' if r['passed'] else 'FAIL'}")
        results[ck] = laps

    print(f"\n{'checkpoint':46s} {'laps held':>10s} {'worst |CTE|':>12s} {'% of budget':>12s}")
    for ck, laps in results.items():
        good = [l for l in laps if not l.get("error")]
        held = sum(1 for l in good if l["passed"])
        worst = max((l["max_cte_ft"] for l in good), default=float("nan"))
        print(f"{ck:46s} {held:>6d}/{len(laps):<3d} {worst:11.2f}ft "
              f"{100 * worst / C.CTE_BUDGET_FT:11.0f}%")

    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(weather=args.weather, reps=args.reps,
                                   budget_ft=C.CTE_BUDGET_FT, results=results),
                              indent=2))
    print(f"\n  -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

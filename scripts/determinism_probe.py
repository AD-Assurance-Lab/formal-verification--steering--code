#!/usr/bin/env python3
"""Are two identical runs actually identical? And if not, where do they diverge?

CARLA is deterministic in synchronous mode with a fixed timestep, and this study pins
the timestep, the substepping, the spawn, the weather and the camera exposure. So three
repetitions of one cell ought to produce three identical traces -- and a competence gate
reporting "held 2/3" ought to be impossible.

It is not impossible in practice, so this measures it: run the SAME checkpoint, section
and condition N times, each on a freshly restarted server, and compare the full
per-step trace rather than just the summary. Reports the first step at which any pair
diverges and by how much, which is what identifies the source.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/determinism_probe.py --reps 3
"""
import argparse
import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402


def one_run(ck, ch, fc, iw, ih, sec, cond, restart):
    if restart:
        logp = REPO / "results" / "town06_logs" / "restart_inline.log"
        with open(logp, "a") as fh:
            subprocess.run(["bash", str(REPO / "scripts" / "carla_restart.sh")],
                           stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                           timeout=300, env=dict(os.environ))
    p = subprocess.run(
        [sys.executable, "evaluate.py", "--model", ck, "--student", "--channels", ch,
         "--fc", str(fc), "--in-w", str(iw), "--in-h", str(ih), "--direction", sec,
         "--weather", cond, "--max-steps", "2000"],
        cwd=str(REPO / "pipeline"), capture_output=True, text=True,
        env=dict(os.environ, STUDY_MAP="Town06", PYTHONUNBUFFERED="1"))
    src = REPO / "pipeline" / C.RESULTS_SUBDIR / f"eval_{ck}_{sec}.csv" \
        if hasattr(C, "RESULTS_SUBDIR") else Path(C.RESULTS_DIR) / f"eval_{ck}_{sec}.csv"
    if not src.exists():
        src = Path(C.RESULTS_DIR) / f"eval_{ck}_{sec}.csv"
    rows = list(csv.DictReader(open(src))) if src.exists() else []
    return rows, (p.stdout + p.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--section", default="s02")
    ap.add_argument("--cond", default="clear")
    ap.add_argument("--ck", default="S_clear_t06_168x28_w2")
    ap.add_argument("--channels", default="16,32,32")
    ap.add_argument("--fc", type=int, default=64)
    ap.add_argument("--in-w", type=int, default=168)
    ap.add_argument("--in-h", type=int, default=28)
    ap.add_argument("--no-restart", action="store_true")
    args = ap.parse_args()

    traces = []
    for i in range(args.reps):
        rows, _ = one_run(args.ck, args.channels, args.fc, args.in_w, args.in_h,
                          args.section, args.cond, not args.no_restart)
        traces.append(rows)
        mx = max((abs(float(r["cte_ft"])) for r in rows), default=float("nan"))
        print(f"  rep {i}: {len(rows):4d} steps, max|CTE| {mx:6.2f} ft", flush=True)

    print(f"\n  pairwise comparison of the per-step traces:")
    for a in range(len(traces)):
        for b in range(a + 1, len(traces)):
            ta, tb = traces[a], traces[b]
            n = min(len(ta), len(tb))
            first = None
            worst = 0.0
            for k in range(n):
                d = abs(float(ta[k]["cte_ft"]) - float(tb[k]["cte_ft"]))
                ds = abs(float(ta[k]["nn_steer"]) - float(tb[k]["nn_steer"]))
                if first is None and (d > 1e-9 or ds > 1e-9):
                    first = (k, d, ds)
                worst = max(worst, d)
            if first is None and len(ta) == len(tb):
                print(f"    rep{a} vs rep{b}: IDENTICAL ({n} steps)")
            else:
                k, d, ds = first if first else (n, 0, 0)
                print(f"    rep{a} vs rep{b}: diverge at step {k} of {n} "
                      f"(dCTE {d:.2e} ft, dsteer {ds:.2e}); "
                      f"max dCTE over the run {worst:.3f} ft; "
                      f"lengths {len(ta)} vs {len(tb)}")


if __name__ == "__main__":
    sys.exit(main())

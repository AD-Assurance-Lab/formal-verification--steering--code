#!/usr/bin/env python3
"""How reproducible is a closed-loop cell, and does driving order matter?

Two observations forced this:
  - s02/fog driven ALONE, three times: 9.74, 10.12, 9.74 ft -- all FAIL
  - s02/fog driven as part of --direction all: 1.52 and 0.73 ft -- both PASS
Same checkpoint, same section, same weather.

If that holds, a cell's result depends on whether its section was driven in isolation or
after other sections in the same process, which would make "12 runs" mean different
things in different scripts. Candidate cause is UE4 streaming textures and compiling
shaders on first visit to an area, so an isolated run drives partly on assets that have
not finished loading.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/measure_run_variance.py --passes 5
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

OUT = REPO / "results" / "town06" / "run_variance.json"


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


def drive(direction, cond, ck, ch, fc, iw, ih):
    p = subprocess.run(
        [sys.executable, "evaluate.py", "--model", ck, "--student", "--channels", ch,
         "--fc", str(fc), "--in-w", str(iw), "--in-h", str(ih),
         "--direction", direction, "--weather", cond, "--max-steps", "2000"],
        cwd=str(REPO / "pipeline"), capture_output=True, text=True,
        env=dict(os.environ, STUDY_MAP="Town06", PYTHONUNBUFFERED="1"))
    return parse(p.stdout + p.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--passes", type=int, default=5)
    ap.add_argument("--cond", default="fog")
    ap.add_argument("--ck", default="S_mixed_t06_320x64_w3")
    ap.add_argument("--channels", default="24,48,48")
    ap.add_argument("--fc", type=int, default=96)
    ap.add_argument("--in-w", type=int, default=320)
    ap.add_argument("--in-h", type=int, default=64)
    args = ap.parse_args()
    if "CARLA_PORT" not in os.environ:
        sys.exit("set CARLA_PORT")

    res = {"sequential": [], "isolated": []}
    print(f"{args.ck}, {args.cond}, {args.passes} passes each\n")

    print("A. SEQUENTIAL: --direction all, so each section follows the others")
    for i in range(args.passes):
        r = drive("all", args.cond, args.ck, args.channels, args.fc, args.in_w, args.in_h)
        res["sequential"].append({k: v["max_cte_ft"] for k, v in r.items()})
        f = sum(1 for v in r.values() if not v["passed"])
        print(f"  pass {i}: {f}/{len(r)} fail  " +
              " ".join(f"{k}={v['max_cte_ft']:.2f}" for k, v in sorted(r.items())),
              flush=True)

    print("\nB. ISOLATED: one process per section, each a fresh spawn")
    for i in range(args.passes):
        row = {}
        for sec in C.SECTIONS:
            r = drive(sec, args.cond, args.ck, args.channels, args.fc, args.in_w, args.in_h)
            if sec in r:
                row[sec] = r[sec]["max_cte_ft"]
        res["isolated"].append(row)
        nf = sum(1 for v in row.values() if v is not None and v > C.CTE_BUDGET_FT)
        print(f"  pass {i}: {nf}/{len(row)} over budget  " +
              " ".join(f"{k}={v:.2f}" for k, v in sorted(row.items())), flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2))

    print(f"\n{'section':8s} {'sequential (ft)':>34s} {'isolated (ft)':>34s}")
    for sec in C.SECTIONS:
        sq = [p.get(sec) for p in res["sequential"] if p.get(sec) is not None]
        iso = [p.get(sec) for p in res["isolated"] if p.get(sec) is not None]
        f = lambda v: " ".join(f"{x:5.2f}" for x in v)
        print(f"{sec:8s} {f(sq):>34s} {f(iso):>34s}")
    print(f"\nbudget {C.CTE_BUDGET_FT:.2f} ft")


if __name__ == "__main__":
    main()

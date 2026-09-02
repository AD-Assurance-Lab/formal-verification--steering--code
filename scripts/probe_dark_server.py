#!/usr/bin/env python3
"""How often does a CARLA server come up rendering DARK, and is it map-specific?

    python3 scripts/probe_dark_server.py --maps Town06 Town04 --launches 4

T06-F46 established the defect: a server comes up either correct or about 14% darker,
the state is decided at LAUNCH, and it is constant for that server's whole life (five
measurements against one bad server spread 4e-6). It happens headless and windowed. The
trigger is unidentified.

Two things are worth knowing before the study is written up, and neither is expensive:

  1. THE RATE. "Intermittent" is not a number. If one launch in eight is bad, a campaign
     of hundreds of restarts meets it constantly -- which is what the previous session's
     interleaved DAgger rounds look like.
  2. WHETHER TOWN04 SEES IT. Town04 is the published study and the reference this
     deployment test is compared against. If its servers are bimodal too, the defect is
     CARLA's and predates this route; if only Town06's are, it is something about this
     map or how hard it has been exercised.

This launches a fresh server per sample and measures the same fixed-pose frame
check_render_photometry.py uses, so the numbers are directly comparable to the committed
reference. It writes nothing the study consumes.
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


def launch(study_map, log):
    """A fresh server for `study_map`. Returns True if it came up."""
    env = dict(os.environ, STUDY_MAP=study_map, CARLA_WINDOWED="0",
               CARLA_SKIP_PHOTOMETRY="1")
    with open(log, "a") as fh:
        try:
            # carla_restart.sh, not carla_launch.sh: we want the full stop/start, and we
            # must NOT let the launcher's own photometry retry hide the thing we measure.
            subprocess.run(["bash", str(REPO / "scripts" / "carla_restart.sh")],
                           stdout=fh, stderr=subprocess.STDOUT,
                           stdin=subprocess.DEVNULL, timeout=420, env=env)
        except subprocess.TimeoutExpired:
            return False
    return True


def measure(study_map):
    """Spawn-frame brightness, via the same instrument the gate uses."""
    code = (
        "import sys,os,json;"
        "sys.path.insert(0,'scripts');sys.path.insert(0,'pipeline');"
        "import check_render_photometry as m;"
        "v,s,l=m.measure('clear');"
        "print(json.dumps({'mean':v,'std':s,'labels':l}))"
    )
    env = dict(os.environ, STUDY_MAP=study_map)
    p = subprocess.run([sys.executable, "-c", code], cwd=str(REPO), env=env,
                       capture_output=True, text=True)
    for line in reversed((p.stdout or "").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--maps", nargs="+", default=["Town06", "Town04"])
    ap.add_argument("--launches", type=int, default=4)
    ap.add_argument("--out", default="results/dark_server_probe.json")
    args = ap.parse_args()

    log = REPO / "results" / "town06_logs" / "dark_server_probe_restart.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    ref = json.loads((REPO / "results" / "photometry_reference.json").read_text())

    out = {}
    for m in args.maps:
        print(f"\n=== {m}: {args.launches} fresh servers ===", flush=True)
        samples = []
        for i in range(args.launches):
            t0 = time.time()
            if not launch(m, log):
                print(f"  launch {i}: server did not come up", flush=True)
                continue
            r = measure(m)
            if r is None:
                print(f"  launch {i}: measurement failed", flush=True)
                continue
            r["launch"] = i
            r["sec"] = round(time.time() - t0, 1)
            samples.append(r)
            key = f"{m}/clear"
            base = ref.get(key, {}).get("mean")
            rel = (100 * (r["mean"] - base) / base) if base else float("nan")
            print(f"  launch {i}: mean {r['mean']:.6f}"
                  + (f"  {rel:+.2f}% vs reference" if base else "  (no reference)")
                  + f"  [{time.time()-t0:.0f}s]", flush=True)
        out[m] = samples
        if len(samples) >= 2:
            vals = sorted(s["mean"] for s in samples)
            print(f"  -> {len(samples)} servers, min {vals[0]:.6f} max {vals[-1]:.6f}, "
                  f"spread {100*(vals[-1]-vals[0])/vals[-1]:.2f}%", flush=True)

    p = REPO / args.out
    p.write_text(json.dumps(out, indent=2))
    print(f"\n  -> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env bash
# Finish the Town04 redo: gate, certificate, and a ledger driven by a committed script.
#
# Town04 is the DISCOVERY test. T_CLOSED_LOOP_S was back-solved from its own stability
# cliff, so its agreement measures sensitivity, not prediction, and PROTOCOL.md section 1
# says so. There is deliberately NO certificate-before-drive ordering here: imposing one
# would dress a sensitivity result up as a prediction claim.
#
# What IS redone, and why:
#   captures   already recaptured at the 2,861 m SCORED length with a restart before each
#   gate       redriven with a restart before EVERY drive (it restarted once for all)
#   ledger     redriven through run_town04_ledger.sh -- the old one was hand-driven, so
#              its restart discipline cannot be established after the fact (one
#              restart.log, overwritten). That is standing rule 8.
#
# Waits for the Town06 rebuild first: one client per port (R-SIM-3).
#
#   bash scripts/finish_town04_rebuild.sh
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town04 TOWN04_REDO=1
export CARLA_PORT=${CARLA_PORT:-3000}
export CARLA_WINDOWED=${CARLA_WINDOWED:-1} DISPLAY=${DISPLAY:-:0}
export PYTHONUNBUFFERED=1

LOG=$REPO/results/town04_v2/logs
mkdir -p "$LOG"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG/rebuild.log"; }
die() { say "FATAL: $*"; exit 1; }

# R-SIM-3: two clients ticking one server corrupt each other's runs while both look fine.
while pgrep -f "[f]inish_town06_rebuild" >/dev/null; do sleep 60; done
say "Town06 rebuild finished; starting Town04"

N=$(ls results/town04_v2/calibration/lap_*.npz 2>/dev/null | wc -l)
[ "$N" -eq 8 ] || die "expected 8 Town04 captures, found $N"

say "1/4 gate drives (2 students x 2 directions, restart before each)"
python3 scripts/capture_gate_drives.py >"$LOG/gate_drives_rebuild.log" 2>&1 \
    || die "gate drives failed, see $LOG/gate_drives_rebuild.log"

say "2/4 capture gate + certificate"
bash scripts/certify_town04.sh >"$LOG/certify_rebuild.log" 2>&1 \
    || die "gate or certification failed, see $LOG/certify_rebuild.log"
say "    $(grep -E '^  worst' "$LOG/certify_rebuild.log" | tail -1)"

STAMP=$(date '+%Y%m%d_%H%M')
mkdir -p "results/town04_v2/_superseded_$STAMP/ledger"
mv results/town04_v2/ledger/*.json "results/town04_v2/_superseded_$STAMP/ledger/" 2>/dev/null
say "3/4 superseded ledger -> results/town04_v2/_superseded_$STAMP"

say "    ledger (8 cells, restart before each, logged per cell)"
bash scripts/run_town04_ledger.sh >"$LOG/ledger_rebuild.log" 2>&1 \
    || die "ledger failed, see $LOG/ledger_rebuild.log"

say "4/4 agreement"
python3 - <<'PY' 2>&1 | tee -a "$LOG/rebuild.log"
import json, glob, os, sys
sys.path.insert(0, "pipeline")
c = json.load(open("results/town04_v2/calibration/sustained_bound.json"))
led = {}
for p in glob.glob("results/town04_v2/ledger/*.json"):
    d = json.load(open(p))
    led[(d["condition"], d["student"])] = d["verdict"]
rows, agree, tot = [], 0, 0
for stu in sorted({k.split("/")[1] for k in c if "/" in k}):
    for cond in ("fog", "night", "shadows"):
        vs = [c[f"{d}/{stu}/{cond}"]["verdict"] for d in ("westbound", "eastbound")
              if f"{d}/{stu}/{cond}" in c]
        if len(vs) < 2:
            continue
        cell = "CERTIFIED" if all(v == "CERTIFIED" for v in vs) else "FALSIFIED"
        drive = next((v for (cd_, st), v in led.items()
                      if cd_ == cond and st.startswith(stu)), None)
        if drive is None:
            continue
        ok = (cell == "CERTIFIED") == (drive == "PASS")
        agree += ok; tot += 1
        rows.append(f"  {stu:9s} {cond:8s} {vs[0]:10s} {vs[1]:10s} {cell:10s} "
                    f"{drive:5s} {'AGREE' if ok else 'DISAGREE'}")
print("\n".join(rows))
print(f"\n  agreement on scored cells: {agree}/{tot}  (DISCOVERY test: sensitivity, "
      f"not prediction)")
PY
say "TOWN04 REBUILD COMPLETE"

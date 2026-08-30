#!/usr/bin/env bash
# Scored closed-loop ledger for the Town04 redo (the DISCOVERY test).
#
# This did not exist. The Town04 redo's ledger was driven by hand, which is standing
# rule 8 -- if a number goes in a paper the invocation is a script in the repo -- and
# it is the same gap that let a 160 m capture default into a certificate: the two maps
# differed only in that Town06 had committed drivers and Town04 did not.
#
# Its restart discipline was therefore unprovable after the fact: results/town04_v2/logs/
# ledger/ holds one restart.log, overwritten, so nothing records whether the server was
# restarted between cells. R-SIM-1 is enforced here, per cell, and logged per cell.
#
# NOT under PROTOCOL R1, and deliberately so. Town04 is the discovery test:
# T_CLOSED_LOOP_S was back-solved from its own stability cliff, so its agreement measures
# SENSITIVITY, not prediction, and PROTOCOL.md section 1 says so. Imposing a
# certificate-before-drive ordering here would dress a discovery test up as a prediction
# claim, which that section calls worth less than no test at all. closed_loop_ledger.py
# already skips the R1 guard for Town04 for this reason.
#
#   bash scripts/run_town04_ledger.sh
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town04 TOWN04_REDO=1
export CARLA_PORT=${CARLA_PORT:-3000}
export PYTHONUNBUFFERED=1

LOG_DIR=$REPO/results/town04_v2/logs/ledger
mkdir -p "$LOG_DIR"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG_DIR/ledger.log"; }

# An override left exported silently changes what a canonical cell measures, and the
# cell name would not say so.
for v in FOG_DENSITY_OVERRIDE SUN_ALTITUDE_OVERRIDE ROUTE_ROLL OY_OFFSETS OY_YAWS OY_CONDS; do
    if [ -n "${!v:-}" ]; then say "FATAL: $v is set ($(printf '%s' "${!v}")) -- unset it"; exit 1; fi
done

carla_up() { for i in $(seq 1 "${1:-60}"); do
    ss -ltn 2>/dev/null | grep -q ":$CARLA_PORT" && return 0; sleep 5; done; return 1; }
carla_restart() {   # $1 = cell tag, so the restart is auditable per cell
    say "restarting CARLA on port $CARLA_PORT (before $1)"
    pkill -f "[C]arlaUE4-Linux-Shipping.*rpc-port=$CARLA_PORT" 2>/dev/null; sleep 8
    bash "$REPO/scripts/carla_launch.sh" > "$LOG_DIR/restart_$1.log" 2>&1
    carla_up 60 && { say "CARLA back up"; sleep 10; return 0; }
    say "FATAL: CARLA did not return"; return 1; }
carla_up 12 || carla_restart boot || exit 1

mapfile -t STUDENT_ROWS < <(STUDY_MAP=Town04 TOWN04_REDO=1 python3 -c "
import sys; sys.path.insert(0,'pipeline'); import config as C
for nm, ck, ch, fc in C.STUDENTS:
    print(ck, ','.join(str(c) for c in ch), fc)")

for ROW in "${STUDENT_ROWS[@]}"; do
  read -r BASE CH FC <<<"$ROW"
  # Drive the FINAL student -- Town04's procedure includes student DAgger, so the
  # checkpoint that IS the student is the newest round, not the distilled intermediate.
  STU=$(STUDY_MAP=Town04 TOWN04_REDO=1 python3 -c "import sys;sys.path.insert(0,'pipeline');import config as C;print(C.final_student('$BASE'))")
  say "student $BASE -> $STU"
  for COND in clear fog night shadows; do
    CELL="$REPO/results/town04_v2/ledger/${COND}__${BASE}__closed_loop.json"
    if [ -f "$CELL" ]; then say "SKIP  $COND/$BASE (cell exists)"; continue; fi
    carla_restart "${COND}_${BASE}" || exit 1
    rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null
    say "START $COND/$BASE"
    # Two directions x 6 reps = 12 runs per cell, over the >= 10 floor (standing rule 3).
    if python3 scripts/closed_loop_ledger.py --student "$BASE" --condition "$COND" \
         --reps 6 --channels "$CH" --fc "$FC" --w 84 --h 28 \
         >>"$LOG_DIR/${COND}_${BASE}.log" 2>&1; then
        say "OK    $COND/$BASE"
    else
        say "FAIL  $COND/$BASE (see $LOG_DIR/${COND}_${BASE}.log)"; exit 1
    fi
  done
done

say "LEDGER COMPLETE."

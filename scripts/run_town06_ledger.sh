#!/usr/bin/env bash
# Scored closed-loop ledger for the Town06 deployment test.
#
# THIS SCRIPT DRIVES. It must not be run until the certificate exists AND is committed
# (PROTOCOL R1). closed_loop_ledger.py enforces that itself and will refuse, so the
# check below is a clearer early failure, not the guard.
#
# Eight cells (2 students x 4 conditions), six of them scored -- the same six as Town04.
# Sections are REPETITIONS inside a cell, exactly as Town04's two directions are: 6
# sections x 2 reps = 12 runs per cell, over the >= 10 floor.
#
#   bash scripts/run_town06_ledger.sh
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06
export CARLA_PORT=${CARLA_PORT:-3000}
export PYTHONUNBUFFERED=1

# THREE LAPS (PROTOCOL A-4). A Town06 lap is every scored section driven once; three
# laps is a reproducibility check, not a rate estimate. This drove TWO.
LAPS=${LAPS:-3}
NSEC=$(STUDY_MAP=Town06 python3 -c "import sys;sys.path.insert(0,'pipeline');import config as C;print(len(C.SECTIONS))")

LOG_DIR=$REPO/results/town06_logs
mkdir -p "$LOG_DIR"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG_DIR/ledger.log"; }

python3 scripts/check_protocol_lock.py >/dev/null || { say "FATAL: PROTOCOL lock"; exit 1; }
python3 scripts/check_order_town06.py  >/dev/null || {
    say "FATAL: PROTOCOL R1 -- certificate is missing, uncommitted or dirty."
    say "Certify and COMMIT before driving. Refusing to run."; exit 1; }
say "R1 satisfied: certificate is committed. Driving may begin."

# Any override left exported would silently change what a canonical cell measures.
for v in FOG_DENSITY_OVERRIDE SUN_ALTITUDE_OVERRIDE ROUTE_ROLL OY_OFFSETS OY_YAWS OY_CONDS; do
    if [ -n "${!v:-}" ]; then say "FATAL: $v is set ($(printf '%s' "${!v}")) -- unset it"; exit 1; fi
done

CARLA_ROOT=${CARLA_ROOT:-$HOME/carla}
carla_up() { for i in $(seq 1 "${1:-60}"); do
    ss -ltn 2>/dev/null | grep -q ":$CARLA_PORT" && return 0; sleep 5; done; return 1; }
carla_restart() {
    # RETRY A TRANSIENT, via the one place that decides how many times
    # (scripts/carla_restart_retry.sh). The ledger drives 24 laps with a restart before
    # each, so a boot that occasionally misses its 300 s window is a certainty over a
    # stage rather than a risk -- and this stage's output is the published number.
    #
    # Measured 2026-09-03: seven of eight cells were complete and twenty-three laps
    # driven when one server failed to come up, and the whole ledger failed on the last
    # rep of the last cell. Every other driver had grown its own retry; the ledger, the
    # one whose result gets published, had none.
    say "restarting CARLA on port $CARLA_PORT"
    # NOT `... | tee ... ; then`: a pipeline's status is the LAST command's, so tee's
    # success would mask the retry's failure -- the same masking this repo already fixed
    # once in the capture gate. Capture the status, then show the output.
    bash "$REPO/scripts/carla_restart_retry.sh" \
        "$LOG_DIR/ledger_restart.log" "ledger" >>"$LOG_DIR/ledger_run.log" 2>&1
    if [ $? -ne 0 ]; then
        say "restart failed after retries"; return 1
    fi
    say "CARLA back up"; sleep 5; return 0
    say "FATAL: CARLA did not return"; return 1; }
carla_up 12 || carla_restart || exit 1

# CARLA leaks ~10.5 GiB over 11 h and drifts near the stability cliff. A fresh server
# per cell costs ~40 s and removes accumulated state as an explanation for any result.
# One definition, in config: name | channels | fc
mapfile -t STUDENT_ROWS < <(STUDY_MAP=Town06 python3 -c "
import sys; sys.path.insert(0,'pipeline'); import config as C
for nm, ck, ch, fc in C.TOWN06_STUDENTS:
    print(ck, ','.join(str(c) for c in ch), fc, C.TOWN06_INPUT_W, C.TOWN06_INPUT_H)")

for ROW in "${STUDENT_ROWS[@]}"; do
  read -r BASE CH FC IN_W IN_H <<<"$ROW"
  # Drive the FINAL student (newest student-DAgger round), not the distilled base.
  STU=$(STUDY_MAP=Town06 python3 -c "import sys;sys.path.insert(0,'pipeline');import config as C;print(C.final_student('$BASE'))")
  say "student $BASE -> $STU"
  for COND in clear fog night low_sun; do
    CELL="$REPO/results/town06/ledger/${COND}__${STU}__closed_loop.json"
    if [ -f "$CELL" ]; then say "SKIP  $COND/$STU (cell exists)"; continue; fi
    say "START $COND/$STU"
    # ONE PROCESS AND ONE SERVER PER RUN.
    #
    # R-SIM-1 says restart before every measurement RUN. This restarted before every CELL
    # and drove twelve runs on one server with one vehicle, so the twelve repetitions were
    # two chains of six inheriting each other's physics state -- and a Wilson interval over
    # dependent trials is not the interval it claims to be.
    #
    # The restart is done BETWEEN processes rather than inside one, because killing the
    # server under a live carla.Client throws from a context Python cannot catch
    # ("terminate called", core dumped) and releasing every reference was not enough. A
    # process boundary is the only version that is certainly correct.
    RUN_OK=1
    for REP in $(seq 0 $((LAPS-1))); do
      for SEC in $(STUDY_MAP=Town06 python3 -c "import sys;sys.path.insert(0,'pipeline');import config as C;print(' '.join(C.SECTIONS))"); do
        RUNF="$REPO/results/town06/ledger/runs/${COND}__${STU}__${SEC}__rep0${REP}.json"
        [ -f "$RUNF" ] && { say "SKIP  $COND/$STU $SEC rep$REP (run exists)"; continue; }
        carla_restart || { RUN_OK=0; break; }
        rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null
        if ! python3 scripts/closed_loop_ledger.py --student "$STU" --condition "$COND" \
             --channels "$CH" --fc "$FC" --w "$IN_W" --h "$IN_H" \
             --only-section "$SEC" --only-rep "$REP" \
             >>"$LOG_DIR/ledger_${COND}_${STU}.log" 2>&1; then
            say "FAIL  $COND/$STU $SEC rep$REP"; RUN_OK=0; break
        fi
      done
      [ $RUN_OK -eq 1 ] || break
    done
    if [ $RUN_OK -eq 1 ] && python3 scripts/aggregate_ledger_runs.py \
         --condition "$COND" --cell "$STU" --expect $((LAPS*NSEC)) \
         >>"$LOG_DIR/ledger_${COND}_${STU}.log" 2>&1; then
        say "OK    $COND/$STU"
    else
        say "FAIL  $COND/$STU (see $LOG_DIR/ledger_${COND}_${STU}.log)"; exit 1
    fi
  done
done

say "LEDGER COMPLETE. Now: python3 scripts/compare_town06.py"

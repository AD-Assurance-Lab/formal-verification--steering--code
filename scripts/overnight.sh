#!/usr/bin/env bash
# Unattended overnight run: finish M3, then fill the ledger's left half (M4).
#
# GOAL, in Zach's words: a formally verifiable student mixed model that drives clear, fog,
# night and shadows. Verifiability is already established -- F12 measured 0.94-2.5% UNKNOWN
# at 10k-15k ReLU -- so what remains is making it drive, then recording the evidence.
#
# ---------------------------------------------------------------------------
# CARLA SAFETY. This machine is shared. Several hours were lost today to two servers on
# port 2000 and to `pkill -f CarlaUE4` taking down someone else's simulator.
#
#   * we run on CARLA_PORT (default 3000), never 2000
#   * we record OUR server's PID and kill ONLY that PID, never by name
#
# ---------------------------------------------------------------------------
# RESUMABLE. Background jobs on this box have died repeatedly. Every stage writes a marker
# on clean completion and is skipped on restart, so a kill costs the current stage, not the
# night. Stages are ordered so the blocking one runs first.
set -uo pipefail

export CARLA_PORT=${CARLA_PORT:-3000}
PY=/home/za/ad-assurance--workspace/sdp-crown--automated-driving--code/venv_sdp/bin/python
cd "$(dirname "$0")/.."
LOG=/tmp/claude-1000/-home-za-ad-assurance--workspace/2d554514-19ad-4b08-93b4-d6fc6b8b3af3/scratchpad
MARK=pipeline/checkpoints/.overnight_done
PIDFILE=/tmp/claude-1000/-home-za-ad-assurance--workspace/2d554514-19ad-4b08-93b4-d6fc6b8b3af3/scratchpad/my_carla.pid
mkdir -p "$MARK"

log() { echo "[$(date +%H:%M:%S)] $*"; }

carla_up() {
    timeout 45 $PY -c "
import carla, os
c = carla.Client('127.0.0.1', int(os.environ['CARLA_PORT'])); c.set_timeout(35.0)
c.get_world()" >/dev/null 2>&1
}

start_carla() {
    if carla_up; then log "CARLA on :$CARLA_PORT already healthy"; return 0; fi
    # Only ever kill the server WE started.
    if [ -f "$PIDFILE" ]; then
        local old; old=$(cat "$PIDFILE")
        if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
            log "killing OUR previous CARLA (pid $old)"; kill -9 "$old" 2>/dev/null; sleep 5
        fi
    fi
    log "starting CARLA on :$CARLA_PORT"
    ( cd /home/za/carla && DISPLAY=:0 setsid ./CarlaUE4.sh -quality-level=Epic \
        -windowed -ResX=1280 -ResY=720 -carla-rpc-port="$CARLA_PORT" \
        > "$LOG/carla_overnight.log" 2>&1 & echo $! > "$PIDFILE" )
    for _ in $(seq 1 24); do sleep 5; carla_up && { log "CARLA ready"; return 0; }; done
    log "CARLA FAILED to come up"; return 1
}

stage() {   # marker, description, then command
    local m="$1" desc="$2"; shift 2
    if [ -f "$MARK/$m" ]; then log "SKIP $m (already complete)"; return 0; fi
    start_carla || { log "aborting $m -- no CARLA"; return 1; }
    log "START $m -- $desc"
    if "$@"; then touch "$MARK/$m"; log "DONE $m"
    else log "FAILED $m (unmarked, will retry on rerun)"; fi
}

# --- A. student-DAgger on the mixed candidate (the blocking step) ------------
stage student_dagger_w3 "student-DAgger, mixed w3, 4 rounds x 4 conditions" \
    $PY -u pipeline/dagger_student.py --student S_mixed_84x28_w3 --w 84 --h 28 \
        --rounds 4 --weathers clear,fog,night,shadows --dagger-dir dagger_student_w3 \
        --teacher teacher_mixed_dagger_r07 --base conditions \
        --distill-dirs dagger_mixed,dagger_student_w3 --channels 24,48,48 --fc 96 \
        --beta0 0.6 --beta-decay 0.5

# --- B. student-DAgger on the CONTROL, clear only ----------------------------
# The negative control has to be a GOOD clear specialist. If S_clear is merely
# undertrained, "S_clear fails fog" is confounded -- it must fail because it never saw
# fog, not because it drives badly.
stage student_dagger_clear "student-DAgger, S_clear, clear only" \
    $PY -u pipeline/dagger_student.py --student S_clear_84x28 --w 84 --h 28 \
        --rounds 3 --weathers clear --dagger-dir dagger_student_clear \
        --teacher teacher_clear_dagger_r03 --base conditions \
        --distill-dirs dagger_clear,dagger_student_clear --channels 8,16,16 --fc 32 \
        --beta0 0.6 --beta-decay 0.5

log "############ stages A/B complete -- ledger cells next ############"

# --- C. M4: fill the ledger's left half --------------------------------------
# 2 students x 4 conditions x 10 reps x 2 directions, Wilson intervals. These ARE ledger
# cells, so they go to results/ledger/ under the canonical S_clear / S_mixed names.
#
# The final policy name is not known in advance -- student-DAgger emits
# <student>_dagger_r<NN> per round -- so it is discovered rather than hardcoded.
latest() {   # prefix -> newest matching checkpoint basename, or the prefix itself
    local p; p=$(ls -1 pipeline/checkpoints/"$1"_dagger_r*.pth 2>/dev/null | sort | tail -1)
    if [ -n "$p" ]; then basename "$p" .pth; else echo "$1"; fi
}

MIXED_FINAL=$(latest S_mixed_84x28_w3)
CLEAR_FINAL=$(latest S_clear_84x28)
log "ledger will use  mixed=$MIXED_FINAL  clear=$CLEAR_FINAL"

for cond in clear fog night shadows; do
    stage "ledger_mixed_$cond" "ledger cell S_mixed/$cond, 10 reps" \
        $PY -u scripts/closed_loop_ledger.py --student "$MIXED_FINAL" \
            --condition "$cond" --reps 10 --channels 24,48,48 --fc 96 \
            --cell-name S_mixed
done

for cond in clear fog night shadows; do
    stage "ledger_clear_$cond" "ledger cell S_clear/$cond, 10 reps" \
        $PY -u scripts/closed_loop_ledger.py --student "$CLEAR_FINAL" \
            --condition "$cond" --reps 10 --channels 8,16,16 --fc 32 \
            --cell-name S_clear
done

log "############ ledger left half complete ############"
$PY -m study.ledger || true

# Release OUR CARLA so the machine is free in the morning.
if [ -f "$PIDFILE" ]; then
    p=$(cat "$PIDFILE"); kill -0 "$p" 2>/dev/null && { kill -9 "$p"; log "released our CARLA (pid $p)"; }
fi
log "############ OVERNIGHT RUN COMPLETE ############"

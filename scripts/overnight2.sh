#!/usr/bin/env bash
# Phase 2: the closed-loop cells that were DEFERRED so verification could go first.
#
# WHY THIS SCRIPT EXISTS. overnight.sh fills the ledger left-to-right, which puts every
# closed-loop cell before its verification counterpart. That inverts the blind protocol in
# CLAUDE.md -- verification verdicts must be committed FIRST, or step 4 is a postdiction
# and the study's whole claim ("verification predicts, closed loop then agrees") is not
# demonstrated. So the four S_clear closed-loop cells were held back, the S_clear verify
# cells were run and committed, and this script now fills what was held back.
#
# Also reruns ledger_mixed_clear, which was lost when CARLA died mid-cell and cleanup
# raised out of the finally block, discarding 10 driven repetitions.
#
# Same CARLA hygiene as overnight.sh: our own port, and kill ONLY our own PID.
set -uo pipefail

export CARLA_PORT=${CARLA_PORT:-3000}
PY="${PYTHON:-python3}"
cd "$(dirname "$0")/.."
LOG="${LOG_DIR:-$(dirname "$0")/../results/logs}"
MARK=pipeline/checkpoints/.overnight2_done
PIDFILE=$LOG/my_carla2.pid
mkdir -p "$MARK" "$LOG"

log() { echo "[$(date +%H:%M:%S)] $*"; }

carla_up() {
    timeout 45 $PY -c "
import carla, os
c = carla.Client('127.0.0.1', int(os.environ['CARLA_PORT'])); c.set_timeout(35.0)
c.get_world()" >/dev/null 2>&1
}

start_carla() {
    if carla_up; then log "CARLA on :$CARLA_PORT already healthy"; return 0; fi
    if [ -f "$PIDFILE" ]; then
        old=$(cat "$PIDFILE")
        if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
            log "killing OUR previous CARLA (pid $old)"; kill -9 "$old" 2>/dev/null; sleep 5
        fi
    fi
    log "starting CARLA on :$CARLA_PORT"
    ( cd "${CARLA_ROOT:-$HOME/carla}" && DISPLAY=:0 setsid ./CarlaUE4.sh -quality-level=Epic \
        -windowed -ResX=1280 -ResY=720 -carla-rpc-port="$CARLA_PORT" \
        > "$LOG/carla_phase2.log" 2>&1 & )
    for _ in $(seq 1 24); do
        sleep 5
        if carla_up; then
            # Record the PID actually LISTENING on our port, not $! of the launcher.
            # overnight.sh recorded $! of `setsid ./CarlaUE4.sh`, which is a wrapper whose
            # child is the real binary -- so its kill hit the wrapper, CARLA survived, and
            # it logged "released our CARLA" anyway. Verified tonight: the server was still
            # on :3000 after that script exited. Resolving the listener keeps the promise
            # that we kill ours and only ours.
            record_carla_pid
            log "CARLA ready (pid $(cat "$PIDFILE" 2>/dev/null))"
            return 0
        fi
    done
    log "CARLA FAILED to come up"; return 1
}

record_carla_pid() {
    local pid
    pid=$(ss -lntpH "sport = :$CARLA_PORT" 2>/dev/null \
          | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2)
    [ -n "$pid" ] && echo "$pid" > "$PIDFILE"
}

stage() {
    local m="$1" desc="$2"; shift 2
    if [ -f "$MARK/$m" ]; then log "SKIP $m (already complete)"; return 0; fi
    start_carla || { log "aborting $m -- no CARLA"; return 1; }
    log "START $m -- $desc"
    if "$@"; then touch "$MARK/$m"; log "DONE $m"
    else log "FAILED $m (unmarked, will retry on rerun)"; fi
}

MIXED=$(ls -1 pipeline/checkpoints/S_mixed_84x28_w3_dagger_r*.pth 2>/dev/null | sort | tail -1)
MIXED=$([ -n "$MIXED" ] && basename "$MIXED" .pth || echo S_mixed_84x28_w3)
CLEARM=$(ls -1 pipeline/checkpoints/S_clear_84x28_dagger_r*.pth 2>/dev/null | sort | tail -1)
CLEARM=$([ -n "$CLEARM" ] && basename "$CLEARM" .pth || echo S_clear_84x28)
log "mixed=$MIXED  clear=$CLEARM"

# --- the cell lost to the cleanup bug ---------------------------------------
stage ledger_mixed_clear "rerun ledger cell S_mixed/clear, 10 reps" \
    $PY -u scripts/closed_loop_ledger.py --student "$MIXED" \
        --condition clear --reps 10 --channels 24,48,48 --fc 96 --cell-name S_mixed

# --- the four deferred S_clear cells ----------------------------------------
# Verification has already committed a verdict for each of these. fog and night were
# predicted FALSIFIED; shadows was predicted CERTIFIED, which CONTRADICTS the
# pre-registered ledger. That contradiction is the interesting one, because the prediction
# is on the record before the drive.
#
# The checkpoint is read FROM THE VERIFY CELL, not globbed independently. Both instruments
# must judge the same weights or the ledger row compares two different models -- and a glob
# for "*_dagger_r*.pth" silently starts resolving to something else the moment a
# student-DAgger round lands. Today both sides happen to agree; that is luck, not a
# guarantee.
ckpt_from_verify() {
    $PY - "$1" <<'PYEOF'
import json, sys, pathlib
p = pathlib.Path("results/ledger") / f"{sys.argv[1]}__S_clear__verify.json"
print(json.load(open(p)).get("checkpoint", "") if p.exists() else "")
PYEOF
}

for cond in clear fog night shadows; do
    want=$(ckpt_from_verify "$cond")
    if [ -z "$want" ]; then
        log "SKIP ledger_clear_$cond -- no verify cell yet; the blind protocol needs it first"
        continue
    fi
    if [ "$want" != "$CLEARM" ]; then
        log "NOTE ledger_clear_$cond uses '$want' (from the verify cell), not '$CLEARM'"
    fi
    stage "ledger_clear_$cond" "ledger cell S_clear/$cond, 10 reps, $want" \
        $PY -u scripts/closed_loop_ledger.py --student "$want" \
            --condition "$cond" --reps 10 --channels 8,16,16 --fc 32 \
            --cell-name S_clear
done

log "############ phase 2 complete ############"
$PY -m study.ledger || true
$PY -m study.ledger --check-order || true

if [ -f "$PIDFILE" ]; then
    p=$(cat "$PIDFILE"); kill -0 "$p" 2>/dev/null && { kill -9 "$p"; log "released our CARLA (pid $p)"; }
fi
log "############ DONE ############"

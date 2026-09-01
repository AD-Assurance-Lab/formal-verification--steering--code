#!/usr/bin/env bash
# Drive DAgger ONE ROUND PER PROCESS, restarting CARLA between rounds.
#
# dagger.py restarts CARLA in-process between rounds (R-SIM-1) and dies doing it:
# "terminate called after throwing carla::client::TimeoutException", core dumped, after
# the round is already trained. Releasing the caller's references did not fix it, and
# neither did skipping the world reload -- the same fight the ledger lost before it moved
# to a process per run.
#
# A process boundary settles it: the OS reclaims the client, so nothing can outlive the
# server it was talking to. dagger.py already resumes from its newest round, so one round
# per invocation loses no work, and the crash it used to die on cannot happen because
# there is no in-process restart left to make.
#
#   bash scripts/run_dagger_rounds.sh clear  12
#   bash scripts/run_dagger_rounds.sh mixed  12
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
WHICH=${1:?clear or mixed}
MAX=${2:-12}
export STUDY_MAP=Town06 CARLA_PORT=${CARLA_PORT:-3000} PYTHONUNBUFFERED=1
export CARLA_WINDOWED=${CARLA_WINDOWED:-1} DISPLAY=${DISPLAY:-:0}

LOG_DIR=$REPO/results/town06_logs
# The log name carries the study namespace, exactly as the datasets and checkpoints
# do. It did not, and the six-section study's dagger_mixed.log -- which legitimately says
# "PASSED at round 12" -- was read by the LAP study's gate, which skipped a stage that had
# never run. Namespacing three kinds of artifact and not the fourth is how that happens.
LOG=$LOG_DIR/dagger_${WHICH}_t06lap.log
mkdir -p "$LOG_DIR"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG_DIR/dagger_rounds_${WHICH}_t06lap.log"; }

if [ "$WHICH" = clear ]; then
    WEATHERS=clear
else
    WEATHERS=clear,fog,night,shadows
fi

for r in $(seq 1 "$MAX"); do
    if grep -q "\*\*\* LAP GATE PASSED" "$LOG" 2>/dev/null; then
        say "$WHICH teacher already passed the per-lap gate; nothing to do"; exit 0
    fi
    say "round attempt $r/$MAX"
    bash scripts/carla_restart.sh > "$LOG_DIR/dagger_${WHICH}_t06lap_restart.log" 2>&1 || {
        say "restart failed; stopping"; exit 1; }
    rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null
    # One round, then exit. The next iteration restarts CARLA and resumes.
    # --gate-reps 1: dagger's internal gate is now only a progress signal. The decision
    # is made below, one lap per process on a freshly restarted server, because the
    # teacher's pass/fail is what licenses distilling from it.
    python3 pipeline/dagger.py --base "${WHICH}_t06lap" \
        --init "teacher_${WHICH}_t06lap_bc" --rounds 1 --min-rounds 1 --gate-reps 1 \
        --weathers "$WEATHERS" --dagger-dir "dagger_${WHICH}_t06lap" \
        --out-prefix "teacher_${WHICH}_t06lap_dagger" >>"$LOG" 2>&1
    say "  round trained (rc=$?)"

    NEWEST=$(ls -t "$REPO"/pipeline/checkpoints/teacher_${WHICH}_t06lap_dagger_r*.pth \
             2>/dev/null | head -1)
    [ -n "$NEWEST" ] || { say "  no checkpoint produced; stopping"; exit 1; }
    CK=$(basename "$NEWEST" .pth)

    # THE GATE: three laps, a clean server before EACH, one process per lap.
    PASSES=0
    for lap in 0 1 2; do
        bash scripts/carla_restart.sh > "$LOG_DIR/dagger_${WHICH}_t06lap_restart.log" 2>&1 || {
            say "  restart failed before gate lap $lap"; break; }
        rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null
        for W in ${WEATHERS//,/ }; do
            python3 scripts/gate_teacher_lap.py --checkpoint "$CK" --weather "$W" \
                --lap "$lap" >>"$LOG" 2>&1 && PASSES=$((PASSES+1)) || true
        done
    done
    NEED=$(( 3 * $(echo "$WEATHERS" | tr ',' ' ' | wc -w) ))
    say "  gate: $PASSES/$NEED laps passed with $CK"
    if [ "$PASSES" -eq "$NEED" ]; then
        # A marker only THIS gate writes. dagger.py prints "*** PASSED at round N ***"
        # from its own 1-rep internal gate, and sharing that string let the loose gate
        # override the strict one: the log read "gate: 0/3 laps passed" and then
        # "clear teacher already PASSED" on the next line.
        echo "*** LAP GATE PASSED: $CK ($PASSES/$NEED laps, clean server each) ***" >> "$LOG"
        say "$WHICH teacher PASSED at $CK"
        exit 0
    fi
done

if grep -q "\*\*\* LAP GATE PASSED" "$LOG" 2>/dev/null; then
    say "$WHICH teacher PASSED the per-lap gate"
    exit 0
fi
say "$WHICH teacher did NOT pass in $MAX rounds -- refusing to pretend otherwise"
exit 1

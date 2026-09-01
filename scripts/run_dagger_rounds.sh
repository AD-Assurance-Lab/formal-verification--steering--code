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

# ONE DRIVER AT A TIME.
#
# carla_restart.sh kills client processes by name, and dagger.py is on that list. So two
# of these running at once kill each other's training: every round exited rc=143 (SIGTERM)
# without producing a checkpoint, the gate then re-scored the previous round forever, and
# from the outside it looked like a policy that had stopped improving.
#
# The second driver was an orphan -- the watchdog restarted the pipeline while a previous
# pipeline's driver was still alive, and setsid means the child outlives its parent.
# ONE lock for ALL stages, not one per stage: clear and mixed both drive the single
# CARLA server, so two of them is the same collision as two of the same one. They were
# found running together -- an orphaned mixed driver from before the stale-log fix, plus
# the live clear driver -- each killing the other's dagger.py through carla_restart.
LOCK=/tmp/dagger_rounds.lock
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
    echo "another run_dagger_rounds is alive (pid $(cat "$LOCK")); exiting"
    exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

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
    # Mark where THIS round's output starts in the shared log, and when it started,
    # so the checkpoint it produced can be told apart from one already on disk.
    ROUND_START=$(date +%s)
    LOG_MARK=$(wc -l < "$LOG" 2>/dev/null || echo 0)
    python3 pipeline/dagger.py --base "${WHICH}_t06lap" \
        --init "teacher_${WHICH}_t06lap_bc" --rounds 1 --min-rounds 1 --gate-reps 1 --external-gate \
        --weathers "$WEATHERS" --dagger-dir "dagger_${WHICH}_t06lap" \
        --out-prefix "teacher_${WHICH}_t06lap_dagger" >>"$LOG" 2>&1
    TRAIN_RC=$?
    say "  round exited rc=$TRAIN_RC"

    NEWEST=$(ls -t "$REPO"/pipeline/checkpoints/teacher_${WHICH}_t06lap_dagger_r*.pth \
             2>/dev/null | head -1)
    [ -n "$NEWEST" ] || { say "  no checkpoint produced; stopping"; exit 1; }
    CK=$(basename "$NEWEST" .pth)

    # A CHECKPOINT ON DISK IS NOT A ROUND THAT RAN.
    #
    # `ls -t | head -1` takes the newest file, not this round's output. On 2026-09-01
    # four consecutive attempts were killed (rc=143) having trained nothing, and the
    # driver gated teacher_mixed_t06lap_dagger_r00 -- a checkpoint from before the stage
    # started -- three times over, logging "0/12 laps passed with r00" each time as
    # though it had measured a fresh round. A fifth attempt exited rc=0 after collecting
    # data but never training, and gated r00 again at "3/12".
    #
    # Two independent facts are required, because either alone has already been wrong:
    # the file is newer than this round started, AND this round's own log segment says
    # it trained that exact checkpoint. mtime alone trusts the filesystem; the marker
    # alone trusts a log that another process also writes to.
    if [ "$(stat -c %Y "$NEWEST")" -lt "$ROUND_START" ]; then
        say "  STALE: $CK predates this round (trained $(date -d @$(stat -c %Y "$NEWEST") '+%H:%M'), round began $(date -d @$ROUND_START '+%H:%M'))"
        say "  the round produced no checkpoint of its own -- not gating a stale one; stopping"
        exit 3
    fi
    if ! tail -n +$((LOG_MARK + 1)) "$LOG" | grep -q -- "-> $CK"; then
        say "  UNVERIFIED: this round's log never says it trained $CK; stopping"
        exit 3
    fi
    # rc != 0 is now survivable ONLY because the two checks above passed. The observed
    # failure is a carla::client::TimeoutException thrown in the client's destructor
    # AFTER "aggregating ... -> <ck>" is written, so the round's work is complete and
    # the abort is teardown. rc=143 (killed) never gets here: it trains nothing.
    if [ "$TRAIN_RC" -ne 0 ]; then
        say "  round completed and saved $CK, then exited rc=$TRAIN_RC at teardown"
    fi

    # THE GATE: three laps, a clean server before EACH, one process per lap.
    PASSES=0
    # A RESTART BEFORE EVERY LAP, not before every group of laps.
    #
    # This restarted once per lap INDEX and then drove all four conditions on that one
    # server -- 3 restarts for 12 laps. A lap is the repetition (A-4), and the clean
    # server is per repetition: three laps is defensible only while "a clean server
    # restart before every run" holds, and four laps sharing a server is the ageing-server
    # coupling the per-run restart exists to break.
    for lap in 0 1 2; do
        for W in ${WEATHERS//,/ }; do
            bash scripts/carla_restart.sh > "$LOG_DIR/dagger_${WHICH}_t06lap_restart.log" 2>&1 || {
                say "  restart failed before gate lap $lap/$W"; break 2; }
            rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null
            python3 scripts/gate_teacher_lap.py --checkpoint "$CK" --weather "$W" \
                --lap "$lap" >>"$LOG" 2>&1
            rc=$?
            case $rc in
                0) PASSES=$((PASSES+1)) ;;
                1) : ;;                 # drove the lap, missed the budget: a real fail
                *) # ANY OTHER EXIT IS A BROKEN GATE, NOT A FAILED LAP.
                   #
                   # gate_teacher_lap.py died on ModuleNotFoundError for six rounds. Every
                   # lap "failed", the teacher could never pass, and the driver reported
                   # "0/3 laps passed" as though it had measured something. I read that as
                   # a marginal policy and said so. A gate that cannot run has not failed
                   # the thing it was pointed at.
                   say "  GATE IS BROKEN (exit $rc), not a failed lap -- stopping"
                   exit 2 ;;
            esac
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

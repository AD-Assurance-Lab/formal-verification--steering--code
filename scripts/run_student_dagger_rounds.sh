#!/usr/bin/env bash
# Drive STUDENT DAgger one round per process, restarting CARLA between rounds.
#
# The teacher path got this treatment on 2026-09-01 (scripts/run_dagger_rounds.sh) and
# the student path did not, so it kept the two defects that driver exists to remove:
#
#   1. dagger_student.py restarts CARLA in-process between rounds and dies doing it:
#      "terminate called after throwing carla::client::TimeoutException", core dumped,
#      AFTER the round is already trained. Measured 2026-09-02, round 0 of the clear
#      student. The work survives; the process does not.
#
#   2. The pipeline's guard for the stage was `ls <student>_dagger_r*.pth` -- true after
#      ONE round. So the crash above left 1 of 3 rounds done and the stage was skipped
#      as complete on every subsequent run. That is verbatim the defect the teacher
#      stage fixed: "the guard used to be 'checkpoints exist', which is true after a
#      single round, so a DAgger run that crashed at round 2 of 12 was treated as
#      complete and the stage was skipped forever after."
#
# A process boundary settles (1): the OS reclaims the client, so nothing can outlive the
# server it was talking to. dagger_student.py resumes from its newest round, so one round
# per invocation loses no work. A completion MARKER settles (2): the stage is done when
# this driver says it is, not when a file exists.
#
#   bash scripts/run_student_dagger_rounds.sh S_clear_t06lap_168x28_w2 3 clear "16,32,32" 64 168 28
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
CK=${1:?student checkpoint base}
ROUNDS=${2:-3}
WEATHERS=${3:-clear}
CHANNELS=${4:?channels}
FC=${5:?fc}
IN_W=${6:-168}
IN_H=${7:-28}
TEACHER=${TEACHER:?TEACHER must be set}
BASE=${BASE:?BASE dataset must be set}
DDIR=${DDIR:?DDIR must be set}

export STUDY_MAP=Town06 CARLA_PORT=${CARLA_PORT:-3000} PYTHONUNBUFFERED=1
export CARLA_WINDOWED=${CARLA_WINDOWED:-0} DISPLAY=${DISPLAY:-:0}

# ONE DRIVER AT A TIME, and the SAME lock the teacher driver takes: both drive the one
# CARLA server, so two of them is the same collision as two of either.
LOCK=/tmp/dagger_rounds.lock
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
    echo "another DAgger driver is alive (pid $(cat "$LOCK")); exiting"
    exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

LOG_DIR=$REPO/results/town06_logs
mkdir -p "$LOG_DIR"
LOG=$LOG_DIR/dagger_student_${CK}.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG_DIR/student_dagger_rounds_${CK}.log"; }

n_rounds() { ls -d "$REPO/pipeline/data/$DDIR"/round*/ 2>/dev/null | wc -l; }

if grep -q "\*\*\* STUDENT DAGGER COMPLETE" "$LOG" 2>/dev/null; then
    say "$CK student DAgger already complete"; exit 0
fi


# A SLOW BOOT MUST NOT ABANDON A STAGE.
#
# carla_restart.sh gives the server 300 s to become ready and fails if it does not. That
# is right for the restart; it is wrong as a stage-level verdict. The drivers treated one
# failure as terminal -- "restart failed; stopping" -- and threw away the whole round or
# the whole twelve-lap gate. Measured 2026-09-02: a boot exceeded 300 s while a
# distillation was using the GPU, and nine completed student-DAgger rounds were abandoned
# because the tenth restart was slow.
#
# The retry is bounded and it is LOUD. A restart that fails three times in a row is a
# genuine problem and still stops the stage.
restart_carla_retrying() {   # restart_carla_retrying <logfile> <label>
    local logf=$1 label=$2 i
    for i in 1 2 3; do
        if bash scripts/carla_restart.sh > "$logf" 2>&1; then
            [ "$i" -gt 1 ] && say "  restart succeeded on attempt $i ($label)"
            rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null
            return 0
        fi
        say "  restart attempt $i/3 FAILED ($label); $(tail -1 "$logf" | tr -s ' ' | cut -c1-80)"
        sleep 20
    done
    say "  restart FAILED three times ($label) -- that is not a slow boot"
    return 1
}

for r in $(seq 1 "$ROUNDS"); do
    HAVE=$(n_rounds)
    if [ "$HAVE" -ge "$ROUNDS" ]; then break; fi
    say "student round attempt $r/$ROUNDS (rounds on disk: $HAVE)"
    restart_carla_retrying "$LOG_DIR/dagger_student_restart.log" "round $r" || exit 1

    ROUND_START=$(date +%s)
    python3 pipeline/dagger_student.py --student "$CK" --w "$IN_W" --h "$IN_H" \
        --rounds 1 --weathers "$WEATHERS" --teacher "$TEACHER" --base "$BASE" \
        --dagger-dir "$DDIR" --channels "$CHANNELS" --fc "$FC" >>"$LOG" 2>&1
    RC=$?
    say "  round exited rc=$RC"

    # A ROUND THAT PRODUCED NOTHING IS NOT A ROUND. rc != 0 is survivable only because
    # the observed failure is a TimeoutException thrown in the client's DESTRUCTOR, after
    # the checkpoint is written -- so require positive evidence that this invocation
    # actually advanced, exactly as the teacher driver does.
    NOW=$(n_rounds)
    if [ "$NOW" -le "$HAVE" ]; then
        say "  no new round on disk ($HAVE -> $NOW); not pretending otherwise -- stopping"
        exit 3
    fi
    NEWEST=$(ls -t "$REPO"/pipeline/checkpoints/${CK}_dagger_r*.pth 2>/dev/null | head -1)
    if [ -n "$NEWEST" ] && [ "$(stat -c %Y "$NEWEST")" -ge "$ROUND_START" ]; then
        say "  round trained $(basename "$NEWEST" .pth)"
    else
        say "  round produced no checkpoint of its own -- stopping"
        exit 3
    fi
    # dagger_student.py stops early when its own gate passes; that is a legitimate end.
    if grep -q "\*\*\* student PASSED at round" "$LOG" 2>/dev/null; then
        say "  student passed its own gate; no further rounds needed"
        break
    fi
done

HAVE=$(n_rounds)
FINAL=$(ls -t "$REPO"/pipeline/checkpoints/${CK}_dagger_r*.pth 2>/dev/null | head -1)
if [ -z "$FINAL" ]; then
    say "$CK: no student-DAgger checkpoint was produced"; exit 1
fi
echo "*** STUDENT DAGGER COMPLETE: $(basename "$FINAL" .pth) ($HAVE round(s)) ***" >> "$LOG"
say "$CK student DAgger complete at $(basename "$FINAL" .pth) ($HAVE round(s))"
exit 0

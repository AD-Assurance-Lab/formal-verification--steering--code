#!/usr/bin/env bash
# Keep running student DAgger until the student holds every section in clear weather.
#
# Distillation alone does not produce a usable student. Measured on Town06:
#
#   checkpoint                        sections within budget   worst |CTE|
#   S_clear_t06_84x28 (distilled)             1 / 6              16.50 ft
#   ... after 3 student-DAgger rounds         4 / 6               8.57 ft
#   S_mixed_t06_84x28_w3 (distilled)          2 / 6              28.18 ft
#   ... after 3 student-DAgger rounds         5 / 6               6.40 ft
#
# against a 2.19 ft budget. The direction is right and three rounds is simply not
# enough, so this keeps going rather than accepting a student that cannot drive.
#
# Clear weather only, and competence only. This is the s=0 anchor of the disturbance
# family, not a disturbance condition, so it tells us nothing about fog, night or low
# sun and does not weaken the blind protocol (PROTOCOL R3).
#
#   bash scripts/student_dagger_until_competent.sh [max_attempts] [rounds_per_attempt]
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06
export CARLA_PORT=${CARLA_PORT:-3000}
export PYTHONUNBUFFERED=1

MAX_ATTEMPTS=${1:-8}
ROUNDS=${2:-4}
LOG_DIR=$REPO/results/town06_logs
mkdir -p "$LOG_DIR"
LOG=$LOG_DIR/student_until_competent.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

CARLA_ROOT=${CARLA_ROOT:-$HOME/carla}
carla_up() { for i in $(seq 1 "${1:-60}"); do
    ss -ltn 2>/dev/null | grep -q ":$CARLA_PORT" && return 0; sleep 5; done; return 1; }
carla_restart() {
    say "restarting CARLA on $CARLA_PORT"
    pkill -f "[C]arlaUE4-Linux-Shipping.*rpc-port=$CARLA_PORT" 2>/dev/null; sleep 8
    ( cd "$CARLA_ROOT" && setsid nohup ./CarlaUE4.sh -carla-rpc-port="$CARLA_PORT" \
        -RenderOffScreen -quality-level=Epic >>"$LOG_DIR/carla.log" 2>&1 < /dev/null & )
    carla_up 60 && { say "CARLA back"; sleep 10; return 0; }
    say "FATAL: CARLA did not return"; return 1; }

# name | base checkpoint | dagger dir | teacher | base dataset | weathers | channels | fc
SPECS=(
  "clear|S_clear_t06_84x28|dagger_student_clear_t06|clear_t06|clear|8,16,16|32"
  "mixed|S_mixed_t06_84x28_w3|dagger_student_mixed_t06|mixed_t06|clear,fog,night,shadows|24,48,48|96"
)
latest_teacher() { ls -1 "$REPO"/pipeline/checkpoints/$1*.pth 2>/dev/null \
    | sort | tail -1 | xargs -r basename | sed 's/\.pth$//'; }

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
    carla_up 6 || carla_restart || exit 1
    rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null

    if python3 scripts/check_student_competence.py --require \
         >"$LOG_DIR/competence_attempt${attempt}.log" 2>&1; then
        say "BOTH STUDENTS COMPETENT in clear weather"
        grep -E "sections within budget|using " "$LOG_DIR/competence_attempt${attempt}.log" | tee -a "$LOG"
        exit 0
    fi
    say "attempt $attempt/$MAX_ATTEMPTS: not competent yet"
    grep -E "sections within budget" "$LOG_DIR/competence_attempt${attempt}.log" | tee -a "$LOG"

    for spec in "${SPECS[@]}"; do
        IFS='|' read -r WHICH BASE DDIR DATASET WEATHERS CH FC <<<"$spec"
        TEACH=$(latest_teacher "teacher_${WHICH}_t06_dagger_r")
        [ -n "$TEACH" ] || { say "FATAL: no ${WHICH} teacher"; exit 1; }
        say "  +$ROUNDS student-DAgger rounds for $WHICH (teacher $TEACH)"
        ( cd "$REPO/pipeline" && python3 dagger_student.py \
            --student "$BASE" --w 84 --h 28 --rounds "$ROUNDS" \
            --weathers "$WEATHERS" --dagger-dir "$DDIR" --teacher "$TEACH" \
            --base "$DATASET" --channels "$CH" --fc "$FC" \
            --distill-dirs "dagger_${WHICH}_t06,${DDIR}" ) \
          >>"$LOG_DIR/student_dagger_${WHICH}.log" 2>&1 \
          || { say "  ${WHICH} student DAgger exited nonzero; restarting CARLA"; carla_restart || exit 1; }
    done
done

say "STOPPING after $MAX_ATTEMPTS attempts without both students competent."
say "This is a plateau, not a budget to widen."
say ""
say "NEXT LEVER IS WIDTH, and that is evidence, not a guess. Town04 commit 4b2ad73:"
say "  w1 failed all four conditions; w2 failed night 10/10; w3 passed everything."
say "  w3 was the MINIMUM that worked there, and both Town04 students then passed"
say "  student-DAgger at round 0 -- so on that map capacity, not DAgger rounds, was"
say "  the binding constraint. F7 (5be6862) had blamed DAgger and was wrong."
say ""
say "  Town06 currently uses the same pair: clear (8,16,16)/fc32 = 5,152 ReLU,"
say "  mixed (24,48,48)/fc96 = 15,456 ReLU. If DAgger has plateaued, re-distil the"
say "  MIXED student wider (w4: 32,64,64 / fc 128) before adding more rounds."
say ""
say "  Student capacity is NOT frozen by PROTOCOL section 3 -- it is a property of the"
say "  model under test, not of the criterion -- so widening needs no amendment. It"
say "  does need declaring, since the paper reports the mixed student as 3x width."
exit 1

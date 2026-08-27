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

# One definition, in config: which | base checkpoint | dagger dir | dataset | weathers | channels | fc
mapfile -t SPECS < <(STUDY_MAP=Town06 python3 -c "
import sys; sys.path.insert(0,'pipeline'); import config as C
for nm, ck, ch, fc in C.TOWN06_STUDENTS:
    which = 'clear' if 'clear' in nm else 'mixed'
    ddir  = f'dagger_student_{which}_t06'
    dset  = f'{which}_t06'
    wx    = 'clear' if which == 'clear' else 'clear,fog,night,shadows'
    print('|'.join([which, ck, ddir, dset, wx, ','.join(str(c) for c in ch), str(fc),
                    str(C.TOWN06_INPUT_W), str(C.TOWN06_INPUT_H)]))")

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

    # Only DAgger the students that FAILED. Running it on a competent student is not
    # neutral: T06-F13 measured the mixed student going from clear 6/6 at 1.11 ft to
    # clear 4/6 at 23.00 ft over four rounds, because its DAgger spans four weathers and
    # at w2 it could not absorb off-nominal states across all of them without losing the
    # straight-line cue. The gate is per-student, so this loop should be too.
    NEEDY=$(python3 -c "
import json
d = json.load(open('results/town06/competence_clear.json'))
print(' '.join('clear' if 'clear' in k else 'mixed'
               for k, v in d['students'].items() if not v.get('competent')))" 2>/dev/null)
    say "  students needing work: ${NEEDY:-<none parsed>}"

    for spec in "${SPECS[@]}"; do
        IFS='|' read -r WHICH BASE DDIR DATASET WEATHERS CH FC IN_W IN_H <<<"$spec"
        if [ -n "$NEEDY" ] && [[ " $NEEDY " != *" $WHICH "* ]]; then
            say "  SKIP $WHICH student DAgger -- it already passed the gate"
            continue
        fi
        TEACH=$(latest_teacher "teacher_${WHICH}_t06_dagger_r")
        [ -n "$TEACH" ] || { say "FATAL: no ${WHICH} teacher"; exit 1; }
        say "  +$ROUNDS student-DAgger rounds for $WHICH (teacher $TEACH)"
        ( cd "$REPO/pipeline" && python3 dagger_student.py \
            --student "$BASE" --w "$IN_W" --h "$IN_H" --rounds "$ROUNDS" \
            --weathers "$WEATHERS" --dagger-dir "$DDIR" --teacher "$TEACH" \
            --base "$DATASET" --channels "$CH" --fc "$FC" \
            --distill-dirs "dagger_${WHICH}_t06,${DDIR}") \
          >>"$LOG_DIR/student_dagger_${WHICH}.log" 2>&1 \
          || { say "  ${WHICH} student DAgger exited nonzero; restarting CARLA"; carla_restart || exit 1; }
    done
done

say "STOPPING after $MAX_ATTEMPTS attempts without both students competent."
say "This is a plateau. Read T06-F11 and T06-F13 before reaching for a lever."
say ""
say "  Resolution buys STRAIGHTS: the lateral cue on a 620 m straight is sub-pixel at"
say "  84 px width, and only horizontal resolution addresses it. Width buys CONDITIONS."
say "  Both students are already at 168x28; clear is w2 (21,408 ReLU) and mixed is w3"
say "  (32,112), which is the pairing those two findings imply."
say ""
say "  If the MIXED student is the one stuck, check whether its clear-weather numbers"
say "  DEGRADE across rounds. If they do, that is T06-F13 again and the answer is"
say "  capacity or no DAgger at all for it, NOT more rounds."
say ""
say "  If the CLEAR student is stuck, it is more likely data: it trains on 18,623"
say "  samples against the mixed student's 121,925, and distillation seed variance alone"
say "  moved it across the gate (KD RMSE 0.0489 -> 6/6, 0.0553 -> 5/6, same data, same"
say "  120 epochs). Collect more clear laps. Do NOT re-roll seeds until one passes --"
say "  that turns a precondition into a selection step."
exit 1

#!/usr/bin/env bash
# Generic ARM sweep: distil, measure KD error, and drive one or more training-configuration
# arms across a seed set. Used by E4 (depth) and E6 (label balancing).
#
# Kernels are PINNED (DISTILL_DETERMINISTIC=1) on every arm. That is not optional here:
# E2-F6 measured three draws of "seed 0" giving fog p99 0.1027 / 0.1427 / 0.1036 with the
# objective and data held fixed, which is as large as the spread across six different
# seeds. Without pinning, a comparison between two training configurations is confounded
# by run-to-run noise of the same size as the effect. With it, the seed is a control
# variable and the comparison is paired.
#
# ARMS is a ';'-separated list of  name|channels|fc|ENV|FLAGS  entries, where ENV is
# space-separated VAR=value passed to distill.py's environment and FLAGS is extra
# command-line flags for distill.py itself, e.g.
#
#   ARMS='d3|32,64,64|128||;d5|32,64,48,24,20|128||' OUT_DIR=results/town06/depth \
#       PREFIX=S_mixed_depth bash scripts/arm_sweep.sh
#
#   ARMS='bal|32,64,64|128||--balance;curv|32,64,64|128|DISTILL_CURV_BETA=4.0|'
#
# Promotes nothing and writes no .selected pin.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export PATH="$REPO/.venv/bin:$PATH"
export STUDY_MAP=Town06 CARLA_PORT=${CARLA_PORT:-3000} CARLA_WINDOWED=${CARLA_WINDOWED:-1}
export PYTHONUNBUFFERED=1

ARMS=${ARMS:?ARMS required, e.g. 'd3|32,64,64|128|;d5|32,64,48,24,20|128|'}
SEEDS=${SEEDS:-"0 1 2 3 4 5"}
CONDS=${CONDS:-"fog clear"}
REPS=${REPS:-3}
IN_W=${IN_W:-168}; IN_H=${IN_H:-56}
PREFIX=${PREFIX:?PREFIX required, e.g. S_mixed_depth}
OUT_DIR=${OUT_DIR:?OUT_DIR required}
TEACHER=${TEACHER:-teacher_mixed_t06lap_dagger_r03}
BASE=${BASE:-mixed_t06lap}
DAGGER_DIRS=${DAGGER_DIRS:-dagger_mixed_t06lap,dagger_student_S_mixed_t06_t06lap}

OUT_DIR=$REPO/$OUT_DIR
mkdir -p "$OUT_DIR"
LOG=$OUT_DIR/sweep.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

LOCK=/tmp/arm_sweep_$(echo "$PREFIX" | tr -c 'a-zA-Z0-9' '_').lock
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
    echo "sweep $PREFIX already running (pid $(cat "$LOCK")); exiting"; exit 0
fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT

say "=== arm sweep $PREFIX: seeds [$SEEDS], conds [$CONDS], deterministic kernels ==="

IFS=';' read -ra ARM_LIST <<< "$ARMS"
for ARM in "${ARM_LIST[@]}"; do
    [ -z "$ARM" ] && continue
    IFS='|' read -r NAME CH FC EXTRA FLAGS <<< "$ARM"
    say "--- arm $NAME: channels $CH, fc $FC, env [${EXTRA:-none}], flags [${FLAGS:-none}] ---"
    for SEED in $SEEDS; do
        SCK="${PREFIX}_${NAME}_s${SEED}"

        if [ ! -f "$REPO/pipeline/checkpoints/$SCK.pth" ]; then
            say "distil $SCK"
            ( cd pipeline && env $EXTRA DISTILL_SEED="$SEED" DISTILL_DETERMINISTIC=1 \
                CUBLAS_WORKSPACE_CONFIG=:4096:8 \
                python3 distill.py --in-w "$IN_W" --in-h "$IN_H" --out "$SCK" \
                --teacher "$TEACHER" --base "$BASE" --dagger-dirs "$DAGGER_DIRS" \
                --channels "$CH" --fc "$FC" ${FLAGS:-} ) \
                >>"$REPO/results/town06_logs/distill_${SCK}.log" 2>&1 \
                || { say "  $SCK: distillation FAILED -- skipping"; continue; }
        fi

        K=$OUT_DIR/kd_${NAME}_s${SEED}.json
        if [ ! -f "$K" ]; then
            say "  KD error: $NAME s$SEED"
            STUDENT="$SCK" CHANNELS="$CH" FC="$FC" TEACHER="$TEACHER" BASE="$BASE" \
            DAGGER_DIRS="$DAGGER_DIRS" KD_JSON="$K" \
                python3 scripts/kd_error_by_condition.py >>"$LOG" 2>&1
        fi

        for COND in $CONDS; do
            OUT="$OUT_DIR/drive_${NAME}_s${SEED}_${COND}.json"
            [ -f "$OUT" ] && { say "  skip (done) $NAME s$SEED $COND"; continue; }
            say "  drive $NAME s$SEED $COND: $REPS laps"
            python3 scripts/compare_student_variants.py --checkpoints "$SCK" \
                --channels "$CH" --fc "$FC" --in-w "$IN_W" --in-h "$IN_H" \
                --reps "$REPS" --weather "$COND" --out "$OUT" >>"$LOG" 2>&1
            rc=$?
            # An unmeasured lap is not a failing lap (rule 8): stop, do not score.
            [ $rc -eq 3 ] && { say "  FATAL: $NAME s$SEED $COND unmeasurable. Stopping."; exit 3; }
            [ -f "$OUT" ] && say "    worst $(python3 -c "
import json
d=json.load(open('$OUT'))
laps=[l for l in list(d['results'].values())[0] if not l.get('error')]
print(f\"{max(l['max_cte_ft'] for l in laps):.2f} ft\" if laps else 'NO MEASURED LAPS')") "
        done
    done
done
say "=== sweep $PREFIX complete ==="

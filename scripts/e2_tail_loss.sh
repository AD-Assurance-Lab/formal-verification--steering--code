#!/usr/bin/env bash
# E2 -- tail-sensitive distillation loss. docs/E2_PREREGISTRATION.md is the prediction.
#
# Distils the shipped architecture at each declared DISTILL_TAIL_ALPHA, measures the KD
# error tail per condition (no CARLA), then drives fog and clear. Measures every cell:
# stops for nothing but a harness that cannot produce a lap.
#
# AMENDMENT A-1: the alpha 0.0 arm IS re-distilled here, under its own name. Re-distilling
# the baseline objective at the SAME seed moved fog p99 by +38.9% against the committed
# pass-3 checkpoint -- larger than the effect alpha is being measured for. Inheriting that
# baseline would have measured the re-run difference and attributed it to the loss.
#
# Promotes nothing and writes no .selected pin.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export PATH="$REPO/.venv/bin:$PATH"
export STUDY_MAP=Town06 CARLA_PORT=${CARLA_PORT:-3000} CARLA_WINDOWED=${CARLA_WINDOWED:-1}
export PYTHONUNBUFFERED=1

ALPHAS=${ALPHAS:-"0.0 2.0 8.0"}      # 0.0 IS re-distilled here -- see amendment A-1
SEEDS=${SEEDS:-"0 1 2 3 4 5"}
CONDS=${CONDS:-"fog clear"}
REPS=${REPS:-3}
IN_W=168; IN_H=56
CH=32,64,64; FC=128
TEACHER=teacher_mixed_t06lap_dagger_r03
BASE=mixed_t06lap
DAGGER_DIRS=dagger_mixed_t06lap,dagger_student_S_mixed_t06_t06lap

OUT_DIR=$REPO/results/town06/tail_loss
mkdir -p "$OUT_DIR"
LOG=$OUT_DIR/e2.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

LOCK=/tmp/e2_tail_loss.lock
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
    echo "E2 already running (pid $(cat "$LOCK")); exiting"; exit 0
fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT

# alpha -> checkpoint name. 0.0 resolves to the existing baseline students.
# Every arm, including the baseline, gets a fresh checkpoint distilled in THIS session.
ck_name() { echo "S_mixed_tail_a${1/./p}_s${2}"; }

kd_for() {  # kd_for <checkpoint> <outfile>
    STUDENT="$1" CHANNELS="$CH" FC="$FC" TEACHER="$TEACHER" BASE="$BASE" \
    DAGGER_DIRS="$DAGGER_DIRS" KD_JSON="$2" \
        python3 scripts/kd_error_by_condition.py >>"$LOG" 2>&1
}

say "=== E2 tail-sensitive loss: alphas [$ALPHAS] + baseline 0.0, seeds [$SEEDS] ==="

for A in $ALPHAS; do
    for SEED in $SEEDS; do
        SCK=$(ck_name "$A" "$SEED")

        if [ ! -f "$REPO/pipeline/checkpoints/$SCK.pth" ]; then
            say "distil $SCK  (alpha $A, seed $SEED)"
            ( cd pipeline && DISTILL_SEED="$SEED" DISTILL_TAIL_ALPHA="$A" \
                python3 distill.py --in-w "$IN_W" --in-h "$IN_H" \
                --out "$SCK" --teacher "$TEACHER" --base "$BASE" \
                --dagger-dirs "$DAGGER_DIRS" --channels "$CH" --fc "$FC" ) \
                >>"$REPO/results/town06_logs/distill_${SCK}.log" 2>&1 \
                || { say "  $SCK: distillation FAILED -- skipping"; continue; }
        fi

        K=$OUT_DIR/kd_a${A/./p}_s${SEED}.json
        [ -f "$K" ] || { say "  KD error: alpha $A seed $SEED"; kd_for "$SCK" "$K"; }

        for COND in $CONDS; do
            OUT="$OUT_DIR/e2_a${A/./p}_s${SEED}_${COND}.json"
            [ -f "$OUT" ] && { say "  skip (done) a$A s$SEED $COND"; continue; }
            say "  drive a$A s$SEED $COND: $REPS laps"
            python3 scripts/compare_student_variants.py --checkpoints "$SCK" \
                --channels "$CH" --fc "$FC" --in-w "$IN_W" --in-h "$IN_H" \
                --reps "$REPS" --weather "$COND" --out "$OUT" >>"$LOG" 2>&1
            rc=$?
            if [ $rc -eq 3 ]; then
                say "  FATAL: a$A s$SEED $COND could not be measured (harness). Stopping."
                exit 3
            fi
            [ -f "$OUT" ] && say "    worst $(python3 -c "
import json
d=json.load(open('$OUT'))
laps=[l for l in list(d['results'].values())[0] if not l.get('error')]
print(f\"{max(l['max_cte_ft'] for l in laps):.2f} ft\" if laps else 'NO MEASURED LAPS')") "
        done
    done
done
say "=== E2 complete; summarise with scripts/e2_summarise.py ==="

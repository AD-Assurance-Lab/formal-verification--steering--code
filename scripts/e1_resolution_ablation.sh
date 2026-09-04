#!/usr/bin/env bash
# E1 -- input-resolution ablation on fog. docs/E1_PREREGISTRATION.md is the prediction.
#
# THE QUESTION. Does fog robustness decrease monotonically with student input resolution,
# and does straight-line CTE move the other way? T06-F48 has one draw at each of three
# sizes (84x28 fog-robust on Town04, 168x28 fog 6.85 ft, 168x56 fog 11.15 ft) and a single
# draw is a coin toss here -- 389f192 measured an UNCHANGED configuration swinging
# 1.16 -> 8.68 ft. So every point is re-measured over a seed sweep before it is believed
# or dismissed.
#
# WHY THIS IS NOT select_student_seed.sh. That script SELECTS a student: it breaks out of
# the screen at the first failing condition and exits at the first seed that passes the
# gate. Both are right for choosing a model to ship and wrong for measuring a trend --
# a seed that fails `clear` would never have its fog measured, and the sweep would stop
# before the later seeds that the trend is computed from. This driver measures EVERY
# (resolution, seed, condition) cell and stops early for nothing except a harness that
# cannot produce a lap.
#
# WHAT IT DOES NOT DO. It never promotes a checkpoint and never writes a `.selected` pin,
# so the models resolved by the committed Town06 results cannot move underneath them
# (NEXT_EXPERIMENTS "what must not be touched"). It writes only under
# results/town06/res_ablation/.
#
#   bash scripts/e1_resolution_ablation.sh
#
# Resumable: a cell whose output JSON already exists is skipped, so the run can be killed
# and restarted without redriving what it already measured.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export PATH="$REPO/.venv/bin:$PATH"
export STUDY_MAP=Town06 CARLA_PORT=${CARLA_PORT:-3000} CARLA_WINDOWED=${CARLA_WINDOWED:-1}
export PYTHONUNBUFFERED=1

# --- the declared set. Fixed BEFORE running, per NEXT_EXPERIMENTS rule 6. -------------
RESOLUTIONS=${RESOLUTIONS:-"84x28 168x28 168x56 252x84"}
SEEDS=${SEEDS:-"0 1 2 3 4 5"}
CONDS=${CONDS:-"fog clear"}          # fog is the question; clear measures the straights
REPS=${REPS:-3}                       # standing rule 3
CH=32,64,64                           # w4, held fixed to isolate resolution
FC=128
TEACHER=teacher_mixed_t06lap_dagger_r03
BASE=mixed_t06lap
DAGGER_DIRS=dagger_mixed_t06lap,dagger_student_S_mixed_t06_t06lap

OUT_DIR=$REPO/results/town06/res_ablation
mkdir -p "$OUT_DIR"
LOG=$OUT_DIR/e1.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

LOCK=/tmp/e1_resolution_ablation.lock
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
    echo "E1 already running (pid $(cat "$LOCK")); exiting"; exit 0
fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT

# 168x56 w4 is the pass-3 architecture and its seeds are already distilled -- reuse them
# rather than re-drawing, so this ablation's middle point IS the measured study point.
ck_name() {
    local wh=$1 seed=$2
    if [ "$wh" = "168x56" ]; then echo "S_mixed_t06lap_168x56_w4_s${seed}"
    else echo "S_mixed_res_${wh}_s${seed}"; fi
}

say "=== E1 resolution ablation ==="
say "    resolutions [$RESOLUTIONS] x seeds [$SEEDS] x conds [$CONDS], $REPS laps each"
say "    channels $CH fc $FC (w4, fixed); teacher $TEACHER"

for WH in $RESOLUTIONS; do
    W=${WH%x*}; H=${WH#*x}
    for SEED in $SEEDS; do
        SCK=$(ck_name "$WH" "$SEED")

        if [ ! -f "$REPO/pipeline/checkpoints/$SCK.pth" ]; then
            say "distil $SCK  (${W}x${H}, seed $SEED)"
            ( cd pipeline && DISTILL_SEED="$SEED" python3 distill.py --in-w "$W" --in-h "$H" \
                --out "$SCK" --teacher "$TEACHER" --base "$BASE" \
                --dagger-dirs "$DAGGER_DIRS" --channels "$CH" --fc "$FC" ) \
                >>"$REPO/results/town06_logs/distill_${SCK}.log" 2>&1 \
                || { say "  $SCK: distillation FAILED -- skipping this seed"; continue; }
        fi

        for COND in $CONDS; do
            OUT="$OUT_DIR/e1_${WH}_s${SEED}_${COND}.json"
            if [ -f "$OUT" ]; then say "  skip (done) ${WH} s${SEED} ${COND}"; continue; fi
            say "  drive ${WH} s${SEED} ${COND}: $REPS laps"
            python3 scripts/compare_student_variants.py --checkpoints "$SCK" \
                --channels "$CH" --fc "$FC" --in-w "$W" --in-h "$H" \
                --reps "$REPS" --weather "$COND" --out "$OUT" >>"$LOG" 2>&1
            rc=$?
            # EXIT 3 = a lap could not be MEASURED. An unmeasured lap is not a failing lap
            # (NEXT_EXPERIMENTS rule 8): scoring the model for it would blame the model for
            # the harness, so the whole run stops instead.
            if [ $rc -eq 3 ]; then
                say "  FATAL: ${WH} s${SEED} ${COND} could not be measured (harness). Stopping."
                exit 3
            fi
            [ $rc -ne 0 ] && say "  WARNING: driver exited $rc for ${WH} s${SEED} ${COND}"
            if [ -f "$OUT" ]; then
                say "    worst $(python3 -c "
import json
d=json.load(open('$OUT'))
laps=[l for l in list(d['results'].values())[0] if not l.get('error')]
print(f\"{max(l['max_cte_ft'] for l in laps):.2f} ft over {len(laps)} lap(s)\" if laps else 'NO MEASURED LAPS')") "
            fi
        done
    done
done
say "=== E1 sweep complete; summarise with scripts/e1_summarise.py ==="

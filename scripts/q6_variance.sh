#!/usr/bin/env bash
# Q6 -- where does the distillation dispersion come from? docs/Q6_PREREGISTRATION.md is
# the prediction, and amendment A-1 is why the `both` arm is run rather than reused.
#
# NO CARLA AT ANY POINT. Every endpoint is a KD error measured on cached teacher targets,
# which is the whole reason Q6 is cheap enough to run before the expensive items.
#
# Five arms, all on the tuned recipe (lr 3e-4) and all on the OPT-IN seed path, so one
# variable moves between them:
#
#   init    INIT=s   DATA=0   frac 1.00    initialisation alone
#   data    INIT=0   DATA=s   frac 1.00    minibatch order alone
#   both    INIT=s   DATA=s   frac 1.00    the study's current notion of "a seed"
#   f50     INIT=s   DATA=s   frac 0.50    half the training pool
#   f25     INIT=s   DATA=s   frac 0.25    a quarter of it
#
# `both` IS the frac-1.00 arm, so Q6a and Q6b share it. Kernels are pinned on every arm
# (DISTILL_DETERMINISTIC=1): without that a comparison between two training
# configurations is confounded by run-to-run noise the size of the effect (E2-F6).
#
# Promotes nothing, writes no .selected pin, touches no ledger and no certificate.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export PATH="$REPO/.venv/bin:$PATH"
export STUDY_MAP=Town06
export PYTHONUNBUFFERED=1
unset PYTHONPATH

SEEDS=${SEEDS:-"0 1 2 3 4 5 6 7"}
ARMS=${ARMS:-"init data both f50 f25"}
IN_W=168; IN_H=56
CH=32,64,64; FC=128
LR=${LR:-3e-4}
TEACHER=teacher_mixed_t06lap_dagger_r03
BASE=mixed_t06lap
DAGGER_DIRS=dagger_mixed_t06lap,dagger_student_S_mixed_t06_t06lap

OUT_DIR=$REPO/${OUT_DIR:-results/town06/variance}
mkdir -p "$OUT_DIR" "$REPO/results/town06_logs"
LOG=$OUT_DIR/q6.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

LOCK=/tmp/q6_variance.lock
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
    echo "Q6 already running (pid $(cat "$LOCK")); exiting"; exit 0
fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT

# arm -> INIT_SEED DATA_SEED TRAIN_FRAC, as functions of the seed $1.
arm_env() {
    case "$1" in
        init) echo "DISTILL_INIT_SEED=$2 DISTILL_DATA_SEED=0 DISTILL_TRAIN_FRAC=1.0" ;;
        data) echo "DISTILL_INIT_SEED=0 DISTILL_DATA_SEED=$2 DISTILL_TRAIN_FRAC=1.0" ;;
        both) echo "DISTILL_INIT_SEED=$2 DISTILL_DATA_SEED=$2 DISTILL_TRAIN_FRAC=1.0" ;;
        f50)  echo "DISTILL_INIT_SEED=$2 DISTILL_DATA_SEED=$2 DISTILL_TRAIN_FRAC=0.5" ;;
        f25)  echo "DISTILL_INIT_SEED=$2 DISTILL_DATA_SEED=$2 DISTILL_TRAIN_FRAC=0.25" ;;
        *)    echo "BADARM" ;;
    esac
}

say "=== Q6 variance decomposition: arms [$ARMS], seeds [$SEEDS], lr $LR, no CARLA ==="

for ARM in $ARMS; do
    ENV_PROBE=$(arm_env "$ARM" 0)
    [ "$ENV_PROBE" = "BADARM" ] && { say "unknown arm $ARM -- stopping"; exit 2; }
    say "--- arm $ARM ---"
    for SEED in $SEEDS; do
        SCK="S_q6_${ARM}_s${SEED}"
        AENV=$(arm_env "$ARM" "$SEED")

        if [ ! -f "$REPO/pipeline/checkpoints/$SCK.pth" ]; then
            say "distil $SCK  [$AENV]"
            ( cd pipeline && env $AENV DISTILL_DETERMINISTIC=1 \
                CUBLAS_WORKSPACE_CONFIG=:4096:8 \
                python3 distill.py --in-w "$IN_W" --in-h "$IN_H" --out "$SCK" \
                --teacher "$TEACHER" --base "$BASE" --dagger-dirs "$DAGGER_DIRS" \
                --channels "$CH" --fc "$FC" --lr "$LR" ) \
                >>"$REPO/results/town06_logs/distill_${SCK}.log" 2>&1 \
                || { say "  $SCK: distillation FAILED -- skipping"; continue; }
        fi

        K=$OUT_DIR/kd_${ARM}_s${SEED}.json
        if [ ! -f "$K" ]; then
            STUDENT="$SCK" CHANNELS="$CH" FC="$FC" TEACHER="$TEACHER" BASE="$BASE" \
            DAGGER_DIRS="$DAGGER_DIRS" KD_JSON="$K" \
                python3 scripts/kd_error_by_condition.py >>"$LOG" 2>&1 \
                || { say "  $SCK: KD error FAILED"; continue; }
        fi
        say "  $ARM s$SEED fog p99 $(python3 -c "
import json; print(f\"{json.load(open('$K'))['conditions']['fog']['p99_abs_err']:.4f}\")")"
    done
done
say "=== Q6 complete; summarise with scripts/q6_summarise.py ==="

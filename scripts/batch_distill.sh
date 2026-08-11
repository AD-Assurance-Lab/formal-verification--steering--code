#!/usr/bin/env bash
# M3: distil both students, sweeping capacity for the mixed one. NO CARLA.
#
# Objective is NOT "enough width" -- it is the MINIMUM ReLU COUNT that can drive all four
# conditions, because ReLU count is what drives bound looseness at verification time. The
# previous generation's mixed student needed 2x width for three conditions, and its own
# methodology records the cost: the wider student certified 20% on fog against the narrow
# one's 72%, part of which was width rather than robustness.
#
# Two knobs, different cost profiles:
#   width      channels x k  ->  roughly x k   ReLU
#   resolution both dims x k ->  roughly x k^2 ReLU
# Resolution is genuinely available now in a way it was not before: the verifier's input is
# the physical parameter, not the image, so resolution no longer inflates the perturbation
# dimension. Whether it buys competence more cheaply than width in ReLU terms is measured
# here, not assumed.
#
# KD RMSE is a SCREEN, not a decision. Measured today: 4x width barely moved it (0.0338 ->
# 0.0314) while flipping a closed-loop direction from fail to pass. Closed loop decides;
# this batch only narrows the candidates so one CARLA session can test them all.
set -uo pipefail

PY=/home/za/ad-assurance--workspace/sdp-crown--automated-driving--code/venv_sdp/bin/python
cd "$(dirname "$0")/.."

# RESUMABLE. Something on this machine reaps background jobs -- twice today every
# background process died at once with no OOM entry in our own logs, and the likely cause
# is another CARLA session loading a very large map and exhausting memory, after which the
# OOM killer takes the biggest processes it can find. Long unattended runs must therefore
# be cheap to lose, not merely restartable.
#
# A config is skipped only when its DONE marker exists. Keying on the .pth alone would be
# wrong: distil saves a checkpoint on every improvement, so a killed run leaves a valid but
# undertrained file that would be mistaken for a finished one.
MARKERS=pipeline/checkpoints/.batch_done
mkdir -p "$MARKERS"

run_distill() {   # name, then distill args
    local name="$1"; shift
    if [ -f "$MARKERS/$name" ]; then
        echo "############ $name -- already complete, skipping ############"
        return 0
    fi
    if $PY -u pipeline/distill.py "$@"; then
        touch "$MARKERS/$name"
    else
        echo "!!!! $name FAILED or was killed; leaving unmarked so it reruns"
    fi
}

CLEAR_TEACHER=teacher_clear_dagger_r03
MIXED_TEACHER=teacher_mixed_dagger_r07

echo "############ S_clear -- baseline width, clear frames only ############"
run_distill S_clear_84x28 --in-w 84 --in-h 28 --out S_clear_84x28 \
    --teacher "$CLEAR_TEACHER" --base conditions --dagger-dirs dagger_clear \
    --weathers clear --channels 8,16,16 --fc 32 --epochs 120

# --- S_mixed: width sweep at the baseline resolution ------------------------
for cfg in "8,16,16 32 w1" "16,32,32 64 w2" "24,48,48 96 w3" "32,64,64 128 w4"; do
    set -- $cfg
    echo "############ S_mixed 84x28 channels=$1 fc=$2 ($3) ############"
    run_distill "S_mixed_84x28_$3" --in-w 84 --in-h 28 --out "S_mixed_84x28_$3" \
        --teacher "$MIXED_TEACHER" --base conditions --dagger-dirs dagger_mixed \
        --channels "$1" --fc "$2" --epochs 120
done

# --- S_mixed: resolution sweep at 2x width ----------------------------------
# Teacher targets are resolution-independent and cached, so these reuse the same targets.
for cfg in "112 38 r112" "140 47 r140"; do
    set -- $cfg
    echo "############ S_mixed ${1}x${2} channels=16,32,32 fc=64 ($3) ############"
    run_distill "S_mixed_$3_w2" --in-w "$1" --in-h "$2" --out "S_mixed_$3_w2" \
        --teacher "$MIXED_TEACHER" --base conditions --dagger-dirs dagger_mixed \
        --channels 16,32,32 --fc 64 --epochs 120
done

echo "############ batch complete ############"

#!/usr/bin/env bash
# E1b -- probe one bimodal cell. docs/E1B_PREREGISTRATION.md is the prediction.
#
# E1 left six VOID cells that are bimodal rather than noisy. This drives the cleanest one
# 24 times in two arms that differ ONLY in whether the client process persists across
# laps -- CARLA is restarted before every lap in both (A-4) -- which is exactly the
# question E5 asked about the screen/gate discrepancy.
#
#   arm A: one process, --reps 12
#   arm B: twelve processes, --reps 1
#
# NOT a failure-rate measurement. Standing rule 3: a cell whose laps disagree is VOID,
# and more laps would convert an identified defect into a plausible rate and lose it.
# This characterises the mechanism so the VOID cells can be dispositioned.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export PATH="$REPO/.venv/bin:$PATH"
export STUDY_MAP=Town06 CARLA_PORT=${CARLA_PORT:-3000} CARLA_WINDOWED=${CARLA_WINDOWED:-1}
export PYTHONUNBUFFERED=1

CK=${CK:-S_mixed_res_252x84_s1}
CH=${CH:-32,64,64}
FC=${FC:-128}
IN_W=${IN_W:-252}
IN_H=${IN_H:-84}
COND=${COND:-fog}
N=${N:-12}

OUT_DIR=$REPO/results/town06/bimodal
mkdir -p "$OUT_DIR"
LOG=$OUT_DIR/e1b.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

LOCK=/tmp/e1b_bimodal_probe.lock
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
    echo "E1b already running (pid $(cat "$LOCK")); exiting"; exit 0
fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT

drive() {   # drive <reps> <outfile>
    python3 scripts/compare_student_variants.py --checkpoints "$CK" \
        --channels "$CH" --fc "$FC" --in-w "$IN_W" --in-h "$IN_H" \
        --reps "$1" --weather "$COND" --out "$2" >>"$LOG" 2>&1
    rc=$?
    # An unmeasured lap is not a failing lap: stop rather than score the model for it.
    [ $rc -eq 3 ] && { say "FATAL: a lap could not be measured (harness). Stopping."; exit 3; }
    return 0
}

say "=== E1b bimodal probe: $CK / $COND, ${IN_W}x${IN_H} ==="

A=$OUT_DIR/armA_one_process_${N}reps.json
if [ -f "$A" ]; then say "arm A already done"; else
    say "arm A: ONE process, $N laps"
    drive "$N" "$A"
fi

for i in $(seq 1 "$N"); do
    B=$OUT_DIR/armB_proc$(printf '%02d' "$i").json
    if [ -f "$B" ]; then say "arm B lap $i already done"; continue; fi
    say "arm B: process $i of $N, 1 lap"
    drive 1 "$B"
done

say "=== E1b complete; summarise with scripts/e1b_summarise.py ==="

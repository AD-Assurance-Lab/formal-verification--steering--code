#!/usr/bin/env bash
# Measure the RENDERED OUTCOME of every condition on the Town06 lap, one instrument,
# one lap per condition, a clean CARLA server before each.
#
# WHY. T06-F20 fixed the rule that a condition is DECLARED BY ITS RENDERED OUTCOME, not
# by its sun angle or its shutter. T06-F41 then reported that the lap route renders low
# sun 37.8% darker than the six-section route it was calibrated on, and night 33.7%
# darker, and concluded the constants had to move. Those two numbers came from two
# DIFFERENT dataset collections compared to each other, not from one instrument driving
# one route -- and a dataset's frame mean mixes in whatever poses DAgger happened to
# visit. Three different "Town06 lap brightness" tables exist in this repo and no two
# agree, which is the signature of a comparison, not of a measurement.
#
# This is the measurement: same script, same preprocessing, same pure-pursuit lap, one
# clean server each, all four conditions. The ratios it produces are what the condition
# constants are answerable to.
#
#   bash scripts/calibrate_lap_conditions.sh
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
LOG_DIR="$REPO/results/town06_logs"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/lap_condition_calibration.log"
OUT=${OUT:-results/town06/lap_conditions}
export STUDY_MAP=Town06 CARLA_PORT="${CARLA_PORT:-3000}"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

CONDITIONS="${CONDITIONS:-clear fog night low_sun}"

say "=== lap condition calibration: $CONDITIONS -> $OUT ==="
for C in $CONDITIONS; do
    say "restarting CARLA before $C"
    bash scripts/carla_restart.sh >>"$LOG_DIR/lap_condition_restart.log" 2>&1 || {
        say "  restart FAILED before $C"; continue; }
    rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null
    say "driving $C"
    python3 scripts/measure_lap_condition.py --condition "$C" --out-dir "$OUT" 2>&1 \
        | tee -a "$LOG"
done
say "=== done ==="

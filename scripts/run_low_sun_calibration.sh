#!/usr/bin/env bash
# Sweep sun azimuth for low sun on the Town06 lap, one lap per config, a clean CARLA
# server before each (A-4: the lap is the repetition and the clean server is per lap).
#
# The reference lap is `clear` at its own azimuth -- clear is the s = 0 anchor and is
# never swept, exactly as the altitude override is scoped to skip it.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
LOG_DIR="$REPO/results/town06_logs"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/low_sun_calibration.log"
export STUDY_MAP=Town06 CARLA_PORT="${CARLA_PORT:-3000}" DISPLAY="${DISPLAY:-:0}" CARLA_WINDOWED=1
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

AZIMUTHS="${AZIMUTHS:-0 45 90 135 180 225 270 315}"

run_one() {   # run_one <label> <args...>
    local label="$1"; shift
    say "restarting CARLA before $label"
    bash scripts/carla_restart.sh >>"$LOG_DIR/low_sun_restart.log" 2>&1 || {
        say "  restart FAILED before $label"; return 1; }
    rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null
    say "driving $label"
    python3 scripts/calibrate_low_sun_azimuth.py "$@" 2>&1 | tee -a "$LOG"
    return "${PIPESTATUS[0]}"
}

say "=== low sun azimuth calibration: clear reference + $(echo $AZIMUTHS | wc -w) azimuths ==="
run_one "clear (reference)" --condition clear || say "clear reference FAILED"
for AZ in $AZIMUTHS; do
    run_one "low_sun az=$AZ" --condition low_sun --azimuth "$AZ" || say "  az=$AZ FAILED"
done
say "=== sweep complete ==="
python3 scripts/report_low_sun_calibration.py 2>&1 | tee -a "$LOG"

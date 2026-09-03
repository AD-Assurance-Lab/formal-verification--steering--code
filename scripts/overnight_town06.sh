#!/usr/bin/env bash
# Chain the remaining Town06 work unattended: student gate -> everything after it.
#
#   setsid nohup bash scripts/overnight_town06.sh > /tmp/overnight.log 2>&1 &
#
# Two stages, and the second only runs if the first genuinely succeeded:
#
#   1. Student DAgger until the mixed student holds ALL FOUR conditions over THREE laps
#      each, from-scratch re-distillation per round. Writes the checkpoint pin.
#   2. scripts/finish_town06_lap.sh -- clear student, competence gate, captures, the A-3
#      capture gate, blind certification, COMMIT, the scored ledger, the comparison.
#
# It does NOT invent a pass. If the student never reaches 12/12 the run stops with the best
# result on the record and stage 2 does not start, because certifying a model that cannot
# drive bounds deviation from an output that is already wrong (PROTOCOL section 4a).
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06 CARLA_PORT=${CARLA_PORT:-3000} CARLA_WINDOWED=${CARLA_WINDOWED:-0}
export PYTHONUNBUFFERED=1

LOG=$REPO/results/town06_logs/overnight.log
mkdir -p "$(dirname "$LOG")"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

say "=== overnight run begins ==="

# ---------------------------------------------------------------- 1. the student gate
PIN=$REPO/pipeline/checkpoints/S_mixed_t06lap_168x56_w4.selected
if [ -f "$PIN" ]; then
    say "mixed student already pinned: $(cat "$PIN")"
else
    # If a loop is already running, wait for it rather than starting a second one --
    # two DAgger drivers on one CARLA port is the collision the lock exists to stop.
    if pgrep -f "[s]dagger_loop.sh" >/dev/null; then
        say "a student-DAgger loop is already running; waiting for it"
        while pgrep -f "[s]dagger_loop.sh" >/dev/null; do sleep 60; done
    else
        say "starting the student-DAgger loop"
        bash "$REPO/scripts/student_dagger_until_12.sh" >>"$LOG" 2>&1
    fi
fi

if [ ! -f "$PIN" ]; then
    say "STOPPING: the mixed student never held 12/12."
    say "  Best per-condition results are in results/town06/sdl_*.json."
    say "  Not certifying: a bound on deviation from an output that is already wrong"
    say "  says nothing about the system (PROTOCOL section 4a)."
    exit 1
fi
say "mixed student pinned: $(cat "$PIN")"

# ---------------------------------------------------------------- 2. everything after
say "running scripts/finish_town06_lap.sh"
bash "$REPO/scripts/finish_town06_lap.sh" >>"$LOG" 2>&1
rc=$?
say "finish_town06_lap.sh exited $rc"
if [ "$rc" -eq 0 ]; then
    say "=== DEPLOYMENT TEST COMPLETE ==="
    python3 "$REPO/scripts/compare_town06.py" 2>&1 | tee -a "$LOG"
else
    say "=== stopped at rc=$rc; see $LOG ==="
fi
exit $rc

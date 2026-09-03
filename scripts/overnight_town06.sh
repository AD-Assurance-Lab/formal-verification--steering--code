#!/usr/bin/env bash
# Chain the remaining Town06 work unattended: student gate -> everything after it.
#
#   setsid nohup bash scripts/overnight_town06.sh > /tmp/overnight.log 2>&1 &
#
# Two stages, and the second only runs if the first genuinely succeeded:
#
#   1. Find a mixed student that holds ALL FOUR conditions over THREE laps each, by
#      re-drawing the distillation seed on the fixed pool. Writes the checkpoint pin.
#      Successive DAgger rounds on that pool oscillate between failing fog and failing
#      night while the pool stays balanced to 0.5%, which is training variance rather
#      than missing data -- see the header of select_mixed_student_seed.sh.
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

# ONE SUPERVISOR AT A TIME. Without this, launching a second overnight run while the
# first is working restarts CARLA underneath it: on 2026-09-02 the first instance's
# capture-gate drive had just passed (clear student, 1.28 ft) when a second instance's
# restart killed its server, and the stage reported "restart FAILED ... refusing to
# measure". One CARLA per port is the oldest rule in this repo and the supervisor was the
# one driver not honouring it.
OVERNIGHT_LOCK=/tmp/town06_overnight.lock
if [ -e "$OVERNIGHT_LOCK" ] && kill -0 "$(cat "$OVERNIGHT_LOCK" 2>/dev/null)" 2>/dev/null; then
    echo "another overnight run is alive (pid $(cat "$OVERNIGHT_LOCK")); exiting"
    exit 0
fi
echo $$ > "$OVERNIGHT_LOCK"
trap 'rm -f "$OVERNIGHT_LOCK"' EXIT

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
    # A PID LOCK, NOT A PROCESS-NAME MATCH. pgrep -f matches any command line CONTAINING
    # the script's name, and this supervisor waited on a git commit whose message named it.
    SWEEP_LOCK=/tmp/town06_seed_sweep.lock
    if [ -e "$SWEEP_LOCK" ] && kill -0 "$(cat "$SWEEP_LOCK" 2>/dev/null)" 2>/dev/null; then
        say "a seed sweep is already running (pid $(cat "$SWEEP_LOCK")); waiting for it"
        while [ -e "$SWEEP_LOCK" ] && kill -0 "$(cat "$SWEEP_LOCK" 2>/dev/null)" 2>/dev/null; do
            sleep 60
        done
    else
        say "starting the seed sweep (see scripts/select_mixed_student_seed.sh for why"
        say "  a seed re-draw rather than more DAgger rounds)"
        bash "$REPO/scripts/select_mixed_student_seed.sh" >>"$LOG" 2>&1
    fi
fi

if [ ! -f "$PIN" ]; then
    say "STOPPING: the mixed student never held 12/12."
    say "  Per-seed results are in results/town06/seed_gate_*.json."
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

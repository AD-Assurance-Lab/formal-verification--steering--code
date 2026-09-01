#!/usr/bin/env bash
# Keep the Town06 pipeline alive, and make its death LOUD.
#
# Three times today the pipeline stopped and sat idle -- once for four hours, once for
# thirty-eight minutes -- because noticing depended on me choosing to look. The pipeline
# resumes cleanly from disk (datasets, checkpoints and DAgger rounds all persist), so
# there is no reason a human or an assistant should be the retry mechanism.
#
# This restarts it when it dies and writes a line every time, so the log itself is the
# alarm rather than someone remembering to check.
#
#   setsid nohup bash scripts/watchdog_town06.sh > /tmp/t06_watchdog.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06 CARLA_PORT=${CARLA_PORT:-3000}
export CARLA_WINDOWED=${CARLA_WINDOWED:-1} DISPLAY=${DISPLAY:-:0}
LOG=$REPO/results/town06_logs/watchdog.log
mkdir -p "$(dirname "$LOG")"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

MAX_RESTARTS=${MAX_RESTARTS:-40}
n=0
say "watchdog started (max $MAX_RESTARTS restarts)"
while : ; do
    if pgrep -f "[r]un_town06_pipeline" >/dev/null; then
        sleep 60; continue
    fi
    # Pipeline is not running. Is it because everything finished?
    # DONE means THIS study's artifacts, not any artifacts. The first version checked
    # for certificate_town06.json plus ledger cells and exited immediately -- both were
    # present, left over from the superseded six-section study on a different route. A
    # stale artifact of the right shape is indistinguishable from a current one, which is
    # the failure this whole week has been about.
    if ls "$REPO"/results/town06/ledger/*S_*t06lap*closed_loop.json >/dev/null 2>&1; then
        say "lap-study ledger cells present; watchdog exiting"
        exit 0
    fi
    n=$((n+1))
    if [ "$n" -gt "$MAX_RESTARTS" ]; then
        say "STOPPING: $MAX_RESTARTS restarts is not a transient failure. Something needs"
        say "  a human. Last pipeline lines:"
        tail -5 /tmp/t06_pipeline_wd.log 2>/dev/null | sed 's/^/    /' | tee -a "$LOG"
        exit 1
    fi
    # BACK OFF. Restarting instantly means a pipeline that dies on startup is restarted
    # three times a minute, and concurrent pipelines then fight over CARLA -- which is
    # worse than being stopped. Wait long enough that a fast failure is visible as one.
    say "pipeline is not running -- restart $n/$MAX_RESTARTS (waiting 60 s first)"
    sleep 60
    rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null
    setsid nohup bash "$REPO/scripts/run_town06_pipeline.sh" \
        > /tmp/t06_pipeline_wd.log 2>&1 < /dev/null &
    sleep 90
done

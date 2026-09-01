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
    if [ -f "$REPO/results/town06/certificate_town06.json" ] && \
       ls "$REPO"/results/town06/ledger/*closed_loop.json >/dev/null 2>&1; then
        say "pipeline complete (certificate and ledger present); watchdog exiting"
        exit 0
    fi
    n=$((n+1))
    if [ "$n" -gt "$MAX_RESTARTS" ]; then
        say "STOPPING: $MAX_RESTARTS restarts is not a transient failure. Something needs"
        say "  a human. Last pipeline lines:"
        tail -5 /tmp/t06_pipeline_wd.log 2>/dev/null | sed 's/^/    /' | tee -a "$LOG"
        exit 1
    fi
    say "pipeline is not running -- restart $n/$MAX_RESTARTS"
    rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null
    setsid nohup bash "$REPO/scripts/run_town06_pipeline.sh" \
        > /tmp/t06_pipeline_wd.log 2>&1 < /dev/null &
    sleep 90
done

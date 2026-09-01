#!/usr/bin/env bash
# THE launcher. Every script that starts CARLA must call this one.
#
# Why this file exists: the determinism flags are LAUNCH-time properties, invisible over
# RPC, and this repo had EIGHT separate places that started the server. Seven of them
# lacked -notexturestreaming, which is the dominant render entropy source (168x,
# carla-determinism D-3). A server started by any of those answers perfectly normally and
# quietly makes every measurement taken against it noisier -- including, in
# finish_town06_deployment.sh, the SCORED LEDGER itself.
#
# That is the same failure mode as vendoring a copy of a rule per repo: copies drift, and
# the drift is silent. One launcher, or the flags will go missing again.
#
#   bash scripts/carla_launch.sh          # start and wait until it SERVES
#   CARLA_WINDOWED=1 bash scripts/...     # visible window, so runs can be watched
#
# Does NOT stop anything first -- that is carla_restart.sh's job, and it matters that the
# two are separate: mid-pipeline restarts must not pkill the client that is driving.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
PORT=${CARLA_PORT:-3000}
CARLA_ROOT=${CARLA_ROOT:-$HOME/carla}
QUALITY=${CARLA_QUALITY:-Epic}          # D-5: High measured catastrophically worse
LOG=${CARLA_LOG:-$REPO/results/town06_logs/carla.log}
mkdir -p "$(dirname "$LOG")"

# D-3, defaulted per map so Town04 relaunches exactly as the published study did.
if [ -n "${CARLA_EXTRA_ARGS:-}" ]; then
    EXTRA=$CARLA_EXTRA_ARGS
else
    # EVERY map, as of the Town04 redo. This was Town06-only while the published Town04
    # artifact had to keep reproducing byte-for-byte; Town04 is now being re-measured
    # under the corrected harness, so there is no longer a map that wants the old
    # behaviour. `main` still carries the Town06-only default.
    EXTRA="-notexturestreaming"
fi

if [ "${CARLA_WINDOWED:-0}" = "1" ]; then
    echo "  launching CARLA WINDOWED on DISPLAY=${DISPLAY:-:0} (quality=$QUALITY, extra=[$EXTRA])"
    ( cd "$CARLA_ROOT" && DISPLAY="${DISPLAY:-:0}" setsid nohup ./CarlaUE4.sh \
        -carla-rpc-port="$PORT" -quality-level="$QUALITY" $EXTRA -windowed -ResX=1280 -ResY=720 \
        >>"$LOG" 2>&1 < /dev/null & )
else
    echo "  launching CARLA headless (quality=$QUALITY, extra=[$EXTRA])"
    ( cd "$CARLA_ROOT" && setsid nohup ./CarlaUE4.sh -carla-rpc-port="$PORT" \
        -RenderOffScreen -quality-level="$QUALITY" $EXTRA >>"$LOG" 2>&1 < /dev/null & )
fi

# A bound port is not a ready simulator: it binds well before it can serve, and a gate
# once drove for 12 minutes against a listening-but-unready server and recorded the
# failure as if the students had failed. Readiness is a successful get_world() on the
# STUDY map. `timeout` as a wall clock: a probe that hangs is worse than one that fails.
CARLA_PORT=$PORT timeout 300 python3 "$REPO/scripts/wait_carla_ready.py" --timeout 240 || {
    echo "FATAL: CARLA did not come up on $PORT"; exit 1; }

# Prove the flags actually landed, rather than trusting that they did. This reads the
# server's real /proc argv, so a server left running by something else -- a stale one on
# the same port, a hand-started one -- is caught here instead of poisoning a measurement.
# The GPU must be USABLE, not merely present -- see scripts/check_gpu_usable.py.
python3 "$REPO/scripts/check_gpu_usable.py" || exit 1

python3 -m carla_determinism --port "$PORT" || {
    echo "FATAL: the server on $PORT violates the determinism rules (above)."; exit 1; }

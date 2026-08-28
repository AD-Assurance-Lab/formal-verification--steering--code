#!/usr/bin/env bash
# Stop CARLA, start it, wait until it actually SERVES. Routine hygiene, not a last resort.
#
# A server left up degrades silently: it keeps answering, keeps reporting plausible
# vehicle velocities, and stops advancing physics correctly. Measured on a degraded
# server, sections drove 14-62% of their length at 1.3-5.6 m/s while speed_mph reported
# 20.0 the whole time, and one run flung the car 190 m in 18 steps. Nothing in a result
# reveals it. A whole evening of "findings" was built on top of it.
#
# Restarting costs ~30 s. Parsing bad data costs a night. Restart.
#
#   bash scripts/carla_restart.sh
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
PORT=${CARLA_PORT:-3000}
CARLA_ROOT=${CARLA_ROOT:-$HOME/carla}
# CARLA_QUALITY defaults to Epic, so every existing caller and the published Town04
# reproduction are byte-for-byte unaffected. It is a variable only because the
# determinism campaign has to SWEEP it: temporal AA and the postprocess chain are
# quality-gated, and they are prime suspects for the render-path entropy.
QUALITY=${CARLA_QUALITY:-Epic}
# CARLA_EXTRA_ARGS passes UE4 flags through. Empty by default, so nothing existing
# changes. The determinism campaign needs -notexturestreaming: UE4 streams textures in
# asynchronously, so which mip is resident when a frame is rendered depends on load
# timing rather than on world state, and that is a render difference no camera
# attribute can pin.
# -notexturestreaming is DEFAULT ON FOR TOWN06 and off elsewhere, so Town04 relaunches
# exactly as the published study did. UE4 streams texture mips in asynchronously, so
# which mip is resident when a frame is rendered depends on load timing rather than on
# world state. Measured open loop with physics pinned bit-identical, over four repeats
# of one scripted run: it was the DOMINANT render entropy source, and disabling it cut
# the steering difference the renderer injects from 3.9e-3 to 2.4e-5, a 168x reduction,
# and removed the cold-server first-run outlier entirely.
if [ -n "${CARLA_EXTRA_ARGS:-}" ]; then
    EXTRA=$CARLA_EXTRA_ARGS
elif [ "${STUDY_MAP:-}" = "Town06" ]; then
    EXTRA="-notexturestreaming"
else
    EXTRA=""
fi

# SIGTERM first, never SIGKILL: a client killed with -9 skips env.cleanup and leaves the
# world in synchronous mode with nothing ticking, which is how the server gets wedged in
# the first place. Give clients a chance to restore settings.
for pat in "[e]valuate.py" "[d]agger_student.py" "[d]agger.py" "[c]ollect_data.py" \
           "[c]apture_offset_yaw.py" "[c]losed_loop_ledger.py"; do
    pkill -TERM -f "$pat" 2>/dev/null
done
sleep 5
for pat in "[e]valuate.py" "[d]agger_student.py" "[d]agger.py" "[c]ollect_data.py" \
           "[c]apture_offset_yaw.py" "[c]losed_loop_ledger.py"; do
    pkill -KILL -f "$pat" 2>/dev/null      # only after they were asked politely
done

pkill -f "[C]arlaUE4-Linux-Shipping.*rpc-port=$PORT" 2>/dev/null
sleep 10
rm -f "/tmp/carla-locks/carla-$PORT.lock" 2>/dev/null

# CARLA_WINDOWED=1 launches with a visible window on DISPLAY so runs can be WATCHED.
# The spectator chase camera (carla_env.update_spectator) follows the ego automatically;
# it only needs a window to draw into. Headless is the default for unattended sweeps.
if [ "${CARLA_WINDOWED:-0}" = "1" ]; then
    echo "  launching CARLA WINDOWED on DISPLAY=${DISPLAY:-:0}"
    ( cd "$CARLA_ROOT" && DISPLAY="${DISPLAY:-:0}" setsid nohup ./CarlaUE4.sh \
        -carla-rpc-port="$PORT" -quality-level="$QUALITY" $EXTRA -windowed -ResX=1280 -ResY=720 \
        >>"$REPO/results/town06_logs/carla.log" 2>&1 < /dev/null & )
else
    ( cd "$CARLA_ROOT" && setsid nohup ./CarlaUE4.sh -carla-rpc-port="$PORT" \
        -RenderOffScreen -quality-level="$QUALITY" $EXTRA >>"$REPO/results/town06_logs/carla.log" 2>&1 \
        < /dev/null & )
fi

# `timeout` as a wall clock. A readiness probe that hangs is worse than one that fails,
# because every caller then waits on it forever.
CARLA_PORT=$PORT timeout 300 python3 "$REPO/scripts/wait_carla_ready.py" --timeout 240 || {
    echo "FATAL: CARLA did not come back on $PORT"; exit 1; }
nvidia-smi --query-gpu=memory.used --format=csv,noheader | sed 's/^/  GPU after restart: /'

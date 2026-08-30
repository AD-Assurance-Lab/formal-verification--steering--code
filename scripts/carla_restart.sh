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

# REFUSE TO RUN IF SOMEONE ELSE HOLDS THE CARLA LOCK.
#
# The kill list below terminates client processes BY NAME, which is correct when this
# script owns the machine and catastrophic when it does not: a capture job calling this
# per capture will SIGTERM a ledger that is mid-run, in another job, holding the lock.
# That happened -- a ledger cell died with exit 143 and left a stale lock, and it read as
# a mysterious silent failure because the signal came from a different pipeline.
#
# The lock already exists to stop two clients ticking one world. Honour it here too:
# killing the holder is a worse version of the same collision.
LOCKF="/tmp/carla-locks/carla-$PORT.lock"
if [ "${CARLA_RESTART_FORCE:-}" != "1" ] && [ -f "$LOCKF" ]; then
    LOCKPID=$(head -c 64 "$LOCKF" 2>/dev/null | tr -dc '0-9' | head -c 9)
    if [ -n "$LOCKPID" ] && kill -0 "$LOCKPID" 2>/dev/null; then
        echo "REFUSING to restart: CARLA :$PORT is held by live pid $LOCKPID"
        echo "  ($(cat "$LOCKF" 2>/dev/null))"
        echo "  This script kills clients by name and would terminate that job mid-run."
        echo "  Wait for it, or re-run with CARLA_RESTART_FORCE=1 if it is genuinely dead."
        exit 3
    fi
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
# The LAUNCH half lives in carla_launch.sh, which is the single place that knows the
# determinism flags. This script owns the STOP half -- the order of which matters
# (SIGTERM, wait, SIGKILL) and is why the two are separate files.
bash "$REPO/scripts/carla_launch.sh" || exit 1

nvidia-smi --query-gpu=memory.used --format=csv,noheader | sed 's/^/  GPU after restart: /'

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
    # 9>&- : do NOT let the daemonised server inherit the caller's descriptors.
    # carla_restart.sh holds its serialisation lock on fd 9, and CARLA inheriting that fd
    # holds the lock for the SERVER's entire lifetime -- so the next restart waits the full
    # timeout and fails. Same family as this repo's older note about piping
    # carla_restart.sh: the detached child inherits what the parent had open.
    ( cd "$CARLA_ROOT" && DISPLAY="${DISPLAY:-:0}" setsid nohup ./CarlaUE4.sh \
        -carla-rpc-port="$PORT" -quality-level="$QUALITY" $EXTRA -windowed -ResX=1280 -ResY=720 \
        >>"$LOG" 2>&1 < /dev/null 9>&- & )
else
    echo "  launching CARLA headless (quality=$QUALITY, extra=[$EXTRA])"
    ( cd "$CARLA_ROOT" && setsid nohup ./CarlaUE4.sh -carla-rpc-port="$PORT" \
        -RenderOffScreen -quality-level="$QUALITY" $EXTRA >>"$LOG" 2>&1 < /dev/null 9>&- & )
fi

# A bound port is not a ready simulator: it binds well before it can serve, and a gate
# once drove for 12 minutes against a listening-but-unready server and recorded the
# failure as if the students had failed. Readiness is a successful get_world() on the
# STUDY map. `timeout` as a wall clock: a probe that hangs is worse than one that fails.
if ! CARLA_PORT=$PORT timeout 300 python3 "$REPO/scripts/wait_carla_ready.py" --timeout 240; then
    # WINDOWED FALLS BACK TO HEADLESS, LOUDLY.
    #
    # Standing rule 6 wants a visible window so runs can be WATCHED, and that is the
    # default. But a windowed launch depends on the X session the launcher happens to sit
    # in, and it fails silently when that session cannot reach the display: measured
    # 2026-09-02, CarlaUE4 exits rc=1 with an EMPTY log while `xdpyinfo` on the same
    # DISPLAY succeeds. Headless starts fine in the same shell.
    #
    # Refusing outright would stop an unattended campaign for a cosmetic reason. Falling
    # back silently would hide a deviation from a standing rule. So: fall back, say so on
    # every launch, and let the photometry gate below prove the render did not move --
    # headless and windowed agree to 4e-5 on a full driven lap (T06-F42), which is what
    # makes the fallback safe rather than merely convenient.
    if [ "${CARLA_WINDOWED:-0}" = "1" ]; then
        echo "  WINDOWED LAUNCH FAILED on DISPLAY=${DISPLAY:-:0}; falling back to HEADLESS."
        echo "  (standing rule 6 asks for a watchable window; this run is not watchable.)"
        pkill -f "[C]arlaUE4.*rpc-port=$PORT" 2>/dev/null
        for i in $(seq 1 20); do
            ss -ltn 2>/dev/null | grep -q ":$PORT " || break
            sleep 1
        done
        ( cd "$CARLA_ROOT" && setsid nohup ./CarlaUE4.sh -carla-rpc-port="$PORT" \
            -RenderOffScreen -quality-level="$QUALITY" $EXTRA >>"$LOG" 2>&1 < /dev/null 9>&- & )
        CARLA_PORT=$PORT timeout 300 python3 "$REPO/scripts/wait_carla_ready.py" --timeout 240 || {
            echo "FATAL: CARLA did not come up on $PORT, windowed OR headless"; exit 1; }
    else
        echo "FATAL: CARLA did not come up on $PORT"; exit 1
    fi
fi

# Prove the flags actually landed, rather than trusting that they did. This reads the
# server's real /proc argv, so a server left running by something else -- a stale one on
# the same port, a hand-started one -- is caught here instead of poisoning a measurement.
# The GPU must be USABLE, not merely present -- see scripts/check_gpu_usable.py.
python3 "$REPO/scripts/check_gpu_usable.py" || exit 1

python3 -m carla_determinism --port "$PORT" || {
    echo "FATAL: the server on $PORT violates the determinism rules (above)."; exit 1; }

# PHOTOMETRY, on every fresh server. The determinism preflight verifies how the server
# was LAUNCHED and verify_condition() reads the weather struct back; both were green
# through half a day in which this server rendered the identical scene 15% darker, and
# every teacher trained on the result. See scripts/check_render_photometry.py.
#
# Only maps that have a recorded reference are checked, and a map without one SAYS SO on
# every launch rather than passing quietly -- an unchecked server that prints nothing is
# indistinguishable from a checked one, which is how this was missed.
PHOTO_REF="$REPO/results/photometry_reference.json"
if [ -f "$PHOTO_REF" ] && grep -q "\"${STUDY_MAP:-Town04}/clear\"" "$PHOTO_REF" 2>/dev/null; then
    # A DARK SERVER IS RELAUNCHED, NOT ACCEPTED AND NOT FATAL.
    #
    # T06-F46 measured what this defect is: a server comes up either correct or ~14% dark,
    # the state is decided at LAUNCH, it is constant for that server's whole life (five
    # measurements, spread 4e-6), and -- corrected 2026-09-02 -- it happens HEADLESS as
    # well as windowed. It is not a property of the flags, the map, the weather or the
    # camera, and the trigger is still unidentified.
    #
    # That combination is unusually kind: the bad state is per-instance and detectable in
    # about two seconds, so the cure is to throw the server away and start another.
    # Failing the whole restart instead turned a two-second retry into a stopped campaign,
    # and before this check existed, into two contaminated rebuilds.
    _photo_ok=0
    for _try in 1 2 3 4; do
        if STUDY_MAP="${STUDY_MAP:-Town04}" CARLA_PORT="$PORT" \
               python3 "$REPO/scripts/check_render_photometry.py"; then
            _photo_ok=1; break
        fi
        echo "  photometry REJECTED this server (attempt $_try/4); relaunching a new one."
        pkill -f "[C]arlaUE4.*rpc-port=$PORT" 2>/dev/null
        for _i in $(seq 1 25); do
            ss -ltn 2>/dev/null | grep -q ":$PORT " || break
            sleep 1
        done
        if [ "${CARLA_WINDOWED:-0}" = "1" ]; then
            ( cd "$CARLA_ROOT" && DISPLAY="${DISPLAY:-:0}" setsid nohup ./CarlaUE4.sh \
                -carla-rpc-port="$PORT" -quality-level="$QUALITY" $EXTRA -windowed \
                -ResX=1280 -ResY=720 >>"$LOG" 2>&1 < /dev/null 9>&- & )
        else
            ( cd "$CARLA_ROOT" && setsid nohup ./CarlaUE4.sh -carla-rpc-port="$PORT" \
                -RenderOffScreen -quality-level="$QUALITY" $EXTRA >>"$LOG" 2>&1 < /dev/null 9>&- & )
        fi
        CARLA_PORT=$PORT timeout 300 python3 "$REPO/scripts/wait_carla_ready.py" --timeout 240 \
            || { echo "FATAL: relaunched CARLA did not come up on $PORT"; exit 1; }
        python3 -m carla_determinism --port "$PORT" >/dev/null || {
            echo "FATAL: relaunched server on $PORT violates the determinism rules"; exit 1; }
    done
    [ "$_photo_ok" = 1 ] || {
        echo "FATAL: four servers in a row rendered at the wrong brightness on $PORT."
        echo "  That is not the intermittent launch defect; something has changed."; exit 1; }
else
    echo "  photometry NOT CHECKED: no reference for ${STUDY_MAP:-Town04} in results/photometry_reference.json"
fi

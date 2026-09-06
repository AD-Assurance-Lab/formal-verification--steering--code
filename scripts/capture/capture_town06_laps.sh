#!/usr/bin/env bash
# Full-lap verification captures for the Town06 deployment test.
#
# Only the centreline slice is needed: the for-all-disturbance coverage claim is
# per-frame, so the offset x yaw state grid costs 72,000 frames per condition and buys
# nothing here. OY_OFFSETS=0.0 OY_YAWS=0.0 collapses it to the nominal pose.
#
# Pose count is set so that the certifier's frozen stride of 8 lands on 200 poses per
# direction, matching PROTOCOL section 3 and the published Town04 sampling.
#
#   bash scripts/capture/capture_town06_laps.sh
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06
export CARLA_PORT=${CARLA_PORT:-3000}
export PYTHONUNBUFFERED=1

python3 -m steering.protocol_lock >/dev/null || { echo "PROTOCOL lock mismatch"; exit 1; }

# Q7: OY_CAPTURE_DIR retargets the capture set. A capture set is what a certificate is
# computed against, so a stray value here would silently certify a different set of frames
# than the committed one -- and standing rule 7 is explicit that a default which quietly
# changes scope is the worst kind. It is therefore REQUIRED to name a directory that does
# not already exist, and the canonical path is refused outright.
CAPDIR=${OY_CAPTURE_DIR:-results/arterial/captures}
if [ "$CAPDIR" != "results/arterial/captures" ]; then
    [ -d "$REPO/$CAPDIR" ] && { echo "FATAL: $CAPDIR already exists; refusing to mix capture sets"; exit 1; }
    echo "capture set: $CAPDIR  (projection ${OY_IN_W:-default}x${OY_IN_H:-default})"
fi
OUTDIR=$REPO/$CAPDIR
LOGD=$REPO/results/arterial_logs
mkdir -p "$OUTDIR" "$LOGD"

# The sampling RULE is frozen (every 8th control-rate pose, PROTOCOL section 3); the
# pose count follows from each section's length rather than being fixed at Town04's 200.
SECTIONS=$(STUDY_MAP=Town06 python3 -c "import steering.config as C;print(' '.join(C.SECTIONS))")
echo "sections: $SECTIONS"

for SEC in $SECTIONS; do
  # THE SCORED LENGTH. SECTION_LEN_M is the route's GEOMETRY, and on the lap the two
  # differ by the 170 m of bridged intersection that no closed-loop cell scores.
  LEN=$(STUDY_MAP=Town06 python3 -c "import steering.config as C;print(f\"{C.scored_len_m('$SEC'):.1f}\")")
  POSES=$(STUDY_MAP=Town06 python3 -c "import steering.config as C;print(C.steps_for('$SEC'))")
  for COND in clear fog night low_sun; do
    OUT="$CAPDIR/lap_${SEC}_${COND}.npz"
    if [ -f "$REPO/$OUT" ]; then echo "SKIP  $OUT"; continue; fi
    echo "[$(date '+%F %T')] capture $SEC/$COND  (${LEN} m, ${POSES} poses)"
    # R-SIM-1: restart before EVERY measurement. This driver took all captures in one
    # server session, which is exactly the exposure the rule exists to remove -- a server
    # degrades silently and nothing in a capture reveals which server produced it. The
    # Town04 driver restarts per capture; this one did not, and the drift went unnoticed
    # because the rule lived in prose rather than in a check.
    # RETRY A FAILED RESTART. A capture run is 20+ minutes of driving per condition and a
    # single transient must not throw it away. Observed 2026-09-02: CARLA reported "ready
    # on 3000 after 46s" and had DIED by the time the determinism preflight looked for it
    # ("no CarlaUE4 server found serving rpc-port 3000"), with nothing listening on the
    # port -- a server crash between readiness and the check, after three captures had
    # already succeeded on the same loop.
    #
    # Three attempts, twenty seconds apart. Three consecutive failures is a real problem
    # and still stops the run, because a capture taken against a server that cannot be
    # verified is a capture nobody can defend (D-11).
    _restarted=0
    for _try in 1 2 3; do
        if bash scripts/simulator/carla_restart.sh > "$LOGD/restart_${SEC}_${COND}.log" 2>&1; then
            [ "$_try" -gt 1 ] && echo "  restart succeeded on attempt $_try ($SEC/$COND)"
            _restarted=1; break
        fi
        echo "  restart attempt $_try/3 FAILED ($SEC/$COND): $(tail -1 "$LOGD/restart_${SEC}_${COND}.log" | tr -s ' ' | cut -c1-70)"
        sleep 20
    done
    [ "$_restarted" = 1 ] || { echo "  restart FAILED three times $SEC/$COND"; exit 1; }
    OY_OFFSETS=0.0 OY_YAWS=0.0 OY_CONDS="$COND" OY_OUT="$OUT" \
      python3 scripts/capture/capture_offset_yaw.py \
        --direction "$SEC" --poses "$POSES" --start-m 0 --length-m "$LEN" \
        >>"$LOGD/capture_${SEC}_${COND}.log" 2>&1 \
      && echo "  OK $OUT" || { echo "  FAIL $SEC/$COND (see $LOGD/capture_${SEC}_${COND}.log)"; exit 1; }
  done
done
echo "[$(date '+%F %T')] captures complete"
echo "NEXT: STUDY_MAP=Town06 python3 scripts/verify/certify_town06.py, then COMMIT the"
echo "certificate, and only then run the scored closed-loop ledger."

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
#   bash scripts/capture_town06_laps.sh
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06
export CARLA_PORT=${CARLA_PORT:-3000}
export PYTHONUNBUFFERED=1

python3 scripts/check_protocol_lock.py >/dev/null || { echo "PROTOCOL lock mismatch"; exit 1; }

OUTDIR=$REPO/results/town06/captures
LOGD=$REPO/results/town06_logs
mkdir -p "$OUTDIR" "$LOGD"

# The sampling RULE is frozen (every 8th control-rate pose, PROTOCOL section 3); the
# pose count follows from each section's length rather than being fixed at Town04's 200.
SECTIONS=$(STUDY_MAP=Town06 python3 -c "import sys;sys.path.insert(0,'pipeline');import config as C;print(' '.join(C.SECTIONS))")
echo "sections: $SECTIONS"

for SEC in $SECTIONS; do
  # THE SCORED LENGTH. SECTION_LEN_M is the route's GEOMETRY, and on the lap the two
  # differ by the 170 m of bridged intersection that no closed-loop cell scores.
  LEN=$(STUDY_MAP=Town06 python3 -c "import sys;sys.path.insert(0,'pipeline');import config as C;print(f\"{C.scored_len_m('$SEC'):.1f}\")")
  POSES=$(STUDY_MAP=Town06 python3 -c "import sys;sys.path.insert(0,'pipeline');import config as C;print(C.steps_for('$SEC'))")
  for COND in clear fog night low_sun; do
    OUT="results/town06/captures/lap_${SEC}_${COND}.npz"
    if [ -f "$REPO/$OUT" ]; then echo "SKIP  $OUT"; continue; fi
    echo "[$(date '+%F %T')] capture $SEC/$COND  (${LEN} m, ${POSES} poses)"
    # R-SIM-1: restart before EVERY measurement. This driver took all captures in one
    # server session, which is exactly the exposure the rule exists to remove -- a server
    # degrades silently and nothing in a capture reveals which server produced it. The
    # Town04 driver restarts per capture; this one did not, and the drift went unnoticed
    # because the rule lived in prose rather than in a check.
    bash scripts/carla_restart.sh > "$LOGD/restart_${SEC}_${COND}.log" 2>&1 \
      || { echo "  restart FAILED $SEC/$COND"; exit 1; }
    OY_OFFSETS=0.0 OY_YAWS=0.0 OY_CONDS="$COND" OY_OUT="$OUT" \
      python3 scripts/capture_offset_yaw.py \
        --direction "$SEC" --poses "$POSES" --start-m 0 --length-m "$LEN" \
        >>"$LOGD/capture_${SEC}_${COND}.log" 2>&1 \
      && echo "  OK $OUT" || { echo "  FAIL $SEC/$COND (see $LOGD/capture_${SEC}_${COND}.log)"; exit 1; }
  done
done
echo "[$(date '+%F %T')] captures complete"
echo "NEXT: STUDY_MAP=Town06 python3 scripts/certify_town06.py, then COMMIT the"
echo "certificate, and only then run the scored closed-loop ledger."

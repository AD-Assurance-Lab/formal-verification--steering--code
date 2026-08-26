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

# 200 scored poses x stride 8 = 1600 captured poses over the scored lap.
POSES=1600
LAP=$(STUDY_MAP=Town06 python3 -c "import sys;sys.path.insert(0,'pipeline');import config as C;print(f'{C.LAP_END_M:.1f}')")
echo "scored lap = ${LAP} m, ${POSES} poses (stride 8 -> 200)"

for DIR in eastbound westbound; do
  for COND in clear fog night shadows; do
    OUT="results/town06/captures/lap_${DIR}_${COND}.npz"
    if [ -f "$REPO/$OUT" ]; then echo "SKIP  $OUT"; continue; fi
    echo "[$(date '+%F %T')] capture $DIR/$COND"
    OY_OFFSETS=0.0 OY_YAWS=0.0 OY_CONDS="$COND" OY_OUT="$OUT" \
      python3 scripts/capture_offset_yaw.py \
        --direction "$DIR" --poses "$POSES" --start-m 0 --length-m "$LAP" \
        >>"$LOGD/capture_${DIR}_${COND}.log" 2>&1 \
      && echo "  OK $OUT" || { echo "  FAIL $DIR/$COND (see $LOGD/capture_${DIR}_${COND}.log)"; exit 1; }
  done
done
echo "[$(date '+%F %T')] captures complete"
echo "NEXT: STUDY_MAP=Town06 python3 scripts/certify_town06.py, then COMMIT the"
echo "certificate, and only then run the scored closed-loop ledger."

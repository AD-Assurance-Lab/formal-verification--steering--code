#!/usr/bin/env bash
# Full-lap verification captures for Town04, at the students' 84x28 resolution.
#
# This exists because the redo's captures were made by a hand-rolled invocation that
# inherited capture_offset_yaw's 160 m --length-m default and covered 5.6% of the lap.
# Town06 had a committed capture script and was unaffected; Town04 did not. It does now.
#
# Centreline slice only (OY_OFFSETS=0 OY_YAWS=0): the for-all-disturbance coverage claim
# is per-frame, so the offset x yaw grid costs a great deal and buys nothing here.
# --length-m is deliberately NOT passed, so the whole route is covered.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
# THIS IS THE REDO'S DRIVER: it writes to results/town04_v2/, so it must run under the
# REDO's config. It set only STUDY_MAP, so it captured with the PUBLISHED constants while
# writing into the redo's directory. That was invisible for as long as the two agreed --
# and the moment LAP_END_M diverged (2,861 published, 2,988 redo) it silently captured
# 127 m of the wrong road into the redo's artifacts.
export STUDY_MAP=Town04 TOWN04_REDO=1
export CARLA_PORT=${CARLA_PORT:-3000}
export PYTHONUNBUFFERED=1
export OY_OFFSETS=0.0 OY_YAWS=0.0
OUTDIR=${OY_DIR:-$REPO/results/town04_v2/calibration}
LOGD=$REPO/results/town04_v2/logs/capture
mkdir -p "$OUTDIR" "$LOGD"
POSES=${POSES:-1600}          # matches the published captures' pose count

python3 scripts/check_protocol_lock.py >/dev/null || { echo "PROTOCOL lock mismatch"; exit 1; }

for d in eastbound westbound; do
  for c in clear fog night shadows; do
    f="$OUTDIR/lap_${d}_${c}.npz"
    if [ -f "$f" ]; then echo "  SKIP $d/$c (exists)"; continue; fi
    bash scripts/carla_restart.sh > "$LOGD/restart.log" 2>&1 || { echo "  restart FAILED $d/$c"; exit 1; }
    OY_OUT="$f" OY_CONDS="$c" timeout 10800 python3 scripts/capture_offset_yaw.py \
        --direction "$d" --poses "$POSES" > "$LOGD/${d}_${c}.log" 2>&1
    rc=$?
    echo "  $d/$c rc=$rc  $(grep -E 'route coverage' "$LOGD/${d}_${c}.log" | tail -1)"
    [ $rc -eq 0 ] || exit 1
  done
done
echo "CAPTURE TOWN04 DONE"

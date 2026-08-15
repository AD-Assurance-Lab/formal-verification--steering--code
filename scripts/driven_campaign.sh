#!/usr/bin/env bash
# Driven-offset captures, eastbound. Two groups:
#   sun cells      -- the localised mode P-09 could not predict
#   canonical      -- the false-alarm test the static grid failed 2/6
# 6 phases each: 6 (offset, heading, steering) samples per pose, enough for a plane fit.
PY=/home/za/ad-assurance--workspace/sdp-crown--automated-driving--code/venv_sdp/bin/python
D=/home/za/.claude/jobs/00970870/tmp
R=/home/za/ad-assurance--workspace/formal-verification--automated-driving--code
cd $R
run () {  # name, condition, sun-altitude-or-empty
  local NAME=$1 COND=$2 SUN=$3
  local OUT=results/calibration/driven_${NAME}_eastbound.npz
  [ -f "$OUT" ] && { echo "[$(date +%H:%M)] skip $NAME"; return; }
  echo "[$(date +%H:%M)] driven capture $NAME (cond=$COND sun=${SUN:-default})"
  if [ -n "$SUN" ]; then
    CARLA_PORT=3000 SUN_ALTITUDE_OVERRIDE=$SUN $PY -u scripts/capture_driven_offsets.py \
      --direction eastbound --condition $COND --phases 6 --out $OUT >> $D/driven_cap.log 2>&1
  else
    CARLA_PORT=3000 $PY -u scripts/capture_driven_offsets.py \
      --direction eastbound --condition $COND --phases 6 --out $OUT >> $D/driven_cap.log 2>&1
  fi
  echo "[$(date +%H:%M)] done $NAME rc=$?"
}
# baseline first -- every rollout is relative to it
run clear   clear   ""
# sun cells: driven outcomes known (+60 PASS, +30 FAIL, +37 FAIL 3/10, +15 PASS)
run sun60   clear   60
run sun30   clear   30
run sun37   clear   37
run sun15   clear   15
# canonical: the cells the static rollout false-alarmed on
run fog     fog     ""
run night   night   ""
run shadows shadows ""
echo "[$(date +%H:%M)] DRIVEN CAMPAIGN COMPLETE"

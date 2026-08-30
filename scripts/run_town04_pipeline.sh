#!/usr/bin/env bash
# Town04 REDO -- the published study rebuilt under the corrected simulator harness.
#
# A DISCOVERY test, as the published one was: T_CLOSED_LOOP_S was back-solved from
# Town04's own closed-loop cliff, so its agreement measures sensitivity rather than
# prediction. Re-running does not make it a deployment test. Town06 is that.
#
# The recipe is the PUBLISHED one, recovered from the artifact rather than guessed:
#   base `conditions`  27,109 frames, 4 weathers x 2 directions x 2 laps, balanced
#   teachers           BC -> teacher DAgger, clear on clear only, mixed on all four
#   students           clear (8,16,16)/fc32 = 5,152 ReLU; mixed (24,48,48)/fc96 = 15,456
#                      -- the paper's own numbers; the mixed student TRIPLES the width
#   student DAgger     part of Town04's procedure (unlike Town06, where T06-F14 removed it)
#
# Everything is written under _v2 names and results/town04_v2 (TOWN04_REDO=1), because the
# published artifacts are tracked in git under exactly the unsuffixed names and comparing
# old against new IS the result.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town04
export TOWN04_REDO=1
export CARLA_PORT=${CARLA_PORT:-3000}
export PYTHONUNBUFFERED=1

LOG_DIR=$REPO/results/town04_v2/logs; mkdir -p "$LOG_DIR"
CK_DIR=$REPO/pipeline/checkpoints
DATA=$REPO/pipeline/data
say(){ echo "[$(date '+%F %T')] $*" | tee -a "$LOG_DIR/pipeline.log"; }

python3 -m carla_determinism --lock-only >/dev/null || {
    say "FATAL: carla-determinism rules lock mismatch"; exit 1; }
say "determinism rules lock OK; STUDY_MAP=$STUDY_MAP TOWN04_REDO=1 port $CARLA_PORT"

carla_up(){ for i in $(seq 1 "${1:-60}"); do
    ss -ltn 2>/dev/null | grep -q ":$CARLA_PORT" && return 0; sleep 5; done; return 1; }
carla_restart(){ say "restarting CARLA"
    pkill -f "[C]arlaUE4-Linux-Shipping.*rpc-port=$CARLA_PORT" 2>/dev/null; sleep 8
    bash "$REPO/scripts/carla_launch.sh" >>"$LOG_DIR/carla_launch.log" 2>&1 \
        && { say "CARLA back"; sleep 5; return 0; }
    say "FATAL: CARLA did not return"; return 1; }
carla_up 12 || carla_restart || exit 1
python3 -m carla_determinism --port "$CARLA_PORT" >>"$LOG_DIR/pipeline.log" 2>&1 || {
    say "FATAL: the server violates the determinism rules; relaunch via scripts/carla_launch.sh"
    exit 1; }
say "determinism preflight OK on the live server"
rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null

run(){ local name=$1; shift
  for attempt in 1 2; do
    say "START $name (attempt $attempt)"; : > "$LOG_DIR/$name.log"
    if "$@" >>"$LOG_DIR/$name.log" 2>&1; then say "OK    $name"; return 0; fi
    say "FAIL  $name attempt $attempt (see $LOG_DIR/$name.log)"
    carla_up 3 || carla_restart || return 1
    rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null; sleep 5
  done
  say "FAIL  $name after 2 attempts -- stopping"; return 1; }

# dagger.py EXITS 0 even when the teacher never meets budget (it prints "without passing").
# A teacher that cannot drive invalidates everything downstream, so it is a hard stop.
teacher_gate(){ local log="$LOG_DIR/$1.log"
  if grep -q "without passing" "$log" 2>/dev/null; then
    say "FATAL: $1 exhausted its rounds WITHOUT meeting budget. Refusing to distil."; return 1; fi
  say "GATE  $1: teacher met budget"; return 0; }

cd "$REPO/pipeline"

# ------------------------------------------------------------------ base data
if [ ! -f "$DATA/conditions_v2/manifest.csv" ]; then
  run collect python3 collect_data.py --dataset conditions_v2 \
      --weathers clear,fog,night,shadows --laps 2 --direction both || exit 1
else say "SKIP  collect (manifest exists)"; fi

# ------------------------------------------------------------------ teachers
if [ ! -f "$CK_DIR/teacher_clear_v2_bc.pth" ]; then
  run train_clear_bc python3 train.py --dataset conditions_v2 --weathers clear \
      --epochs 120 --out teacher_clear_v2_bc || exit 1
else say "SKIP  train_clear_bc"; fi

if ! ls "$CK_DIR"/teacher_clear_v2_dagger_r*.pth >/dev/null 2>&1; then
  run dagger_clear python3 dagger.py --base conditions_v2 --init teacher_clear_v2_bc \
      --rounds 12 --weathers clear --dagger-dir dagger_clear_v2 \
      --out-prefix teacher_clear_v2_dagger || exit 1
  teacher_gate dagger_clear || exit 1
else say "SKIP  dagger_clear"; teacher_gate dagger_clear || exit 1; fi

if [ ! -f "$CK_DIR/teacher_mixed_v2_bc.pth" ]; then
  run train_mixed_bc python3 train.py --dataset conditions_v2 \
      --weathers clear,fog,night,shadows --epochs 120 --out teacher_mixed_v2_bc || exit 1
else say "SKIP  train_mixed_bc"; fi

if ! ls "$CK_DIR"/teacher_mixed_v2_dagger_r*.pth >/dev/null 2>&1; then
  run dagger_mixed python3 dagger.py --base conditions_v2 --init teacher_mixed_v2_bc \
      --rounds 16 --weathers clear,fog,night,shadows --dagger-dir dagger_mixed_v2 \
      --out-prefix teacher_mixed_v2_dagger || exit 1
  teacher_gate dagger_mixed || exit 1
else say "SKIP  dagger_mixed"; teacher_gate dagger_mixed || exit 1; fi

latest(){ ls -1 "$CK_DIR"/$1*.pth 2>/dev/null | sort | tail -1 | xargs -r basename | sed 's/\.pth$//'; }
TC=$(latest teacher_clear_v2_dagger_r); TM=$(latest teacher_mixed_v2_dagger_r)
say "teachers: clear=$TC mixed=$TM"
[ -n "$TC" ] && [ -n "$TM" ] || { say "FATAL: a DAgger teacher is missing"; exit 1; }

# ------------------------------------------------------------------ distillation
# The paper's architectures: clear 5,152 ReLU, mixed 15,456 -- the mixed student TRIPLES
# the width. They are NOT matched; an early methodology draft required that and it was
# discarded, because w1 failed all four conditions and w3 passed everything (4b2ad73).
if [ ! -f "$CK_DIR/S_clear_84x28_v2.pth" ]; then
  run distill_clear python3 distill.py --in-w 84 --in-h 28 --out S_clear_84x28_v2 \
      --teacher "$TC" --base conditions_v2 --dagger-dirs dagger_clear_v2 \
      --weathers clear --channels 8,16,16 --fc 32 || exit 1
else say "SKIP  distill_clear"; fi

if [ ! -f "$CK_DIR/S_mixed_84x28_w3_v2.pth" ]; then
  run distill_mixed python3 distill.py --in-w 84 --in-h 28 --out S_mixed_84x28_w3_v2 \
      --teacher "$TM" --base conditions_v2 --dagger-dirs dagger_mixed_v2 \
      --channels 24,48,48 --fc 96 || exit 1
else say "SKIP  distill_mixed"; fi

# ------------------------------------------------------------------ student DAgger
# Town04's procedure INCLUDES this (README "Reproduce"; the archived dagger_student_clear
# and dagger_student_w3 round directories). Town06 removed it (T06-F14) and did not need
# it; Town04 is being reproduced as published, so it runs.
if ! ls "$CK_DIR"/S_clear_84x28_v2_dagger_r*.pth >/dev/null 2>&1; then
  run dagger_student_clear python3 dagger_student.py --student S_clear_84x28_v2 \
      --w 84 --h 28 --rounds 3 --weathers clear --teacher "$TC" \
      --base conditions_v2 --dagger-dir dagger_student_clear_v2 \
      --channels 8,16,16 --fc 32 || exit 1
else say "SKIP  dagger_student_clear"; fi

if ! ls "$CK_DIR"/S_mixed_84x28_w3_v2_dagger_r*.pth >/dev/null 2>&1; then
  run dagger_student_mixed python3 dagger_student.py --student S_mixed_84x28_w3_v2 \
      --w 84 --h 28 --rounds 3 --weathers clear,fog,night,shadows --teacher "$TM" \
      --base conditions_v2 --dagger-dir dagger_student_mixed_v2 \
      --channels 24,48,48 --fc 96 || exit 1
else say "SKIP  dagger_student_mixed"; fi

say "TOWN04 REDO BUILD COMPLETE"
say "NEXT: capture -> certify -> drive the ledger into results/town04_v2/ledger,"
say "      then compare against the published cells in results/ledger."

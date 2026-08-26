#!/usr/bin/env bash
# Town06 deployment test -- the whole model-building pipeline, unattended.
#
# Order matters and is fixed by PROTOCOL.md:
#   expert -> BC data -> teacher -> DAgger teacher -> distil student -> DAgger student
# for BOTH the clear-only and mixed policies. Certification happens AFTER this, and
# the certificate is committed BEFORE any scored closed-loop run (PROTOCOL R1).
#
# This script deliberately does NOT run any scored ledger cell. Training telemetry is
# not a scored result (PROTOCOL section 5), but the boundary is only safe if the two
# never live in the same script.
#
# Each stage is skipped if its output already exists, so the pipeline is resumable
# after an interrupt, an OOM, or a CARLA restart.
#
#   bash scripts/run_town06_pipeline.sh            # run it
#   STAGES=teacher_clear bash scripts/...          # run one stage
set -uo pipefail

cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06
export CARLA_PORT=${CARLA_PORT:-3000}
export PYTHONUNBUFFERED=1

LOG_DIR=$REPO/results/town06_logs
mkdir -p "$LOG_DIR"
CK=$REPO/pipeline/checkpoints
DATA=$REPO/pipeline/data

say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG_DIR/pipeline.log"; }

# PROTOCOL gate: refuse to build anything if the frozen constants have moved.
python3 scripts/check_protocol_lock.py >/dev/null || {
    say "FATAL: PROTOCOL lock mismatch -- refusing to run"; exit 1; }
say "PROTOCOL lock OK; STUDY_MAP=$STUDY_MAP CARLA_PORT=$CARLA_PORT"

carla_up() {
    for i in $(seq 1 60); do
        ss -ltn 2>/dev/null | grep -q ":$CARLA_PORT" && return 0
        sleep 5
    done
    return 1
}
carla_up || { say "FATAL: no CARLA on port $CARLA_PORT"; exit 1; }

run() {   # run <logname> <cmd...>
    local name=$1; shift
    say "START $name"
    if "$@" >>"$LOG_DIR/$name.log" 2>&1; then
        say "OK    $name"
        return 0
    fi
    say "FAIL  $name (see $LOG_DIR/$name.log)"
    return 1
}

cd "$REPO/pipeline"

# ---------------------------------------------------------------- clear policy
if [ ! -f "$DATA/clear_t06/manifest.csv" ]; then
    run collect_clear python3 collect_data.py --dataset clear_t06 \
        --weathers clear --laps 2 --direction both || exit 1
else say "SKIP  collect_clear (manifest exists)"; fi

if [ ! -f "$CK/teacher_clear_t06_bc.pth" ]; then
    run train_clear_bc python3 train.py --dataset clear_t06 --epochs 120 \
        --out teacher_clear_t06_bc || exit 1
else say "SKIP  train_clear_bc"; fi

if ! ls "$CK"/teacher_clear_t06_dagger_r*.pth >/dev/null 2>&1; then
    run dagger_clear python3 dagger.py --base clear_t06 \
        --init teacher_clear_t06_bc --rounds 6 --weathers clear \
        --dagger-dir dagger_clear_t06 --out-prefix teacher_clear_t06_dagger || exit 1
else say "SKIP  dagger_clear"; fi

# ---------------------------------------------------------------- mixed policy
if [ ! -f "$DATA/mixed_t06/manifest.csv" ]; then
    run collect_mixed python3 collect_data.py --dataset mixed_t06 \
        --weathers clear,fog,night,shadows --laps 2 --direction both || exit 1
else say "SKIP  collect_mixed"; fi

if [ ! -f "$CK/teacher_mixed_t06_bc.pth" ]; then
    run train_mixed_bc python3 train.py --dataset mixed_t06 --epochs 120 \
        --out teacher_mixed_t06_bc || exit 1
else say "SKIP  train_mixed_bc"; fi

if ! ls "$CK"/teacher_mixed_t06_dagger_r*.pth >/dev/null 2>&1; then
    run dagger_mixed python3 dagger.py --base mixed_t06 \
        --init teacher_mixed_t06_bc --rounds 8 --weathers clear,fog,night,shadows \
        --dagger-dir dagger_mixed_t06 --out-prefix teacher_mixed_t06_dagger || exit 1
else say "SKIP  dagger_mixed"; fi

# ---------------------------------------------------------------- distillation
latest() { ls -1 "$CK"/$1*.pth 2>/dev/null | sort | tail -1 | xargs -r basename | sed 's/\.pth$//'; }

TC=$(latest teacher_clear_t06_dagger_r)
TM=$(latest teacher_mixed_t06_dagger_r)
say "teachers: clear=$TC mixed=$TM"
[ -n "$TC" ] && [ -n "$TM" ] || { say "FATAL: a DAgger teacher is missing"; exit 1; }

if [ ! -f "$CK/S_clear_t06_84x28.pth" ]; then
    run distill_clear python3 distill.py --in-w 84 --in-h 28 \
        --out S_clear_t06_84x28 --teacher "$TC" --base clear_t06 \
        --dagger-dirs dagger_clear_t06 --channels 8,16,16 --fc 32 || exit 1
else say "SKIP  distill_clear"; fi

if [ ! -f "$CK/S_mixed_t06_84x28_w3.pth" ]; then
    run distill_mixed python3 distill.py --in-w 84 --in-h 28 \
        --out S_mixed_t06_84x28_w3 --teacher "$TM" --base mixed_t06 \
        --dagger-dirs dagger_mixed_t06 --channels 24,48,48 --fc 96 || exit 1
else say "SKIP  distill_mixed"; fi

# ---------------------------------------------------------- student DAgger
if ! ls "$DATA"/dagger_student_clear_t06/manifest.csv >/dev/null 2>&1; then
    run dagger_student_clear python3 dagger_student.py \
        --student S_clear_t06_84x28 --w 84 --h 28 --rounds 3 --weathers clear \
        --dagger-dir dagger_student_clear_t06 --teacher "$TC" --base clear_t06 || exit 1
else say "SKIP  dagger_student_clear"; fi

if ! ls "$DATA"/dagger_student_mixed_t06/manifest.csv >/dev/null 2>&1; then
    run dagger_student_mixed python3 dagger_student.py \
        --student S_mixed_t06_84x28_w3 --w 84 --h 28 --rounds 3 \
        --weathers clear,fog,night,shadows \
        --dagger-dir dagger_student_mixed_t06 --teacher "$TM" --base mixed_t06 || exit 1
else say "SKIP  dagger_student_mixed"; fi

say "PIPELINE COMPLETE -- students built."
say "NEXT, in this order, and not before: certify (scripts/certify_sustained_bound.py),"
say "COMMIT the certificate, then and only then run the scored closed-loop ledger."

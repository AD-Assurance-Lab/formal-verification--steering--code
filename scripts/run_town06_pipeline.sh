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

CARLA_ROOT=${CARLA_ROOT:-$HOME/carla}
CARLA_LOG=$LOG_DIR/carla.log

carla_up() {
    for i in $(seq 1 "${1:-60}"); do
        ss -ltn 2>/dev/null | grep -q ":$CARLA_PORT" && return 0
        sleep 5
    done
    return 1
}

# CARLA dies. It leaks ~10.5 GiB over 11 h, and it aborts with "Pure virtual function
# called!" whenever a synchronous client disappears mid-tick -- which is exactly what a
# killed or crashed stage looks like from the server's side. Over a multi-hour
# unattended run that is a certainty, not a risk, so the driver restarts it rather than
# losing the campaign to it.
carla_restart() {
    say "restarting CARLA on port $CARLA_PORT"
    pkill -f "[C]arlaUE4-Linux-Shipping.*rpc-port=$CARLA_PORT" 2>/dev/null
    sleep 8
    ( cd "$CARLA_ROOT" && setsid nohup ./CarlaUE4.sh -carla-rpc-port="$CARLA_PORT" \
        -RenderOffScreen -quality-level=Epic >>"$CARLA_LOG" 2>&1 < /dev/null & )
    if carla_up 60; then say "CARLA back up"; sleep 10; return 0; fi
    say "FATAL: CARLA did not come back on port $CARLA_PORT"
    return 1
}

carla_up 12 || carla_restart || exit 1

# Stale lock from a killed stage would block every subsequent one.
rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null

run() {   # run <logname> <cmd...>  -- one retry after a CARLA restart
    local name=$1; shift
    local attempt
    for attempt in 1 2; do
        say "START $name (attempt $attempt)"
        if "$@" >>"$LOG_DIR/$name.log" 2>&1; then
            say "OK    $name"
            return 0
        fi
        say "FAIL  $name attempt $attempt (see $LOG_DIR/$name.log)"
        # A stage failure and a dead simulator are usually the same event.
        carla_up 3 || carla_restart || return 1
        rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null
        sleep 5
    done
    say "FAIL  $name after 2 attempts -- stopping"
    return 1
}

# ROUTE FINGERPRINT. Every stage below is skipped when its output exists, which is
# what makes the pipeline resumable -- and which silently reuses data collected on a
# DIFFERENT route if the route is ever re-selected. That is not hypothetical: the first
# Town06 route was invalidated after its teacher failed, and without this guard the
# rerun would have skipped collection and trained on the old route's frames while
# reporting success. A dataset is only reusable if it was built on the current route.
ROUTE_FP=$(python3 - <<'PY'
import hashlib, os, sys
sys.path.insert(0, "pipeline")
import config as C
h = hashlib.sha256()
d = os.path.join(C.DATASET_DIR, C.ROUTES_SUBDIR)
for n in ("eastbound", "westbound"):
    h.update(open(os.path.join(d, n + ".npy"), "rb").read())
print(h.hexdigest()[:16])
PY
)
say "route fingerprint $ROUTE_FP"

fp_ok() {   # fp_ok <dataset-dir> -- true if it was built on THIS route
    local f="$1/.route_fingerprint"
    [ -f "$f" ] && [ "$(cat "$f")" = "$ROUTE_FP" ]
}
fp_stamp() { echo "$ROUTE_FP" > "$1/.route_fingerprint"; }

fp_guard() {  # fp_guard <dataset-dir> <label> -- refuse a foreign-route dataset
    if [ -d "$1" ] && ! fp_ok "$1"; then
        say "FATAL: $2 exists but was built on a DIFFERENT route."
        say "       Reusing it would train on the wrong map. Remove it and rerun:"
        say "         rm -rf $1"
        return 1
    fi
    return 0
}

# dagger.py EXITS 0 EVEN WHEN THE TEACHER NEVER MEETS BUDGET. It prints
# "Exhausted N rounds without passing" and returns success, so the driver happily
# distilled an undrivable teacher and carried on. Measured on the first Town06 route:
# all 6 rounds FAIL, max|CTE| 24-101 ft against a 2.19 ft gate, and the pipeline
# treated it as OK. A teacher that cannot drive clear weather is a precondition
# failure, not a stage to continue past.
teacher_gate() {   # teacher_gate <logname>
    local log="$LOG_DIR/$1.log"
    if grep -q "without passing" "$log" 2>/dev/null; then
        say "FATAL: $1 exhausted its rounds WITHOUT the teacher meeting budget."
        say "       A teacher that cannot drive clear weather invalidates everything"
        say "       downstream. Refusing to distil. See $log"
        return 1
    fi
    say "GATE  $1: teacher met budget"
    return 0
}

cd "$REPO/pipeline"

# ---------------------------------------------------------------- clear policy
fp_guard "$DATA/clear_t06" clear_t06 || exit 1
if [ ! -f "$DATA/clear_t06/manifest.csv" ]; then
    run collect_clear python3 collect_data.py --dataset clear_t06 \
        --weathers clear --laps 4 --direction all || exit 1
    fp_stamp "$DATA/clear_t06"
else say "SKIP  collect_clear (manifest exists, fingerprint matches)"; fi

if [ ! -f "$CK/teacher_clear_t06_bc.pth" ]; then
    run train_clear_bc python3 train.py --dataset clear_t06 --epochs 120 \
        --out teacher_clear_t06_bc || exit 1
else say "SKIP  train_clear_bc"; fi

if ! ls "$CK"/teacher_clear_t06_dagger_r*.pth >/dev/null 2>&1; then
    run dagger_clear python3 dagger.py --base clear_t06 \
        --init teacher_clear_t06_bc --rounds 12 --weathers clear \
        --dagger-dir dagger_clear_t06 --out-prefix teacher_clear_t06_dagger || exit 1
    teacher_gate dagger_clear || exit 1
else say "SKIP  dagger_clear"; teacher_gate dagger_clear || exit 1; fi

# ---------------------------------------------------------------- mixed policy
fp_guard "$DATA/mixed_t06" mixed_t06 || exit 1
if [ ! -f "$DATA/mixed_t06/manifest.csv" ]; then
    run collect_mixed python3 collect_data.py --dataset mixed_t06 \
        --weathers clear,fog,night,shadows --laps 3 --direction all || exit 1
    fp_stamp "$DATA/mixed_t06"
else say "SKIP  collect_mixed (fingerprint matches)"; fi

if [ ! -f "$CK/teacher_mixed_t06_bc.pth" ]; then
    run train_mixed_bc python3 train.py --dataset mixed_t06 --epochs 120 \
        --out teacher_mixed_t06_bc || exit 1
else say "SKIP  train_mixed_bc"; fi

if ! ls "$CK"/teacher_mixed_t06_dagger_r*.pth >/dev/null 2>&1; then
    run dagger_mixed python3 dagger.py --base mixed_t06 \
        --init teacher_mixed_t06_bc --rounds 14 --weathers clear,fog,night,shadows \
        --dagger-dir dagger_mixed_t06 --out-prefix teacher_mixed_t06_dagger || exit 1
    teacher_gate dagger_mixed || exit 1
else say "SKIP  dagger_mixed"; teacher_gate dagger_mixed || exit 1; fi

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
    # --distill-dirs MUST be given. Its default is "dagger,dagger_student", which are
    # TOWN04 directory names: leaving it unset re-distils the Town06 student against
    # whatever Town04 data happens to be on disk, or silently against nothing. Either
    # way it contaminates the deployment test with the discovery test's data.
    run dagger_student_clear python3 dagger_student.py \
        --student S_clear_t06_84x28 --w 84 --h 28 --rounds 3 --weathers clear \
        --dagger-dir dagger_student_clear_t06 --teacher "$TC" --base clear_t06 \
        --channels 8,16,16 --fc 32 \
        --distill-dirs dagger_clear_t06,dagger_student_clear_t06 || exit 1
else say "SKIP  dagger_student_clear"; fi

if ! ls "$DATA"/dagger_student_mixed_t06/manifest.csv >/dev/null 2>&1; then
    run dagger_student_mixed python3 dagger_student.py \
        --student S_mixed_t06_84x28_w3 --w 84 --h 28 --rounds 3 \
        --weathers clear,fog,night,shadows \
        --dagger-dir dagger_student_mixed_t06 --teacher "$TM" --base mixed_t06 \
        --channels 24,48,48 --fc 96 \
        --distill-dirs dagger_mixed_t06,dagger_student_mixed_t06 || exit 1
else say "SKIP  dagger_student_mixed"; fi

say "PIPELINE COMPLETE -- students built."
say "NEXT, in this order, and not before: certify (scripts/certify_sustained_bound.py),"
say "COMMIT the certificate, then and only then run the scored closed-loop ledger."

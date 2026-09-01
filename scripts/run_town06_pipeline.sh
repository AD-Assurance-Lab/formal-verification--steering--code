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
CK_DIR=$REPO/pipeline/checkpoints
DATA=$REPO/pipeline/data

say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG_DIR/pipeline.log"; }

# PROTOCOL gate: refuse to build anything if the frozen constants have moved.
python3 scripts/check_protocol_lock.py >/dev/null || {
    say "FATAL: PROTOCOL lock mismatch -- refusing to run"; exit 1; }
say "PROTOCOL lock OK; STUDY_MAP=$STUDY_MAP CARLA_PORT=$CARLA_PORT"

# DETERMINISM gate, alongside the PROTOCOL gate and for the same reason: a campaign
# built on a non-compliant simulator is not slightly worse, it is unusable (D-11), and
# nothing in the resulting data reveals which server produced it.
python3 -m carla_determinism --lock-only >/dev/null || {
    say "FATAL: carla-determinism rules lock mismatch -- refusing to run"; exit 1; }
say "carla-determinism rules lock OK"

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
    # -notexturestreaming is REQUIRED (carla-determinism D-3) and this inline restart
    # is a second launcher, so it can drift from scripts/carla_restart.sh. It already
    # did: this line lacked the flag, which would have relaunched a non-compliant server
    # part-way through an unattended multi-hour campaign and silently made every stage
    # after the first restart noisier than the ones before it. Exactly the failure the
    # preflight exists to catch, arriving from inside our own driver.
    ( cd "$CARLA_ROOT" && setsid nohup ./CarlaUE4.sh -carla-rpc-port="$CARLA_PORT" \
        -RenderOffScreen -quality-level=Epic -notexturestreaming \
        >>"$CARLA_LOG" 2>&1 < /dev/null & )
    if carla_up 60; then say "CARLA back up"; sleep 10; return 0; fi
    say "FATAL: CARLA did not come back on port $CARLA_PORT"
    return 1
}

carla_up 12 || carla_restart || exit 1

# Now that a server exists, check HOW it was launched. carla_up only proves something is
# listening; D-3 and D-5 are launch flags and invisible over RPC, so a server someone
# started by hand answers perfectly and quietly poisons the whole campaign.
python3 -m carla_determinism --port "$CARLA_PORT" >>"$LOG_DIR/pipeline.log" 2>&1 || {
    say "FATAL: the server on $CARLA_PORT violates the determinism rules."
    say "       Relaunch it with: bash scripts/carla_restart.sh"
    say "       (see $LOG_DIR/pipeline.log for which rule)"; exit 1; }
say "determinism preflight OK on the live server"

# Stale lock from a killed stage would block every subsequent one.
rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null

run() {   # run <logname> <cmd...>  -- one retry after a CARLA restart
    local name=$1; shift
    local attempt
    for attempt in 1 2; do
        say "START $name (attempt $attempt)"
        # Truncate so the gate reads THIS attempt, not a previous one -- but keep the
        # previous attempt first. Truncating outright destroyed the evidence twice today:
        # a stage failed, the retry cleared the log, and the only record of why was gone
        # before it could be read. Diagnosis is not a luxury when a stage fails silently.
        if [ -s "$LOG_DIR/$name.log" ]; then
            cp "$LOG_DIR/$name.log" \
               "$LOG_DIR/$name.prev$(date '+%H%M%S').log" 2>/dev/null || true
        fi
        : > "$LOG_DIR/$name.log"
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
names = sorted(f for f in os.listdir(d) if f.endswith(".npy"))
if not names:
    raise SystemExit("no route .npy files in " + d)
for n in names:
    h.update(open(os.path.join(d, n), "rb").read())
print(h.hexdigest()[:16])
PY
)
# An EMPTY fingerprint is a broken guard, not a passing one. The first version hashed
# two hardcoded filenames and silently produced "" once the routes became s00..s05.
if [ -z "$ROUTE_FP" ]; then
    say "FATAL: route fingerprint is empty -- the guard is broken, refusing to run"
    exit 1
fi
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
    # FAIL CLOSED. This used to grep only for "without passing" and pass otherwise, so
    # any way of NOT printing that string counted as success -- and DAgger crashing is
    # one. It did exactly that: the port-release bug killed DAgger after two rounds, the
    # log never said "without passing", and the gate announced "teacher met budget" for a
    # teacher whose last round missed by 29.57 ft against a 2.19 ft budget.
    #
    # The gate that exists to stop a bad teacher propagating downstream must require
    # POSITIVE evidence, because the absence of a failure message is not a pass.
    local log="$LOG_DIR/$1.log"
    if [ ! -s "$log" ]; then
        say "FATAL: $1 has no log. Refusing to assume it passed."
        return 1
    fi
    if grep -q "without passing" "$log" 2>/dev/null; then
        say "FATAL: $1 exhausted its rounds WITHOUT the teacher meeting budget."
        say "       A teacher that cannot drive clear weather invalidates everything"
        say "       downstream. Refusing to distil. See $log"
        return 1
    fi
    if ! grep -q "\*\*\* PASSED at round" "$log" 2>/dev/null; then
        say "FATAL: $1 never printed a passing round."
        say "       Its last gate line was:"
        say "       $(grep -E 'gate .*ft\) ->' "$log" | tail -1)"
        say "       A gate that passes because nothing said 'fail' is not a gate."
        return 1
    fi
    say "GATE  $1: teacher met budget ($(grep '\*\*\* PASSED at round' "$log" | tail -1 | tr -s ' '))"
    return 0
}

# ── THE LAP REBUILD ──────────────────────────────────────────────────────────
# Every artifact name carries `t06lap`, not `t06`. Town06 was rebuilt as ONE continuous
# lap (2,289 m, 93% policy-driven, 2 PPC bridges) after the six discrete sections proved
# hard to justify -- they are pieces of road 70-500 m apart. The six-section datasets and
# checkpoints are a valid study on a DIFFERENT route, so they are kept, not overwritten:
# the route fingerprint guard below would refuse to reuse them anyway, which is exactly
# what it is for.

cd "$REPO/pipeline"

# ---------------------------------------------------------------- clear policy
fp_guard "$DATA/clear_t06lap" clear_t06lap || exit 1
if [ ! -f "$DATA/clear_t06lap/manifest.csv" ]; then
    run collect_clear python3 collect_data.py --dataset clear_t06lap \
        --weathers clear --laps 4 --direction all || exit 1
    fp_stamp "$DATA/clear_t06lap"
else say "SKIP  collect_clear (manifest exists, fingerprint matches)"; fi

if [ ! -f "$CK_DIR/teacher_clear_t06lap_bc.pth" ]; then
    run train_clear_bc python3 train.py --dataset clear_t06lap --epochs 120 \
        --out teacher_clear_t06lap_bc || exit 1
else say "SKIP  train_clear_bc"; fi

# RESUME AN UNFINISHED TEACHER, do not skip it.
#
# The guard used to be "checkpoints exist", which is true after a single round -- so a
# DAgger run that crashed at round 2 of 12 was treated as complete, and the stage was
# skipped forever after. Combined with a gate that failed open, that shipped a teacher
# missing its budget by 13x; combined with a gate that fails closed, it deadlocks: the
# stage is skipped, the gate refuses, and nothing can ever finish it.
#
# The real question is whether the teacher PASSED, and dagger.py says so in its log.
# DAgger resumes from its newest round by itself, so re-running an unfinished one is
# cheap and correct.
if ! grep -q "\*\*\* PASSED at round" "$LOG_DIR/dagger_clear.log" 2>/dev/null; then
    run dagger_clear python3 dagger.py --base clear_t06lap \
        --init teacher_clear_t06lap_bc --rounds 12 --min-rounds 8 --gate-reps 3 --weathers clear \
        --dagger-dir dagger_clear_t06lap --out-prefix teacher_clear_t06lap_dagger || exit 1
    teacher_gate dagger_clear || exit 1
else say "SKIP  dagger_clear"; teacher_gate dagger_clear || exit 1; fi

# ---------------------------------------------------------------- mixed policy
fp_guard "$DATA/mixed_t06lap" mixed_t06lap || exit 1
if [ ! -f "$DATA/mixed_t06lap/manifest.csv" ]; then
    run collect_mixed python3 collect_data.py --dataset mixed_t06lap \
        --weathers clear,fog,night,shadows --laps 3 --direction all || exit 1
    fp_stamp "$DATA/mixed_t06lap"
else say "SKIP  collect_mixed (fingerprint matches)"; fi

if [ ! -f "$CK_DIR/teacher_mixed_t06lap_bc.pth" ]; then
    run train_mixed_bc python3 train.py --dataset mixed_t06lap --epochs 120 \
        --out teacher_mixed_t06lap_bc || exit 1
else say "SKIP  train_mixed_bc"; fi

# RESUME AN UNFINISHED TEACHER, do not skip it.
#
# The guard used to be "checkpoints exist", which is true after a single round -- so a
# DAgger run that crashed at round 2 of 12 was treated as complete, and the stage was
# skipped forever after. Combined with a gate that failed open, that shipped a teacher
# missing its budget by 13x; combined with a gate that fails closed, it deadlocks: the
# stage is skipped, the gate refuses, and nothing can ever finish it.
#
# The real question is whether the teacher PASSED, and dagger.py says so in its log.
# DAgger resumes from its newest round by itself, so re-running an unfinished one is
# cheap and correct.
if ! grep -q "\*\*\* PASSED at round" "$LOG_DIR/dagger_mixed.log" 2>/dev/null; then
    run dagger_mixed python3 dagger.py --base mixed_t06lap \
        --init teacher_mixed_t06lap_bc --rounds 14 --min-rounds 8 --gate-reps 3 --weathers clear,fog,night,shadows \
        --dagger-dir dagger_mixed_t06lap --out-prefix teacher_mixed_t06lap_dagger || exit 1
    teacher_gate dagger_mixed || exit 1
else say "SKIP  dagger_mixed"; teacher_gate dagger_mixed || exit 1; fi

# ---------------------------------------------------------------- distillation
latest() { ls -1 "$CK_DIR"/$1*.pth 2>/dev/null | sort | tail -1 | xargs -r basename | sed 's/\.pth$//'; }

TC=$(latest teacher_clear_t06lap_dagger_r)
TM=$(latest teacher_mixed_t06lap_dagger_r)
say "teachers: clear=$TC mixed=$TM"
[ -n "$TC" ] && [ -n "$TM" ] || { say "FATAL: a DAgger teacher is missing"; exit 1; }

# Distil at the widths the registry declares. Town06 needs more than Town04's pair:
# w1/w3 there plateaued ON the budget here, so each student is sized to its own task
# (4ac6002), which is the rule this lab settled rather than identical architecture.
mapfile -t ROWS < <(STUDY_MAP=Town06 python3 -c "
import sys; sys.path.insert(0,'$REPO/pipeline'); import config as C
for nm, ck, ch, fc in C.TOWN06_STUDENTS:
    print(nm, ck, ','.join(str(c) for c in ch), fc,
          C.relu_count(ch, fc, C.TOWN06_INPUT_H, C.TOWN06_INPUT_W),
          C.TOWN06_INPUT_W, C.TOWN06_INPUT_H)")

for ROW in "${ROWS[@]}"; do
    read -r NM CK CH FC RELU IN_W IN_H <<<"$ROW"
    case "$NM" in
        S_clear_t06lap) TEACH=$TC; DSET=clear_t06lap; DDIR=dagger_clear_t06lap ;;
        *)           TEACH=$TM; DSET=mixed_t06lap; DDIR=dagger_mixed_t06lap ;;
    esac
    if [ ! -f "$CK_DIR/$CK.pth" ]; then
        say "distil $NM -> $CK (${IN_W}x${IN_H}, $RELU ReLU) from $TEACH"
        run "distill_$NM" python3 distill.py --in-w "$IN_W" --in-h "$IN_H" \
            --out "$CK" --teacher "$TEACH" --base "$DSET" \
            --dagger-dirs "$DDIR" --channels "$CH" --fc "$FC"|| exit 1
    else say "SKIP  distil $NM ($CK exists)"; fi
done

# ---------------------------------------------------------- NO student DAgger
# T06-F14 removed this stage. It ran student DAgger until the students drove, which was
# the right call at 84x28 -- the distilled student held 1 of 6 sections at 16.50 ft, so
# DAgger was rescuing an incompetent policy. At 168x28 distillation alone is already
# competent and DAgger only takes capability away. Measured, 3 reps, clear weather,
# architecture held fixed and only the procedure varied:
#
#     mixed w2  distilled only  6/6      after 4 DAgger rounds  3/6
#     clear w2  distilled only  4/6      after 3 DAgger rounds  4/6, and its worst
#                                        section went 1/3 at 3.45 ft to 0/3 at 11.97 ft
#
# No comparison showed it helping. If a student is not competent now, the lever is data
# or capacity, and the gate below says so rather than grinding rounds.

# Clear-weather competence, before anything is certified. The certificate bounds
# deviation FROM clear, so a student that is wrong in clear -- or that ignores its input
# -- certifies perfectly and drives off the road. Distillation is where that can arise.
run competence python3 "$REPO/scripts/check_student_competence.py" --require || {
    say "FATAL: a student is not competent in clear weather. Certifying it would bound"
    say "       deviation from an output that is already wrong. Fix capacity or"
    say "       distillation before proceeding."; exit 1; }

say "PIPELINE COMPLETE -- students built and competent in clear weather."
say "NEXT: bash scripts/finish_town06_deployment.sh"
say "  It captures at the students' resolution, stops CARLA, certifies blind, COMMITS"
say "  the certificate, and only then drives the scored ledger. That order is PROTOCOL"
say "  R1 and check_order_town06.py enforces it independently."

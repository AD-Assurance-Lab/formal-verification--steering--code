#!/usr/bin/env bash
# Keep running DAgger on a teacher until it meets budget on EVERY section and condition.
#
# An expert has no excuse for failing a condition it was trained on, so a teacher that
# exhausts its rounds is a reason to keep training, not to widen the gate. dagger.py
# resumes correctly: it discovers prior round directories, aggregates their data, and
# derives the starting policy from THIS run's completed rounds rather than from the
# original --init (which would silently discard every round of improvement).
#
# --rounds N means N MORE rounds on a resume, not N total.
#
#   bash scripts/retrain_until_pass.sh mixed   [max_attempts] [rounds_per_attempt]
#   bash scripts/retrain_until_pass.sh clear
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06
export CARLA_PORT=${CARLA_PORT:-3000}
export PYTHONUNBUFFERED=1

WHICH=${1:-mixed}
MAX_ATTEMPTS=${2:-8}
ROUNDS=${3:-10}
LOG_DIR=$REPO/results/town06_logs
mkdir -p "$LOG_DIR"
LOG=$LOG_DIR/retrain_${WHICH}.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

case "$WHICH" in
  clear) BASE=clear_t06; INIT=teacher_clear_t06_bc; DDIR=dagger_clear_t06
         PREFIX=teacher_clear_t06_dagger; WEATHERS=clear ;;
  mixed) BASE=mixed_t06; INIT=teacher_mixed_t06_bc; DDIR=dagger_mixed_t06
         PREFIX=teacher_mixed_t06_dagger; WEATHERS=clear,fog,night,shadows ;;
  *) echo "usage: $0 {clear|mixed} [max_attempts] [rounds_per_attempt]"; exit 2 ;;
esac

CARLA_ROOT=${CARLA_ROOT:-$HOME/carla}
carla_up() { for i in $(seq 1 "${1:-60}"); do
    ss -ltn 2>/dev/null | grep -q ":$CARLA_PORT" && return 0; sleep 5; done; return 1; }
carla_restart() {
    say "restarting CARLA on $CARLA_PORT"
    pkill -f "[C]arlaUE4-Linux-Shipping.*rpc-port=$CARLA_PORT" 2>/dev/null; sleep 8
    # ONE launcher: the determinism flags are launch-time and invisible over RPC,
    # so a second copy of this command is a second chance to omit them.
    bash "$REPO/scripts/carla_launch.sh"
    carla_up 60 && { say "CARLA back"; sleep 10; return 0; }
    say "FATAL: CARLA did not return"; return 1; }

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
    carla_up 6 || carla_restart || exit 1
    rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null
    OUT=$LOG_DIR/retrain_${WHICH}_attempt${attempt}.log
    : > "$OUT"
    PRIOR=$(ls -d "$REPO/pipeline/data/$DDIR"/round* 2>/dev/null | wc -l)
    say "attempt $attempt/$MAX_ATTEMPTS: +$ROUNDS rounds (resuming after $PRIOR)"

    ( cd "$REPO/pipeline" && python3 dagger.py --base "$BASE" --init "$INIT" \
        --rounds "$ROUNDS" --weathers "$WEATHERS" --dagger-dir "$DDIR" \
        --out-prefix "$PREFIX" ) >>"$OUT" 2>&1
    rc=$?

    if grep -q "\*\*\* PASSED at round" "$OUT"; then
        say "PASSED: $(grep -o '\*\*\* PASSED at round.*' "$OUT" | tail -1)"
        say "teacher meets budget on every section and condition"
        # The pipeline's teacher_gate greps dagger_<which>.log. That file still holds the
        # FAILED run's "Exhausted N rounds without passing", and the stage will be SKIPPED
        # on the next pipeline run because the checkpoints now exist -- so the gate would
        # read stale evidence and FATAL on a teacher that just passed. Replace it with the
        # attempt that actually succeeded.
        cp "$OUT" "$LOG_DIR/dagger_${WHICH}.log"
        say "wrote the passing run to dagger_${WHICH}.log so the pipeline gate sees it"
        exit 0
    fi
    if [ $rc -ne 0 ]; then
        say "dagger.py exited $rc; restarting CARLA and retrying"
        carla_restart || exit 1
        continue
    fi
    # Progress report, so a plateau is visible rather than inferred from wall-clock.
    say "attempt $attempt did not pass. Best rounds this attempt:"
    awk '/DAgger round/{r=$4} /-> PASS/{p[r]++} /-> FAIL/{f[r]++}
         END{for (k in p) printf "    round %s: %d pass / %d fail\n", k, p[k], f[k]+0}' \
        "$OUT" | sort -t' ' -k4 -n | tail -3 | tee -a "$LOG"
done

say "STOPPING after $MAX_ATTEMPTS attempts without a passing teacher."
say "This is a plateau, not a budget to widen: rounds alone are not closing it."
say "Next levers, in order: more base data (collect_data --laps), then teacher capacity."
exit 1

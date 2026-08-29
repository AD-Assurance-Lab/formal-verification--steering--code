#!/usr/bin/env bash
# Overnight driver: wait for the model-building pipeline, then run the deployment test.
#
# The two are separate scripts on purpose (training must not live in the same script as
# scored measurement, PROTOCOL section 5), so this only sequences them -- it makes no
# decisions and skips no gate. Every precondition is still checked by the scripts it
# calls: the PROTOCOL lock, the determinism lock, the clear-weather competence record,
# R1 ordering via check_order_town06.py, and the ledger's refusal to run a cell whose
# certificate is missing, untracked or dirty.
#
# It STOPS rather than improvising if the pipeline fails. A teacher that never met budget
# or a student that is not competent in clear weather is a decision for a person, not
# something to work around at 3 a.m.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06
export CARLA_PORT=${CARLA_PORT:-3000}
LOG=$REPO/results/town06_logs/overnight.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

say "waiting for run_town06_pipeline.sh"
while pgrep -f "run_town06_pipeline.sh" >/dev/null; do sleep 30; done

REB=$REPO/results/town06_logs/rebuild.log
if ! grep -q "PIPELINE COMPLETE" "$REB" 2>/dev/null; then
    say "STOP: the pipeline did not complete. Last lines:"
    tail -15 "$REB" | tee -a "$LOG"
    say "Not proceeding to the deployment test. This needs a person."
    exit 1
fi
say "pipeline complete; students built and competent in clear weather"

# The working tree must be clean BEFORE the deployment test runs: it commits the
# certificate together with docs/TOWN06_FINDINGS.md, and anything else left uncommitted
# would be swept into the commit that is supposed to contain only the prediction.
if [ -n "$(git status --porcelain)" ]; then
    say "STOP: working tree is dirty; the certificate commit must contain only the"
    say "      prediction. Commit or stash first."
    git status --short | tee -a "$LOG"
    exit 1
fi

say "starting the deployment test: capture -> certify -> COMMIT -> drive"
bash scripts/finish_town06_deployment.sh >>"$REPO/results/town06_logs/finish_driver.log" 2>&1
rc=$?
say "finish_town06_deployment.sh exited $rc"
tail -25 "$REPO/results/town06_logs/finish.log" 2>/dev/null | tee -a "$LOG"
say "OVERNIGHT DRIVER DONE (rc=$rc)"
exit $rc

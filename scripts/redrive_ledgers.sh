#!/usr/bin/env bash
# Re-drive BOTH ledgers under independent runs: fresh server AND fresh vehicle per run.
#
# WHY. R-SIM-1 says restart before every measurement RUN. The ledger restarted before
# every CELL and spawned the vehicle once for all twelve runs in it, so the twelve
# repetitions were two chains of six, each inheriting the previous run's physics state on
# an ageing server. A failure RATE over dependent trials is not a rate, and the Wilson
# interval in standing rule 3 assumes independence -- so this is in every ledger number in
# both studies, not only the clear/S_clear_t06 cell where it happened to cross the budget.
#
# ORDERING. Town06 first: its certificate is already committed, so re-driving preserves
# PROTOCOL R1 (the verdict was recorded before these drives). Town04 is the discovery test
# and carries no such ordering.
#
# Waits for the Town04 certification to finish first -- it is GPU-bound and CARLA renders
# on the same GPU, and correctness beats overlap.
#
#   bash scripts/redrive_ledgers.sh
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export CARLA_PORT=${CARLA_PORT:-3000}
export CARLA_WINDOWED=${CARLA_WINDOWED:-1} DISPLAY=${DISPLAY:-:0}
export PYTHONUNBUFFERED=1
LOG=$REPO/results/town06_logs
mkdir -p "$LOG"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG/redrive.log"; }
die() { say "FATAL: $*"; exit 1; }

while pgrep -f "[c]ertify_sustained_bound" >/dev/null; do sleep 60; done
say "Town04 certification finished; GPU is free"

STAMP=$(date '+%Y%m%d_%H%M')

# ---- Town06 -------------------------------------------------------------------
mkdir -p "results/town06/_dependent_runs_$STAMP"
mv results/town06/ledger/*.json "results/town06/_dependent_runs_$STAMP/" 2>/dev/null
say "1/2 Town06 ledger, dependent-run cells -> _dependent_runs_$STAMP"
python3 scripts/check_order_town06.py >/dev/null \
    || die "PROTOCOL R1: the Town06 certificate is not committed. Refusing to drive."
bash scripts/run_town06_ledger.sh >"$LOG/ledger_independent_t06.log" 2>&1 \
    || die "Town06 ledger failed, see $LOG/ledger_independent_t06.log"
python3 scripts/compare_town06.py >"$LOG/compare_independent.log" 2>&1 || true
say "    Town06 agreement:"
grep -E "agreement on scored|DISAGREE|CONTRADICTS" "$LOG/compare_independent.log" \
    | head -12 | tee -a "$LOG/redrive.log"

# ---- Town04 -------------------------------------------------------------------
mkdir -p "results/town04_v2/_dependent_runs_$STAMP"
mv results/town04_v2/ledger/*.json "results/town04_v2/_dependent_runs_$STAMP/" 2>/dev/null
say "2/2 Town04 ledger, dependent-run cells -> _dependent_runs_$STAMP"
bash scripts/run_town04_ledger.sh >"$LOG/ledger_independent_t04.log" 2>&1 \
    || die "Town04 ledger failed, see $LOG/ledger_independent_t04.log"
say "REDRIVE COMPLETE -- both ledgers on independent runs"

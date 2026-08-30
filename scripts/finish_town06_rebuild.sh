#!/usr/bin/env bash
# Rebuild the Town06 deployment test end to end, in the order the protocol requires.
#
# WHY A REBUILD. All 24 verification captures were taken in one server session with no
# restarts (R-SIM-1), so they are suspect by the lab's own standard: a server degrades
# silently and nothing in a capture says which server produced it. T06-F39 measured the
# cost -- 1-4% of tolerance in the mean, 1.39x tolerance in the worst frame.
#
# THE ORDER IS THE POINT, and it is what makes this a deployment test rather than a
# discovery test:
#
#   captures -> gate -> certificate -> COMMIT -> drives -> agreement
#
# The gate must pass BEFORE certification (the paper states it as a precondition and it
# has, until now, never been run before one). The certificate must be committed BEFORE
# any scored drive (PROTOCOL R1) -- run_town06_ledger.sh refuses otherwise, and that
# refusal is the guard, not this comment.
#
#   bash scripts/finish_town06_rebuild.sh
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06
export CARLA_PORT=${CARLA_PORT:-3000}
export CARLA_WINDOWED=${CARLA_WINDOWED:-1} DISPLAY=${DISPLAY:-:0}
export PYTHONUNBUFFERED=1

LOG=$REPO/results/town06_logs
mkdir -p "$LOG"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG/rebuild.log"; }
die() { say "FATAL: $*"; exit 1; }

# ---- 1. captures must be complete and compliant -----------------------------
while pgrep -f "[c]apture_town06_laps" >/dev/null; do sleep 30; done
N=$(ls results/town06/captures/lap_*.npz 2>/dev/null | wc -l)
[ "$N" -eq 24 ] || die "expected 24 captures, found $N"
say "1/6 captures complete: $N files, restart before each"

# ---- 2. driven traces for the gate, one restart per drive -------------------
say "2/6 gate drives (2 students x 6 sections, restart before each)"
python3 scripts/capture_gate_drives.py >"$LOG/gate_drives_rebuild.log" 2>&1 \
    || die "gate drives failed, see $LOG/gate_drives_rebuild.log"

# ---- 3. THE GATE, before certification ---------------------------------------
say "3/6 capture gate"
python3 scripts/capture_driven_gate.py --captures results/town06/captures \
    --drives pipeline/results >"$LOG/capture_gate_rebuild.log" 2>&1 \
    || die "CAPTURE GATE FAILED -- the captures do not reproduce the vehicle. $(tail -3 "$LOG/capture_gate_rebuild.log")"
say "    $(grep -E '^  worst' "$LOG/capture_gate_rebuild.log")"

# ---- 4. certify, on captures that just passed the gate -----------------------
# The old certificate and ledger are the record this is compared against, so they are
# moved aside rather than overwritten.
STAMP=$(date '+%Y%m%d_%H%M')
mkdir -p "results/town06/_superseded_$STAMP"
[ -f results/town06/certificate_town06.json ] && \
    git mv results/town06/certificate_town06.json "results/town06/_superseded_$STAMP/" 2>/dev/null || \
    mv results/town06/certificate_town06.json "results/town06/_superseded_$STAMP/" 2>/dev/null
mkdir -p "results/town06/_superseded_$STAMP/ledger"
mv results/town06/ledger/*.json "results/town06/_superseded_$STAMP/ledger/" 2>/dev/null
say "4/6 superseded artifacts -> results/town06/_superseded_$STAMP"

python3 scripts/certify_town06.py >"$LOG/certify_rebuild.log" 2>&1 \
    || die "certification failed, see $LOG/certify_rebuild.log"
[ -f results/town06/certificate_town06.json ] || die "certifier wrote no certificate"
say "    certificate written"

# ---- 5. COMMIT the certificate. R1: the verdict is a prediction only if it is ----
#         recorded before the drive that tests it.
git add -A results/town06 pipeline/results >/dev/null 2>&1
git commit -q -m "Town06 rebuild: certificate on R-SIM-1-compliant captures, gated first

Captures retaken with a restart before each (they were taken in one server session;
T06-F39 measured the cost). The capture gate ran BEFORE certification for the first
time -- the paper states it as a precondition and it had only ever been run after.

Committed before any scored drive, so PROTOCOL R1 holds and the verdicts below are
predictions rather than descriptions. The superseded certificate and ledger are kept
alongside as the record this replaces.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01ShU3GkJPKyadKYYmn82com" \
    || die "could not commit the certificate; R1 cannot be satisfied"
git push -q 2>/dev/null || say "    (push deferred)"
say "5/6 certificate COMMITTED -- R1 satisfied, driving may begin"

# ---- 6. drive, then compare ---------------------------------------------------
say "6/6 ledger (8 cells, restart before each)"
bash scripts/run_town06_ledger.sh >"$LOG/ledger_rebuild.log" 2>&1 \
    || die "ledger failed, see $LOG/ledger_rebuild.log"
python3 scripts/compare_town06.py >"$LOG/compare_rebuild.log" 2>&1 || true
say "TOWN06 REBUILD COMPLETE"
tail -20 "$LOG/compare_rebuild.log" | tee -a "$LOG/rebuild.log"

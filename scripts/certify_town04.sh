#!/usr/bin/env bash
# The committed driver for the Town04 redo's certification.
#
# There was no such script for the redo, and that is the whole reason the 160 m capture
# defect reached a finding: the captures and the certification were both driven by hand,
# so a scope-narrowing default nobody typed became part of a result nobody could re-derive.
# Standing rule 8 -- if a number goes in a paper, the invocation is in the repo.
#
# Preconditions, in order, because a certificate computed out of order proves nothing:
#   1. captures cover the WHOLE route (certify_sustained_bound refuses below 80%)
#   2. the capture gate has run and passed (frames reproduce what the vehicle commanded)
#   3. only then the bound
#
# No CARLA. Everything here reads artifacts that already exist.
set -euo pipefail
cd "$(dirname "$0")/.."
export STUDY_MAP=Town04 TOWN04_REDO=1

CAL=results/town04_v2/calibration
LOG=results/town04_v2/logs
mkdir -p "$LOG"

echo "=== capture gate (precondition) ==="
python3 scripts/capture_driven_gate.py --captures "$CAL" --drives pipeline/results \
    2>&1 | tee "$LOG/capture_gate.log"

echo
echo "=== sustained-bias bound ==="
python3 scripts/certify_sustained_bound.py "$@" 2>&1 | tee "$LOG/certify_full_route.log"

echo
echo "CERTIFY TOWN04 DONE -> $CAL/sustained_bound.json"

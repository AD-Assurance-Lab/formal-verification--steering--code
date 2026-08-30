#!/usr/bin/env bash
# Redo the interpolation-fidelity measurements on both maps, then re-derive the findings.
#
# WHY. interpolation_fidelity.json recorded n_poses 81 -- the 160 m default -- and covered
# ONE section, at most 23% of Town06's 3,834 m of scored road. This is the worst place for
# that defect to have landed: the fidelity test is what validates the DISTURBANCE FAMILY,
# and every certified bound is quantified over that family, so a narrow measurement here
# narrows every downstream claim at once while the JSON still reads as complete.
#
# It is upstream of meaning, not a loose end: the paper's "interior s is an interpolation,
# which we measure rather than assume" rests on it, and T06-F32/F33 -- the interior-failure
# findings, the study's headline -- are interpreted through it.
#
# Captures cover every section, restart before each (R-SIM-1), nominal pose only.
# The analysis refuses a short capture and records sections, poses_per_section and
# route_span_m, so the result states its own scope.
#
#   bash scripts/finish_fidelity_rebuild.sh
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export CARLA_PORT=${CARLA_PORT:-3000}
export CARLA_WINDOWED=${CARLA_WINDOWED:-1} DISPLAY=${DISPLAY:-:0}
export PYTHONUNBUFFERED=1

LOG=$REPO/results/town06_logs
mkdir -p "$LOG"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG/fidelity_rebuild.log"; }
die() { say "FATAL: $*"; exit 1; }

# R-SIM-3: one client per port.
while pgrep -f "[f]inish_town06_rebuild|[f]inish_town04_rebuild" >/dev/null; do sleep 60; done
say "map rebuilds finished; starting fidelity"

# ---- Town06: all six sections -------------------------------------------------
say "1/4 Town06 fidelity captures (6 sections x 13 intensities)"
STUDY_MAP=Town06 bash scripts/capture_interp_fidelity.sh s00 s01 s02 s03 s04 s05 \
    >"$LOG/fid_capture_t06.log" 2>&1 || die "Town06 fidelity captures failed"

say "2/4 Town06 fidelity analysis (fog, lowsun, night -- pooled over all six sections)"
for AXIS in fog lowsun; do
    STUDY_MAP=Town06 python3 scripts/interpolation_fidelity.py --axis "$AXIS" \
        >"$LOG/fid_${AXIS}_t06.log" 2>&1 \
        || say "  WARN: $AXIS analysis exited nonzero, see $LOG/fid_${AXIS}_t06.log"
    say "  --- $AXIS ---"; grep -E "scope:|^ +[0-9]" "$LOG/fid_${AXIS}_t06.log" | head -12 \
        | tee -a "$LOG/fidelity_rebuild.log"
done
STUDY_MAP=Town06 python3 scripts/interp_fidelity_night.py \
    >"$LOG/fid_night_t06.log" 2>&1 || say "  WARN: night analysis exited nonzero"
say "  --- night ---"; grep -E "scope:|^ +[0-9-]" "$LOG/fid_night_t06.log" | head -12 \
    | tee -a "$LOG/fidelity_rebuild.log"

# ---- Town04: the night axis, which is what T04-R7 rests on --------------------
say "3/4 Town04 fidelity captures (2 directions x 13 intensities)"
STUDY_MAP=Town04 TOWN04_REDO=1 bash scripts/capture_interp_fidelity.sh eastbound westbound \
    >"$LOG/fid_capture_t04.log" 2>&1 || die "Town04 fidelity captures failed"

say "4/4 Town04 fidelity analysis"
STUDY_MAP=Town04 TOWN04_REDO=1 python3 scripts/interp_fidelity_night.py \
    >"$LOG/fid_night_t04.log" 2>&1 || say "  WARN: T04 night analysis exited nonzero"
say "  --- Town04 night ---"; grep -E "scope:|^ +[0-9-]" "$LOG/fid_night_t04.log" | head -12 \
    | tee -a "$LOG/fidelity_rebuild.log"

say "FIDELITY REBUILD COMPLETE -- T06-F34, T06-F37 and T04-R7 can now be re-derived"

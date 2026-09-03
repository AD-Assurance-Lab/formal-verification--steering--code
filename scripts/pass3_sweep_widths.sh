#!/usr/bin/env bash
# PASS 3 stages 1-2: sweep BOTH mixed widths under one margin gate, fixed in advance.
#
# docs/TOWN06_PASS3_PREREGISTRATION.md is the criterion and was committed before any draw.
# This script does not choose it, cannot change it, and reads it from config.
#
#   bash scripts/pass3_sweep_widths.sh
#
# WHAT IT DOES NOT DO. It does not stop when one width succeeds. Both widths are swept
# with the same seed list in the same order, because the question is which width holds the
# gate and a sweep that stopped early would answer a different one -- and would answer it
# in whichever order the widths happened to be listed.
#
# WHAT "NOBODY PASSES" MEANS. It is a pre-registered outcome, not a failure of the run:
# "fog is neither a capacity problem nor a seed problem at this input size and pool ...
# the mixed student is fog-limited, and the study says so rather than shipping another
# 19%-margin student." So this exits 0 with that recorded, and the caller must not treat
# an empty result as an error to be retried around.
#
# Model BUILDING, PROTOCOL section 5: no canonical cell is scored, nothing reaches a
# ledger, no certificate exists yet.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06
export CARLA_PORT=${CARLA_PORT:-3000}
export CARLA_WINDOWED=${CARLA_WINDOWED:-1}
export PYTHONUNBUFFERED=1

LOG=$REPO/results/town06_logs/pass3_sweep.log
mkdir -p "$(dirname "$LOG")"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

python3 scripts/check_protocol_lock.py >/dev/null || { say "FATAL: PROTOCOL lock"; exit 1; }

# The criterion, read from config so it cannot drift from the pre-registered document.
MARGIN=$(python3 -c "import sys;sys.path.insert(0,'pipeline');import config as C;print(C.TOWN06_PASS3_GATE_MARGIN)")
BUDGET=$(python3 -c "import sys;sys.path.insert(0,'pipeline');import config as C;print(f'{C.CTE_BUDGET_FT:.4f}')")
GATE=$(python3 -c "print(f'{$BUDGET * $MARGIN:.4f}')")
SEEDS="${SEEDS:-0 1 2 3 4 5 6 7}"

TEACHER=${TEACHER:-teacher_mixed_t06lap_dagger_r03}
DSET=${DSET:-mixed_t06lap}
DDIRS=${DDIRS:-dagger_mixed_t06lap,dagger_student_S_mixed_t06_t06lap}

say "=================================================================="
say "PASS 3 stages 1-2: both mixed widths, gate <= $GATE ft (${MARGIN}x of $BUDGET)"
say "  seeds: $SEEDS   teacher: $TEACHER"
say "  pools: $DSET + $DDIRS"
say "=================================================================="

mapfile -t ROWS < <(python3 -c "
import sys; sys.path.insert(0,'pipeline'); import config as C
for nm, sw, pin, ch, fc in C.TOWN06_PASS3_WIDTHS:
    print(nm, sw, pin, ','.join(str(c) for c in ch), fc)")

RESULTS=()
for ROW in "${ROWS[@]}"; do
    read -r NM SWEEP PIN CH FC <<<"$ROW"
    say ""
    say "---- $NM  (sweep base $SWEEP -> pin $PIN, channels $CH fc $FC) ----"
    if [ -f "$REPO/pipeline/checkpoints/${PIN}.selected" ]; then
        say "  already pinned: $(cat "$REPO/pipeline/checkpoints/${PIN}.selected") -- skipping"
        RESULTS+=("$NM PASS $(cat "$REPO/pipeline/checkpoints/${PIN}.selected")")
        continue
    fi
    # PROMOTE=0: never overwrite the base .pth. S_mixed_t06lap_168x56_w4.pth is the model
    # passes 1 and 2 were certified and driven with.
    CK="$SWEEP" CH="$CH" FC="$FC" TEACHER="$TEACHER" BASE="$DSET" \
    DAGGER_DIRS="$DDIRS" CONDS="clear fog night low_sun" REPS=3 \
    SEEDS="$SEEDS" MARGIN_FRAC="$MARGIN" SCREEN_FRAC=1.0 \
    PIN_CK="$PIN" PROMOTE=0 \
        bash scripts/select_student_seed.sh
    RC=$?
    if [ $RC -eq 0 ] && [ -f "$REPO/pipeline/checkpoints/${PIN}.selected" ]; then
        say "  $NM PASSES: $(cat "$REPO/pipeline/checkpoints/${PIN}.selected")"
        RESULTS+=("$NM PASS $(cat "$REPO/pipeline/checkpoints/${PIN}.selected")")
    else
        say "  $NM: NO SEED held every lap under $GATE ft"
        RESULTS+=("$NM NONE -")
    fi
done

say ""
say "=================== PASS 3 stages 1-2 result ====================="
NPASS=0
for R in "${RESULTS[@]}"; do
    say "  $R"
    [[ "$R" == *" PASS "* ]] && NPASS=$((NPASS+1))
done
say "  $NPASS of ${#ROWS[@]} width(s) met the pre-registered gate"
if [ "$NPASS" -eq 0 ]; then
    say ""
    say "  NEITHER WIDTH MET THE GATE. This is a pre-registered outcome, not a run"
    say "  failure: fog is neither a capacity problem nor a seed problem at this input"
    say "  size and pool. Do NOT relax the gate and re-run -- that is the one move the"
    say "  pre-registration forbids. Report it."
fi
say "=================================================================="
exit 0

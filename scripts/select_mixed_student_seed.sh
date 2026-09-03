#!/usr/bin/env bash
# Find a mixed student that holds ALL FOUR conditions over THREE laps, by re-drawing the
# distillation seed on a FIXED dataset.
#
#   bash scripts/select_mixed_student_seed.sh
#
# WHY A SEED SWEEP RATHER THAN MORE DAGGER ROUNDS.
#
# Successive from-scratch re-distillations of the SAME balanced pool oscillate between
# which condition they fail:
#
#     dagger_r02   clear 3/3  fog 3/3 (2.03 ft)  night 1/3 (3.24 ft)  low sun 3/3   10/12
#     dagger_r05   clear 3/3  fog 0/3 (9.63 ft)  night 3/3 (0.97 ft)  low sun 3/3    9/12
#
# The pool is not the problem: it is balanced to within 0.5% across conditions (clear
# 5,165 / fog 5,189 / night 5,167 / low sun 5,176) and is mostly nominal driving. Two
# models trained from scratch on nearly the same data land in different basins, which is
# TRAINING VARIANCE, and this study has measured it before -- T06-F14 recorded a seed
# flipping a student from 4/6 to 6/6 with architecture and data held fixed.
#
# config.DISTILL_SEED exists for exactly this and says so: "Seed is not a tuning knob here
# -- it is the variable T06-F14 measured as flipping a student ... Leaving it hardcoded
# makes that variance invisible: one draw is taken, and whether it was a good one is
# unknowable without re-drawing." This re-draws.
#
# WHAT THIS IS AND IS NOT. It is model BUILDING, on the same side of PROTOCOL section 5's
# leakage boundary as the teacher gate and the competence gate: no canonical cell is
# scored, nothing is written to the ledger, and no certificate exists yet. It is not
# verdict shopping -- the criterion is fixed at "every lap under budget", the sweep stops
# at the first seed that meets it rather than continuing to a best one, and the number that
# matters is produced later by a blind certificate and a scored ledger.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06 CARLA_PORT=${CARLA_PORT:-3000} CARLA_WINDOWED=${CARLA_WINDOWED:-0}
export PYTHONUNBUFFERED=1

# ONE SWEEP AT A TIME, via a PID lock rather than a process-name match. `pgrep -f
# select_mixed_student_seed.sh` also matches a git commit whose message names this file,
# a grep for it, or an editor with it open -- and it did: the overnight supervisor waited
# on its own commit command. A lock holding a PID cannot be confused with a mention.
LOCK=/tmp/town06_seed_sweep.lock
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
    echo "another seed sweep is alive (pid $(cat "$LOCK")); exiting"
    exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

LOG=$REPO/results/town06_logs/seed_sweep.log
mkdir -p "$(dirname "$LOG")"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

BASE_CK=S_mixed_t06lap_168x56_w4
CH=32,64,64; FC=128; IN_W=168; IN_H=56
TEACHER=teacher_mixed_t06lap_dagger_r03
DDIR=dagger_student_S_mixed_t06_t06lap
SEEDS="${SEEDS:-0 1 2 3 4 5 6 7 8 9}"

held_of() {   # held_of <json>  -> laps held
    python3 -c "
import json,sys
d=json.load(open('$1'))
laps=[l for l in list(d['results'].values())[0] if not l.get('error')]
print(sum(1 for l in laps if l['passed']))"
}
worst_of() {
    python3 -c "
import json
d=json.load(open('$1'))
laps=[l for l in list(d['results'].values())[0] if not l.get('error')]
print(f\"{max(l['max_cte_ft'] for l in laps):.2f}\")"
}

say "=== seed sweep: $(echo $SEEDS | wc -w) draws on a fixed dataset ==="
for SEED in $SEEDS; do
    CK="${BASE_CK}_s${SEED}"
    if [ ! -f "$REPO/pipeline/checkpoints/$CK.pth" ]; then
        say "seed $SEED: distilling $CK"
        ( cd pipeline && DISTILL_SEED="$SEED" python3 distill.py --in-w "$IN_W" --in-h "$IN_H" \
            --out "$CK" --teacher "$TEACHER" --base mixed_t06lap \
            --dagger-dirs "dagger_mixed_t06lap,$DDIR" --channels "$CH" --fc "$FC" ) \
            >>"$REPO/results/town06_logs/distill_seed_${SEED}.log" 2>&1 \
            || { say "  seed $SEED: distillation FAILED"; continue; }
    else say "seed $SEED: $CK already distilled"; fi

    # CHEAP SCREEN FIRST: one lap per condition. A seed that cannot hold a single lap will
    # not hold three, and screening costs a third of what gating costs.
    say "  screen: 1 lap x 4 conditions"
    SCREEN=0
    for COND in fog night clear low_sun; do
        OUT="$REPO/results/town06/seed_screen_${CK}_${COND}.json"
        python3 scripts/compare_student_variants.py --checkpoints "$CK" \
            --channels "$CH" --fc "$FC" --reps 1 --weather "$COND" --out "$OUT" \
            >>"$LOG" 2>&1
        N=$(held_of "$OUT"); W=$(worst_of "$OUT")
        say "    $COND $N/1  worst $W ft"
        SCREEN=$((SCREEN+N))
        [ "$N" -eq 0 ] && break        # one failed condition is enough to reject the draw
    done
    if [ "$SCREEN" -lt 4 ]; then
        say "  seed $SEED rejected at the screen ($SCREEN/4)"
        continue
    fi

    say "  seed $SEED passed the screen; STRICT GATE: 3 laps x 4 conditions"
    HELD=0
    for COND in fog night clear low_sun; do
        OUT="$REPO/results/town06/seed_gate_${CK}_${COND}.json"
        python3 scripts/compare_student_variants.py --checkpoints "$CK" \
            --channels "$CH" --fc "$FC" --reps 3 --weather "$COND" --out "$OUT" \
            >>"$LOG" 2>&1
        N=$(held_of "$OUT"); W=$(worst_of "$OUT")
        say "    $COND $N/3  worst $W ft"
        HELD=$((HELD+N))
    done
    say "  seed $SEED held $HELD/12"
    if [ "$HELD" -eq 12 ]; then
        cp -p "$REPO/pipeline/checkpoints/$CK.pth" \
              "$REPO/pipeline/checkpoints/${BASE_CK}.pth"
        echo "$CK" > "$REPO/pipeline/checkpoints/${BASE_CK}.selected"
        say "*** MIXED STUDENT PASSES 12/12: $CK (seed $SEED, pinned) ***"
        exit 0
    fi
done
say "no seed held 12/12"
exit 1

#!/usr/bin/env bash
# Find a student that holds every lap of every condition it is responsible for, by
# re-drawing the distillation seed on a FIXED dataset.
#
#   NAME=S_clear CK=S_clear_t06lap_168x56_w2 CH=16,32,32 FC=64 \
#   TEACHER=teacher_clear_t06lap_dagger_r04 BASE=clear_t06lap \
#   DAGGER_DIRS=dagger_clear_t06lap CONDS=clear \
#   bash scripts/select_student_seed.sh
#
# WHY A SEED SWEEP. Distillation on this route is high variance, and the variance is not
# small: it decides whether a student drives.
#
#     mixed student, same pool, same architecture, same code
#       seed 0  rejected on the first lap of the screen
#       seed 1  rejected
#       seed 2  rejected
#       seed 3  12/12 laps, worst 1.78 ft against a 2.19 ft budget
#
#     clear student, same base, same teacher, DEFAULT seed both times
#       first draw   1.16 / 1.08 / 1.16 ft   3/3
#       second draw  8.68 / 8.59 / 8.58 ft   0/3
#
# The clear pair is the sharper evidence, because nothing about the inputs changed between
# the two draws: distill.py seeds python, numpy and torch but does not pin cuDNN
# determinism, so the same nominal seed can still land in a different basin. Training
# variance is therefore a property of this pipeline that has to be handled, not an
# irregularity to be explained away -- which is what T06-F14 measured (a seed flipping a
# student 4/6 -> 6/6) and what config.DISTILL_SEED's own comment asks for.
#
# WHAT THIS IS. Model BUILDING, on the same side of PROTOCOL section 5's leakage boundary
# as the teacher gate and the competence gate: no canonical cell is scored, nothing reaches
# the ledger, no certificate exists yet. The criterion is fixed before the sweep starts,
# the sweep stops at the FIRST seed that meets it rather than continuing to the best one,
# and the numbers that decide the study come later from a blind certificate and a scored
# ledger.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06 CARLA_PORT=${CARLA_PORT:-3000} CARLA_WINDOWED=${CARLA_WINDOWED:-0}
export PYTHONUNBUFFERED=1

CK=${CK:?CK (checkpoint base name) required}
CH=${CH:?CH (channels) required}
FC=${FC:?FC required}
TEACHER=${TEACHER:?TEACHER required}
BASE=${BASE:?BASE dataset required}
DAGGER_DIRS=${DAGGER_DIRS:?DAGGER_DIRS required}
CONDS=${CONDS:-clear}
REPS=${REPS:-3}
IN_W=${IN_W:-168}
IN_H=${IN_H:-56}
SEEDS="${SEEDS:-0 1 2 3 4 5 6 7 8 9}"

# MARGIN, not merely a pass (pass-3 pre-registration).
#
# The gate below counted `passed`, which is "max |CTE| <= budget". A sweep that stops at
# the first draw meeting that criterion CANNOT select for headroom, because it stops at
# the first student that has none: the shipped mixed student cleared fog at 1.78 ft of a
# 2.19 ft budget -- 19% margin -- and then went VOID under fog in two independent passes.
#
# MARGIN_FRAC is the fraction of budget every GATE lap must stay under. The SCREEN stays
# at the full budget: it is a cheap filter, not the criterion.
#
# Default 1.0 reproduces the old behaviour exactly, so passes 1 and 2 are unaffected.
MARGIN_FRAC=${MARGIN_FRAC:-1.0}
SCREEN_FRAC=${SCREEN_FRAC:-1.0}

# Where the winner is recorded, and whether it overwrites the base checkpoint.
#
# PIN_CK lets a new sweep pin under its OWN name. Without it, re-sweeping w4 for pass 3
# would overwrite S_mixed_t06lap_168x56_w4.selected -- the pin passes 1 and 2 resolve
# through -- and silently change which model those committed results refer to.
PIN_CK=${PIN_CK:-$CK}
PROMOTE=${PROMOTE:-1}

# Where screen/gate artifacts land. A new sweep of an OLD checkpoint overwrites the old
# sweep's artifacts in place -- which is how the committed 11.45 ft fog screen of
# S_mixed_t06lap_168x56_w4_s0 was replaced by a 1.48 ft one, destroying the only record
# of the measurement that rejected it. The originals were recoverable only because they
# happened to be tracked in git.
OUT_DIR=${OUT_DIR:-results/town06}
mkdir -p "$REPO/$OUT_DIR"

BUDGET_FT=$(python3 -c "import sys;sys.path.insert(0,'pipeline');import config as C;print(C.CTE_BUDGET_FT)")
GATE_FT=$(python3 -c "print(f'{$BUDGET_FT * $MARGIN_FRAC:.4f}')")
SCREEN_FT=$(python3 -c "print(f'{$BUDGET_FT * $SCREEN_FRAC:.4f}')")

# ONE SWEEP AT A TIME, by PID lock. A process-name match also matches a git commit whose
# message names this file, and that has already made a supervisor wait on itself.
LOCK=/tmp/town06_seed_sweep_$(echo "$CK" | tr -c 'a-zA-Z0-9' '_').lock
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
    echo "another sweep for $CK is alive (pid $(cat "$LOCK")); exiting"; exit 0
fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT

LOG=$REPO/results/town06_logs/seed_sweep_${CK}.log
mkdir -p "$(dirname "$LOG")"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

held_of() { python3 -c "
import json
d=json.load(open('$1'))
laps=[l for l in list(d['results'].values())[0] if not l.get('error')]
print(sum(1 for l in laps if l['passed']))"; }
# Laps at or under a THRESHOLD in feet, rather than merely under budget. A lap that
# errored is not counted as held -- an absent measurement is not a passing one.
held_under() { python3 -c "
import json
d=json.load(open('$1'))
laps=[l for l in list(d['results'].values())[0] if not l.get('error')]
print(sum(1 for l in laps if l['max_cte_ft'] <= $2))"; }
worst_of() { python3 -c "
import json
d=json.load(open('$1'))
laps=[l for l in list(d['results'].values())[0] if not l.get('error')]
print(f\"{max(l['max_cte_ft'] for l in laps):.2f}\")"; }

NCOND=$(echo "$CONDS" | wc -w)
say "=== seed sweep for $CK -> pin $PIN_CK: conditions [$CONDS], $REPS laps each ==="
say "    budget $BUDGET_FT ft | screen <= $SCREEN_FT ft | GATE <= $GATE_FT ft (${MARGIN_FRAC}x)"
for SEED in $SEEDS; do
    SCK="${CK}_s${SEED}"
    if [ ! -f "$REPO/pipeline/checkpoints/$SCK.pth" ]; then
        say "seed $SEED: distilling $SCK"
        ( cd pipeline && DISTILL_SEED="$SEED" python3 distill.py --in-w "$IN_W" --in-h "$IN_H" \
            --out "$SCK" --teacher "$TEACHER" --base "$BASE" \
            --dagger-dirs "$DAGGER_DIRS" --channels "$CH" --fc "$FC" ) \
            >>"$REPO/results/town06_logs/distill_${SCK}.log" 2>&1 \
            || { say "  seed $SEED: distillation FAILED"; continue; }
    else say "seed $SEED: $SCK already distilled"; fi

    # Screen on ONE lap per condition before spending three: a draw that cannot hold a
    # single lap will not hold three, and the screen costs a third as much.
    SCREEN=0
    for COND in $CONDS; do
        OUT="$REPO/$OUT_DIR/seed_screen_${SCK}_${COND}.json"
        python3 scripts/compare_student_variants.py --checkpoints "$SCK" \
            --channels "$CH" --fc "$FC" --reps 1 --weather "$COND" --out "$OUT" >>"$LOG" 2>&1
        # EXIT 3 = a lap could not be measured. Rejecting the seed on that would blame
        # the model for the harness: the SHIPPED student was "rejected at the screen"
        # exactly this way, when one restart failed and its night lap was never driven.
        # A sweep that cannot get a server cannot evaluate anything, so it stops.
        if [ $? -eq 3 ]; then
            say "  FATAL: $COND lap for seed $SEED could not be measured (harness)."
            say "  Refusing to score any seed against a harness that cannot produce a lap."
            exit 2
        fi
        N=$(held_under "$OUT" "$SCREEN_FT")
        say "    screen $COND $N/1  worst $(worst_of "$OUT") ft (<= $SCREEN_FT)"
        SCREEN=$((SCREEN+N)); [ "$N" -eq 0 ] && break
    done
    [ "$SCREEN" -lt "$NCOND" ] && { say "  seed $SEED rejected at the screen"; continue; }

    say "  seed $SEED passed the screen; strict gate: $REPS laps x $NCOND condition(s)"
    HELD=0
    for COND in $CONDS; do
        OUT="$REPO/$OUT_DIR/seed_gate_${SCK}_${COND}.json"
        python3 scripts/compare_student_variants.py --checkpoints "$SCK" \
            --channels "$CH" --fc "$FC" --reps "$REPS" --weather "$COND" --out "$OUT" >>"$LOG" 2>&1
        if [ $? -eq 3 ]; then
            say "  FATAL: $COND gate for seed $SEED could not be measured (harness)."
            exit 2
        fi
        N=$(held_under "$OUT" "$GATE_FT")
        say "    gate $COND $N/$REPS  worst $(worst_of "$OUT") ft (<= $GATE_FT)"
        HELD=$((HELD+N))
    done
    NEED=$((REPS*NCOND))
    say "  seed $SEED held $HELD/$NEED"
    if [ "$HELD" -eq "$NEED" ]; then
        if [ "$PROMOTE" = "1" ]; then
            cp -p "$REPO/pipeline/checkpoints/$SCK.pth" \
                  "$REPO/pipeline/checkpoints/${CK}.pth"
        fi
        echo "$SCK" > "$REPO/pipeline/checkpoints/${PIN_CK}.selected"
        say "*** $PIN_CK PASSES $HELD/$NEED at <= $GATE_FT ft: $SCK (seed $SEED, pinned) ***"
        exit 0
    fi
done
say "no seed held every lap under $GATE_FT ft for $CK"
exit 1

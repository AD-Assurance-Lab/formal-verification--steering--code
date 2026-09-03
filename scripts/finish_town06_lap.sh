#!/usr/bin/env bash
# Everything from "the mixed student passes its gate" to "the deployment test is done".
#
# One committed driver, because standing rule 8 says a number that goes in a paper comes
# from a script in the repo and not from a command someone typed. It is resumable: every
# stage is skipped when its artifact already exists.
#
#   bash scripts/finish_town06_lap.sh
#
# Order, and it is not negotiable:
#   1. clear student: distil, verify 3 laps clear
#   2. clear-weather competence gate (PROTOCOL section 4a precondition)
#   3. captures at the students' resolution
#   4. A-3 capture gate: captured frames must reproduce what the vehicle commanded
#   5. certify BLIND, with CARLA down
#   6. COMMIT the certificate            <- PROTOCOL R1
#   7. scored ledger, 3 laps per cell    <- only after 6
#   8. compare prediction against outcome
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06 CARLA_PORT=${CARLA_PORT:-3000} PYTHONUNBUFFERED=1
export CARLA_WINDOWED=${CARLA_WINDOWED:-0}

LOG_DIR=$REPO/results/town06_logs; mkdir -p "$LOG_DIR"
LOG=$LOG_DIR/finish_lap.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

CK_DIR=$REPO/pipeline/checkpoints
read -r CLEAR_CK CLEAR_CH CLEAR_FC MIXED_CK MIXED_CH MIXED_FC IN_W IN_H <<<"$(
python3 - <<'PY'
import sys; sys.path.insert(0,'pipeline'); import config as C
rows = {nm: (ck, ",".join(str(c) for c in ch), fc) for nm, ck, ch, fc in C.TOWN06_STUDENTS}
c = rows["S_clear_t06"]; m = rows["S_mixed_t06"]
print(c[0], c[1], c[2], m[0], m[1], m[2], C.TOWN06_INPUT_W, C.TOWN06_INPUT_H)
PY
)"
say "students: clear=$CLEAR_CK ($CLEAR_CH/$CLEAR_FC)  mixed=$MIXED_CK ($MIXED_CH/$MIXED_FC)  input ${IN_W}x${IN_H}"

# ---------------------------------------------------------------- 1. clear student
# It was overwritten during the six-lap experiment (T06-F49) and that data is gone, so the
# checkpoint on disk cannot be reproduced from what is in the repo. Rebuild it from the
# three-lap base and prove it drives before anything downstream consumes it.
if [ ! -f "$CK_DIR/$CLEAR_CK.pth" ] || [ ! -f "$REPO/results/town06/clear_student_verified.json" ]; then
    # A SEED SWEEP, NOT ONE DRAW. Distillation on this route is high variance: the same
    # base, the same teacher and the same default seed produced 1.16 ft one afternoon and
    # 8.68 ft that evening, because distill.py seeds python/numpy/torch but does not pin
    # cuDNN determinism. One draw is a coin toss; the sweep keeps drawing until a student
    # holds every lap, then pins it.
    say "selecting a clear student by seed sweep (3 laps clear)"
    CK="$CLEAR_CK" CH="$CLEAR_CH" FC="$CLEAR_FC" \
        TEACHER="$(ls -t "$CK_DIR"/teacher_clear_t06lap_dagger_r*.pth | head -1 | xargs basename | sed 's/\.pth$//')" \
        BASE=clear_t06lap DAGGER_DIRS=dagger_clear_t06lap CONDS=clear REPS=3 \
        IN_W="$IN_W" IN_H="$IN_H" \
        bash scripts/select_student_seed.sh >>"$LOG" 2>&1 \
        || { say "FATAL: no seed produced a clear student that holds three laps"; exit 1; }
    SEL=$(cat "$CK_DIR/${CLEAR_CK}.selected")
    cp -p "$REPO/results/town06/seed_gate_${SEL}_clear.json" \
          "$REPO/results/town06/clear_student_verified.json"
else say "SKIP clear student (verified artifact present)"; fi
python3 - <<'PY' || exit 1
import json, sys
d = json.load(open("results/town06/clear_student_verified.json"))
laps = [l for l in list(d["results"].values())[0] if not l.get("error")]
held = sum(1 for l in laps if l["passed"])
worst = max(l["max_cte_ft"] for l in laps)
print(f"  clear student: {held}/{len(laps)} laps, worst {worst:.2f} ft "
      f"({100*worst/d['budget_ft']:.0f}% of budget)")
if held != len(laps):
    sys.exit("FATAL: the clear student does not hold every lap in clear weather.")
PY

# ---------------------------------------------------------------- 2. competence gate
if [ ! -f "$REPO/results/town06/competence_clear.json" ]; then
    say "clear-weather competence gate (3 laps per student)"
    python3 scripts/check_student_competence.py --reps 3 --require >>"$LOG_DIR/competence.log" 2>&1 \
        || { say "FATAL: a student is not competent in clear weather (section 4a)"; exit 1; }
else say "SKIP competence gate (record present)"; fi
say "competence: $(python3 -c "
import json;d=json.load(open('results/town06/competence_clear.json'))
print('OK' if d.get('all_competent') else 'NOT COMPETENT')")"

# ---------------------------------------------------------------- 3-8. the rest
say "handing over to finish_town06_deployment.sh (captures -> gate -> certify -> COMMIT -> drive)"
bash scripts/finish_town06_deployment.sh
rc=$?
say "finish_town06_deployment.sh exited $rc"
exit $rc

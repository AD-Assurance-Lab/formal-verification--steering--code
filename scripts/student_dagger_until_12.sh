#!/usr/bin/env bash
# Student DAgger until the mixed student holds ALL FOUR conditions over THREE laps each.
#
# The internal gate is one rep and it is not the decision: it said night 1.50 ft PASS for a
# policy that then failed night 2 of 3 at 3.24 ft. It stays as the cheap filter; the strict
# gate below is 12 laps with a clean server before every one, exactly as the teacher gate is.
cd /home/za/ad-assurance--workspace/formal-verification--steering--code
export STUDY_MAP=Town06 CARLA_PORT=3000 CARLA_WINDOWED=0 PYTHONUNBUFFERED=1
LOG=results/town06_logs/sdagger_loop.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
rm -f /tmp/dagger_rounds.lock /tmp/carla-locks/carla-3000.lock

for r in $(seq 1 10); do
  say "=== round attempt $r ==="
  bash scripts/carla_restart.sh > results/town06_logs/sdl_restart.log 2>&1 || { say "restart failed"; exit 1; }
  rm -f /tmp/carla-locks/carla-3000.lock
  python3 pipeline/dagger_student.py --student S_mixed_t06lap_168x56_w4 \
      --w 168 --h 56 --rounds 1 --weathers clear,fog,night,low_sun \
      --teacher teacher_mixed_t06lap_dagger_r03 --base mixed_t06lap \
      --dagger-dir dagger_student_S_mixed_t06_t06lap \
      --distill-dirs dagger_mixed_t06lap,dagger_student_S_mixed_t06_t06lap \
      --channels 32,64,64 --fc 128 >> results/town06_logs/sd_loop_rounds.log 2>&1
  CK=$(ls -t pipeline/checkpoints/S_mixed_t06lap_168x56_w4_dagger_r*.pth 2>/dev/null | head -1)
  [ -n "$CK" ] || { say "no checkpoint produced"; exit 1; }
  CK=$(basename "$CK" .pth)
  say "  trained $CK; strict gate: 3 laps x 4 conditions"

  HELD=0
  for COND in clear fog night low_sun; do
    python3 scripts/compare_student_variants.py --checkpoints "$CK" \
        --channels 32,64,64 --fc 128 --reps 3 --weather "$COND" \
        --out "results/town06/sdl_${CK}_${COND}.json" >> "$LOG" 2>&1
    N=$(python3 -c "
import json;d=json.load(open('results/town06/sdl_${CK}_${COND}.json'))
laps=list(d['results'].values())[0]
print(sum(1 for l in laps if not l.get('error') and l['passed']))")
    W=$(python3 -c "
import json;d=json.load(open('results/town06/sdl_${CK}_${COND}.json'))
laps=[l for l in list(d['results'].values())[0] if not l.get('error')]
print(f\"{max(l['max_cte_ft'] for l in laps):.2f}\")")
    say "    $COND $N/3  worst $W ft"
    HELD=$((HELD+N))
  done
  say "  $CK held $HELD/12"
  if [ "$HELD" -eq 12 ]; then
    cp -p "pipeline/checkpoints/$CK.pth" pipeline/checkpoints/S_mixed_t06lap_168x56_w4_PASSING.pth
    # Record WHICH checkpoint the gate accepted, so nothing downstream has to infer it
    # from a timestamp (config.final_student honours this pin).
    echo "$CK" > pipeline/checkpoints/S_mixed_t06lap_168x56_w4.selected
    say "*** MIXED STUDENT PASSES 12/12: $CK (pinned) ***"
    exit 0
  fi
done
say "did not reach 12/12 in 10 rounds"
exit 1

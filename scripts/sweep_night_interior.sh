#!/usr/bin/env bash
# Does the mixed student fail an INTERIOR point of the night family while passing the
# endpoint? Zach's question, and the certificate's NOT_CERTIFIED says it might.
#
#   bash scripts/sweep_night_interior.sh
#
# THE QUESTION. night/S_mixed_t06 drove PASS 0/3 at the PRESET and the certificate says
# NOT_CERTIFIED. Those disagree only if the certificate is about the endpoint, and it is
# not: it quantifies over the whole one-parameter family, and the ledger drives one point
# of it. T06-F32 already found exactly this on the FOG axis -- both endpoints clean, the
# interior not, with a 100% failure rate at fog density 35 -- so the disagreement is a
# reason to look between the endpoints rather than a mark against the bound.
#
# THE AXIS. certify_cell.night_map models night as a darkening away from the headlight
# field plus retroreflection, over a box in (gain, retro). Its interior is partial
# darkness: dusk. The closed-loop analogue is sun altitude between clear's 90 degrees and
# night's -25.
#
# THE EXPOSURE, and this is where the previous attempt went wrong. T06-F35 withdrew most
# of T06-F33 because it swept sun altitude with `--weather night`, whose declared shutter
# is 200 against daylight's 800, so daylight scenes were rendered through a night camera
# and read as 'clear' at mean 0.49. Those failures were an artefact of the camera, not
# operating points on any family.
#
# So this sweeps with `--weather low_sun`, whose declared exposure IS daylight (shutter
# 800), and overrides only the sun altitude. One camera across the whole band, no
# discontinuity in the middle of the family, and the frame statistics are recorded at each
# point so "is this a physically sensible image?" is measured rather than assumed.
#
# Not a scored cell: closed_loop_ledger.py refuses a canonical cell while
# SUN_ALTITUDE_OVERRIDE is set, and this writes to results/town06/night_interior/.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06 CARLA_PORT=${CARLA_PORT:-3000} CARLA_WINDOWED=${CARLA_WINDOWED:-0}
export PYTHONUNBUFFERED=1

CK=${CK:-S_mixed_t06lap_168x56_w4_s3}
CH=${CH:-32,64,64}
FC=${FC:-128}
# 90 is clear (s=0) and -25 is the night preset (s=1). The band that matters is the last
# of the light: 20 down to -25, plus one high point to show the top of the range is clean.
ALTS="${ALTS:-45 20 10 5 0 -5 -10 -25}"

LOG=$REPO/results/town06_logs/night_interior.log
OUT=$REPO/results/town06/night_interior
mkdir -p "$OUT" "$(dirname "$LOG")"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

say "=== night interior sweep: $CK, sun altitude [$ALTS], daylight exposure ==="
for ALT in $ALTS; do
    bash scripts/carla_restart_retry.sh /tmp/night_interior_restart.log "alt=$ALT" \
        >/dev/null 2>&1 || { say "  restart failed at alt=$ALT"; exit 1; }
    rm -f "/tmp/carla-locks/carla-$CARLA_PORT.lock" 2>/dev/null
    TAG=$(echo "$ALT" | tr -- '-' 'm')
    SUN_ALTITUDE_OVERRIDE="$ALT" python3 scripts/compare_student_variants.py \
        --checkpoints "$CK" --channels "$CH" --fc "$FC" --reps 1 --weather low_sun \
        --out "$OUT/alt_${TAG}.json" >>"$LOG" 2>&1
    RES=$(python3 -c "
import json
d=json.load(open('$OUT/alt_${TAG}.json'))
l=[x for x in list(d['results'].values())[0] if not x.get('error')]
if not l: print('RUN FAILED')
else:
    w=max(x['max_cte_ft'] for x in l)
    print(f\"max|CTE| {w:6.2f} ft  ({100*w/d['budget_ft']:4.0f}% of budget)  \"
          f\"{'PASS' if all(x['passed'] for x in l) else 'FAIL'}  \"
          f\"steps {l[0]['steps']}/{l[0]['full_steps']}\")")
    say "  sun altitude ${ALT}deg : $RES"
done
say "=== sweep complete ==="

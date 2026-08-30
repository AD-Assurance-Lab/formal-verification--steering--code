#!/usr/bin/env bash
# The committed driver for the INTERPOLATION-FIDELITY captures.
#
# There was no such script. The fidelity captures were driven by hand, and they carry
# exactly the defect that reached the Town04 finding: results/diagnostic/
# interpolation_fidelity.json records n_poses 81, which is the 160 m default, while the
# Town04-era captures archived beside it are 200 poses over 2,798 m. The measurement that
# validates the DISTURBANCE FAMILY -- the thing the whole certificate is quantified over --
# was itself made on 5.6% of the road.
#
# Standing rules 7 and 8: --length-m is deliberately NOT passed, so every capture covers
# the whole section, and the invocation lives here rather than in a shell history.
#
# Three axes, matching what the analysis scripts expect:
#   fog     clear -> fog,     densities 17.5 / 35 / 52.5 / 70   (endpoint = 70)
#   lowsun  clear -> shadows, sun 60 / 30 / 15 / 5 deg          (endpoint = 5)
#   night   clear -> night,   sun 45 / 20 / 5 (shadows), -10 (night), endpoint -25
#
#   bash scripts/capture_interp_fidelity.sh s00            # one section
#   bash scripts/capture_interp_fidelity.sh s00 s01 s02    # several
set -uo pipefail
cd "$(dirname "$0")/.."
export CARLA_PORT=${CARLA_PORT:-3000}
# NOMINAL POSE ONLY. Both consumers of these files index argmin(|offsets|) and
# argmin(|yaws|), so the 9x5 grid is 45x the frames for data nothing reads: 18,000 per
# file instead of 400, across 78 files. Left unset the grid is the default. The lap
# drivers already collapse it the same way.
export OY_OFFSETS=0.0 OY_YAWS=0.0
export STUDY_MAP=${STUDY_MAP:-Town06}

SECTIONS=("$@")
[ ${#SECTIONS[@]} -eq 0 ] && { echo "usage: $0 <section> [section...]"; exit 2; }

DIAG=results/diagnostic
mkdir -p "$DIAG" results/town06_logs

cap () {   # cap <out.npz> <conds> <direction> <env assignments...>
    local out="$1" conds="$2" dir="$3"; shift 3
    if [ -f "$DIAG/$out" ]; then echo "  $out exists, skipping"; return 0; fi
    # R-SIM-1: RESTART BEFORE EVERY MEASUREMENT, not when something looks wrong.
    #
    # This driver did not restart at all, which is how 78 captures were about to be taken
    # on one ageing server (it leaks ~10.5 GiB over 11 h) -- and worse, a killed run leaves
    # its vehicle and camera ALIVE, because SIGTERM does not run Python cleanup handlers.
    # Two Teslas and two cameras were found in the world, so the first captures of that
    # run photographed a road with a parked car in it. Nothing in the resulting arrays
    # would have shown that. The lap drivers already restart per capture; this now does.
    bash scripts/carla_restart.sh > "results/town06_logs/restart_${out%.npz}.log" 2>&1 \
        || { echo "  restart FAILED for $out"; return 1; }
    echo "  capturing $out ($conds, $dir) $*"
    env "$@" OY_CONDS="$conds" OY_OUT="$DIAG/$out" \
        python3 scripts/capture_offset_yaw.py --poses 200 --direction "$dir" \
        > "results/town06_logs/cap_${out%.npz}.log" 2>&1
    local rc=$?
    echo -n "    rc=$rc  "
    grep -E "route coverage|WHOLE route" "results/town06_logs/cap_${out%.npz}.log" | tail -1
    return $rc
}

for SEC in "${SECTIONS[@]}"; do
    echo "=== section $SEC ==="
    for d in 17.5 35 52.5 70; do
        cap "interp_fog_${SEC}_d${d}.npz"    clear,fog     "$SEC" FOG_DENSITY_OVERRIDE=$d
    done
    for s in 60 30 15 5; do
        cap "interp_lowsun_${SEC}_s${s}.npz" clear,shadows "$SEC" SUN_ALTITUDE_OVERRIDE=$s
    done
    for s in 45 20 5; do
        cap "interp_night_${SEC}_s${s}.npz"  clear,shadows "$SEC" SUN_ALTITUDE_OVERRIDE=$s
    done
    cap "interp_night_${SEC}_s-10.npz"       clear,night   "$SEC" SUN_ALTITUDE_OVERRIDE=-10
    cap "interp_night_${SEC}_end.npz"        clear,night   "$SEC" SUN_ALTITUDE_OVERRIDE=-25
done
echo "CAPTURE INTERP FIDELITY DONE"

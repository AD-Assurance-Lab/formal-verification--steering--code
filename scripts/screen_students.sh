#!/usr/bin/env bash
# M3b: fast triage of the distilled students across all four conditions.
#
# ONE repetition per direction. This is a SCREEN, not a ledger cell -- ledger cells need
# >= 10 repetitions with a Wilson interval, and results go to _screen_* names so they can
# never be mistaken for one.
#
# Expectation, stated before running: these students have NOT had student-DAgger, and last
# time a freshly distilled student failed closed loop for exactly that reason. So the
# useful output here is probably not "which one passes" but "which one is closest", to
# decide what to spend a 2-3 hour student-DAgger run on.
#
# We are minimising ReLU count subject to driving all four conditions, because ReLU count
# is what drives bound looseness at M6. So the candidates run smallest-first and the
# screen stops early if a small one already drives everything.
set -uo pipefail

PY="${PYTHON:-python3}"
cd "$(dirname "$0")/.."

run_one() {   # student, channels, fc, label
    local student="$1" ch="$2" fc="$3" label="$4"
    echo ""
    echo "################ $student ($label) ################"
    for cond in clear fog night shadows; do
        $PY -u scripts/closed_loop_ledger.py --student "$student" --condition "$cond" \
            --reps 1 --channels "$ch" --fc "$fc" --cell-name "_screen_$label" \
            2>&1 | grep -E "rep 0|failure rate|verdict" | sed "s/^/  [$cond] /"
    done
}

run_one S_mixed_84x28_w1 8,16,16   32  w1
run_one S_mixed_84x28_w2 16,32,32  64  w2
run_one S_mixed_84x28_w3 24,48,48  96  w3

echo ""
echo "################ S_clear on clear (control) ################"
$PY -u scripts/closed_loop_ledger.py --student S_clear_84x28 --condition clear \
    --reps 1 --channels 8,16,16 --fc 32 --cell-name _screen_clear \
    2>&1 | grep -E "rep 0|failure rate|verdict" | sed 's/^/  [clear] /'

echo ""
echo "################ screen complete ################"

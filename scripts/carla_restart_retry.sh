#!/usr/bin/env bash
# Restart CARLA, retrying a transient failure. THE one place that decides how many times.
#
#   bash scripts/carla_restart_retry.sh <logfile> [label]
#
# carla_restart.sh gives the server 300 s to become ready and fails if it does not. That is
# right for a single restart and wrong as a STAGE verdict: every driver in this study
# restarts before every measurement, so a stage is dozens of restarts and a boot that
# occasionally misses its window is a certainty rather than a risk.
#
# Measured on 2026-09-02/03, all four the same shape:
#
#   * a boot exceeded 300 s while a distillation held the GPU, and NINE completed
#     student-DAgger rounds were abandoned;
#   * a teacher-gate restart failed and discarded a twelve-lap gate that was passing;
#   * a capture stage lost three completed captures to one failed boot;
#   * the SCORED LEDGER died on the last rep of its eighth cell -- seven cells and
#     twenty-three laps already driven -- because one server did not come up.
#
# Each driver grew its own copy of the retry except the ledger, which is the one whose
# output is a published number. Four copies of a policy is how they drift, so there is one.
#
# The retry is bounded and loud. Three consecutive failures is not a slow boot, and the
# caller still stops: a measurement taken against a server that cannot be verified is one
# nobody can defend (D-11). This lowers no bar -- carla_restart.sh still runs the full
# determinism preflight and the photometry gate on every attempt.
set -uo pipefail
cd "$(dirname "$0")/.."
LOGF=${1:?logfile required}
LABEL=${2:-restart}
ATTEMPTS=${CARLA_RESTART_ATTEMPTS:-3}
PORT=${CARLA_PORT:-3000}

for i in $(seq 1 "$ATTEMPTS"); do
    if bash scripts/carla_restart.sh > "$LOGF" 2>&1; then
        [ "$i" -gt 1 ] && echo "  restart succeeded on attempt $i ($LABEL)"
        rm -f "/tmp/carla-locks/carla-$PORT.lock" 2>/dev/null
        exit 0
    fi
    echo "  restart attempt $i/$ATTEMPTS FAILED ($LABEL): $(tail -1 "$LOGF" | tr -s ' ' | cut -c1-80)"
    sleep 20
done
echo "  restart FAILED $ATTEMPTS times ($LABEL) -- that is not a slow boot"
exit 1

#!/usr/bin/env bash
# Everything after the students are competent: capture -> certify -> COMMIT -> drive.
#
# The ordering here IS the experiment. PROTOCOL R1 requires the certificate to be
# committed before any scored drive, because that is what makes a verdict a prediction
# rather than a description. check_order_town06.py enforces it independently; this
# script is the clearer early failure, not the guard.
#
# CARLA IS STOPPED BEFORE CERTIFYING (T06-F12). It holds ~10.25 GiB of the 12 GiB card
# after a long run, which OOMs alpha-CROWN outright on a batched graph and leaves the
# unbatched path launch-bound -- 1.43 s/pose on GPU against 2.55 on CPU, a 12 GiB GPU
# buying 1.8x. Certification needs no simulator, so the simulator goes down first and
# comes back for the ledger.
#
#   bash scripts/finish_town06_deployment.sh
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export STUDY_MAP=Town06
export CARLA_PORT=${CARLA_PORT:-3000}
export PYTHONUNBUFFERED=1

LOG_DIR=$REPO/results/town06_logs
mkdir -p "$LOG_DIR"
LOG=$LOG_DIR/finish.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

CARLA_ROOT=${CARLA_ROOT:-$HOME/carla}
carla_up()   { for i in $(seq 1 "${1:-60}"); do
    ss -ltn 2>/dev/null | grep -q ":$CARLA_PORT" && return 0; sleep 5; done; return 1; }
carla_stop() {
    say "stopping CARLA on $CARLA_PORT (certification needs the GPU, not the simulator)"
    pkill -f "[C]arlaUE4-Linux-Shipping.*rpc-port=$CARLA_PORT" 2>/dev/null
    sleep 12
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader | \
        sed 's/^/    GPU after stop: /' | tee -a "$LOG"; }
carla_start() {
    say "starting CARLA on $CARLA_PORT"
    ( cd "$CARLA_ROOT" && setsid nohup ./CarlaUE4.sh -carla-rpc-port="$CARLA_PORT" \
        -RenderOffScreen -quality-level=Epic >>"$LOG_DIR/carla.log" 2>&1 < /dev/null & )
    carla_up 60 && { say "CARLA up"; sleep 10; return 0; }
    say "FATAL: CARLA did not come up"; return 1; }

# ---------------------------------------------------------------- preconditions
python3 scripts/check_protocol_lock.py >/dev/null || { say "FATAL: PROTOCOL lock"; exit 1; }

# The certificate bounds deviation FROM clear. A student that is wrong in clear weather
# certifies perfectly and drives off the road, so competence is a precondition for the
# certificate meaning anything -- and it must be the CURRENT students' record.
python3 - <<'PY' || exit 1
import json, sys
from pathlib import Path
p = Path("results/town06/competence_clear.json")
if not p.exists():
    sys.exit("FATAL: no competence record. Run the pipeline first.")
d = json.loads(p.read_text())
if not d.get("all_competent"):
    sys.exit("FATAL: competence record says a student is NOT competent in clear weather.")
print(f"  competence OK ({d.get('reps')} reps, every section on every rep): "
      + ", ".join(f"{k}={v.get('checkpoint')}" for k, v in d["students"].items()))
PY

# ---------------------------------------------------------------- 1. capture
# The captures ARE the verifier's input, so they must be at the students' resolution.
if ls results/town06/captures/*.npz >/dev/null 2>&1; then
    say "SKIP capture (npz present)"
else
    carla_up 6 || carla_start || exit 1
    say "capturing 24 laps (6 sections x 4 conditions) at the students' resolution"
    bash scripts/capture_town06_laps.sh >>"$LOG_DIR/capture.log" 2>&1 \
        || { say "FATAL: capture failed, see capture.log"; exit 1; }
fi
python3 - <<'PY' || exit 1
import sys, numpy as np
from pathlib import Path
sys.path.insert(0, "pipeline"); import config as C
bad = []
for p in sorted(Path("results/town06/captures").glob("*.npz")):
    a = np.load(p)
    k = "frames" if "frames" in a.files else a.files[0]
    s = a[k].shape
    if s[-2:] != (C.TOWN06_INPUT_H, C.TOWN06_INPUT_W):
        bad.append(f"{p.name} {s[-2:]}")
if bad:
    sys.exit(f"FATAL: captures are at the wrong resolution, expected "
             f"{(C.TOWN06_INPUT_H, C.TOWN06_INPUT_W)}: " + ", ".join(bad[:4]))
print(f"  captures OK at {C.TOWN06_INPUT_H}x{C.TOWN06_INPUT_W}")
PY

# ---------------------------------------------------------------- 2. certify (blind)
carla_stop
say "certifying -- blind: no truth table is read, and the drives have not happened"
python3 scripts/certify_town06.py >>"$LOG_DIR/certify.log" 2>&1 \
    || { say "FATAL: certification failed, see certify.log"; carla_start; exit 1; }
tail -20 "$LOG_DIR/certify.log" | tee -a "$LOG"

# ---------------------------------------------------------------- 3. COMMIT (R1)
CERT=results/town06/certificate_town06.json
[ -f "$CERT" ] || { say "FATAL: no certificate written"; carla_start; exit 1; }
git add "$CERT" docs/TOWN06_FINDINGS.md 2>/dev/null
if git diff --cached --quiet; then
    say "certificate already committed, nothing to add"
else
    git commit -q -F - <<MSG
Town06 certificate: the prediction, committed before any scored drive

PROTOCOL R1. This is what makes the verdicts a prediction rather than a description:
no closed-loop cell has been driven, and no truth table was read to produce it.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_017s53EDyiBNRN9VM8sxqLT8
MSG
    say "committed the certificate"
fi
git push -q origin validation/town06-deployment-test && say "pushed"

python3 scripts/check_order_town06.py >/dev/null || {
    say "FATAL: R1 still not satisfied after commit. Refusing to drive."; exit 1; }
say "R1 satisfied. The prediction is on the record; driving may begin."

# ---------------------------------------------------------------- 4. drive, 5. compare
carla_start || exit 1
say "running the scored ledger: 8 cells x 12 runs"
bash scripts/run_town06_ledger.sh >>"$LOG_DIR/ledger_run.log" 2>&1 \
    || say "WARNING: ledger exited nonzero, see ledger_run.log"

say "comparing prediction against outcome"
python3 scripts/compare_town06.py 2>&1 | tee -a "$LOG"
say "DEPLOYMENT TEST COMPLETE"

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
    # ONE launcher (scripts/carla_launch.sh). This function used to start CARLA itself
    # and lacked -notexturestreaming -- and it is the server the SCORED LEDGER runs
    # against, so every certified cell would have been measured 168x noisier than the
    # floor while looking completely normal. carla_launch.sh also verifies the flags
    # actually landed, by reading the server's real /proc argv.
    say "starting CARLA on $CARLA_PORT (via scripts/carla_launch.sh)"
    if bash scripts/carla_launch.sh >>"$LOG" 2>&1; then say "CARLA ready"; return 0; fi
    say "FATAL: CARLA did not become ready, or violates the determinism rules"; return 1; }

# ---------------------------------------------------------------- preconditions
python3 scripts/check_protocol_lock.py >/dev/null || { say "FATAL: PROTOCOL lock"; exit 1; }
python3 -m carla_determinism --lock-only >/dev/null || {
    say "FATAL: carla-determinism rules lock mismatch"; exit 1; }

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

# The record must be about THESE weights. Without this the record is keyed to nothing,
# and one left over from a superseded generation of students would gate the
# certification of entirely different checkpoints.
sys.path.insert(0, "pipeline"); sys.path.insert(0, "scripts")
import config as C
from check_student_competence import checkpoint_digest
have = d.get("checkpoint_digests")
if not have:
    sys.exit("FATAL: competence record predates checkpoint digests, so it cannot be "
             "shown to describe the students on disk. Re-run the competence gate.")
for _, ck, _, _ in C.TOWN06_STUDENTS:
    # The checkpoint that IS the student, which after student DAgger is not the
    # distilled one. Checking the distilled file here would verify a model the gate
    # never drove and the ledger will never run.
    ck = C.final_student(ck)
    now = checkpoint_digest(ck)
    if have.get(ck) != now:
        sys.exit(f"FATAL: competence record is STALE for {ck} "
                 f"(recorded {have.get(ck)}, on disk {now}). Re-run the competence gate.")
print("  competence record verified against the checkpoints on disk")
print(f"  competence OK ({d.get('reps')} reps, every section on every rep): "
      + ", ".join(f"{k}={v.get('checkpoint')}" for k, v in d["students"].items()))
PY

# ---------------------------------------------------------------- 1. capture
# The captures ARE the verifier's input, so they must be at the students' resolution.
# "FILES EXIST" IS NOT "THE RIGHT FILES EXIST".
#
# This skipped whenever ANY npz sat in the capture directory, and twenty-four of them did
# -- the six-section era's, at 168x28, on sections s00..s05 that this study no longer
# drives. The stage skipped, and the resolution check below then refused to certify, which
# is the good outcome only because that check exists. The guard now asks whether the
# captures on disk are the ones THIS study needs: one per condition, on the current
# sections, at the current students' resolution.
NEED_CAPS=$(python3 - <<'PY'
import sys, os, glob
import numpy as np
sys.path.insert(0, "pipeline"); sys.path.insert(0, ".")
import config as C
from study import town06_design as D
need = [f"lap_{d}_{c}.npz" for d in D.SECTIONS for c in D.CONDITIONS]
missing = [n for n in need if not os.path.exists(os.path.join("results/town06/captures", n))]
wrong = []
for n in need:
    p = os.path.join("results/town06/captures", n)
    if os.path.exists(p):
        try:
            s = np.load(p)["frames"].shape[-2:]
            if tuple(s) != (C.TOWN06_INPUT_H, C.TOWN06_INPUT_W):
                wrong.append(f"{n}{tuple(s)}")
        except Exception as e:
            wrong.append(f"{n}(unreadable)")
print("OK" if not missing and not wrong else
      f"REBUILD missing={len(missing)} wrong={','.join(wrong[:3])}")
PY
)
if [ "$NEED_CAPS" = "OK" ]; then
    say "SKIP capture (every capture present at the current resolution)"
else
    carla_up 6 || carla_start || exit 1
    say "capture needed: $NEED_CAPS"
    say "capturing $(STUDY_MAP=Town06 python3 -c "import sys;sys.path.insert(0,'pipeline');import config as C;print(len(C.SECTIONS)*4)") captures (sections x 4 conditions) at the students' resolution"
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

CERT=results/town06/certificate_town06.json

# ------------------------------------------------ 1b. THE CAPTURE GATE (PROTOCOL A-3)
# A-3 makes this a PRECONDITION of certification, and audit_repo.py fails when a
# certificate exists with no capture_gate.json beside it -- but nothing in this driver
# ran it. The Town06 lap would have reached a committed certificate and then failed the
# audit, with R1 making the certificate un-regenerable: recomputing it would place its
# commit after the drives and destroy the ordering that makes it a prediction.
#
# Sound bounds computed on frames that do not reproduce the system prove nothing about
# the system. It needs per-pose DRIVEN steering, which the ledger does not keep, so the
# committed driver produces the traces first. Both are clear-weather training telemetry
# and not scored cells, so they sit on the correct side of the leakage boundary
# (PROTOCOL section 5) and may run before the certificate exists.
if [ -f results/town06/captures/capture_gate.json ]; then
    say "SKIP capture gate (capture_gate.json present)"
else
    carla_up 6 || carla_start || exit 1
    say "capture gate: driving each student once per section for the comparison traces"
    python3 scripts/capture_gate_drives.py >>"$LOG_DIR/capture_gate.log" 2>&1 \
        || { say "FATAL: capture-gate drives failed, see capture_gate.log"; exit 1; }
    say "capture gate: comparing captured frames against what the vehicle commanded"
    # NOT `... | tee -a "$LOG" || fail`: a pipeline's status is the LAST command's, so
    # tee's success would mask the gate's failure and the "FATAL" branch could never be
    # reached. That is the same shape as the teacher gate that failed open and passed a
    # teacher missing its budget by 13x. Capture the status, then show the output.
    python3 scripts/capture_driven_gate.py --captures results/town06/captures \
        >>"$LOG_DIR/capture_gate.log" 2>&1
    GATE_RC=$?
    tail -20 "$LOG_DIR/capture_gate.log" | tee -a "$LOG"
    if [ "$GATE_RC" -ne 0 ]; then
        say "FATAL: the capture gate FAILED (exit $GATE_RC). The frames the certificate"
        say "       would be computed on do not reproduce the driving system (A-3)."
        exit 1
    fi
fi

# ---------------------------------------------------------------- 2. certify (blind)
# DO NOT RE-CERTIFY A COMMITTED CERTIFICATE.
#
# This ran the certifier unconditionally, so every resume of the chain spent twenty
# minutes recomputing an artifact that was already committed and pushed. Worse in
# principle than the waste: the certificate is the pre-registered prediction under R1, and
# rewriting the file it lives in -- even with identical contents -- is the kind of churn
# that makes "was this the committed version?" a question anyone has to ask. PROTOCOL R4
# is explicit that a recomputation after the drives is a NEW cell with a new name.
if [ -f "$CERT" ] && git -C "$REPO" diff --quiet HEAD -- "$CERT" 2>/dev/null \
   && git -C "$REPO" ls-files --error-unmatch "$CERT" >/dev/null 2>&1; then
    say "SKIP certification (certificate committed and unmodified)"
else
carla_stop
say "certifying -- blind: no truth table is read, and the drives have not happened"
python3 scripts/certify_town06.py >>"$LOG_DIR/certify.log" 2>&1 \
    || { say "FATAL: certification failed, see certify.log"; carla_start; exit 1; }
tail -20 "$LOG_DIR/certify.log" | tee -a "$LOG"

fi

# ---------------------------------------------------------------- 3. COMMIT (R1)
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
Claude-Session: https://claude.ai/code/session_01RZSRHb9mJhzPz6BooMK9eM
MSG
    say "committed the certificate"
fi
# PUSH THE BRANCH THIS WORK IS ON, not a name hardcoded when it was on another one.
# The lap rebuild is on `main`; this line named validation/town06-deployment-test, which
# still exists and is stale, so it would have pushed a branch WITHOUT the certificate
# while reporting "pushed" -- and R1's whole point is that the prediction is on the
# record before the drives.
BRANCH=$(git rev-parse --abbrev-ref HEAD)
git push -q origin "$BRANCH" && say "pushed $BRANCH" || say "WARNING: push of $BRANCH failed"

python3 scripts/check_order_town06.py >/dev/null || {
    say "FATAL: R1 still not satisfied after commit. Refusing to drive."; exit 1; }
say "R1 satisfied. The prediction is on the record; driving may begin."

# ---------------------------------------------------------------- 4. drive, 5. compare
carla_start || exit 1
say "running the scored ledger: 8 cells (2 students x 4 conditions), 3 laps each (A-4)"
# A FAILED LEDGER IS NOT A WARNING.
#
# This logged "WARNING: ledger exited nonzero" and carried on to the comparison, which
# then printed a table with no rows, after which the driver announced "DEPLOYMENT TEST
# COMPLETE" and exited 0. Measured 2026-09-02: the ledger died on its FIRST cell with a
# ModuleNotFoundError, zero cells were scored, and the overnight chain reported success.
#
# A study that cannot drive its cells has not completed; it has failed, and the run must
# stop where a person can see it.
if ! bash scripts/run_town06_ledger.sh >>"$LOG_DIR/ledger_run.log" 2>&1; then
    say "FATAL: the scored ledger failed. See ledger_run.log."
    say "  No comparison is printed: a table built from missing cells is not a result."
    exit 1
fi

say "comparing prediction against outcome"
python3 scripts/compare_town06.py 2>&1 | tee -a "$LOG"
say "DEPLOYMENT TEST COMPLETE"

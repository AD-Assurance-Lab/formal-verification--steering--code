#!/usr/bin/env python3
"""Full-repository audit: does every claim still stand against the artifacts on disk?

Run before any release. It checks the things that have actually gone wrong in this study
rather than a generic file list: duplicated registries, stale records, certify/drive
checkpoint mismatches, protocol locks, and whether the shipped models are present.

    python3 scripts/audit_repo.py
"""
import hashlib, json, os, subprocess, sys, glob
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
sys.path.insert(0, "pipeline")
ok, bad = [], []
def chk(c, m): (ok if c else bad).append(m)

def dig(p):
    if not os.path.exists(p): return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()[:16]

# --- locks -------------------------------------------------------------------
chk(subprocess.run([sys.executable, "scripts/check_protocol_lock.py"],
                   capture_output=True).returncode == 0, "PROTOCOL.lock verifies")
chk(subprocess.run([sys.executable, "-m", "carla_determinism", "--lock-only"],
                   capture_output=True).returncode == 0, "carla-determinism RULES.lock verifies")

# --- every shipped model is present and tracked ------------------------------
tracked = set(subprocess.run(["git", "ls-files", "pipeline/checkpoints"],
                             capture_output=True, text=True).stdout.split())
SHIPPED = ["S_clear_84x28", "S_mixed_84x28_w3", "S_clear_84x28_v2",
           "S_mixed_84x28_w3_v2_dagger_r00", "S_clear_t06_168x28_w2",
           "S_mixed_t06_168x28_w3"]
for ck in SHIPPED:
    p = f"pipeline/checkpoints/{ck}.pth"
    chk(os.path.exists(p), f"shipped policy present: {ck}")
    chk(p in tracked, f"shipped policy tracked in git: {ck}")

# --- registries are read from config, not duplicated -------------------------
for f, pat in (("scripts/certify_sustained_bound.py", "STUDENTS = C.STUDENTS"),
               ("scripts/check_student_competence.py", "C.TOWN06_STUDENTS if C.STUDY_MAP")):
    chk(pat in open(f).read(), f"{os.path.basename(f)}: registry read from config (T04-R5)")

# --- certifier and ledger resolve the POLICY ---------------------------------
for f in ("scripts/certify_sustained_bound.py", "scripts/closed_loop_ledger.py"):
    chk("final_student" in open(f).read(),
        f"{os.path.basename(f)}: resolves the policy via final_student (T04-R5)")

# --- per-round CARLA restarts where a loop drives repeatedly -----------------
for f in ("pipeline/dagger.py", "pipeline/dagger_student.py"):
    chk("R-SIM-1" in open(f).read(), f"{os.path.basename(f)}: restarts CARLA per round")

# --- the gate is a rate, and has a min-rounds floor --------------------------
chk("--gate-reps" in open("pipeline/dagger.py").read(), "teacher gate can be a RATE (T06-F24)")
for d in ("scripts/run_town04_pipeline.sh", "scripts/run_town06_pipeline.sh"):
    s = open(d).read()
    chk("--min-rounds" in s and "--gate-reps" in s, f"{os.path.basename(d)}: passes both")

# --- competence records are keyed to the weights they describe ---------------
for p in glob.glob("results/*/competence_clear.json"):
    d = json.load(open(p))
    digs = d.get("checkpoint_digests") or {}
    chk(bool(digs), f"{p}: records checkpoint digests")
    for ck, want in digs.items():
        chk(dig(f"pipeline/checkpoints/{ck}.pth") == want, f"{p}: {ck} digest matches disk")

# --- certificates name checkpoints that exist --------------------------------
for p in glob.glob("results/**/certificate_town06.json", recursive=True):
    meta = json.load(open(p)).get("_meta", {})
    for _, ck in (meta.get("checkpoints") or {}).items():
        chk(os.path.exists(f"pipeline/checkpoints/{ck}.pth"), f"{p}: {ck} present")

# --- ledger cells are complete and name their checkpoint ---------------------
for p in glob.glob("results/**/ledger/*closed_loop.json", recursive=True):
    j = json.load(open(p))
    n = j.get("repetitions") or len(j.get("runs", []))
    chk(n >= 10, f"{os.path.basename(p)}: {n} reps (rule 3 floor is 10)")

# --- no scratch re-committed -------------------------------------------------
scratch = [f for f in subprocess.run(["git", "ls-files", "pipeline/results"],
           capture_output=True, text=True).stdout.split()
           if not any(k in f for k in ("teacher_clear_bc", "oracle_", "reference_routes",
                                       "_bc_training"))]
chk(not scratch, f"no scratch traces tracked ({len(scratch)} found)")

print("PASS:")
for m in ok: print("   ", m)
if bad:
    print("\nFAIL:")
    for m in bad: print("   ", m)
print(f"\n  {len(ok)} passed, {len(bad)} failed")
sys.exit(1 if bad else 0)

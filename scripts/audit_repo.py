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
import config as C  # noqa: E402
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


# --- capture coverage: the defect that motivated these checks ----------------
# A capture that spans a sliver of the route is indistinguishable downstream from one
# that spans all of it: same shapes, clean bound, reproducible certificate. The Town04
# redo certified 160 m of a 2,861 m lap and nothing complained.
import numpy as _np
for cap in glob.glob("results/**/lap_*.npz", recursive=True) + glob.glob("results/**/captures/*.npz", recursive=True):
    if "_superseded" in cap or "marked-for-deletion" in cap:
        continue
    try:
        z = _np.load(cap, allow_pickle=True)
    except Exception:
        continue
    # Measure the pose track; treat route_span_m as a claim to be checked, not a source.
    span = None
    if "pose_x" in z.files:
        x, y = _np.asarray(z["pose_x"], float), _np.asarray(z["pose_y"], float)
        span = float(_np.hypot(_np.diff(x), _np.diff(y)).sum())
    claimed = float(z["route_span_m"]) if "route_span_m" in z.files else None
    if span is not None and claimed is not None:
        chk(abs(claimed - span) <= 25.0,
            f"{os.path.basename(cap)}: recorded span {claimed:.0f} m matches its poses "
            f"({span:.0f} m)")
    if span is None:
        span = claimed
    if span is None:
        continue
    # Compare against what this capture is SUPPOSED to cover, not a magic number:
    # Town06 captures one section per file, Town04 a whole lap. A fixed floor flagged
    # s05 (489 m spanned, 490 m scored) as a sliver, which is the check being wrong
    # rather than the capture.
    stem = os.path.basename(cap)[len("lap_"):].rsplit("_", 1)[0]
    want = None
    if stem in getattr(C, "SECTION_LEN_M", {}):
        want = float(C.SECTION_LEN_M[stem])
    elif stem in ("eastbound", "westbound"):
        try:
            import numpy as _n2
            from route import load_route as _lr
            rt = _n2.asarray(_lr(stem), dtype=float)
            want = float(_n2.linalg.norm(_n2.diff(rt, axis=0), axis=1).sum())
        except Exception:
            want = None
    if want:
        # Two-sided. A one-sided floor catches the 160 m bug and misses its mirror --
        # capturing the whole 3,042 m Town04 loop when the SCORED prefix is 2,861 m,
        # which certifies 181 m of ODD-boundary road the study excludes.
        chk(span >= 0.80 * want,
            f"{os.path.basename(cap)}: spans {span:.0f} m of {want:.0f} m "
            f"({100*span/want:.0f}%)")
        chk(span <= want + 25.0,
            f"{os.path.basename(cap)}: spans {span:.0f} m, within the {want:.0f} m "
            f"scored length")

# --- sibling tools must carry the same guards --------------------------------
# certify_town06 had MIN_POSES_PER_CELL and certify_sustained_bound did not, and the redo
# ran the one without it. An asymmetry between two tools doing the same job is detectable.
cert_a = open("scripts/certify_town06.py").read()
cert_b = open("scripts/certify_sustained_bound.py").read()
for guard in ("MIN_POSES_PER_CELL",):
    chk(guard in cert_a and guard in cert_b,
        f"both certifiers carry {guard} (parity, not one-sided)")
chk("MIN_ROUTE_COVERAGE" in cert_b or "check_coverage" in cert_b,
    "certify_sustained_bound checks route coverage")

# --- a redo's artifacts should be comparable in SIZE to what they replace -----
# The single loudest available signal: the redo's captures were 1.8 MB against the
# published 1.7 GB, and 81 poses against 1,600. Orders of magnitude are worth asserting.
pub = sorted(glob.glob("results/calibration/lap_*_clear.npz"))
redo = sorted(glob.glob("results/town04_v2/calibration/lap_*_clear.npz"))
if pub and redo:
    def poses(p):
        try:
            return int(_np.load(p, allow_pickle=True)["frames"].shape[1])
        except Exception:
            return -1
    pn, rn = poses(pub[0]), poses(redo[0])
    chk(rn >= 0.5 * pn, f"redo captures have {rn} poses against the published {pn}")

# --- stated preconditions must have run --------------------------------------
# The paper states the capture-vs-driven gate as a precondition of certification. It was
# stated and never executed for either rebuild.
for d in ("results/town06", "results/town04_v2/calibration"):
    if glob.glob(os.path.join(d, "**", "*certificate*.json"), recursive=True) or \
       glob.glob(os.path.join(d, "sustained_bound.json")):
        chk(bool(glob.glob(os.path.join(d, "**", "capture_gate.json"), recursive=True)),
            f"{d}: capture gate ran before certification")

print("PASS:")
for m in ok: print("   ", m)
if bad:
    print("\nFAIL:")
    for m in bad: print("   ", m)
print(f"\n  {len(ok)} passed, {len(bad)} failed")
sys.exit(1 if bad else 0)

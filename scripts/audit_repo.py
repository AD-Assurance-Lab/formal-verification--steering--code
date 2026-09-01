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

# --- ledger cells carry a full set of LAPS (PROTOCOL A-4) --------------------
# This asserted ">= 10 repetitions", which A-4 superseded: the lap is the repetition and
# three laps is the standard, because rep-to-rep verdict disagreement measured 0 of 48
# section-pairs on the corrected harness. The check was still enforcing the OLD rule and
# failing correct cells -- the audit contradicting the protocol is the same defect as a
# driver contradicting it, one level up.
#
# What matters now is that a cell holds WHOLE laps: three of them, each with every span.
# A partial lap is not a lap, and a cell short of three is not a cell.
LAPS_REQUIRED = 3
for p in glob.glob("results/**/ledger/*closed_loop.json", recursive=True):
    if "_superseded" in p or "_dependent_runs" in p or "_pre_2988" in p:
        continue
    j = json.load(open(p))
    runs = j.get("runs", [])
    spans = {r.get("direction") for r in runs}
    reps = {r.get("rep") for r in runs}
    whole = [rp for rp in reps
             if {r.get("direction") for r in runs if r.get("rep") == rp} == spans]
    # results/ledger/ is the v1 baseline, collected under the old design and frozen.
    if p.startswith("results/ledger/"):
        continue
    # LAPS ONLY. Runs and spans are implementation detail; reporting them invites the
    # count to be misread as a lap count, which it was. Span-level detail stays in the
    # artifact for when a specific nuance needs it.
    chk(len(whole) >= LAPS_REQUIRED,
        f"{os.path.basename(p)}: {len(whole)} complete laps (A-4 requires "
        f"{LAPS_REQUIRED})")

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
# The parity check was ITSELF one-sided: it required the coverage guard on
# certify_sustained_bound only, and certify_town06 had none at all. A symmetric claim
# has to be asserted symmetrically or it is just the same asymmetry one level up.
for guard in ("MIN_POSES_PER_CELL", "MIN_ROUTE_COVERAGE", "check_coverage"):
    chk(guard in cert_a and guard in cert_b,
        f"both certifiers carry {guard} (parity, not one-sided)")

# --- the CARLA rules must hold at a choke point, not by each caller remembering ---
# R-SIM-1 and standing rule 5 lived in prose and were re-typed into each new driver, so
# they drifted the moment a driver was added: require_deterministic() was called only in
# evaluate.py and only under `if STUDY_MAP == "Town06"`, and the fidelity driver restarted
# nothing at all. Both now sit in the path every measurement takes.
_env = open("pipeline/carla_env.py").read()
chk("require_deterministic" in _env.split("def enable_sync_mode")[1][:2000],
    "enable_sync_mode asserts the determinism rules, for every map")
chk("require_clean_world" in _env.split("def spawn_vehicle")[1][:400],
    "spawn_vehicle refuses a world holding another run's actors")
chk("signal.signal" in open("scripts/capture_offset_yaw.py").read(),
    "capture_offset_yaw destroys its actors on SIGTERM (a killed run must not leak)")

# Nobody may hand-roll sync mode: it provisions substepping, and a partial copy runs
# partial physics per tick while looking fine.
_rogue = [f for f in glob.glob("pipeline/*.py") + glob.glob("scripts/*.py")
          if f not in ("pipeline/carla_env.py", "scripts/audit_repo.py")
          and "synchronous_mode =" in open(f).read()]
chk(not _rogue, f"sync mode only via env.enable_sync_mode (rogue: {_rogue})")

# Every driver that MEASURES must restart the server first (R-SIM-1).
for _d in ("scripts/capture_town04_laps.sh", "scripts/capture_town06_laps.sh",
           "scripts/capture_interp_fidelity.sh", "scripts/capture_gate_drives.py",
           "scripts/run_town06_ledger.sh", "scripts/run_town04_ledger.sh"):
    if os.path.exists(_d):
        chk("carla_restart" in open(_d).read(),
            f"{os.path.basename(_d)} restarts CARLA before measuring (R-SIM-1)")

# --- a driver that writes REDO artifacts must run under REDO config -------------
# capture_town04_laps.sh wrote into results/town04_v2/ while exporting only STUDY_MAP, so
# it captured with the PUBLISHED constants. Invisible while the two configs agreed; the
# moment LAP_END_M diverged it silently captured the wrong extent into the redo's
# directory. A path and a config that disagree is a defect whatever the values happen to be.
for _d in glob.glob("scripts/*.sh") + glob.glob("scripts/*.py"):
    _t = open(_d).read()
    if "town04_v2" in _t and "STUDY_MAP=Town04" in _t:
        chk("TOWN04_REDO=1" in _t or "TOWN04_REDO" in _t,
            f"{os.path.basename(_d)} writes town04_v2 and sets TOWN04_REDO")

# --- anything that can be killed must clean up, or it wedges the server ---------
# R-SIM-2. Python's default SIGTERM exits without unwinding, so `finally` never runs and
# the world is left in synchronous mode with nothing ticking. A tool MEANT to be killed
# (an inspector) is the most likely offender, and it wedged the server once.
for _d in ("scripts/inspect_lap_bounds.py", "scripts/capture_offset_yaw.py"):
    if os.path.exists(_d):
        _t = open(_d).read()
        chk("install_cleanup_handlers" in _t or "signal.signal" in _t,
            f"{os.path.basename(_d)} cleans up on SIGTERM (R-SIM-2)")

# --- the ledger drivers must drive the LAP COUNT the protocol states -----------
# A-4 sets three laps. The drivers had SIX (Town04) and TWO (Town06), both hardcoded
# alongside a hardcoded --expect 12 from the older "12 runs per cell" framing. A results
# format stated in the protocol and contradicted by the script is not a format.
for _drv, _mult in (("scripts/run_town04_ledger.sh", "LAPS*2"),
                    ("scripts/run_town06_ledger.sh", "LAPS*NSEC")):
    if os.path.exists(_drv):
        _t = open(_drv).read()
        chk("LAPS=${LAPS:-3}" in _t, f"{os.path.basename(_drv)} drives 3 laps (A-4)")
        chk(_mult in _t,
            f"{os.path.basename(_drv)} expects laps x spans, not a hardcoded run count")

# --- ledger cells must come from INDEPENDENT runs -----------------------------
# The ledger restarted per CELL and spawned the vehicle once for all twelve runs, so the
# runs were two chains of six that inherited each other's physics state on an ageing
# server. A failure rate over dependent trials is not a rate, and the Wilson interval
# assumes independence. Cells written under the old regime carry neither key.
# results/ledger/ is the PUBLISHED study's frozen record and is not rebuilt -- it is the
# baseline the redo is compared against, so it stays as it was collected.
_led = [f for f in glob.glob("results/*/ledger/*.json")
        if f.startswith(("results/town06/", "results/town04_v2/"))]
_dep = []
for _c in _led:
    if "_superseded" in _c:
        continue
    try:
        _p = json.load(open(_c)).get("provenance", {})
    except ValueError:
        continue
    if _p.get("restart_granularity") != "per_run":
        _dep.append(os.path.basename(_c))
chk(not _dep, f"every ledger cell came from independent runs "
              f"({len(_dep)} predate the fix: {_dep[:3]})")

# --- PPC bridges must be driven by the expert AND excluded from scoring ---------
# Town06's lap crosses intersections where a lane-follower has no lane to follow. The
# expert drives those spans; scoring them would score the expert, and would compare a
# verdict against road the certificate does not cover -- the same scope mismatch that
# put half of Town04's ledger runs beyond the scored prefix.
# EVERY loop that drives a POLICY must bridge -- including the ones that TRAIN it.
# evaluate and the ledger bridged; dagger.py did not, so the teacher was asked to drive
# an intersection a lane-follower cannot drive and failed at 62 ft, every attempt, at the
# same step. Enumerating the loops that "measure" missed the loop that builds.
for _f in ("pipeline/evaluate.py", "scripts/closed_loop_ledger.py", "pipeline/dagger.py",
           "pipeline/dagger_student.py"):
    if not os.path.exists(_f):
        continue
    _t = open(_f).read()
    chk("BRIDGE_SPANS" in _t and "in_bridge" in _t,
        f"{os.path.basename(_f)} hands bridges to pure pursuit")
chk("not r.get(\"bridged\")" in open("pipeline/evaluate.py").read(),
    "evaluate excludes bridged steps from the score")
chk("not in_bridge" in open("scripts/closed_loop_ledger.py").read(),
    "closed_loop_ledger excludes bridged steps from the score")

# --- the GPU must be waited for, not raced -------------------------------------
# Restarting before EVERY run (R-SIM-1 at run granularity) means the client's CUDA init
# races CARLA's GPU startup once per run instead of once per cell. torch dies with
# "CUDA-capable device(s) is/are busy or unavailable" and the run is lost.
# `device = "cuda" if torch.cuda.is_available() else "cpu"` reads like portability and
# is a silent-failure switch: while CARLA initialises on the same device the flag is
# False, so the run continues ON THE CPU and says nothing. Caught when a Town06 policy
# drive printed "CUDA unknown error" and then drove the whole lap anyway.
for _f in ("pipeline/evaluate.py", "pipeline/dagger.py", "pipeline/dagger_student.py",
           "scripts/closed_loop_ledger.py"):
    _t = open(_f).read()
    chk('torch.cuda.is_available() else "cpu"' not in _t,
        f"{os.path.basename(_f)} does not fall back to the CPU silently")
    chk("require_cuda" in _t, f"{os.path.basename(_f)} waits for the GPU")

# --- a certificate must state the extent it covers -----------------------------
# It recorded nsplit, stride and tolerance but not which road the bounds cover -- and the
# extent is what moved underneath it. A certificate that cannot say what it covers cannot
# be checked against drives whose coverage also moved.
for _cert in ("results/town04_v2/calibration/sustained_bound.json",):
    if os.path.exists(_cert):
        try:
            _m = json.load(open(_cert)).get("_meta", {})
            chk(_m.get("lap_end_m") is not None,
                f"{os.path.basename(_cert)} records the scored extent it covers")
        except ValueError:
            pass

# --- a certificate must have scored every cell it expected ---------------------
# certify_sustained_bound WARNS when a cell does not run and still writes the file; a
# warning in a long log is not a guard. Both certifiers record the two counts, so the
# comparison is available and is asserted here.
for _cert in ("results/town06/certificate_town06.json",
              "results/town04_v2/calibration/sustained_bound.json"):
    if os.path.exists(_cert):
        try:
            _m = json.load(open(_cert)).get("_meta", {}) or json.load(open(_cert))
            _exp, _got = _m.get("cells_expected"), _m.get("cells_scored")
            if _exp is not None and _got is not None:
                chk(_exp == _got,
                    f"{os.path.basename(_cert)}: scored {_got} of {_exp} expected cells")
        except (ValueError, KeyError):
            pass

# --- every scored measurement needs a COMMITTED driver (standing rule 8) -------
# Town06 had run_town06_ledger.sh and Town04 had nothing, so its ledger was hand-driven
# and its restart discipline is unprovable after the fact. The asymmetry between the two
# maps' tooling is what the 160 m defect exploited.
for _pair in (("scripts/capture_town06_laps.sh", "scripts/capture_town04_laps.sh"),
              ("scripts/run_town06_ledger.sh", "scripts/run_town04_ledger.sh")):
    chk(all(os.path.exists(x) for x in _pair),
        f"both maps have a committed driver: {' / '.join(os.path.basename(x) for x in _pair)}")

# --- the guards must be DEMONSTRATED to refuse, not just present ---------------
# Every guard written for the 160 m defect had a defect of its own, and grepping for the
# guard's name would have passed all three. Presence is not force.
_t = subprocess.run([sys.executable, "tests/test_scope_guards.py"],
                    capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(
                        os.path.abspath(__file__))))
chk(_t.returncode == 0, "scope guards demonstrably refuse short, over-long and "
                        "self-contradicting captures (tests/test_scope_guards.py)")

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

"""The gate that decides which model ships must record the harness it measured on.

WHY THIS EXISTS. `S_mixed_t06lap_168x56_w4_s0` scored 11.45 ft on fog on 2026-09-02 and
1.48 ft on fog on 2026-09-03 -- the SAME checkpoint file, byte-identical, with no change
to the route file, to config, or to any driving code between the two (the only commit
touching a driving-path file added `scored_span_m`, which is not called while driving).

That disagreement could not be attributed, because the entire artifact behind the
rejection was:

    {"weather": "fog", "reps": 1, "budget_ft": 2.19, "results": {"...": [
      {"max_cte_ft": 11.45, "steps": 1178, "passed": false, "rep": 0, "sec": 29.6}]}}

No server command line, no determinism state, no git SHA, not even a timestamp. The
scored ledger records all of it; the selection gate recorded none of it -- and the
selection gate is what chose the model the study then certified and drove.

D-11 says data collected under a violating harness is not reusable. That is only
enforceable if the data says which harness it ran under.

Second defect pinned here: `restart_carla()` called subprocess.run with no `check=` and
never read the returncode, so a restart that printed "FATAL: CARLA did not come up" and
exited non-zero was indistinguishable from one that worked, and the lap was driven
anyway. The restart log carries five such failures.

No CARLA and no GPU: provenance is built from config, git and an absent-server lookup.
"""
import ast
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(REPO, "scripts", "compare_student_variants.py")

REQUIRED = ("run_started", "git_sha", "git_dirty", "determinism", "weather", "map")
REQUIRED_DET = ("deterministic_control", "server_cmdline", "notexturestreaming",
                "quality_level")


def _provenance():
    """Call lap_provenance() in a fresh interpreter and return it as JSON."""
    code = (
        "import sys, json;"
        f"sys.path.insert(0, {os.path.join(REPO, 'pipeline')!r});"
        f"sys.path.insert(0, {os.path.join(REPO, 'scripts')!r});"
        "import importlib.util as u;"
        f"spec = u.spec_from_file_location('gate', {GATE!r});"
        "m = u.module_from_spec(spec); spec.loader.exec_module(m);"
        "print(json.dumps(m.lap_provenance('clear'), default=str))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=dict(os.environ, STUDY_MAP="Town06"), cwd=REPO, timeout=180)
    if out.returncode != 0:
        pytest.skip(f"gate will not import here: {out.stderr.strip()[-300:]}")
    import json
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_gate_records_a_provenance_block():
    prov = _provenance()
    for k in REQUIRED:
        assert k in prov, f"selection-gate provenance is missing {k!r}"


def test_gate_records_the_determinism_harness():
    det = _provenance()["determinism"]
    for k in REQUIRED_DET:
        assert k in det, f"selection-gate determinism block is missing {k!r}"


def test_absent_server_is_unknown_not_absent():
    """With no server up, flags must be None -- never False.

    Recording notexturestreaming=False because the lookup returned nothing describes a
    D-3 violation that did not happen, and it would later be read as evidence that one
    did. "Unknown" and "absent" are different facts.
    """
    det = _provenance()["determinism"]
    if det.get("server_cmdline"):
        pytest.skip("a CARLA server is running; this checks the absent-server path")
    assert det["notexturestreaming"] is None
    assert det["quality_level"] is None


def test_restart_failure_is_checked_not_ignored():
    """restart_carla must inspect the exit status and return a boolean."""
    src = open(GATE).read()
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "restart_carla"), None)
    assert fn is not None, "restart_carla is gone"
    body = ast.get_source_segment(src, fn) or ""
    assert "returncode" in body, (
        "restart_carla does not read the restart's exit status; a failed restart would "
        "be driven through, which is how a student gets rejected by the simulator "
        "rather than by its own behaviour")
    assert any(isinstance(n, ast.Return) and n.value is not None
               for n in ast.walk(fn)), "restart_carla returns nothing to check"


def test_measurement_loop_refuses_after_a_failed_restart():
    src = open(GATE).read()
    assert "if not restart_carla(log)" in src, (
        "the lap loop does not act on a failed restart")
    assert "restart_failed" in src, (
        "a lap skipped for a failed restart is not marked as such in the artifact")


def test_sweep_artifacts_can_be_written_somewhere_else():
    """A new sweep of an old checkpoint must not overwrite the old sweep's record.

    The 11.45 ft screen that rejected w4_s0 was overwritten in place by a later sweep of
    the same checkpoint, and survived only because it happened to be tracked in git.
    """
    src = open(os.path.join(REPO, "scripts/select_student_seed.sh")).read()
    assert "OUT_DIR=${OUT_DIR:-results/town06}" in src
    assert '"$REPO/$OUT_DIR/seed_screen_' in src
    assert '"$REPO/$OUT_DIR/seed_gate_' in src
    p3 = open(os.path.join(REPO, "scripts/pass3_sweep_widths.sh")).read()
    assert 'OUT_DIR="results/town06/pass3"' in p3, (
        "pass 3 would write over the historical selection artifacts")


# --- an UNMEASURED lap must never read as a model verdict --------------------------

def test_unmeasured_lap_exits_distinctly():
    """compare_student_variants must exit 3 when a lap could not be measured.

    An unmeasured lap is not a failing lap. The sweep counts laps under a threshold
    against the EXPECTED count, so an unmeasured lap made a seed look rejected -- and it
    did: S_mixed_t06lap_168x56_w4_s3, the SHIPPED student, was "rejected at the screen"
    because one restart failed and its night lap was never driven. The restart-status fix
    stopped the bad DATA and not the bad VERDICT; this is the other half.
    """
    src = open(GATE).read()
    assert "return 3" in src, "no distinct exit for an unmeasured lap"
    assert "unmeasured" in src, "unmeasured laps are not counted"


def test_sweep_aborts_on_an_unmeasured_lap():
    """The sweep must STOP, not reject the seed, when the harness cannot produce a lap."""
    src = open(os.path.join(REPO, "scripts/select_student_seed.sh")).read()
    assert src.count("eq 3") >= 2, (
        "select_student_seed.sh does not check the unmeasured-lap exit code at both the "
        "screen and the gate")
    assert "Refusing to score any seed against a harness" in src


def test_width_sweep_does_not_call_a_harness_abort_a_width_result():
    src = open(os.path.join(REPO, "scripts/pass3_sweep_widths.sh")).read()
    assert "RC -eq 2" in src, "pass3 sweep treats a harness abort as 'no seed passed'"
    assert "NOT a width result" in src


def test_gate_uses_the_one_retry_policy():
    """A boot that misses its window is a certainty over a stage, not a risk.

    carla_restart_retry.sh is 'THE one place that decides how many times' (5c8b340).
    Calling carla_restart.sh directly here made a slow boot into a failed lap, and four
    copies of a retry policy is how they drift.
    """
    src = open(GATE).read()
    assert "carla_restart_retry.sh" in src, (
        "the selection gate does not use the shared retry policy")

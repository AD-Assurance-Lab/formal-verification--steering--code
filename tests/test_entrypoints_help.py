"""`--help` must never drive, restart CARLA, or touch a result.

audit_repo.py probes every CARLA entry point with `--help` to prove it imports cleanly as
its own process. That probe is only safe if the script PARSES arguments.

`capture_gate_drives.py` had no argparse at all. `--help` fell straight through into the
body, which restarts CARLA and drives a lap per student per section -- so running the
audit while a server happened to be up made the audit itself restart the simulator and
begin driving, violating R-SIM-3 (one client per port) from inside the tool whose job is
to check the repo is sound. It passed for months because the audit was normally run with
no server listening: the port guard returned 2 immediately and the check went green.

The behaviour of the audit depended on whether CARLA happened to be running. That is the
bug, and a green check is exactly what it looked like.

These tests need no CARLA and no GPU: `--help` must exit fast and print usage.
"""
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The entry points audit_repo.py probes with --help, plus the other committed drivers
# that take arguments. Any script here that reaches its body on --help is the defect.
ENTRYPOINTS = [
    "scripts/closed_loop_ledger.py",
    "scripts/gate_teacher_lap.py",
    "scripts/certify_town06.py",
    "scripts/check_student_competence.py",
    "scripts/compare_student_variants.py",
    "scripts/capture_gate_drives.py",
    "scripts/capture_driven_gate.py",
    "scripts/compare_town06.py",
    "scripts/score_scopes.py",
    "scripts/scored_scope.py",
    "scripts/falsify_witness.py",
]


@pytest.mark.parametrize("entry", ENTRYPOINTS)
def test_help_is_fast_and_side_effect_free(entry):
    """--help exits 0 with usage, within a budget no real drive could meet.

    The timeout is the assertion. A script that starts driving cannot answer in 60 s;
    one that parses arguments answers in about one.
    """
    path = os.path.join(REPO, entry)
    if not os.path.exists(path):
        pytest.skip(f"{entry} not present")
    try:
        p = subprocess.run([sys.executable, path, "--help"], capture_output=True,
                           text=True, timeout=60, cwd=REPO,
                           env=dict(os.environ, STUDY_MAP="Town06"))
    except subprocess.TimeoutExpired:
        pytest.fail(f"{entry} --help did not return in 60 s: it is running its body, "
                    f"not parsing arguments. This is how the audit came to restart CARLA.")
    assert p.returncode == 0, f"{entry} --help exited {p.returncode}\n{p.stderr[-400:]}"
    assert "usage:" in (p.stdout + p.stderr).lower(), (
        f"{entry} --help printed no usage line; it may not parse arguments at all")


@pytest.mark.parametrize("entry", ENTRYPOINTS)
def test_entrypoint_imports_cleanly(entry):
    """The check audit_repo.py is actually making, kept here so it runs in CI too."""
    path = os.path.join(REPO, entry)
    if not os.path.exists(path):
        pytest.skip(f"{entry} not present")
    try:
        p = subprocess.run([sys.executable, path, "--help"], capture_output=True,
                           text=True, timeout=60, cwd=REPO,
                           env=dict(os.environ, STUDY_MAP="Town06"))
    except subprocess.TimeoutExpired:
        pytest.fail(f"{entry} --help hung")
    blob = p.stdout + p.stderr
    assert "ModuleNotFoundError" not in blob and "ImportError" not in blob, blob[-400:]

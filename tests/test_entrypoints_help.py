"""`--help` must never drive, restart CARLA, or touch a result.

audit_repo.py probes every CARLA entry point with `--help` to prove it imports cleanly as
its own process. That probe is only safe if the script PARSES arguments.

`capture_gate_drives.py` had no argparse at all. `--help` fell straight through into the
body, which restarts CARLA and drives a lap per student per section -- so running the
audit while a server happened to be up made the audit itself restart the simulator and
begin driving, violating one client per port (one client per port) from inside the tool whose job is
to check the repo is sound. It passed for months because the audit was normally run with
no server listening: the port guard returned 2 immediately and the check went green.

The behaviour of the audit depended on whether CARLA happened to be running. That is the
bug, and a green check is exactly what it looked like.

These tests need no CARLA and no GPU: `--help` must exit fast and print usage.
"""
import ast
import os
import subprocess
import sys

import pytest

from conftest import skip_if_missing_dependency

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The entry points audit_repo.py probes with --help, plus the other committed drivers
# that take arguments. Any script here that reaches its body on --help is the defect.
ENTRYPOINTS = [
    "scripts/drive/closed_loop_ledger.py",
    "scripts/training/gate_teacher_lap.py",
    "scripts/verify/certify_town06.py",
    "scripts/training/check_student_competence.py",
    "scripts/capture/capture_gate_drives.py",
    "scripts/capture/capture_driven_gate.py",
    "scripts/verify/compare_town06.py",
    "scripts/verify/score_scopes.py",
    "scripts/verify/falsify_witness.py",
    "scripts/training/audit_training_data.py",
    "scripts/fetch_captures.py",
    "scripts/verify/interpolation_fidelity.py",
    "scripts/drive/aggregate_ledger_runs.py",
    "scripts/drive/report_laps.py",
    "scripts/verify/q8c_varying_witness.py",
    "scripts/capture/capture_offset_yaw.py",
    "scripts/verify/certify_sustained_bound.py",
    "scripts/training/train.py",
    "scripts/training/distill.py",
    "scripts/training/dagger.py",
    "scripts/training/dagger_student.py",
    "scripts/training/collect_data.py",
    "scripts/drive/drive_expert.py",
    "scripts/training/evaluate.py",
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
    if p.returncode != 0:
        skip_if_missing_dependency(entry, p.stderr)
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
    skip_if_missing_dependency(entry, blob)
    assert "ModuleNotFoundError" not in blob and "ImportError" not in blob, blob[-400:]


# --- the device must be required AFTER the arguments are parsed -------------------
# require_cuda retries for two minutes before it gives up, by design: CARLA holds the
# device while it starts, so a short wait would reject a machine that is merely busy.
# That makes calling it above the argument parser a two-minute `--help` on any machine
# without a GPU -- which is every machine a reader is checking this work on.
# interpolation_fidelity.py did exactly that.
#
# The order that matters is the order INSIDE main(), not in the file: train.py and
# distill.py both call require_cuda from a helper defined near the top and invoked
# after parsing, which a text-position check reads as a defect.
GPU_ENTRYPOINTS = [e for e in ENTRYPOINTS if e.endswith(".py")]


def _first_call_lines(fn, names):
    """Line number of the first call to each name anywhere inside `fn`."""
    seen = {}
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            f = node.func
            name = getattr(f, "id", None) or getattr(f, "attr", None)
            if name in names and name not in seen:
                seen[name] = node.lineno
    return seen


@pytest.mark.parametrize("entry", GPU_ENTRYPOINTS)
def test_arguments_are_parsed_before_the_gpu_is_required(entry):
    path = os.path.join(REPO, entry)
    if not os.path.exists(path):
        pytest.skip(f"{entry} not present")
    with open(path) as f:
        tree = ast.parse(f.read())
    mains = [n for n in tree.body
             if isinstance(n, ast.FunctionDef) and n.name == "main"]
    if not mains:
        pytest.skip(f"{entry} has no main()")
    at = _first_call_lines(mains[0], {"parse_args", "require_cuda"})
    if "require_cuda" not in at or "parse_args" not in at:
        pytest.skip(f"{entry} does not do both in main()")
    assert at["parse_args"] < at["require_cuda"], (
        f"{entry} calls require_cuda() at line {at['require_cuda']}, before parse_args() "
        f"at line {at['parse_args']}, so --help waits two minutes for a GPU it does "
        f"not need")

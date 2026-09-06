"""A pass must never be able to write into another pass's ledger.

PROTOCOL R4 requires pass 1 -- the blind Town06 deployment test -- to stand in the record.
A-5 adds pass 2, which drives the same cells again.

The near-miss this pins: `run_town06_ledger.sh` decides whether to SKIP a cell by looking
at `D.LEDGER_SUBDIR`, while `closed_loop_ledger.py` decided where to WRITE from a path
spelled literally in its own source. With TOWN06_PASS=2 the guard checked an empty
`ledger_pass2/`, found nothing, and would have driven all 24 laps -- every one of which
the writer would have dropped into `ledger/`, overwriting the blind result. The guard and
the writer must resolve the same definition, and nothing but a test keeps them together.

No CARLA and no models: this is path resolution only.
"""
import os
import subprocess
import sys

import pytest

from conftest import skip_if_missing_dependency

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ledger_for(pass_n):
    """Resolve closed_loop_ledger.LEDGER in a FRESH interpreter.

    A subprocess, not importlib.reload: the module imports carla and torch at module
    scope, and the design module caches TOWN06_PASS at import time, so reloading inside
    one process would read whichever value happened to be set first.
    """
    code = (
        "import sys;"
        f"sys.path.insert(0, {REPO!r});"

        f"sys.path.insert(0, {os.path.join(REPO, 'scripts', 'drive')!r});"
        "from closed_loop_ledger import LEDGER;print(LEDGER)"
    )
    env = dict(os.environ, STUDY_MAP="Town06", TOWN06_PASS=str(pass_n))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=env, cwd=REPO)
    if out.returncode != 0:
        # NOT a skip. This test exists to pin which directory a ledger pass writes to,
        # and a module that will not import is exactly how that pin stops being checked
        # while the suite still reads green.
        skip_if_missing_dependency("closed_loop_ledger", out.stderr)
        raise AssertionError(f"the ledger module will not import: {out.stderr[-400:]}")
    return out.stdout.strip().splitlines()[-1]


def _design_for(pass_n):
    code = (f"import sys;sys.path.insert(0, {REPO!r});"
            "from steering.study import town06_design as D;print(D.LEDGER_SUBDIR)")
    env = dict(os.environ, STUDY_MAP="Town06", TOWN06_PASS=str(pass_n))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=env, cwd=REPO)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip().splitlines()[-1]


def test_writer_and_guard_agree_for_every_pass():
    """The path the ledger WRITES must be the path the design module DECLARES."""
    for p in (1, 2):
        assert _ledger_for(p).endswith(_design_for(p)), (
            f"pass {p}: writer and guard disagree -- this is how pass 2 overwrites pass 1")


def test_passes_are_distinct():
    assert _design_for(1) != _design_for(2)
    assert _ledger_for(1) != _ledger_for(2)


def test_pass_1_is_still_the_unsuffixed_directory():
    """Pass 1's committed artifacts live at results/arterial/ledger and must not move."""
    assert _design_for(1) == os.path.join("results", "arterial", "ledger")


def test_an_unknown_pass_refuses():
    code = (f"import sys;sys.path.insert(0, {REPO!r});"
            "from steering.study import town06_design as D;print(D.LEDGER_SUBDIR)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=dict(os.environ, STUDY_MAP="Town06", TOWN06_PASS="7"),
                         cwd=REPO)
    assert out.returncode != 0, "an unrecognised pass silently picked a directory"


def test_pass_2_predicts_with_both_certificates():
    """A-5: pass 2 scores both scopes, so R1 must cover both bounds."""
    code = (f"import sys;sys.path.insert(0, {REPO!r});"
            "from steering.study import town06_design as D;print('|'.join(D.CERT_ARTIFACTS))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=dict(os.environ, STUDY_MAP="Town06", TOWN06_PASS="2"),
                         cwd=REPO)
    assert out.returncode == 0, out.stderr
    arts = out.stdout.strip().splitlines()[-1].split("|")
    assert len(arts) == 2 and any("capped" in a for a in arts)
def test_pass3_gate_would_reject_the_shipped_student():
    """The pre-registered criterion is strict enough to matter, checked against the
    shipped student's own committed gate artifacts rather than asserted."""
    import glob
    import json
    code = ("import sys;"
            "import steering.config as C;print(C.CTE_BUDGET_FT, C.TOWN06_PASS3_GATE_MARGIN)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=dict(os.environ, STUDY_MAP="Town06"), cwd=REPO)
    bud, margin = (float(x) for x in out.stdout.split()[-2:])
    thr = bud * margin
    files = sorted(glob.glob(os.path.join(
        REPO, "results/arterial/seed_gate_S_mixed_t06lap_168x56_w4_s3_*.json")))
    if not files:
        pytest.skip("shipped student's gate artifacts not present")
    worst = 0.0
    for f in files:
        d = json.load(open(f))
        worst = max(worst, max(l["max_cte_ft"]
                               for l in list(d["results"].values())[0]))
    assert worst > thr, (
        f"the pass-3 gate ({thr:.3f} ft) would ADMIT the shipped student "
        f"(worst {worst:.2f} ft). It was chosen to exclude it; if this passes, the "
        f"criterion no longer does what the pre-registration says it does.")

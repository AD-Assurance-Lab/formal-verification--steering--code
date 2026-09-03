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
import importlib
import os
import subprocess
import sys

import pytest

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
        f"sys.path.insert(0, {os.path.join(REPO, 'pipeline')!r});"
        f"sys.path.insert(0, {os.path.join(REPO, 'scripts')!r});"
        "from closed_loop_ledger import LEDGER;print(LEDGER)"
    )
    env = dict(os.environ, STUDY_MAP="Town06", TOWN06_PASS=str(pass_n))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=env, cwd=REPO)
    if out.returncode != 0:
        pytest.skip(f"ledger module will not import here: {out.stderr.strip()[-200:]}")
    return out.stdout.strip().splitlines()[-1]


def _design_for(pass_n):
    code = (f"import sys;sys.path.insert(0, {REPO!r});"
            "from study import town06_design as D;print(D.LEDGER_SUBDIR)")
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
    """Pass 1's committed artifacts live at results/town06/ledger and must not move."""
    assert _design_for(1) == os.path.join("results", "town06", "ledger")


def test_an_unknown_pass_refuses():
    code = (f"import sys;sys.path.insert(0, {REPO!r});"
            "from study import town06_design as D;print(D.LEDGER_SUBDIR)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=dict(os.environ, STUDY_MAP="Town06", TOWN06_PASS="7"),
                         cwd=REPO)
    assert out.returncode != 0, "an unrecognised pass silently picked a directory"


def test_pass_2_predicts_with_both_certificates():
    """A-5: pass 2 scores both scopes, so R1 must cover both bounds."""
    code = (f"import sys;sys.path.insert(0, {REPO!r});"
            "from study import town06_design as D;print('|'.join(D.CERT_ARTIFACTS))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=dict(os.environ, STUDY_MAP="Town06", TOWN06_PASS="2"),
                         cwd=REPO)
    assert out.returncode == 0, out.stderr
    arts = out.stdout.strip().splitlines()[-1].split("|")
    assert len(arts) == 2 and any("capped" in a for a in arts)


# --- pass 3: the width sweep must not disturb what passes 1 and 2 resolve to ----------

def test_pass3_pins_are_a_separate_namespace():
    """Re-sweeping w4 for pass 3 must not overwrite the pin passes 1 and 2 resolve through.

    select_student_seed.sh writes `<PIN_CK>.selected` and PIN_CK defaults to CK. Pass 3
    re-sweeps the SAME sweep base (so it can reuse w4_s0..s3 rather than re-distilling)
    but must pin under its own name, or the winner would silently become the model the
    committed pass-1 and pass-2 results refer to.
    """
    code = (f"import sys;sys.path.insert(0, {os.path.join(REPO, 'pipeline')!r});"
            "import config as C;"
            "print('|'.join(f'{sw}>{pin}' for _,sw,pin,_,_ in C.TOWN06_PASS3_WIDTHS));"
            "print('|'.join(b for _,b,_,_ in C.TOWN06_STUDENTS))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=dict(os.environ, STUDY_MAP="Town06"), cwd=REPO)
    assert out.returncode == 0, out.stderr
    pairs, shipped = out.stdout.strip().splitlines()[-2:]
    shipped = set(shipped.split("|"))
    for pair in pairs.split("|"):
        sweep, pin = pair.split(">")
        assert pin != sweep, f"pass 3 pins under its sweep base {sweep!r}"
        assert pin not in shipped, (
            f"pass-3 pin {pin!r} collides with a pass-1/2 student base; the sweep would "
            f"overwrite the pin those committed results resolve through")


def test_pass3_sweep_never_promotes_over_the_shipped_checkpoint():
    """The driver must pass PROMOTE=0, or the winner overwrites <base>.pth in place."""
    src = open(os.path.join(REPO, "scripts/pass3_sweep_widths.sh")).read()
    assert "PROMOTE=0" in src, "pass3 sweep would overwrite the shipped base checkpoint"
    assert "PIN_CK=" in src, "pass3 sweep does not set a separate pin namespace"


def test_sweep_default_margin_is_unchanged_behaviour():
    """MARGIN_FRAC defaults to 1.0 so passes 1 and 2 remain reproducible."""
    src = open(os.path.join(REPO, "scripts/select_student_seed.sh")).read()
    assert "MARGIN_FRAC=${MARGIN_FRAC:-1.0}" in src
    assert "SCREEN_FRAC=${SCREEN_FRAC:-1.0}" in src
    assert "PROMOTE=${PROMOTE:-1}" in src
    assert "PIN_CK=${PIN_CK:-$CK}" in src


def test_pass3_gate_would_reject_the_shipped_student():
    """The pre-registered criterion is strict enough to matter, checked against the
    shipped student's own committed gate artifacts rather than asserted."""
    import glob, json
    code = (f"import sys;sys.path.insert(0, {os.path.join(REPO, 'pipeline')!r});"
            "import config as C;print(C.CTE_BUDGET_FT, C.TOWN06_PASS3_GATE_MARGIN)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=dict(os.environ, STUDY_MAP="Town06"), cwd=REPO)
    bud, margin = (float(x) for x in out.stdout.split()[-2:])
    thr = bud * margin
    files = sorted(glob.glob(os.path.join(
        REPO, "results/town06/seed_gate_S_mixed_t06lap_168x56_w4_s3_*.json")))
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

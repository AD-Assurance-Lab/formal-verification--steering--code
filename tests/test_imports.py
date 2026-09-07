"""Every module must import as its own process, on both maps.

An import error in a training or capture script cannot be caught by any other test
here: those paths need CARLA and a GPU, so they are exercised on the lab machine and
nowhere else. A refactor that breaks one of them is therefore invisible until someone
tries to rebuild the study, which is months later and on someone else's clone.

Importing is cheap and catches the whole class. Every module below either guards its
body behind `if __name__ == "__main__"` or is a library, so importing one runs no
drive, touches no result and starts no server -- and a module that stops being true
fails this test by timing out, which is the second thing worth knowing.

Two files are excluded and they are excluded because they run on import by design:
audit_repo.py IS its own check, and check_gpu_usable.py probes the card.
"""
import os
import subprocess
import sys

import pytest

from conftest import skip_if_missing_dependency

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_ON_IMPORT = {"scripts/audit_repo.py", "scripts/simulator/check_gpu_usable.py"}


def _modules():
    out = subprocess.run(["git", "ls-files", "scripts/**/*.py", "scripts/*.py", "src/steering/**/*.py",
                          "src/steering/*.py", "src/steering/study/*.py"],
                         capture_output=True, text=True, cwd=REPO).stdout.split()
    return sorted(f for f in out
                  if f not in RUN_ON_IMPORT and not f.endswith("__init__.py"))


@pytest.mark.parametrize("mod", _modules())
@pytest.mark.parametrize("study_map", ["Town04", "Town06"])
def test_module_imports(mod, study_map):
    """Import it, do not run it. A timeout means the body is no longer guarded."""
    path = os.path.join(REPO, mod)
    # Put the script's own directory on the path, which is what running it does.
    # scripts/training/dagger.py imports its neighbour `train` that way.
    code = ("import importlib.util, sys, os; "
            f"os.chdir({REPO!r}); "
            f"sys.path.insert(0, os.path.dirname({path!r})); "
            f"spec = importlib.util.spec_from_file_location('_probe', {path!r}); "
            "m = importlib.util.module_from_spec(spec); "
            "spec.loader.exec_module(m)")
    try:
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                           timeout=120, cwd=REPO,
                           env=dict(os.environ, STUDY_MAP=study_map))
    except subprocess.TimeoutExpired:
        pytest.fail(f"{mod} did not finish importing in 120 s under STUDY_MAP="
                    f"{study_map}: its body is running at import time.")
    if p.returncode != 0:
        skip_if_missing_dependency(mod, p.stderr)
    assert p.returncode == 0, (f"{mod} fails to import under STUDY_MAP={study_map}\n"
                               f"{p.stderr[-1200:]}")

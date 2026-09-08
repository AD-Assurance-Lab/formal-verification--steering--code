"""Every entry point must agree with the package about where the repository is.

This is the check that was missing. When scripts/ was grouped into folders, all
nineteen entry points kept computing the root by counting two directories up from
their own file, which now lands on <repo>/scripts. They then looked for the study's
artifacts under scripts/results/, found nothing, and said so in words that blamed
the data: "REFUSING: no clear-weather competence record" for a record that is
present and tracked.

Nothing caught it. The test suite only ever ran entry points as far as --help, and
--help does not touch a path. So the rule is now asserted directly: whatever an
entry point calls its repository root, it must equal steering.REPO_ROOT.
"""
import os
import re
import subprocess
import sys

import pytest

from steering import REPO_ROOT

REPO = REPO_ROOT
ENTRY_POINTS = subprocess.run(
    ["git", "ls-files", "scripts/*.py", "scripts/*/*.py"],
    capture_output=True, text=True, cwd=REPO).stdout.split()


@pytest.mark.parametrize("entry", ENTRY_POINTS)
def test_entry_point_agrees_with_the_package_about_the_root(entry):
    """Import it and compare, rather than reading the source: a script is free to
    compute the root however it likes, so long as it gets the same answer."""
    path = os.path.join(REPO, entry)
    code = (
        "import importlib.util, os, sys; "
        f"sys.path.insert(0, os.path.dirname({path!r})); "
        f"spec = importlib.util.spec_from_file_location('_probe', {path!r}); "
        "m = importlib.util.module_from_spec(spec); "
        "spec.loader.exec_module(m); "
        "print('ROOT=' + str(getattr(m, 'REPO', '')))"
    )
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       timeout=180, cwd=REPO, env=dict(os.environ, STUDY_MAP="Town06"))
    if p.returncode != 0:
        from conftest import skip_if_missing_dependency
        skip_if_missing_dependency(entry, p.stderr)
        pytest.fail(f"{entry} will not import:\n{p.stderr[-600:]}")
    m = re.search(r"ROOT=(.*)", p.stdout)
    if not m or not m.group(1).strip():
        pytest.skip(f"{entry} defines no REPO")
    got = os.path.realpath(m.group(1).strip())
    assert got == os.path.realpath(REPO), (
        f"{entry} thinks the repository is at {got}, the package says "
        f"{os.path.realpath(REPO)}. Every artifact path it builds is wrong.")


SHELL = subprocess.run(["git", "ls-files", "scripts/*.sh", "scripts/*/*.sh"],
                       capture_output=True, text=True, cwd=REPO).stdout.split()


@pytest.mark.parametrize("script", SHELL)
def test_shell_driver_changes_to_the_repository_root(script):
    """Same rule for the shell drivers, which cd rather than compute. The depth of
    the `..` chain has to match the depth of the file."""
    with open(os.path.join(REPO, script)) as f:
        src = f.read()
    m = re.search(r'cd "\$\(dirname "\$0"\)((?:/\.\.)+)"', src)
    if not m:
        pytest.skip(f"{script} does not cd to the root")
    ups = m.group(1).count("..")
    depth = script.count("/")          # scripts/x.sh -> 1, scripts/g/x.sh -> 2
    assert ups == depth, (
        f"{script} is {depth} directories deep and climbs {ups}; it lands on "
        f"{'/'.join(script.split('/')[:depth - ups] or ['<above the repo>'])} "
        f"instead of the repository root")

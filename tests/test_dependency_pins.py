"""Each dependency version is written down exactly once.

The bootstrap script and pyproject.toml both used to pin numpy, scipy, opencv and the
determinism package. Two copies of a pin is how the recorded environment and the
installed one come apart: the certificate's own _meta records the versions its bounds
were computed under, so a silent drift between the two files is a drift away from the
environment of record, and nothing in a result shows it.

Four dependencies genuinely cannot come from pyproject.toml -- torch needs the CUDA
index matching the card, auto_LiRPA comes from upstream git with --no-deps, and the
CARLA client ships with the simulator. Those stay in the bootstrap, and this test says
so rather than leaving it to a reader to notice.
"""
import re
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(REPO, "scripts/bootstrap_env.sh")) as f:
    BOOTSTRAP = f.read()
with open(os.path.join(REPO, "pyproject.toml")) as f:
    PYPROJECT = f.read()

# The dependency list itself, not the prose around it: the comment above it names torch
# and auto_LiRPA precisely to say they are NOT there, and a test that greps the whole
# file reads that explanation as a declaration.
DEPS = re.search(r"^dependencies = \[(.*?)^\]", PYPROJECT, re.S | re.M).group(1)

# What pyproject pins, and therefore what the bootstrap must not pin again.
# numpy is deliberately absent: see test_numpy_is_a_floor_here_and_exact_there.
RESOLVABLE = ["scipy", "matplotlib", "carla-determinism"]


def test_bootstrap_does_not_repin_what_pyproject_pins():
    for dep in RESOLVABLE:
        assert re.search(rf'"{dep} ?[=><@]', DEPS), \
            f"{dep} is no longer pinned in pyproject.toml; the bootstrap now has to"
        assert not re.search(rf'\$PIP install[^\n]*["\']?{dep}==', BOOTSTRAP), \
            f"bootstrap_env.sh pins {dep} again; pyproject.toml already does"


def test_bootstrap_installs_the_package_itself():
    """Otherwise the pins in pyproject.toml are documentation and nothing reads them."""
    assert re.search(r'\$PIP install[^\n]*-e\s+"?\.', BOOTSTRAP), \
        "bootstrap_env.sh does not install this package, so pyproject's pins never apply"


def test_opencv_pin_is_read_from_pyproject_not_repeated():
    """opencv is special: it must go in with --no-deps, because it declares numpy>=2
    and would otherwise replace the 1.26.4 the published bounds were computed under.
    That makes it the one the bootstrap has to name -- so it reads the pin rather than
    restating it."""
    assert "OPENCV_PIN" in BOOTSTRAP and "pyproject.toml" in BOOTSTRAP, \
        "the opencv pin is no longer read from pyproject.toml"
    assert not re.search(r'OPENCV_VER=\d', BOOTSTRAP), \
        "bootstrap_env.sh has gone back to hardcoding the opencv version"


def test_the_four_unresolvable_dependencies_stay_in_the_bootstrap():
    """They cannot be expressed in pyproject.toml, and each has cost real time."""
    assert "download.pytorch.org/whl/cu" in BOOTSTRAP, "the torch CUDA index is gone"
    assert "auto_LiRPA" in BOOTSTRAP and "--no-deps" in BOOTSTRAP, \
        "auto_LiRPA must come from upstream git with --no-deps or it rewrites torch"
    assert "PythonAPI/carla/dist" in BOOTSTRAP, "the CARLA client wheel is not installed"
    assert "torch" not in DEPS, \
        "torch is in pyproject.toml's dependencies, where a plain resolver installs a "\
        "build that may not match the card: cuda.is_available() returns True and every "\
        "kernel then fails"


def test_numpy_is_a_floor_here_and_exact_there():
    """The one dependency pinned in both files, on purpose, to different things.

    The published bounds were computed under numpy 1.26.4. Pinning that exactly in
    pyproject.toml makes `pip install -e .` unsatisfiable, because opencv-python
    declares numpy>=2 -- and that is the first command the README gives. So pyproject
    carries a floor and the bootstrap installs the recorded version, with opencv going
    in under --no-deps so it cannot pull numpy 2 back over the top.

    The failure this guards is silent: an install that quietly lands on numpy 2 still
    certifies, still prints verdicts and margins, and is no longer the environment the
    artifacts record.
    """
    assert re.search(r'"numpy>=', DEPS), \
        ("pyproject.toml pins numpy exactly again; opencv-python declares numpy>=2, so "
         "`pip install -e .` becomes unsatisfiable")
    m = re.search(r'NUMPY_VER=(\S+)', BOOTSTRAP)
    assert m, "bootstrap_env.sh no longer installs the recorded numpy"
    floor = re.search(r'"numpy>=([^"]+)"', DEPS).group(1)
    assert m.group(1) == floor, \
        (f"the bootstrap installs numpy {m.group(1)} but pyproject's floor is {floor}; "
         "the recorded version must be the floor, or the casual install is below it")
    assert "INSTALLED_NUMPY" in BOOTSTRAP, \
        ("bootstrap_env.sh does not check which numpy survived the editable install. "
         "Resolving numpy>= can move it, and nothing downstream would say so")

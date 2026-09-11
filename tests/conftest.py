"""Shared setup: the entry-point path, and the two dependencies a resolver cannot get.

`src/steering` is installed, so the library imports normally. `scripts/` deliberately is
not a package -- the files there are things you run, not things you import -- but a few
tests cross-check a constant against the script that defines it, and that is worth more
than the purity of never importing one.

The CARLA client wheel ships with the simulator and auto_LiRPA comes from upstream git,
so neither is installable by a resolver and neither exists on a continuous-integration
runner. Tests that need them skip, and `skip_if_missing_dependency` keeps that judgement
in one place and narrow: only those two names, and only when they are genuinely absent,
so a real import error still fails.
"""
import importlib.util
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Both, because that is what happens when you run one: Python puts the script's own
# directory on the path, so scripts/training/dagger.py can say `from train import ...`
# about its neighbour. A test that loads it by file path gets no such directory.
for _d in ("", "verify", "drive", "capture", "simulator", "training"):
    sys.path.insert(0, os.path.join(REPO, "scripts", _d))

# Installable only alongside the simulator, or only from git.
UNRESOLVABLE = ("carla", "auto_LiRPA")


# A machine with no usable GPU is a normal place to run these tests: continuous
# integration installs the CPU build of torch on purpose, so the modules still have to
# import. But one entry point is a GPU DIAGNOSTIC whose whole job is to fail loudly when
# CUDA cannot initialise, so importing it there fails by design and says nothing about
# the thing under test.
NO_GPU = ("Torch not compiled with CUDA enabled",
          "CUDA cannot initialise",
          "No CUDA GPUs are available",
          "Found no NVIDIA driver")


def skip_if_missing_dependency(what, stderr):
    """Skip if `stderr` blames one of the two, and it really is not installed."""
    for dep in UNRESOLVABLE:
        if (f"No module named '{dep}'" in stderr
                and importlib.util.find_spec(dep) is None):
            pytest.skip(f"{what} needs {dep}, which is not installed here")
    if any(m in stderr for m in NO_GPU) and not _cuda_available():
        pytest.skip(f"{what} needs a working GPU, which this machine does not have")


def _cuda_available():
    """True only if torch can actually use a device, not merely that one is present."""
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def requires(dep):
    """Decorator form, for a test that imports one of them directly."""
    return pytest.mark.skipif(importlib.util.find_spec(dep) is None,
                              reason=f"{dep} is not installed here")

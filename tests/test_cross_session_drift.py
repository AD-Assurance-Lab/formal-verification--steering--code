"""The foreign clear baseline must stay small against the disturbance it sits inside.

Every shipped cell certifies against a clear baseline from a different capture session,
because each capture holds one condition and the server is restarted between them so a
previous condition cannot leak into the next. Whatever drifted between those two
sessions sits inside (x_condition - x_clear) and the bound treats it as weather.

That is only acceptable while the drift is small, and a comment saying so is not a
measurement. The photometry gate records what the variation actually is across fresh
servers; this asserts it against the disturbance it would contaminate.

An external reviewer read the historical +0.049 figure in the certifier's docstring,
which predates the gate and the shipped captures by weeks, and concluded the
certificates were contaminated by a drift twice the size of the fog disturbance. It is
0.2% of it. The number is checked here so the claim cannot go stale again.
"""
import json
import os

import numpy as np
import pytest

from steering import REPO_ROOT

REF = os.path.join(REPO_ROOT, "results", "photometry_reference.json")
CAPS = os.path.join(REPO_ROOT, "results", "arterial", "captures")


def _drift():
    with open(REF) as f:
        return json.load(f)["Town06/clear"]["std"]


def test_the_photometry_reference_records_the_cross_session_variation():
    assert os.path.exists(REF), "no photometry reference; the drift is unmeasured"
    assert _drift() < 1e-3, f"cross-session clear drift is {_drift():.2e}"


@pytest.mark.parametrize("cond", ["fog", "night", "low_sun"])
def test_the_drift_is_small_against_every_disturbance(cond):
    base = os.path.join(CAPS, "lap_lap_clear.npz")
    other = os.path.join(CAPS, f"lap_lap_{cond}.npz")
    if not (os.path.exists(base) and os.path.exists(other)):
        pytest.skip("captures not present; run scripts/fetch_captures.py")
    b = np.load(base)["frames"][0, :, 0, 0]
    d = np.load(other)["frames"][0, :, 0, 0]
    mag = float(np.abs(d - b).mean())
    ratio = mag / _drift()
    assert ratio > 50.0, (
        f"the {cond} disturbance is {mag:.4f} per pixel and the cross-session clear "
        f"drift is {_drift():.2e} -- only {ratio:.0f}x apart. Below about 50x the "
        f"baseline choice starts to matter to the bound and the paired-baseline path "
        f"should be used instead")

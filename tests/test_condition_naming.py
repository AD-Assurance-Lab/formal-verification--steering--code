"""The condition is low_sun; "shadows" is the deprecated alias.

A mismatch here RAISES mid-run (evaluate.py asserts the rendered condition), so a
driver that asks for "low_sun" against a classifier that answers "shadows" would abort
every low-sun lap of an unattended rebuild -- on a condition that rendered correctly.
"""
import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

from condition_signature import assert_condition, identify  # noqa: E402


# The four conditions as they MEASURE on the Town06 lap (T06-F42), on the student's
# view. identify() reads mean, sigma and p01, so a synthetic frame has to reproduce all
# three -- a plain Gaussian at clear's mean and sigma has p01 = 0.17 and classifies as
# FOG, which is a fact about the generator and not about clear.
MEASURED = {                    # mean    sigma   p01
    "clear":   (0.3064, 0.0616, 0.0641),
    "fog":     (0.2840, 0.0610, 0.1855),
    "night":   (0.1844, 0.1393, 0.0002),
    "low_sun": (0.1264, 0.0389, 0.0111),
}


def _frame(condition):
    """A synthetic frame carrying the measured mean, sigma and p01 of `condition`.

    All three matter: identify() branches on sigma, then p01, then mean. A plain
    Gaussian at clear's mean and sigma has p01 = 0.16 and classifies as FOG, which is a
    fact about the generator, not about clear -- clear's real p01 is 0.064 because the
    road ROI carries a dark tail the Gaussian has no reason to produce.
    """
    mean, sigma, p01 = MEASURED[condition]
    rng = np.random.default_rng(0)
    a = rng.normal(mean, sigma, size=(3, 28, 168)).astype(np.float32).reshape(-1)
    order = np.argsort(a)
    k = max(2, int(0.02 * a.size))          # the bottom 2%, so percentile(1) lands in it
    if p01 < a[order[k]]:
        # a real dark tail: ramp the bottom 2% from 0 up to 2*p01, putting the 1st
        # percentile at p01 by construction
        a[order[:k]] = np.linspace(0.0, 2.0 * p01, k, dtype=np.float32)
    else:
        a = np.maximum(a, p01)              # fog: airlight lifts the whole floor
    return np.clip(a.reshape(3, 28, 168), 0.0, 1.0)


def test_low_sun_is_the_name_identify_returns():
    got, _ = identify(_frame("low_sun"))
    assert got == "low_sun"


@pytest.mark.parametrize("asked", ["low_sun", "shadows"])
def test_assert_accepts_both_names_for_the_same_condition(asked):
    assert_condition(_frame("low_sun"), asked)


def test_assert_still_catches_a_real_mismatch():
    with pytest.raises(RuntimeError):
        assert_condition(_frame("low_sun"), "clear")


def test_night_and_clear_are_unaffected():
    assert identify(_frame("night"))[0] == "night"
    assert identify(_frame("clear"))[0] == "clear"
    assert identify(_frame("fog"))[0] == "fog"

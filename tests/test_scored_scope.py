"""The two scored scopes must partition the same road, and neither may be silently fitted.

`scored_scope.py` exists because the lap route dropped a constraint the SECTION route
enforced: `SMAX_CAP = 0.060`, declared in build_study_route.py as "steering demand regime
that actually trained on Town04". The lap's smax is 0.0670.

Excluding that road makes the Town06 mixed student look better, so these tests pin the
properties that stop the scope from becoming a knob:

  * `full` reproduces the study's own committed scored length (2,119 m) -- if it did not,
    the capped number would be measured against a moving baseline;
  * the capped scope is a strict SUBSET of the full one, never a different road;
  * the thresholds are the declared constants, not values chosen here;
  * spans are undilated, so no reaction-distance padding can creep in.

No CARLA and no models: this is route geometry only.
"""
import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "scripts"))


@pytest.fixture(scope="module")
def mod():
    os.environ["STUDY_MAP"] = "Town06"
    for m in ("config", "route", "scored_scope"):
        sys.modules.pop(m, None)
    import config as C
    import scored_scope as S
    return C, S


def test_thresholds_are_the_declared_constants(mod):
    """SMAX_CAP and Town04's smax come from build_study_route, not from this study."""
    _, S = mod
    import build_study_route as B
    assert S.SMAX_CAP == B.SMAX_CAP
    assert S.REF_SMAX == B.REF["smax"]


def test_full_scope_reproduces_the_committed_scored_length(mod):
    """`full` must equal the 2,119 m the Town06 result was scored on.

    This is the anchor. The capped scope is only meaningful as a difference from the
    scope the committed ledger actually used.
    """
    C, S = mod
    assert S.scored_length_m("lap", "full") == pytest.approx(C.LAP_SCORED_M, abs=2.0)


def test_capped_is_a_strict_subset_of_full(mod):
    """Capping may only REMOVE road. It must never add any."""
    _, S = mod
    full = S.scope_spans("lap", "full")
    capped = S.scope_spans("lap", "capped")
    assert all(b in capped for b in full), "capping dropped an ODD bridge"
    assert S.scored_length_m("lap", "capped") < S.scored_length_m("lap", "full")


def test_the_route_really_does_exceed_the_cap(mod):
    """If this ever fails, the premise of the whole scope exercise is gone."""
    _, S = mod
    from route import load_route
    _, d = S.demand_profile(load_route("lap"))
    assert d.max() > S.SMAX_CAP


def test_spans_are_undilated(mod):
    """Every excluded vertex is over threshold; no padding, no smoothing.

    A reaction-distance margin would be a knob on the scope definition, and a knob there
    is how a study selects the road that flatters it.
    """
    _, S = mod
    from route import load_route
    arc, d = S.demand_profile(load_route("lap"))
    for a, b in S.excluded_spans("lap", S.SMAX_CAP):
        m = (arc >= a) & (arc <= b)
        assert (d[m] > S.SMAX_CAP).all(), f"span {a:.1f}-{b:.1f} includes in-regime road"


def test_capping_does_not_rescue_the_void_cell(mod):
    """The fog VOID cell's instability at arc ~55 m stays SCORED under the cap.

    Recorded as a test because it is the honest half of this change: the capped scope
    removes the road where low_sun and clear peak, and does NOT remove the road where fog
    goes void. A scope that quietly excused every inconvenient cell would be tuning.
    """
    _, S = mod
    assert not S.in_spans(55.3, S.scope_spans("lap", "capped"))


def test_unknown_scope_refuses(mod):
    _, S = mod
    with pytest.raises(SystemExit):
        S.scope_spans("lap", "whatever_makes_the_number_nicer")

"""A Town06 lap capture must cover the SCORED road: all of it, and none of the bridges.

Standing rule 7 is two-sided. Town04 already paid for the "less" half (a capture that
covered 5.6% of a lap and read as complete); the lap route makes the "more" half live,
because its geometry is 2,289 m and its scored road is 2,119 m -- the two intersections
are driven by pure pursuit and scored by nothing, so certifying them would produce a
bound that no closed-loop cell is comparable to.

This exercises the pose-selection arithmetic offline, without CARLA. It is the part that
was wrong twice: once by sampling the route instead of the scored road, and once by
computing arc-length over (x, y, YAW) because the lap's route array carries a third
column that Town04's does not.
"""
import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "pipeline"))


@pytest.fixture(scope="module")
def lap():
    os.environ["STUDY_MAP"] = "Town06"
    for m in ("config", "route"):
        sys.modules.pop(m, None)
    import config as C
    from route import load_route
    rt = np.asarray(load_route(C.SECTIONS[0]), dtype=float)
    return C, rt


def _select(C, rt, n_poses):
    """The selection capture_offset_yaw.py performs, in the same order."""
    xy = rt[:, :2]
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))])
    bridges = sorted(C.bridge_spans_for(C.SECTIONS[0]))
    length = min(C.scored_len_m(C.SECTIONS[0]), float(d[-1]))

    def to_route(s):
        r = s
        for a, b in bridges:
            if r >= a:
                r += (b - a)
            else:
                break
        return r

    want = np.array([to_route(s) for s in np.linspace(0.0, length, n_poses)])
    ok = np.ones(len(d), dtype=bool)
    for a, b in bridges:
        ok &= ~((d >= a) & (d <= b))
    cand = np.flatnonzero(ok)
    idx = sorted({int(cand[np.argmin(np.abs(d[cand] - w))]) for w in want})
    return d, xy, bridges, length, idx


def test_route_arc_length_uses_x_and_y_only(lap):
    """The lap's route is (N, 3) and column 2 is yaw in DEGREES. Including it inflates
    the lap from 2,289 m to 5,299 m, so every metres-along-the-route lookup lands at
    ~40% of the distance it names."""
    C, rt = lap
    assert rt.shape[1] == 3, "this test is about the third column; the route lost it"
    arc_xy = np.linalg.norm(np.diff(rt[:, :2], axis=0), axis=1).sum()
    arc_all = np.linalg.norm(np.diff(rt, axis=0), axis=1).sum()
    assert arc_xy == pytest.approx(C.LAP_TOTAL_M, abs=1.0)
    assert arc_all > 2 * arc_xy, "expected the yaw column to inflate the arc length"


def test_scored_length_excludes_the_bridges(lap):
    C, _ = lap
    sec = C.SECTIONS[0]
    bridged = sum(b - a for a, b in C.bridge_spans_for(sec))
    assert C.scored_len_m(sec) == pytest.approx(C.LAP_TOTAL_M - bridged, abs=1.0)
    assert C.scored_len_m(sec) < C.SECTION_LEN_M[sec]


def test_no_captured_pose_falls_inside_a_bridge(lap):
    C, rt = lap
    d, _, bridges, _, idx = _select(C, rt, C.steps_for(C.SECTIONS[0]))
    assert bridges, "the lap is expected to have bridged spans"
    inside = [float(d[i]) for i in idx if any(a <= d[i] <= b for a, b in bridges)]
    assert inside == []


def test_poses_span_the_whole_scored_road(lap):
    """Both ends: the capture must reach the end of the lap, and must not claim more
    scored road than exists."""
    C, rt = lap
    d, xy, bridges, length, idx = _select(C, rt, C.steps_for(C.SECTIONS[0]))
    assert d[idx[0]] < 5.0
    assert d[idx[-1]] > C.LAP_TOTAL_M - 5.0

    cov = float(np.linalg.norm(np.diff(xy[idx], axis=0), axis=1).sum())
    for a, b in bridges:
        before = [i for i in idx if d[i] <= a]
        after = [i for i in idx if d[i] >= b]
        if before and after:
            i0, i1 = max(before), min(after)
            cov -= float(np.hypot(xy[i1][0] - xy[i0][0], xy[i1][1] - xy[i0][1]))
    # certify_town06.py's own window: an 80% floor and a +25 m ceiling on the SCORED road
    assert 0.80 * length <= cov <= length + 25.0


def test_town04_is_unaffected():
    """Town04 has no bridges and a 2-column route; none of this may change it."""
    os.environ["STUDY_MAP"] = "Town04"
    for m in ("config", "route"):
        sys.modules.pop(m, None)
    import config as C
    from route import load_route
    for sec in C.SECTIONS:
        assert C.bridge_spans_for(sec) == []
        assert C.scored_len_m(sec) == C.SECTION_LEN_M[sec]
        assert np.asarray(load_route(sec)).shape[1] == 2
    for m in ("config", "route"):
        sys.modules.pop(m, None)

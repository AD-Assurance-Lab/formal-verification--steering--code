"""Route distances are measured in METRES, over x and y, and nowhere else.

A route array is (N, 2) on Town04 and (N, 3) on the Town06 lap, where the third column
is YAW IN DEGREES. `np.linalg.norm(np.diff(route, axis=0), axis=1)` therefore measures a
distance in a mixed metres-and-degrees space on the lap and a correct one on Town04 -- so
the defect is invisible on the map that has published results and silent on the one being
measured.

It was found three times in three files before it was given a name, and the worst
instance had already produced a verdict: evaluate.py's scored-distance cap tripped at
1,006 m of a 2,289 m lap, every run ended with the vehicle on the road at 20 mph, and the
clear student was declared COMPETENT on the truncated drive.
"""
import os
import re
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "pipeline"))

from route import arc_lengths, route_length_m  # noqa: E402


def test_a_third_column_cannot_change_the_length():
    xy = np.stack([np.linspace(0.0, 100.0, 51), np.zeros(51)], axis=1)
    yaw = np.random.default_rng(0).uniform(-180, 180, 51).reshape(-1, 1)
    assert route_length_m(xy) == pytest.approx(100.0)
    assert route_length_m(np.hstack([xy, yaw])) == pytest.approx(100.0)


def test_arc_is_monotonic_and_starts_at_zero():
    xy = np.stack([np.linspace(0.0, 10.0, 11), np.zeros(11)], axis=1)
    a = arc_lengths(xy)
    assert a[0] == 0.0
    assert np.all(np.diff(a) > 0)
    assert a[-1] == pytest.approx(10.0)


def test_the_lap_measures_its_declared_length():
    os.environ["STUDY_MAP"] = "Town06"
    for m in ("config", "route"):
        sys.modules.pop(m, None)
    import config as C
    from route import load_route, route_length_m as rlm
    assert rlm(load_route(C.SECTIONS[0])) == pytest.approx(C.LAP_TOTAL_M, abs=1.0)
    for m in ("config", "route"):
        sys.modules.pop(m, None)


@pytest.mark.parametrize("path", ["pipeline/evaluate.py", "scripts/capture_offset_yaw.py"])
def test_no_driver_measures_distance_over_a_whole_route_array(path):
    """The specific expression that caused it, in the files that drive and capture."""
    src = open(os.path.join(REPO, path)).read()
    bad = re.findall(r"np\.diff\(\s*(?:route|rt)\s*,\s*axis=0\s*\)", src)
    assert not bad, f"{path} measures a route distance over every column: {bad}"
    assert "arc_lengths" in src, f"{path} should use route.arc_lengths"

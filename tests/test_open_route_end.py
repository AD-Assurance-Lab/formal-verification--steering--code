"""A driving loop must stop at the end of an OPEN route, and stop BEFORE recording.

T06-F43: every collected lap ended with a garbage expert label. The lap-end test in
every driving loop is "leave the start, then return to it", which cannot fire when the
start and the end are 174 m apart -- so the loop ran to its step budget, drove past the
last vertex, and recorded a label produced by a lookahead clamped onto that vertex.
13 frames of 15,360, |steer| up to 0.754 against a lap maximum of 0.086, at |CTE| of
0.001 m: the car perfectly on the line and the label meaningless.
"""
import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "pipeline"))

from route import lap_finished, route_is_closed  # noqa: E402

# Pure pursuit commands at most ~0.09 on these routes at 20 mph.
STEER_CEILING = 0.25


def _open_route(n=100):
    """A straight open route: start and end far apart."""
    return np.stack([np.linspace(0.0, 200.0, n), np.zeros(n)], axis=1)


def _closed_route(n=100):
    """A circle: end rejoins start, so index wrap is meaningful."""
    t = np.linspace(0.0, 2 * np.pi, n)
    return np.stack([50.0 * np.cos(t), 50.0 * np.sin(t)], axis=1)


def test_open_route_finishes_before_the_last_vertex():
    r = _open_route()
    assert not route_is_closed(r)
    assert not lap_finished(r, len(r) - 3)
    assert lap_finished(r, len(r) - 2)
    assert lap_finished(r, len(r) - 1)


def test_closed_route_never_finishes_this_way():
    """Town04's lap closes on itself and ends by returning to its start. This helper
    must never fire there, or its lap would be truncated."""
    r = _closed_route()
    assert route_is_closed(r)
    assert not lap_finished(r, len(r) - 1)


def test_no_hint_is_not_a_finish():
    assert not lap_finished(_open_route(), None)


@pytest.mark.parametrize("driver", ["collect_data.py", "dagger.py", "dagger_student.py"])
def test_every_collector_stops_before_it_records(driver):
    """The check must precede the write, so a degenerate label is never recorded at all
    rather than recorded and filtered later."""
    src = open(os.path.join(REPO, "pipeline", driver)).read()
    assert "lap_finished(" in src, f"{driver} does not stop at an open route's end"
    stop = src.index("if lap_finished(")
    write = src.index("cv2.imwrite(")
    assert stop < write, f"{driver} records the frame before testing for the route end"


def test_the_data_auditor_would_catch_a_recurrence():
    src = open(os.path.join(REPO, "scripts", "audit_training_data.py")).read()
    assert "STEER_LABEL_CEILING" in src
    ns = {}
    for line in src.splitlines():
        if line.startswith("STEER_LABEL_CEILING"):
            exec(line, ns)
    assert 0.09 < ns["STEER_LABEL_CEILING"] <= STEER_CEILING


@pytest.mark.parametrize("path", ["pipeline/evaluate.py", "scripts/closed_loop_ledger.py"])
def test_every_measuring_loop_stops_at_the_route_end(path):
    """The loops that SCORE a policy must stop too.

    Their step budget comes from steps_for(), which runs slightly hot, and past the last
    vertex CTE is measured against a segment that no longer exists -- gate_teacher_lap.py
    recorded max|CTE| 75 ft while only 1.2% of steps were over budget, "not a policy that
    leaves the road, a measurement running off the end of its own reference".

    closed_loop_ledger.py is the loop that produces the SCORED RESULT and it had neither
    this check nor evaluate.py's distance cap.
    """
    src = open(os.path.join(REPO, path)).read()
    assert "lap_finished(" in src, f"{path} does not stop at an open route's end"

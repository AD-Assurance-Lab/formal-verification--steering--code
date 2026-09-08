"""The committed oracle traces must be plausible drives of a committed route.

REPRODUCING calls these "the cheapest check that your simulator is configured
correctly": drive the expert twice, diff against these. That only works if they are
what they claim to be, and two of the three were not. One was 380 steps of the
ARTERIAL lap filed under a highway direction name; the other was sixteen steps
ending 7 m off any committed route, at 7.8 m of cross-track error against a 0.67 m
budget -- a run that is void by the repository's own rule about runs ending in a
handful of steps.

They survived every prune because `results/**` is gitignored, and a file already
tracked never appears in `git status`. So the reference set is checked here instead.
"""
import csv
import os

import numpy as np
import pytest

from steering import REPO_ROOT, config as C

ORACLE = os.path.join(REPO_ROOT, "results", "oracle")
FILES = sorted(f for f in os.listdir(ORACLE) if f.endswith(".csv")) \
    if os.path.isdir(ORACLE) else []


def _xy(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    return rows, np.array([[float(r["x"]), float(r["y"])] for r in rows])


def _routes():
    out = {}
    for road in ("highway", "arterial"):
        d = os.path.join(REPO_ROOT, "routes", road)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.endswith(".npy"):
                out[f"{road}/{f[:-4]}"] = np.load(os.path.join(d, f))[:, :2].astype(float)
    return out


@pytest.mark.parametrize("name", FILES)
def test_the_oracle_drove_the_route_its_name_claims(name):
    rows, xy = _xy(os.path.join(ORACLE, name))
    routes = _routes()
    assert routes, "no committed routes to compare against"
    dists = {k: float(np.median(np.min(np.linalg.norm(xy[:, None] - v[None], axis=2), axis=1)))
             for k, v in routes.items()}
    nearest = min(dists, key=dists.get)
    assert dists[nearest] < 1.0, (
        f"{name} is {dists[nearest]:.2f} m from the nearest committed route "
        f"({nearest}); it is not a drive of any route this repository ships")
    claimed = name.replace("oracle_", "").replace(".csv", "")
    assert claimed in nearest, (
        f"{name} claims to be {claimed} but its poses lie on {nearest}")


@pytest.mark.parametrize("name", FILES)
def test_the_oracle_stayed_on_the_road_for_a_whole_route(name):
    """The expert is the reference. If it departs, or stops after a handful of steps,
    it is a broken run and not something to compare a simulator against."""
    rows, xy = _xy(os.path.join(ORACLE, name))
    mx = max(abs(float(r["cte_m"])) for r in rows)
    assert mx <= C.CTE_BUDGET_M, (
        f"{name} reaches {mx:.2f} m of cross-track error against a "
        f"{C.CTE_BUDGET_M:.2f} m budget: the expert left the road")
    span = float(np.hypot(*np.diff(xy, axis=0).T).sum())
    assert span > 500.0, (
        f"{name} spans {span:.0f} m. A reference that ends after a fraction of the "
        f"route is a bug, not a reference")

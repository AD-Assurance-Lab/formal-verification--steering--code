"""Numbers quoted in the documentation are recomputed from the artifacts.

A figure in prose has no way to fail. REPRODUCING claimed "at least 309x headroom
between its bound and the value that would flip it" and justified accepting a
non-reproducible bound on that basis; recomputed from the committed certificates the
tightest cell needs a 4.2% move and the worst measured drift is 0.39%, so the margin
is about 11x. The 309 came from dividing by the best case instead of the worst, and
the document it came from had been pruned, so nothing could check it.

These are the numbers a reader would act on. They are asserted against the files.
"""
import json
import os
import re

from steering import REPO_ROOT

CERTS = {"arterial": "results/arterial/certificate_town06.json",
         "highway": "results/highway/calibration/sustained_bound.json"}


def _dist_to_flip(lo, hi, tol):
    """How far a bound must move, in units of tolerance, to change the verdict.

    A cell is certified when the WHOLE interval lies inside the corridor. So for a
    certified cell the nearer edge is the binding one, and for an uncertified cell it
    is the edge furthest OUTSIDE -- every outside edge has to come in. Taking the
    nearer edge in both cases, which is the obvious thing to write, reports a cell as
    one nudge from flipping when its other edge is four tolerances out.
    """
    if abs(lo) <= tol and abs(hi) <= tol:
        return min(tol - abs(lo), tol - abs(hi)) / tol
    return max((abs(e) - tol) for e in (lo, hi) if abs(e) > tol) / tol


def _tightest(rel):
    with open(os.path.join(REPO_ROOT, rel)) as f:
        d = json.load(f)
    tol = d["_meta"]["tolerance"]
    return min(_dist_to_flip(v["lo"], v["hi"], tol) for k, v in d.items() if k != "_meta")


def _json(rel):
    with open(os.path.join(REPO_ROOT, rel)) as f:
        return json.load(f)


def _doc():
    with open(os.path.join(REPO_ROOT, "REPRODUCING.md")) as f:
        return f.read()


def test_the_documented_flip_distances_match_the_certificates():
    doc = _doc()
    for road, rel in CERTS.items():
        t = _tightest(rel)
        m = re.search(rf"\| {road} \| ([\d.]+) x tol", doc)
        assert m, f"REPRODUCING no longer states the {road} flip distance"
        assert abs(float(m.group(1)) - t) < 0.005, (
            f"REPRODUCING says the {road} tightest cell is {m.group(1)} x tol from "
            f"flipping; the certificate says {t:.3f}")


def test_the_documented_margins_follow_from_the_table():
    doc = _doc()
    for road in CERTS:
        m = re.search(rf"\| {road} \| ([\d.]+) x tol \| ([\d.]+) x tol \| \*\*([\d.]+)x\*\*",
                      doc)
        assert m, f"the {road} row is no longer a complete table row"
        tight, drift, margin = (float(m.group(i)) for i in (1, 2, 3))
        # The table quotes rounded values, so recompute the quotient from the numbers
        # as printed rather than from full precision -- otherwise the test fails on
        # rounding rather than on the claim being wrong.
        assert abs(tight / drift - margin) <= max(1.0, 0.05 * margin), (
            f"the {road} row says {margin}x but {tight}/{drift} is {tight/drift:.1f}x")


def test_the_highway_sensitivity_is_still_disclosed():
    """The highway reproduces its verdicts with under 2x margin. A reader who is told
    only that everything reproduces will absorb a flipped verdict as noise."""
    doc = _doc()
    assert "very little room to spare" in doc, (
        "REPRODUCING no longer warns that the highway certificate reproduces with "
        "little margin")


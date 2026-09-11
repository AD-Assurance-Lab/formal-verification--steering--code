"""The names the config header advertises must exist, and it must stay honest.

The header is a map into a 750-line file: it tells a reader which name holds the
lane-departure budget without making them read the reasoning behind it. A map that
points at a name which has been renamed is worse than no map, and nothing else would
notice -- the header is a docstring, so it cannot fail on its own.
"""
import re

from steering import config as C


def _advertised():
    """The constant names in the header's table and prose."""
    doc = C.__doc__
    table = doc[doc.index("what "):doc.index("Two of those")]
    return {n for n in re.findall(r"\b[A-Z][A-Z0-9_]{2,}\b", table)}


def test_every_name_the_header_advertises_exists():
    missing = sorted(n for n in _advertised() if not hasattr(C, n))
    assert not missing, f"the config header points at names that do not exist: {missing}"


def test_the_header_covers_the_safety_criterion():
    """These four are the criterion. If one stops being advertised, a reader has to
    find it by reading the file, which is the thing the header exists to prevent."""
    for n in ("CTE_BUDGET_M", "CLOSED_LOOP_TOLERANCE", "T_CLOSED_LOOP_S", "STUDY_MAP"):
        assert n in _advertised(), f"{n} is no longer in the config header"


def test_the_tolerance_is_derived_from_the_budget():
    """The header says so, and it is the reason the two cannot disagree."""
    assert C.CLOSED_LOOP_TOLERANCE == C.CLOSED_LOOP_TOLERANCE_RAD / C.MAX_STEER_RAD
    assert C.CTE_BUDGET_M > 0 and C.CLOSED_LOOP_TOLERANCE > 0

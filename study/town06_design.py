"""Pre-registered design for the Town06 DEPLOYMENT TEST.

Written before any Town06 certificate or closed-loop result exists, for the same
reason study/design.py is: an expectation recorded after the fact is not a
prediction, and an aggregation rule chosen after seeing the numbers is a curve fit.

PROTOCOL.md wins over this file. This module is its executable form.

The difference from study/design.py in one line: that study CHOSE the criterion with
the outcomes known; this one INHERITS it and is forbidden from touching it.
"""
import os

# ── What is inherited, and must not be re-derived here ──────────────────────
# These are imported from config so there is exactly one definition. If a future
# reader is tempted to write a Town06-specific value for any of them, PROTOCOL.md
# section 3 is the answer: they are frozen, and re-fitting one destroys the test.
FROZEN_FROM_TOWN04 = (
    "T_CLOSED_LOOP_S",          # 1.85 s -- the single calibrated constant
    "T_HORIZON_S",              # 1.0 s
    "TARGET_SPEED_MS",
    "FIXED_DT",
    "MAX_STEER_RAD",
    "WHEELBASE_M",
    "VEHICLE_WIDTH_M",
    "VEHICLE_BLUEPRINT",
)

# Recomputed from Town06's MEASURED geometry by formula, which is not re-fitting.
# Town06's lane width measures 3.500 m, identical to Town04, so these come out
# numerically unchanged -- a fact about the maps, recorded rather than assumed.
DERIVED_FROM_MAP = ("LANE_WIDTH_M", "CTE_BUDGET_M", "CLOSED_LOOP_TOLERANCE")

STUDENTS = ("S_clear_t06", "S_mixed_t06")
CONDITIONS = ("clear", "fog", "night", "shadows")
DIRECTIONS = ("eastbound", "westbound")

# Verdict vocabularies and the agreement map are inherited unchanged.
AGREES = {("PASS", "CERTIFIED"), ("FAIL", "NOT_CERTIFIED")}

# The clear cells are DEGENERATE exactly as on Town04: the disturbance box has zero
# width, so the bound is exact and CERTIFIED is true by construction. Recorded for
# completeness, excluded from every agreement count.
VACUOUS_CELLS = {"clear"}


def expected(student, condition):
    """The pre-registered expectation for one Town06 cell.

    Same spine as Town04: the clear-only student fails what it never saw, except fog,
    where Town04 disposition D-14 established it is genuinely robust on open road.
    A result contradicting this is a BUG until a written disposition rules out the
    candidate causes (standing rule 2). It is not a finding before that.
    """
    if condition in VACUOUS_CELLS:
        return ("PASS", "CERTIFIED")
    if student == "S_mixed_t06":
        return ("PASS", "CERTIFIED")
    if condition == "fog":
        return ("PASS", "CERTIFIED")          # D-14
    return ("FAIL", "NOT_CERTIFIED")          # night, low sun


def cells():
    """Every scored cell, in display order. 2 students x 4 conditions x 2 directions."""
    for cond in CONDITIONS:
        for student in STUDENTS:
            for direction in DIRECTIONS:
                yield (cond, student, direction)


def scored_cells():
    """Cells that count toward the agreement statistic (clear is vacuous)."""
    return [c for c in cells() if c[0] not in VACUOUS_CELLS]


# ── The risk that this experiment is uninformative, declared in advance ─────
# Town06's best-matching window is 74-79 % straight against Town04's 51-56 %. A
# straighter route is easier to hold, so it is possible every cell passes and every
# cell certifies.
#
# If that happens the experiment has measured SENSITIVITY ONLY and not specificity,
# exactly as the withdrawn rain condition did (4/4, but all four cells shared a
# verdict). It must be reported that way. Writing it here, before the result, is what
# stops it being argued about afterwards.
DEGENERATE_IF_ALL_AGREE = (
    "If every scored cell returns the same verdict pair, report sensitivity only. "
    "A uniform 16/16 is NOT evidence that the certificate discriminates."
)

# Minimum repetitions per closed-loop verdict, inherited. Near the cliff a single run
# is wrong about 1 in 8 times.
MIN_CLOSED_LOOP_REPS = 10

RESULTS_SUBDIR = os.path.join("results", "town06")
CERT_ARTIFACT = os.path.join(RESULTS_SUBDIR, "certificate_town06.json")
LEDGER_SUBDIR = os.path.join(RESULTS_SUBDIR, "ledger")

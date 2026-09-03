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
# THE CONDITION IS low_sun. "shadows" was the code's name for it and never the
# protocol's; consumers accept both, and nothing new is written under the old one.
CONDITIONS = ("clear", "fog", "night", "low_sun")

# THE ROUTE IS ONE CONTINUOUS LAP, and this module reads it from the same place the
# pipeline does.
#
# It used to read `sections` out of routes_town06/route_meta.json, which describes the
# SIX-SECTION route the lap superseded on 2026-08-31. That artifact still exists, so the
# stale read succeeded and returned ('s00'..'s05') -- and certify_town06.py builds its
# capture filenames from this tuple, so it would have demanded lap_s00_fog.npz and the
# other 23 six-section captures, none of which any driver writes any more. The
# certification stage would have refused with 24 files missing, after every capture had
# already been taken.
#
# Reading config means this module and the route CANNOT disagree, which is what the
# original comment claimed the route_meta read was for.
def _sections():
    import sys, os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(here, "pipeline"))
    import config as _C
    return tuple(_C.SECTIONS)


SECTIONS = _sections()
DIRECTIONS = SECTIONS          # name kept so existing call sites keep working

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
    """Every cell: (condition, student). LAPS are the repetitions within a cell.

    PROTOCOL A-4 replaced the arithmetic this docstring used to carry. It said the six
    sections were repetitions -- "2 reps each for 12 total, comfortably over the
    MIN_CLOSED_LOOP_REPS floor" -- and A-4 is the finding that this pooled unlike units:
    a section is a distinct stretch of road, so twelve runs were six different roads
    sampled twice, and two cells reported 2/12 = 17% when the SAME section had failed in
    both passes, a 100% failure diluted by five roads that were never in question.

    A lap is one traversal of all the unique scored road, and the lap is what passes or
    fails. The route is now a single lap, so a cell is three laps.
    """
    for cond in CONDITIONS:
        for student in STUDENTS:
            yield (cond, student)


def scored_cells():
    """Cells that count toward the agreement statistic (clear is vacuous)."""
    return [c for c in cells() if c[0] not in VACUOUS_CELLS]


# Repetitions per cell. PROTOCOL A-4: the LAP is the repetition and THREE laps is the
# standard -- a reproducibility check, not a sample for estimating a rate. Measured on the
# corrected harness, rep-to-rep verdict disagreement was 0 of 48 section-pairs.
LAPS_PER_CELL = 3
REPS_PER_SECTION = LAPS_PER_CELL      # name kept so existing call sites keep working


# ── The risk that this experiment is uninformative, declared in advance ─────
# Town06's lap is 2,289 m with 2,119 m scored, against Town04's 5,722 m over two
# directions, and the window is 74-79% straight (R > 500 m) against Town04's 51-56%
# (PROTOCOL section 4.1). An easier route is easier to hold, so it is possible every
# cell passes and every cell certifies.
#
# If that happens the experiment has measured SENSITIVITY ONLY and not specificity,
# exactly as the withdrawn rain condition did (4/4, but all four cells shared a
# verdict). It must be reported that way. Writing it here, before the result, is what
# stops it being argued about afterwards.
#
# The count is COMPUTED. It read "a uniform 16/16", which was never this design's cell
# count -- there are 3 non-vacuous conditions x 2 students = 6 scored cells -- and a
# declared risk quoting a number the study cannot produce is one nobody can hold it to.
DEGENERATE_IF_ALL_AGREE = (
    "If every scored cell returns the same verdict pair, report sensitivity only. "
    f"A uniform {len(CONDITIONS) - len(VACUOUS_CELLS)} x {len(STUDENTS)} = "
    f"{(len(CONDITIONS) - len(VACUOUS_CELLS)) * len(STUDENTS)}/"
    f"{(len(CONDITIONS) - len(VACUOUS_CELLS)) * len(STUDENTS)} is NOT evidence that the "
    "certificate discriminates."
)

# Minimum repetitions per closed-loop verdict. The floor of 10 was measured on the BROKEN
# harness, where single runs were wrong about 1 in 8 times; PROTOCOL A-4 replaced it with
# three laps under a FULLY ENFORCED harness -- a clean server before every run, a fresh
# vehicle per run, one process per run, the determinism preflight green on each fresh
# server, one client per port, and the capture gate passed before certification.
#
# A-4 is explicit that this is conditional and that there is no fallback to ten: where the
# harness is not enforced the answer is to enforce it, never to compensate with more laps.
# And if the three laps disagree, that is a BUG -- the cell is void, not uncertain.
MIN_CLOSED_LOOP_REPS = LAPS_PER_CELL

RESULTS_SUBDIR = os.path.join("results", "town06")
CERT_ARTIFACT = os.path.join(RESULTS_SUBDIR, "certificate_town06.json")

# PROTOCOL A-5 pass 2. A pass writes its OWN ledger directory, so pass 1 -- the blind
# deployment test whose original PROTOCOL R4 requires to stand in the record -- cannot be
# overwritten or skipped into. run_town06_ledger.sh skips any cell whose file exists, so
# without this a pass-2 run would silently do nothing and report success.
TOWN06_PASS = int(os.environ.get("TOWN06_PASS", "1"))
if TOWN06_PASS not in (1, 2):
    raise SystemExit(f"TOWN06_PASS={TOWN06_PASS}; expected 1 or 2")
LEDGER_SUBDIR = os.path.join(
    RESULTS_SUBDIR, "ledger" if TOWN06_PASS == 1 else f"ledger_pass{TOWN06_PASS}")

# Every certificate a pass drives against. Pass 2 scores BOTH scopes, so both must be
# committed before it drives -- the capped one is new, the full one is pass 1's and has
# been committed since 73415e5.
CAPPED_CERT_ARTIFACT = os.path.join(RESULTS_SUBDIR, "certificate_town06_capped.json")
CERT_ARTIFACTS = ([CERT_ARTIFACT] if TOWN06_PASS == 1
                  else [CERT_ARTIFACT, CAPPED_CERT_ARTIFACT])

"""The pre-registered experimental design.

This module is the single source of truth for what the study expects. It is written
BEFORE results exist and changes only by deliberate, committed amendment -- never to
accommodate a result. See CLAUDE.md.
"""

STUDENTS = ("S_clear", "S_mixed")

INSTRUMENTS = ("closed_loop", "verify")

# Verdict vocabularies. The two instruments answer the same question by different means,
# so their verdicts map onto each other: PASS <-> CERTIFIED, FAIL <-> FALSIFIED.
VERDICTS = {
    "closed_loop": ("PASS", "FAIL"),
    "verify": ("CERTIFIED", "FALSIFIED", "UNKNOWN"),
}

AGREES = {("PASS", "CERTIFIED"), ("FAIL", "FALSIFIED")}


class Condition:
    def __init__(self, name, parameter, unit, lo, hi, status="active"):
        self.name = name
        self.parameter = parameter
        self.unit = unit
        self.lo = lo            # least severe end of the axis
        self.hi = hi            # most severe end
        self.status = status    # active | contingent | out_of_scope

    def __repr__(self):
        return f"<Condition {self.name} ({self.parameter}, {self.unit})>"


CONDITIONS = [
    Condition("clear",   "n/a",             "n/a",  None, None),
    Condition("night",   "road illuminance", "lux",  1e4,  10.0),
    Condition("fog",     "meteorological optical range", "m", 2000.0, 60.0),
    Condition("shadows", "solar elevation",  "deg",  60.0, 10.0),
    Condition("rain",    "rain rate",        "mm/h", 0.0,  25.0, status="contingent"),
]

# CARLA renders no snow. Recorded here so it is a declared scope decision rather than an
# omission a reviewer has to notice.
OUT_OF_SCOPE = {"snow": "CARLA renders no snow"}


def expected(student, condition, instrument):
    """The pre-registered expectation for one ledger cell.

    The spine of the study: the clear-only student fails everything it never saw; the
    mixed student passes; and verification says the same thing as closed loop.
    """
    if condition == "clear":
        return "PASS" if instrument == "closed_loop" else "CERTIFIED"
    if student == "S_clear":
        return "FAIL" if instrument == "closed_loop" else "FALSIFIED"
    return "PASS" if instrument == "closed_loop" else "CERTIFIED"


def cells():
    """Every ledger cell, in display order."""
    for cond in CONDITIONS:
        if cond.status == "out_of_scope":
            continue
        for student in STUDENTS:
            for instrument in INSTRUMENTS:
                yield (cond.name, student, instrument)


# ── How a verification sweep becomes ONE ledger verdict ──────────────────────
# WRITTEN BEFORE ANY VERIFICATION RESULT EXISTS (2026-08-11, 22:4x), for the same reason
# the rest of this module is: an aggregation rule chosen after seeing the numbers is not a
# prediction, it is a curve fit.
#
# A sweep does not return a verdict. It returns, per frame, the fraction of the declared
# axis box that branch-and-bound resolved as CERTIFIED, FALSIFIED, or left UNKNOWN. Those
# have to collapse to one of the three ledger verdicts, and the collapse is where a result
# could quietly be talked into agreeing with closed loop.
VERIFY_FRAMES = 12            # clear-weather frames, sampled evenly along the route
VERIFY_CELL_BUDGET = 96       # bound computations per frame, per condition
VERIFY_CERTIFIED_MIN = 0.50   # certified volume fraction required to call a cell CERTIFIED


def verify_verdict(certified_fracs, falsified_fracs):
    """Collapse a per-frame verification sweep into one ledger verdict.

    Deliberately ASYMMETRIC, because the two claims are not symmetric:

      FALSIFIED is an EXISTENCE claim and is backed by soundness -- the bound lies wholly
        outside the corridor, so a real violating parameter value is present. It needs no
        coverage threshold, only evidence that it is a property of the route rather than
        of one unlucky frame. Hence: the MEDIAN frame has a falsified region.

      CERTIFIED is a COVERAGE claim. "Nothing was falsified" is not it -- an all-UNKNOWN
        sweep also falsifies nothing, and reading that as certified would let bound
        looseness masquerade as robustness. That is exactly the previous study's failure
        mode (11.5% UNKNOWN read as a robustness result). Hence: a majority of the axis
        must be positively certified.

    Median over frames, not mean and not any-frame: one outlier frame should not decide a
    cell in either direction.
    """
    import statistics
    if not certified_fracs:
        return "UNKNOWN"
    c = statistics.median(certified_fracs)
    f = statistics.median(falsified_fracs)
    if f > 0.0:
        return "FALSIFIED"
    if c >= VERIFY_CERTIFIED_MIN:
        return "CERTIFIED"
    return "UNKNOWN"


# The `clear` verify cell is DEGENERATE and is recorded as such. Clear weather is the
# nominal frame: the disturbance box has zero width, so the bound is exact, equals the
# clear-weather steering it is compared against, and CERTIFIED is true by construction.
# It is written to the ledger for completeness and carries `vacuous: true`. It is not
# evidence of anything and must not be counted in any certified-rate summary.
VACUOUS_VERIFY_CELLS = {"clear"}

# Minimum repetitions for any closed-loop verdict. Measured: near the stability cliff a
# single run gives the wrong answer roughly 1 in 8 times, so a single run is not evidence.
MIN_CLOSED_LOOP_REPS = 10

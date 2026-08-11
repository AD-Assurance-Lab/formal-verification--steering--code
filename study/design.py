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


# Minimum repetitions for any closed-loop verdict. Measured: near the stability cliff a
# single run gives the wrong answer roughly 1 in 8 times, so a single run is not evidence.
MIN_CLOSED_LOOP_REPS = 10

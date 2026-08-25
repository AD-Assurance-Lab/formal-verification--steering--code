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
]

# Declared scope decisions, recorded so they are not omissions a reviewer has to notice.
# Rain was withdrawn from the study 2026-08-25: CARLA's rain rendering is temporally
# stochastic (drops and streaks vary frame to frame), so a deterministic two-endpoint
# family cannot represent it; it needs a stochastic element in the disturbance family
# and is future work. The withdrawn rain artifacts are recoverable from git history.
OUT_OF_SCOPE = {
    "snow": "CARLA renders no snow",
    "rain": "temporally stochastic rendering; needs a stochastic disturbance family",
}


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
VERIFY_FRAMES = 60            # AMENDED 2026-08-12, was 12 -- see below
VERIFY_CELL_BUDGET = 96       # bound computations per frame, per condition
VERIFY_CERTIFIED_MIN = 0.50   # retained for the superseded rule; unused by verify_verdict
VERIFY_FALSIFY_FRAC = 0.05    # fraction of frames carrying a violation to call FALSIFIED


def verify_verdict(certified_fracs, falsified_fracs):
    """Collapse a per-frame verification sweep into one ledger verdict.

    AMENDED 2026-08-12. The original rule took the MEDIAN over 12 frames. It produced three
    UNSOUND certificates -- cells CERTIFIED whose closed loop then failed, twice with the
    vehicle leaving the road on every run. The amendment is made deliberately, with the
    reason recorded, and it is NOT a loosening: it makes CERTIFIED strictly harder to earn.

    Two things were wrong, and the second was the deeper one.

    AGGREGATION. A median discards a minority of violating frames by construction. Measured
    on `S_clear` under shadows, 34% of pose-matched route frames already breach the corridor
    empirically, and the median saw none of it.

    SELECTION. Twelve evenly-spaced frames cannot represent a ~1700-frame lap. Verifying the
    frames that actually break the policy, with the SAME disturbance model and verifier,
    falsified 6 of 6 at 67-79% of the axis with zero UNKNOWN -- so the physics and the
    verifier were always capable, and the sweep simply never looked. Hence 12 -> 60 frames,
    still sampled UNIFORMLY along the route: choosing frames by their rendered-condition
    behaviour would import information from the simulator into a prediction that is supposed
    to precede it.

    The rule:

      FALSIFIED  a violation region exists on at least VERIFY_FALSIFY_FRAC of frames.
                 An existence claim backed by soundness, so it needs evidence of being a
                 property of the route rather than one frame -- but not a majority, which
                 is what the median silently demanded and what hid the 34%.
      CERTIFIED  EVERY sampled frame is fully certified. "Nothing was falsified" is not
                 enough; an all-UNKNOWN sweep also falsifies nothing, and reading that as
                 certified is how bound looseness masquerades as robustness.
      UNKNOWN    otherwise -- including the honest case where 60 frames cannot support a
                 positive claim about 1700.
    """
    n = len(certified_fracs)
    if not n:
        return "UNKNOWN"
    frac_with_violation = sum(1 for f in falsified_fracs if f > 0.0) / n
    if frac_with_violation >= VERIFY_FALSIFY_FRAC:
        return "FALSIFIED"
    if all(c >= 0.999 for c in certified_fracs):
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


# ── The lap-scope amendment and the FINAL campaign ───────────────────────────
# AMENDED 2026-08-13 (F28, D-09, D-14). The closed-loop protocol was changed by
# deliberate direction ("it must be the full lap but no intersection"): the lap is
# scored over the open road, 0-2861 m, ending BEFORE the western intersection, whose
# junction has no lane markings and is a real ODD boundary reported separately
# (D-07/D-09). The original full-lap cells stay in results/ledger under the canonical
# names as the record of the superseded protocol; the campaign the paper reports lives
# in the cells below. docs/DISPOSITIONS.md D-14 carries the evidence that every era-1
# fog "failure" originated inside the junction (max-CTE at steps 1695-1706 with 1.2%
# of frames over budget), which is why fog flips to PASS on the open road.
FINAL_CLOSED_LOOP = {
    ("clear",   "S_clear"): "clear___trunc_Sclear",
    ("fog",     "S_clear"): "fog___trunc_Sclear",
    ("night",   "S_clear"): "night___trunc_Sclear",
    ("shadows", "S_clear"): "shadows___trunc_Sclear",
    ("clear",   "S_mixed"): "clear___trunc_Smixed",
    ("fog",     "S_mixed"): "fog___trunc_Smixed",
    ("night",   "S_mixed"): "night___trunc_Smixed",
    ("shadows", "S_mixed"): "shadows___trunc_Smixed",
}

# ── The sustained-bias certificate (F34-F37, F43): the paper's instrument ─────
# D-12: the per-frame-median `verify` cells above belong to a RETIRED instrument; the
# instrument the paper reports had no ledger column at all, which is how the F43
# baseline defect went unseen. This artifact is that column.
#
#   sustained_bound.json      12 canonical cells. IN-SAMPLE: computed after the
#                             driving outcomes were known. It carries no order claim
#                             and must never be presented as a prediction.
SUSTAINED_BOUND_REL = "results/calibration/sustained_bound.json"
SUSTAINED_CONDITIONS = ("fog", "night", "shadows")

# Dispositions for certificate cells whose verdict contradicts the pre-registered
# expectation. The certificate artifact is an aggregate measured file, so its
# dispositions are recorded here rather than by editing the artifact:
#   fog/S_clear CERTIFIED vs expected FALSIFIED -- D-14: S_clear is genuinely
#     fog-robust on the open road (0/60 departures, F27); the expectation predated
#     the junction diagnosis.
CERT_DISPOSITIONS = {
    ("fog", "S_clear"): "D-14",
}

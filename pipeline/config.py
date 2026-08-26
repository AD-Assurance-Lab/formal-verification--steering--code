"""
Single source of truth for the E2E steering pipeline.

Design rule: measured PRIMITIVES are declared explicitly; every SAFETY number
(CTE budget, steering corridor) is DERIVED from them below, so the two can never
silently disagree. All primitives marked [MEASURED] were verified in CARLA
(Town04, Tesla Model 3) on 2026-07-22 via scripts/probe_geometry.
"""
import math
import os
import re

# ── CARLA connection ─────────────────────────────────────────────────────────
HOST = "127.0.0.1"
# Overridable so this session can run on its own RPC port and never collide with
# another CARLA on the machine. Today several hours were lost to exactly that: two
# servers on port 2000, and kill-by-name taking down someone else's simulator.
PORT = int(os.environ.get("CARLA_PORT", "2000"))
CLIENT_TIMEOUT_S = 120.0
# No TrafficManager exists in this study -- the scene is ego + sensors only, so there
# is no TM to seed and no NPC stochasticity. (A TM port constant used to sit here and
# implied otherwise.)
CARLA_ROOT = os.environ.get("CARLA_ROOT", os.path.expanduser("~/carla"))

# ── Map ──────────────────────────────────────────────────────────────────────
# The study map is selectable so the Town06 DEPLOYMENT TEST can reuse this pipeline
# unchanged. Default is Town04, and with STUDY_MAP unset every value below is
# bit-identical to the published study -- that property is deliberate and is what
# lets the same code produce both.
#
# Town06 values are LOADED FROM THE COMMITTED ROUTE ARTIFACT, never hardcoded here:
# the route was fixed on geometry alone before any Town06 model existed (PROTOCOL.md
# section 6), and reading it back from that file is what keeps the two in step.
STUDY_MAP = os.environ.get("STUDY_MAP", "Town04")
MAP_NAME = STUDY_MAP

# ── Vehicle (Tesla Model 3, as instantiated in CARLA) ────────────────────────
VEHICLE_BLUEPRINT = "vehicle.tesla.model3"
WHEELBASE_M = 3.005          # [MEASURED] from CARLA wheel positions (spec is 2.87)
VEHICLE_WIDTH_M = 2.164      # [MEASURED] CARLA bounding box (includes mirrors)
MAX_STEER_RAD = 1.2217       # [MEASURED] 70.0 deg front-wheel max steer

# ── Camera ───────────────────────────────────────────────────────────────────
CAM_WIDTH = 640
CAM_HEIGHT = 480
CAM_FOV = 90
CAM_X, CAM_Y, CAM_Z = 1.6, 0.0, 1.2   # hood mount (m, vehicle frame)
CROP_TOP, CROP_BOT = 180, 400          # remove sky + hood before resize
INPUT_W, INPUT_H = 200, 66             # model input (PilotNet-style)

# Road ROI: rows the network actually sees road in. [MEASURED] over 3,390
# ground-truth segmentation frames. Full image width.
ROAD_ROI_ROWS = (240, 450)

# ── Camera exposure (D1) ─────────────────────────────────────────────────────
# The previous study left these unset, so CARLA's default per-frame HISTOGRAM
# AUTO-EXPOSURE was active for every capture -- the same defect that disqualified
# ACDC for photometry. Auto-exposure re-normalizes each frame AFTER the weather is
# rendered, which is the leading explanation for three prior anomalies: the road
# ROI sitting at mu=0.81 where a real road is ~0.31, rendered fog "preserving more
# contrast than its mean drop permits", and night reading darker-but-SHARPER.
#
# Manual exposure is therefore a precondition for any photometric measurement, and
# because training data is collected through this camera it must be settled BEFORE
# collection, not after.
EXPOSURE_MODE = "manual"
# [MEASURED 2026-08-10] scripts/calibrate_exposure.py, 20 poses. Puts the clear road
# ROI at mu=0.290, sigma=0.0854, inside the real-camera target below. Note that
# shutter=200/f5.6 gives an identical result -- exposure depends only on the
# combination iso/(fstop^2 * shutter), and both settings sit at the same value. That
# equivalence is a useful sanity check that CARLA's photographic model is behaving.
EXPOSURE_SHUTTER_SPEED = 800.0   # 1/s
EXPOSURE_ISO = 100.0
EXPOSURE_FSTOP = 2.8
EXPOSURE_GAMMA = 2.2

# Target for the clear road ROI, from what a real camera outputs for a road.
# Auto-exposure disqualifies ACDC for absolute RADIANCE recovery, but the network
# consumes 8-bit camera output and ACDC *is* real 8-bit camera output, so it is a
# valid reference for this particular quantity.
TARGET_ROAD_MU = (0.28, 0.34)
TARGET_ROAD_SIGMA_RATIO = 1.3    # measured sigma within this factor of a real road's

# ── Condition-dependent exposure ─────────────────────────────────────────────
# [DECIDED 2026-08-11 by Zach] Exposure is a DECLARED FUNCTION OF CONDITION, not a
# single global constant.
#
# Why it is forced: no single exposure serves both ends of the illuminance axis.
# scripts/exposure_dynamic_range.py, 12 poses --
#
#   shutter 800 -> clear mu 0.291 (in target), night 50.6% of the road ROI clipped to 0
#   shutter  25 -> night clipping 0.5%,        clear mu 0.938 (washed out, and a washed
#                                              out road is what made the fog airlight
#                                              unidentifiable in the previous generation)
#
# Night at shutter 800 threw away half its signal, and the mixed teacher then failed
# night in all 6 DAgger rounds while passing fog and shadows. Concluding "the policy
# cannot drive at night" from that camera would have been an artefact of the rig, in
# exactly the way the headlights-off bug was.
#
# What this costs, and it must be stated in the paper: the certificate now reads
# "certified at X lux WITH THE CAMERA EXPOSING AS DECLARED". The night disturbance's
# gain g therefore carries the exposure ratio as a known factor alongside the
# illuminance ratio. Both are known because we set them, so identifiability -- the
# whole reason for pinning exposure in the first place -- is preserved. This is a
# modelling commitment, not auto-exposure: an auto-exposure loop is opaque and
# destroys the mapping, while a declared function does not.
_DAYLIGHT_EXPOSURE = dict(shutter=EXPOSURE_SHUTTER_SPEED, iso=EXPOSURE_ISO,
                          fstop=EXPOSURE_FSTOP, gamma=EXPOSURE_GAMMA)

CONDITION_EXPOSURE = {
    "clear":   _DAYLIGHT_EXPOSURE,
    "fog":     _DAYLIGHT_EXPOSURE,
    "shadows": _DAYLIGHT_EXPOSURE,
    "rain":    _DAYLIGHT_EXPOSURE,
    # 4x the daylight exposure. Chosen so night stays DARKER than clear (mu 0.201 vs
    # 0.290), which keeps night a dimming disturbance rather than an auto-exposure-style
    # normalization, while recovering contrast: sigma 0.059 -> 0.152. Residual clipping
    # ~12% is largely the genuinely unlit far field beyond the headlight throw, which a
    # real night camera also sees and which no exposure can recover.
    "night":   dict(shutter=200.0, iso=EXPOSURE_ISO, fstop=EXPOSURE_FSTOP,
                    gamma=EXPOSURE_GAMMA),
}


def exposure_for(condition):
    """Exposure settings for a condition. Unknown conditions get the daylight setting."""
    return dict(CONDITION_EXPOSURE.get(condition, _DAYLIGHT_EXPOSURE))


def exposure_ratio(condition):
    """Exposure gain relative to daylight -- the known factor the disturbance model's
    gain must carry when the condition changes the camera setting."""
    return _DAYLIGHT_EXPOSURE["shutter"] / exposure_for(condition)["shutter"]

# ── Speed (fixed longitudinal, to remove velocity as a variable) ─────────────
TARGET_SPEED_MPH = 20.0
TARGET_SPEED_MS = 8.9408
MPH_PER_MS = 2.23694

# ── Simulation timing ────────────────────────────────────────────────────────
FIXED_DT = 0.2               # s per tick
SIM_HZ = 1.0 / FIXED_DT      # 5 Hz

# ── Pure-pursuit expert ──────────────────────────────────────────────────────
LOOKAHEAD_M = 5.0

# ── Road geometry ────────────────────────────────────────────────────────────
# [MEASURED] constant on the Town04 highway, both dirs. Town06's chosen window
# measures the SAME 3.500 m (std 0.0000), so the derived CTE budget and tolerance are
# numerically unchanged between the two maps. That is a fact about the maps, not a
# choice, and PROTOCOL.md section 3 requires it be recomputed rather than assumed.
LANE_WIDTH_M = 3.500

# Where the measured route ends. NOT a round number for tidiness: the western traffic-light
# intersection past this point is a real ODD boundary, not a route artifact (D-07 withdrawn,
# D-09 resolved), the lane centreline is undefined through it, and every closed-loop and
# verification number in the study excludes it. Was duplicated across seven scripts.
LAP_END_M = 2861.0

# ── The two verifiable students ──────────────────────────────────────────────
# (name, checkpoint stem, conv channels, FC width). The mixed student is 3x the width of the
# clear-only one -- width, not input resolution, is the verifier-friendly capacity lever,
# because width adds parameters at fixed input-perturbation dimension. This registry was
# copy-pasted into ~20 scripts in three mutually incompatible shapes.
STUDENTS = (("S_clear", "S_clear_84x28", (8, 16, 16), 32),
            ("S_mixed", "S_mixed_84x28_w3", (24, 48, 48), 96))

# ── Spawn points (start just after the western intersection) ─────────────────
SPAWN_EASTBOUND = {"x": -357.1, "y": 30.0, "z": 0.5, "yaw": 0.0}
SPAWN_WESTBOUND = {"x": -396.8, "y": 12.8, "z": 0.5, "yaw": 180.0}

# ── Map-scoped overrides (Town06 deployment test) ────────────────────────────
# Applied only when STUDY_MAP != Town04, and sourced entirely from the committed
# route artifact so the code cannot drift from the pre-registered route.
ROUTES_SUBDIR = "routes"

if STUDY_MAP != "Town04":
    import json as _json
    _rd = os.path.join(DATASET_DIR if "DATASET_DIR" in dir() else
                       os.path.join(_BASE if "_BASE" in dir() else
                                    os.path.dirname(os.path.abspath(__file__)), "data"),
                       f"routes_{STUDY_MAP.lower()}")
    _meta_path = os.path.join(_rd, "route_meta.json")
    if not os.path.exists(_meta_path):
        raise RuntimeError(
            f"STUDY_MAP={STUDY_MAP} but {_meta_path} is missing. The route is a PROTOCOL\n"
            f"artifact and must be built and committed before anything runs on this map:\n"
            f"    CARLA_PORT=$PORT python3 scripts/build_{STUDY_MAP.lower()}_routes.py")
    with open(_meta_path) as _f:
        ROUTE_META = _json.load(_f)
    ROUTES_SUBDIR = f"routes_{STUDY_MAP.lower()}"
    SECTION_BASED = "sections" in ROUTE_META
    if SECTION_BASED:
        # Section-based route (Town06). Town06's outer loop has no dedicated opposing
        # carriageways, so the route is a set of disjoint clean sections rather than one
        # lap driven both ways. "Direction" generalises to "section" throughout.
        SECTIONS = [x["name"] for x in ROUTE_META["sections"]]
        SPAWNS = {x["name"]: x["spawn"] for x in ROUTE_META["sections"]}
        SECTION_LEN_M = {x["name"]: float(x["scored_len_m"])
                         for x in ROUTE_META["sections"]}
        TOTAL_SCORED_M = float(ROUTE_META["total_scored_m"])
        # Kept so code that still names the two Town04 directions keeps importing.
        SPAWN_EASTBOUND = SPAWNS[SECTIONS[0]]
        SPAWN_WESTBOUND = SPAWNS[SECTIONS[min(1, len(SECTIONS) - 1)]]
        LAP_END_M = float(min(SECTION_LEN_M.values()))
    else:
        SECTIONS = ["eastbound", "westbound"]
        SPAWN_EASTBOUND = ROUTE_META["spawns"]["eastbound"]
        SPAWN_WESTBOUND = ROUTE_META["spawns"]["westbound"]
        SPAWNS = {"eastbound": SPAWN_EASTBOUND, "westbound": SPAWN_WESTBOUND}
        SECTION_LEN_M = {}
        if "scored_len_m" in ROUTE_META:
            LAP_END_M = float(ROUTE_META["scored_len_m"])
        else:
            LAP_END_M = float(min(ROUTE_META["window"]["scored_len_m"],
                                  ROUTE_META["opposing"]["scored_len_m"]))
        TOTAL_SCORED_M = LAP_END_M * 2.0
    LANE_WIDTH_M = 3.500

# Section names default to the two Town04 directions; a section-based map overrides
# them above. Every entry point iterates SECTIONS rather than hardcoding a pair.
if STUDY_MAP == "Town04":
    SECTION_BASED = False
    SECTIONS = ["eastbound", "westbound"]
    SPAWNS = {"eastbound": SPAWN_EASTBOUND, "westbound": SPAWN_WESTBOUND}
    SECTION_LEN_M = {"eastbound": LAP_END_M, "westbound": LAP_END_M}
    TOTAL_SCORED_M = LAP_END_M * 2.0

def steps_for(section, margin=1.0):
    """Control steps to drive exactly one section, at the fixed study speed.

    Driving PAST a section's end runs the vehicle into the unclean road the section was
    clipped to exclude, and it fails there for reasons that have nothing to do with the
    policy. Measured: with one 520-step limit applied to all six Town06 sections, the
    pure-pursuit oracle "failed" s03 and s04 at max|CTE| 2.08 m and 7.21 m, both in the
    last few steps. With per-section limits every section passes at <= 0.066 m.

    On Town04 this is a NO-OP by design. Its route is a closed 3042 m loop whose lap
    ends by loop closure (~1701 steps), while LAP_END_M is the 2861 m SCORED prefix
    (~1599 steps). Capping there would truncate the published lap and silently change
    every Town04 number, so section-based maps get a real cap and Town04 gets infinity.
    """
    if not SECTION_BASED:
        return 10 ** 9
    length = SECTION_LEN_M.get(section, LAP_END_M)
    return int(length * margin / (TARGET_SPEED_MS * FIXED_DT))


# ── Town06 student registry ──────────────────────────────────────────────────
# ONE definition, read by the pipeline, the competence gate, the certifier and the
# ledger. They previously each named checkpoints independently and drifted apart: all
# four pointed at the distilled base while student-DAgger was writing <base>_dagger_rNN,
# so the gate tested, and the certifier would have certified, a model nobody ships.
#
# Sizes follow the rule this lab already settled in 4ac6002 -- "size each student to its
# own task", identical architecture explicitly REJECTED because the study's claim is
# WITHIN-model (each policy against its own closed-loop behaviour) and a tool that only
# works when two models share an architecture is not a tool.
#
# Sizes MATCH the Town04 published pair. Widening was tried and is not the fix: the
# Town06 plateau is a LABEL-DISTRIBUTION problem, not a capacity one.
#
#   fraction of the route needing |steer| <= 0.01
#     Town04 eastbound  60.4 %      Town06 overall  83.8 %
#     Town04 westbound  56.0 %      Town06 s02     100.0 %
#                                   Town06 s03     100.0 %  (std 0.0000)
#
# Town04 curves continuously, so steering demand is always present. Town06 has two
# sections, ~1250 m of 3874 m, whose correct steering is identically zero for their
# whole length. A student trained on that emits ~0 with a small offset, and the straight
# sections integrate the offset into a departure -- measured on s03, CTE -0.18 -> -1.24
# -> -8.59 with the sign never changing, while the teacher oscillates about zero.
#
# The fix is distill.py --balance (straight-frame downsampling), which train.py has had
# for the teachers since the start and which distill.py never had, so the STUDENT -- the
# model that actually gets certified -- always trained on the raw distribution. Teachers
# absorb the imbalance at ~107k ReLU; a 5-15k ReLU student does not.
#
#   (name, checkpoint stem, conv channels, FC width)
TOWN06_STUDENTS = (
    ("S_clear_t06", "S_clear_t06_84x28",    (8, 16, 16), 32),
    ("S_mixed_t06", "S_mixed_t06_84x28_w3", (24, 48, 48), 96),
)


def relu_count(channels, fc, in_h=28, in_w=84):
    """ReLU neurons, so it can be reported next to every certified rate (4ac6002:
    a larger model has looser bounds, and that must stay visible rather than be
    engineered away)."""
    h, w = in_h, in_w
    n = 0
    for c, k in zip(channels, (5, 5, 3)):          # StudentNet: 5x5 s2, 5x5 s2, 3x3 s2
        h = (h - k) // 2 + 1
        w = (w - k) // 2 + 1
        n += c * h * w
    return n + fc


def final_student(base):
    """The checkpoint that IS the student: the newest student-DAgger round, else base.

    distill.py writes <base>.pth and dagger_student.py then writes
    <base>_dagger_r00.pth, _r01.pth, ... The distilled checkpoint is an intermediate,
    not the policy: measured on Town06, the base S_clear held 1 of 6 sections in clear
    weather with a worst |CTE| of 16.50 ft, while three rounds of student DAgger took
    the same student to 4 of 6 at 8.57 ft.

    Every downstream stage named the BASE. The competence gate therefore tested a model
    nobody intends to ship, and the certifier and ledger would have certified and driven
    it too -- bounding and measuring a policy that is not the one under study.
    """
    import glob as _glob
    rounds = _glob.glob(os.path.join(CHECKPOINT_DIR, f"{base}_dagger_r*.pth"))
    if not rounds:
        return base
    def _n(p_):
        m = re.search(r"_dagger_r(\d+)\.pth$", p_)
        return int(m.group(1)) if m else -1
    return os.path.basename(max(rounds, key=_n))[:-4]


# ── Unit conversions ─────────────────────────────────────────────────────────
M_TO_FT = 3.28084

# ═══════════════════════════════════════════════════════════════════════════
# DERIVED SAFETY CRITERIA  (do not hardcode — computed from primitives above)
# ═══════════════════════════════════════════════════════════════════════════

# Success criterion: no part of the vehicle body leaves its lane. Expressed as a
# limit on the vehicle-center-to-lane-center CTE. Using the CARLA bounding box
# (2.164 m, includes mirrors) is the defensible in-simulator choice.
#   (spec body 1.849 m would give 2.71 ft — kept for paper discussion only.)
CTE_BUDGET_M = (LANE_WIDTH_M - VEHICLE_WIDTH_M) / 2.0     # 0.668 m
CTE_BUDGET_FT = CTE_BUDGET_M * M_TO_FT                    # 2.19 ft

# Verification corridor: max per-frame steering deviation that keeps CTE within
# budget if a systematic bias persists for T_HORIZON_S. Bicycle model:
#   y(t) = v^2 * dtheta / (2L) * t^2  ->  dtheta_max = 2 L y / (v^2 T^2)
T_HORIZON_S = 1.0
STEER_CORRIDOR_RAD = (2.0 * WHEELBASE_M * CTE_BUDGET_M) / (TARGET_SPEED_MS ** 2 * T_HORIZON_S ** 2)
STEER_CORRIDOR_DEG = math.degrees(STEER_CORRIDOR_RAD)    # 2.88 deg
STEER_CORRIDOR_NORM = STEER_CORRIDOR_RAD / MAX_STEER_RAD  # 0.041 (network output units)

# The per-frame corridor above is ~3.4x TOO PERMISSIVE as a certification target: a
# vehicle departed the road with every single frame inside it. Certify against the
# closed-loop tolerance instead.
#
# The primitive is the MEASURED stability cliff, ~0.012 in network output units.
# It is expressed here as an equivalent bias horizon rather than written down as a
# literal, so that it stays consistent with the geometry: if lane width or vehicle
# width changes, the tolerance moves with them. T_CLOSED_LOOP_S is a property of the
# closed-loop dynamics (how long a steering bias persists before the loop corrects
# it) and is independent of lane geometry, which is what makes this the right
# quantity to hold fixed.
#
#   0.041 / 0.012 = 3.42  ->  T = 1.0 s * sqrt(3.42) = 1.85 s
#
# ── BE PRECISE ABOUT WHAT THIS IS (F45) ──────────────────────────────────────
# T_CLOSED_LOOP_S is CALIBRATED, not derived. It is back-solved so the tolerance
# reproduces the measured stability cliff, and that cliff was measured on the same
# closed-loop runs the certificate is later validated against. The study must NOT
# describe the criterion as having "no fitted parameter": it has exactly one, and
# it was fitted on the validation labels.
#
# That is defensible only because it is ONE global constant, calibrated once, never
# per cell -- and because the verdicts survive a wide range of it. Swept against the
# twelve committed cells (scripts/tolerance_sensitivity.py):
#
#     T = 1.00 s   10/12   BOTH shadows cells CERTIFIED while departing 10/10
#     T = 1.23 s   11/12
#     T = 1.50 s   12/12   <- a literature reaction time also works
#     T = 1.85 s   12/12   <- this value
#     T = 2.13 s   11/12
#     admissible window: T in (1.231, 2.128) s
#
# The failure at T = 1.0 s is the one to remember: that is the a-priori one-second
# horizon of T_HORIZON_S above, and at it the criterion issues UNSOUND CERTIFICATES
# on two cells that leave the lane on every run. The ordering of the cells is correct
# at every T -- the 3.0x separation is a ratio and is invariant -- so what T buys is
# the PLACEMENT of the threshold inside that gap, and T was chosen by looking at
# where the gap is.
T_CLOSED_LOOP_S = 1.85       # [CALIBRATED on closed-loop data -- see F45 above]
T_CLOSED_LOOP_ADMISSIBLE_S = (1.231, 2.128)   # verdicts unchanged inside this window
CLOSED_LOOP_TOLERANCE_RAD = (
    (2.0 * WHEELBASE_M * CTE_BUDGET_M) / (TARGET_SPEED_MS ** 2 * T_CLOSED_LOOP_S ** 2)
)
CLOSED_LOOP_TOLERANCE = CLOSED_LOOP_TOLERANCE_RAD / MAX_STEER_RAD

# ── Output paths ─────────────────────────────────────────────────────────────
# Everything the pipeline writes stays inside the repo. A default pointing at an
# older generation's directories once trained a student on stale data.
_BASE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_BASE)
DATASET_DIR = os.path.join(_BASE, "data")
CHECKPOINT_DIR = os.path.join(_BASE, "checkpoints")
RESULTS_DIR = os.path.join(_BASE, "results")


def summary():
    """Human-readable dump of the derived safety criteria."""
    return (
        f"CTE budget      : {CTE_BUDGET_M:.4f} m ({CTE_BUDGET_FT:.3f} ft)\n"
        f"Steer corridor  : {STEER_CORRIDOR_DEG:.3f} deg "
        f"({STEER_CORRIDOR_RAD:.4f} rad, {STEER_CORRIDOR_NORM:.4f} norm) "
        f"@ T={T_HORIZON_S}s\n"
        f"Speed / dt      : {TARGET_SPEED_MPH} mph, {FIXED_DT}s ({SIM_HZ:.0f} Hz)\n"
        f"Wheelbase       : {WHEELBASE_M} m | max steer {math.degrees(MAX_STEER_RAD):.1f} deg"
    )


if __name__ == "__main__":
    print(summary())

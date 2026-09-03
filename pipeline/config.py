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

# ── Determinism ──────────────────────────────────────────────────────────────
# DETERMINISTIC_CONTROL routes every vehicle command through an ACKNOWLEDGED batch
# command instead of the fire-and-forget `vehicle.apply_control()` RPC.
#
# Measured, open loop, with the feedback cut and the command sequence a pure function
# of the step index (scripts/determinism_tier1_openloop.py):
#
#     vehicle.apply_control()   physics diverges the first time the command CHANGES;
#                               the applied-control READBACK differs between reps at
#                               the same step. Max divergence over 200 steps: ~60 m.
#     apply_batch_sync()        pose, velocity, gear and applied control bit-identical
#                               for every step of every rep.
#
# The race is invisible while a command is unchanged, because a late arrival re-applies
# the same value -- which is exactly why it went unnoticed and why divergence always
# appeared to start mid-run for no reason.
#
# DEFAULT IS TOWN06 ONLY. Town04 is the published artifact and must keep reproducing
# byte-for-byte until its own re-measurement is authorised, so with STUDY_MAP unset
# this is off and the code path is the original one.
# ON FOR EVERY MAP as of the Town04 redo. It defaulted off for Town04 while the published
# artifact had to keep reproducing byte-for-byte; that gate has served its purpose and
# Town04 is now being re-measured under the corrected harness. `main` still carries the old
# default, so reproducing the PUBLISHED study from the published branch is unaffected.
DETERMINISTIC_CONTROL = os.environ.get("DETERMINISTIC_CONTROL", "1") == "1"

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
    exp = dict(CONDITION_EXPOSURE.get(condition, _DAYLIGHT_EXPOSURE))
    return _shutter_override(condition, exp)


def _shutter_override(condition, exp):
    """EXPOSURE_SHUTTER_OVERRIDE exposes the knob a condition's exposure was CHOSEN with.

    Format is `<condition>:<shutter>`, e.g. `night:60`, and it is scoped ON PURPOSE. The
    other sweep knobs (FOG_DENSITY_OVERRIDE, SUN_ALTITUDE_OVERRIDE) are scalars that skip
    `clear` by a rule inside them; a bare scalar here would silently move the ANCHOR too,
    and every ratio this study calibrates against is a ratio TO clear. A sweep that moves
    its own reference measures nothing, and it would still print a number.

    So the variable names the condition it applies to and touches no other. That also
    makes a stray export visible in a log line rather than inferable from one.

    This is a SWEEP knob, never a setting: the committed value lives in
    CONDITION_EXPOSURE, PROTOCOL section 3 freezes that table by name, and
    closed_loop_ledger.py refuses a canonical cell while this is set.
    """
    v = os.environ.get("EXPOSURE_SHUTTER_OVERRIDE")
    if not v:
        return exp
    if ":" not in v:
        raise ValueError(
            f"EXPOSURE_SHUTTER_OVERRIDE must be '<condition>:<shutter>', got {v!r}. "
            "A bare number would move `clear` as well, and clear is the anchor every "
            "calibrated ratio is measured against.")
    want, shutter = v.split(":", 1)
    if want.strip() == condition:
        exp["shutter"] = float(shutter)
    return exp


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
#
# 2,861 m STOPPED BEFORE THE FINAL TURN. Measured on the route and confirmed by parking the
# car there and looking: the last 90-degree corner runs 2,880 -> 2,982 m, the junction
# begins at 2,996 m, and the lane markings end at 3,022 m. So the old cut discarded a full
# corner of marked road -- the most informative road on the lap for a lane-keeper -- and
# was in neither the certificate nor, effectively, anything else.
#
# 2,988 m is 6 m past the turn's exit (long enough to confirm the car straightens) and 8 m
# short of the junction, with dashed markings continuing ~34 m ahead of that point.
#
# The published Town04 run keeps 2,861 m so its artifacts still reproduce exactly; only the
# redo moves. The value is not in PROTOCOL section 3's frozen constants.
# (read the env var directly: TOWN04_REDO is defined further down, and a forward
# reference here would be a NameError on every import.)
LAP_END_M = 2988.0 if os.environ.get("TOWN04_REDO", "0") == "1" else 2861.0

# ── The two verifiable students ──────────────────────────────────────────────
# (name, checkpoint stem, conv channels, FC width). The mixed student is 3x the width of the
# clear-only one -- width, not input resolution, is the verifier-friendly capacity lever,
# because width adds parameters at fixed input-perturbation dimension. This registry was
# copy-pasted into ~20 scripts in three mutually incompatible shapes.
# TOWN04_REDO re-runs the Town04 study under the corrected simulator harness (T06-F22).
#
# It is a DISCOVERY test, as the published one was -- T_CLOSED_LOOP_S was back-solved from
# Town04's own closed-loop cliff, so its agreement measures sensitivity rather than
# prediction, and re-running it does not turn it into a deployment test. Town06 is the
# deployment test and a third map would be needed for another.
#
# Everything the redo writes is NAMESPACED, because the published artifacts are tracked in
# git under exactly these names and a redo would otherwise overwrite the record it is meant
# to be compared against: `results/ledger/clear__S_clear__closed_loop.json` and
# `checkpoints/S_clear_84x28.pth` are the paper's, not scratch space.
TOWN04_REDO = os.environ.get("TOWN04_REDO", "0") == "1"
_V2 = "_v2" if TOWN04_REDO else ""

STUDENTS = (("S_clear", f"S_clear_84x28{_V2}", (8, 16, 16), 32),
            ("S_mixed", f"S_mixed_84x28_w3{_V2}", (24, 48, 48), 96))

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

    # ── ONE LAP, with PPC bridges (Town06, from 2026-08-31) ──────────────────
    # If lap_meta.json exists it supersedes the section layout. The six sections were
    # disjoint pieces of road 70-500 m apart; the lap is a single continuous drive whose
    # intersections are bridged by pure pursuit because the policy is a lane-follower and
    # there is no lane to follow through them. See docs/design/town06_lap_control.png.
    _lap_meta = os.path.join(_rd, "lap_meta.json")
    LAP_BASED = os.path.exists(_lap_meta)
    if LAP_BASED:
        with open(_lap_meta) as _f:
            LAP_META = _json.load(_f)
        # BRIDGE_SPANS are arc-length ranges where PURE PURSUIT drives and NOTHING is
        # scored: the ODD boundary, made explicit and machine-readable rather than left
        # as prose. Everything outside them is the policy's, and is measured.
        BRIDGE_SPANS = [tuple(b) for b in LAP_META["bridges"]]
        LAP_TOTAL_M = float(LAP_META["length_m"])
        LAP_SCORED_M = float(LAP_META["scored_m"])
        SECTIONS = ["lap"]
        # Spawn ON the route's first point with the route's own heading. Taking the
        # marked start x/y with yaw 0 would place the car across the lane: the lap begins
        # heading south-west, not east, and warmup would start by driving off the road.
        import numpy as _np
        _lap0 = _np.load(os.path.join(_rd, "lap.npy"))[0]
        SPAWNS = {"lap": {"x": float(_lap0[0]), "y": float(_lap0[1]), "z": 0.5,
                          "yaw": float(_lap0[2])}}
        SECTION_LEN_M = {"lap": LAP_TOTAL_M}
        TOTAL_SCORED_M = LAP_SCORED_M
        SPAWN_EASTBOUND = SPAWN_WESTBOUND = SPAWNS["lap"]
        LAP_END_M = LAP_TOTAL_M
        SECTION_BASED = True          # per-span step caps still apply

    SECTION_BASED = locals().get("LAP_BASED", False) or "sections" in ROUTE_META
    if LAP_BASED:
        pass
    elif SECTION_BASED:
        # Section-based route (Town06, superseded by the lap). Town06's outer loop has
        # no dedicated opposing
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

def bridge_spans_for(section):
    """Arc-length ranges on `section` where PURE PURSUIT drives and nothing is scored.

    Empty on every map but Town06's lap. The lane centreline is undefined through an
    intersection, so a lane-follower asked to drive one is being scored outside its
    domain -- the spans are driven by the expert and excluded from every CTE.
    """
    if not globals().get("LAP_BASED", False) or section != SECTIONS[0]:
        return []
    return [tuple(b) for b in BRIDGE_SPANS]


def scored_len_m(section):
    """The road this study CLAIMS on `section`, in metres.

    NOT the route's geometry. On Town06's lap they differ by the 170 m of bridged
    intersection: geometry 2,289 m, scored 2,119 m.

    One definition, because the two consumers must agree or the certificate stops being
    comparable to the drives. The capture rig samples poses over THIS length and the
    certifier checks coverage against it; when the capture excluded bridges and the
    certifier still compared against geometry, the certifier refused a correct capture --
    and the other way round it would have certified 170 m of road no closed-loop cell
    scores. Standing rule 7 is two-sided: covering more than the study scopes is the same
    error as covering less.
    """
    if globals().get("LAP_BASED", False) and section == SECTIONS[0]:
        return float(LAP_SCORED_M)
    return float(SECTION_LEN_M.get(section, 0.0))


def steps_for(section, margin=1.0):
    """Control steps to drive exactly one section, at the fixed study speed.

    Driving PAST a section's end runs the vehicle into the unclean road the section was
    clipped to exclude, and it fails there for reasons that have nothing to do with the
    policy. Measured: with one 520-step limit applied to all six Town06 sections, the
    pure-pursuit oracle "failed" s03 and s04 at max|CTE| 2.08 m and 7.21 m, both in the
    last few steps. With per-section limits every section passes at <= 0.066 m.

    On the PUBLISHED Town04 run this is a no-op, deliberately: capping would truncate the
    lap those artifacts were produced with and silently change every published number.

    On the Town04 REDO it is a real cap, and the absence of one was a defect. The redo
    drove to loop closure (~1697 steps, 3,035 m) while its certificate covered the scored
    prefix, so HALF of every mixed-student run took its worst |CTE| beyond the scored road
    -- in the western junction, where the lane centreline is undefined and the markings
    leave the camera on approach. One cell was declared failed on a peak measured 174 m
    past the end of what was verified.

    Certificate and drives must cover the same road, or their agreement compares two
    different claims. This is the same defect as the 160 m capture, mirrored: there the
    evidence covered less than it claimed, here the driving covered more.
    """
    if not SECTION_BASED:
        if os.environ.get("TOWN04_REDO", "0") != "1":
            return 10 ** 9                      # published run: unchanged, on purpose
        return int(LAP_END_M * margin / (TARGET_SPEED_MS * FIXED_DT))
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
# BALANCING WAS TRIED AND IS REFUTED. distill.py --balance (straight-frame downsampling)
# made the clear student WORSE, 5-6/6 sections down to 0-2/6, worst |CTE| 23.08 ft. On a
# route that genuinely IS 84 % straight, downsampling straight frames trains the student
# for a distribution it will not meet. The flag stays in distill.py (train.py has always
# had it for teachers) but is OFF.
#
# So the clear student keeps Town04's size, and only the MIXED student is widened -- the
# lever Town04 itself established (4b2ad73: w1 failed all four conditions, w2 failed
# night 10/10, w3 passed everything) and the one Zach identified as justified, since the
# mixed student needs capacity for the disturbances rather than for the route.
#
# Input size is SHARED by both students, deliberately: the verification captures are
# projected to the model input at capture time, so two different input sizes would mean
# two capture sets (24 npz files each). Only channel width differs per student.
#
# 84x28 is the published Town04 size. Town06's long straights may need more HORIZONTAL
# resolution -- at 84 px the whole 0.668 m CTE budget spans 1.79 px of image shift at
# 20 m lookahead, and a 0.1 m error spans 0.27 px, so on a 620 m straight the only cue
# is sub-pixel. scripts/sweep_student_arch.py measures this closed-loop.
# MEASURED (T06-F11): 168x28. The control error is LATERAL, so horizontal resolution
# carries it and vertical buys nothing. At matched cost, 112x38 w2 (21,504 ReLU) holds
# 4/6 sections at 12.97 ft while 168x28 w2 (21,408) holds 6/6 at 0.97 ft -- inside the
# 2.19 ft budget with 2.3x margin, on all 3 reps, with NO student-DAgger. Town04's F11
# rejected resolution having tested only 112x38, which spends half the budget on the
# axis that does not help.
# INPUT SIZE. 168x56 is TOWN04's 84x28 DOUBLED IN BOTH DIMENSIONS.
#
# The student crop is rows 240:450 of a 640-wide frame -- 640x210, a native aspect
# of 3.05:1. Town04's 84x28 is 3.0:1 and therefore geometrically faithful. Town06
# was 168x28, which is 6.0:1: T06-F11 doubled the WIDTH to keep lane lines alive on
# this route's long straights and never doubled the height, so the Town06 student
# saw an image squashed 2x vertically while the published Town04 student did not.
# That is a difference between the two studies that nothing intended, and it
# compresses exactly the vertical structure the policy needs: the convergence of the
# lane lines, and at night the SHAPE of the headlight throw.
#
# 168x56 keeps T06-F11's doubled width, restores the aspect, and is simply Town04 at
# 2x resolution -- which is the closest this study can be to its reference while
# still answering the reason the width was raised.
TOWN06_INPUT_W, TOWN06_INPUT_H = (int(os.environ.get("T06_IN_W", "168")),
                                  int(os.environ.get("T06_IN_H", "56")))

#   (name, checkpoint stem, conv channels, FC width)
TOWN06_STUDENTS = (
    # The LAP rebuild's students. The six-section checkpoints keep their own names
    # (S_clear_t06_168x28_w2 / S_mixed_t06_168x28_w3) because they are a valid study on a
    # different route, not a superseded attempt at this one.
    ("S_clear_t06", "S_clear_t06lap_168x56_w2", (16, 32, 32), 64),
    # THE RATIO, NOT THE ABSOLUTE WIDTH, IS WHAT TOWN04 SET.
    #
    # Published Town04 is clear (8,16,16)/fc32 -> mixed (24,48,48)/fc96: the mixed student
    # is 3.0x the clear one's width, because it represents four conditions and the clear
    # one represents a single point. The comment below claimed to follow that precedent
    # and did not: Town06's CLEAR student was itself widened w1 -> w2 for the straights
    # (T06-F11), the mixed student stayed at w3, and the ratio silently halved to 1.5x.
    #
    #     Town04    clear  5,152 ReLU  ->  mixed 15,456   3.0x
    #     Town06    clear 21,408 ReLU  ->  mixed 32,112   1.5x   (w3, was here)
    #     Town06    clear 21,408 ReLU  ->  mixed 42,816   2.0x   (w4, now)
    #
    # w4 is also the width T06-F18 measured as the best of five at this input size --
    # 33/48 cells against w3's 15/48, on the six-section route -- and it is the step the
    # architecture sweep would have taken first anyway.
    # THE MIXED STUDENT IS WIDER THAN THE CLEAR ONE, as in published Town04
    # (S_clear (8,16,16)/fc32 against S_mixed (24,48,48)/fc96). There is no reason for the
    # two to match: they fit different functions, and only the mixed one has to represent
    # four conditions.
    #
    # The previous entry pinned both at w2 on the authority of T06-F14, which A-2
    # discarded along with its data. Measured on the REBUILD (T06-F29), w2 mixed drove
    # 22/24 exploratory cells and failed fog/s00 at 8.52 ft and shadows/s02 at 2.99 ft --
    # while the teacher it was distilled from holds those same two cells 3/3 at 0.37-0.40
    # and 0.41-0.49 ft. The teacher is competent and the student cannot reproduce it, so
    # the gap is student capacity and width is the direct lever. This is the same
    # conclusion Town04 reached at 4b2ad73, where w1 failed all four conditions, w2 failed
    # night 10/10 and w3 passed everything.
    # w4 = 2.0x the clear student. w6 (3.0x, Town04's ratio) was tried and did NOT fix
    # fog either -- 11.64 ft against w4's 11.15 -- so the extra 50,000 ReLU buys nothing
    # here and the smaller model is preferred. Fog is not a capacity problem:
    # (clear (8,16,16)/fc32 -> mixed (24,48,48)/fc96). At 168x56 the w4 mixed student held
    # clear 0.83 ft, night 0.68 and low sun 0.70 -- all with 62-69% margin -- and failed
    # FOG alone at 11.15 ft, on 22-25% of the lap. Fog is the one condition where more
    # pixels cannot help: airlight lifts the black floor (p01 0.186), so the lane markings
    # lose contrast against the road rather than resolution, and 168x28 -> 168x56 moved fog
    # the wrong way (6.85 -> 11.15 ft) while fixing night and low sun.
    #
    # So the remaining lever is capacity for the condition the network cannot separate,
    # which is the same conclusion Town04 reached when it put its mixed student at 3x.
    ("S_mixed_t06", "S_mixed_t06lap_168x56_w4", (32, 64, 64), 128),
)

# ── PASS 3: the two mixed widths, swept under a MARGIN gate ──────────────────
# docs/TOWN06_PASS3_PREREGISTRATION.md, committed before any draw.
#
# The comment above records w6 as "tried and did NOT fix fog either -- 11.64 ft against
# w4's 11.15". T06-F55 withdraws that: both numbers are ONE distillation from ONE seed,
# and 389f192 -- committed six hours after the w6 checkpoint was written -- measured a
# re-draw of one UNCHANGED configuration swinging 1.16 -> 8.68 ft. A 7.5 ft swing cannot
# resolve a 0.49 ft difference. w4 ships its fourth draw; w6 was never given a second.
#
# So the widths are swept against each other under one criterion, fixed in advance.
#
#     w4  (32,64,64)/128  101,888 ReLU   2.0x the clear student
#     w6  (48,96,96)/192  152,832 ReLU   3.0x -- published Town04's ratio
#
# PIN NAMES ARE SEPARATE ON PURPOSE. The sweep pins under "<base>p3", so re-sweeping w4
# cannot overwrite S_mixed_t06lap_168x56_w4.selected -- the pin passes 1 and 2 resolve
# through. Overwriting it would silently change which model those committed results refer
# to, which is the failure PROTOCOL R4 exists to prevent.
TOWN06_PASS3_WIDTHS = (
    # (name, SWEEP base -- where _s<seed> checkpoints live, PIN base, channels, fc)
    ("S_mixed_t06_w4", "S_mixed_t06lap_168x56_w4",
     "S_mixed_t06lap_168x56_w4p3", (32, 64, 64), 128),
    ("S_mixed_t06_w6", "S_mixed_t06lap_168x56_w6",
     "S_mixed_t06lap_168x56_w6p3", (48, 96, 96), 192),
)

# Every GATE lap must stay under this fraction of the CTE budget. The screen stays at the
# full budget. Fixed before the first draw and not to be moved afterwards: the shipped
# w4_s3 holds only 6/12 laps under it (fog 1.78/1.28/1.18, low sun 1.10/1.21/1.26 against
# 1.096 ft), which is the point.
TOWN06_PASS3_GATE_MARGIN = 0.50


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


# Does this study's procedure INCLUDE student DAgger?
#
# BOTH maps run it, and this flag must agree with the DRIVER that runs it or the study
# breaks in a way no result reveals. It said `STUDY_MAP == "Town04"` while
# run_town06_pipeline.sh ran the stage for Town06 -- restored by T06-F25, because
# T06-F14 removed it on evidence that A-2 then discarded outright. The two halves of
# that restoration were never joined:
#
#   * final_student() RAISES for Town06 the moment a <base>_dagger_rNN checkpoint
#     exists, which the stage produces. The competence gate, the ledger and the
#     certifier all call it, so the pipeline would have died immediately after student
#     DAgger with an error saying the checkpoints were "stale artefacts of a procedure
#     this study has abandoned" -- about a stage it had just deliberately run.
#   * Had it not raised, it would have returned the DISTILLED intermediate while the
#     stage shipped a DAgger'd model, which is the "certify a model nobody intended to
#     ship" failure the same function was written to prevent.
#
# Town04's published pipeline is behaviour cloning -> teacher DAgger -> distillation ->
# STUDENT DAgger (README "Reproduce", and the archived dagger_student_clear /
# dagger_student_w3 round directories). Town06 is the deployment test of that same
# pipeline, so it runs the same procedure; whether student DAgger HELPS at 168x28 is
# then a measurement the competence gate and the three-lap ledger make on the corrected
# harness, which is exactly what T06-F25 asked for and what nobody has.
STUDENT_DAGGER = True


def final_student(base):
    """The checkpoint that IS the student.

    Which one that is depends on whether the study RUNS student DAgger, so this is gated
    on STUDENT_DAGGER rather than assumed. Getting it wrong certifies a model nobody
    intended to ship, in either direction: preferring a DAgger round where the procedure
    no longer runs one selects a stale artefact, and preferring the distilled
    intermediate where the procedure DOES run one selects a model that is not the policy.

    Both maps currently run student DAgger, so this returns the newest round. The
    STUDENT_DAGGER = False branch below is kept because the choice is a property of the
    PROCEDURE, not of the map, and a study that stops running the stage must not silently
    keep driving its leftovers:

    This function used to return the newest <base>_dagger_rNN, because student DAgger
    was part of the procedure and every downstream stage was naming the distilled
    intermediate -- the gate, the certifier and the ledger would each have used a model
    nobody intended to ship.

    T06-F14 removed student DAgger: at 168x28 it is harmful, not merely unnecessary
    (mixed 6/6 -> 3/6 on a 3-rep clear gate). So the distilled checkpoint IS the policy
    and the old preference is exactly backwards -- it now selects the artefact of a
    procedure that is no longer run. That is not hypothetical: it happened. A gate run
    reported the mixed student at 3/6 and the clear student at 5/6, both NOT COMPETENT,
    while the freshly distilled checkpoints sat unread beside them, and the 3/6 matched
    the DAgger'd model's measured score exactly.

    Stale rounds are therefore a hard error rather than a warning. They are only ever
    left behind by a procedure this study has abandoned, and silently preferring either
    checkpoint is how the wrong model gets certified.
    """
    import glob as _glob

    # A PIN BEATS A TIMESTAMP.
    #
    # "The student is the newest <base>_dagger_rNN" is an inference from the filesystem,
    # and this study has now been bitten four separate times by reading a stale artifact
    # as though the current step produced it. The last one was expensive: a DAgger run
    # resumed from an r03 left behind by an abandoned run and destroyed a policy that had
    # just passed all four conditions.
    #
    # Which checkpoint IS the student is a decision made by a gate, so it is recorded by
    # the gate that made it. `<base>.selected` holds one checkpoint name; if it names a
    # file that exists, that file is the student and nothing about mtimes matters.
    _pin = os.path.join(CHECKPOINT_DIR, f"{base}.selected")
    if os.path.exists(_pin):
        with open(_pin) as _fh:
            _name = _fh.read().strip()
        if _name and os.path.exists(os.path.join(CHECKPOINT_DIR, f"{_name}.pth")):
            return _name
        raise RuntimeError(
            f"{base}.selected names '{_name}', which is not in {CHECKPOINT_DIR}. A pin "
            f"that points at nothing is worse than no pin: fix or remove it.")

    rounds = sorted(_glob.glob(os.path.join(CHECKPOINT_DIR, f"{base}_dagger_r*.pth")))

    if STUDENT_DAGGER:
        # Town04: student DAgger is part of the procedure, so the newest round IS the
        # policy and the distilled checkpoint is the intermediate.
        if not rounds:
            return base          # not yet DAgger'd; the distilled one is all there is
        return os.path.splitext(os.path.basename(rounds[-1]))[0]

    stale = rounds
    if stale:
        raise RuntimeError(
            f"{len(stale)} student-DAgger checkpoint(s) for '{base}' are still in "
            f"{CHECKPOINT_DIR}. Student DAgger was removed by T06-F14 and these are "
            f"stale artefacts of it; leaving them there is how the wrong model gets "
            f"certified. Move them to checkpoints/_superseded_student_dagger/ "
            f"(they are kept, not deleted) and re-run.")
    return base


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

# The Town04 redo keeps its results beside the published ones rather than on top of them,
# so old and new can be compared directly in the working tree. Comparing them IS the
# result of a discovery-test redo.
LEDGER_DIR = os.path.join(REPO_ROOT, "results",
                          "town04_v2" if TOWN04_REDO else "", "ledger")


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

"""
Single source of truth for the E2E steering pipeline.

Design rule: measured PRIMITIVES are declared explicitly; every SAFETY number
(CTE budget, steering corridor) is DERIVED from them below, so the two can never
silently disagree. All primitives marked [MEASURED] were verified in CARLA
(Town04, Tesla Model 3) on 2026-07-22 via scripts/probe_geometry.
"""
import math
import os

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
MAP_NAME = "Town04"

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
LANE_WIDTH_M = 3.500         # [MEASURED] constant on Town04 highway, both dirs

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

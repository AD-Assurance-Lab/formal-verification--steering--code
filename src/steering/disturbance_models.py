#!/usr/bin/env python3
"""
Formally verifiable disturbance models for fog, rain, night and snow.

APPLIED AT FULL SENSOR RESOLUTION, BEFORE CROP AND DOWNSAMPLE.
--------------------------------------------------------------
Weather happens in the world, not in a network's input tensor. Applying a disturbance to
the 84x28 student input makes it model-specific and quantitatively wrong: each student
pixel averages ~57 full-resolution pixels, so thin structure (rain streaks, snow flakes)
is diluted several-fold by the downsample. Injecting post-downsample simulates streaks
far brighter than any real drop. The pipeline must be:

    render (or capture) -> APPLY DISTURBANCE at full resolution -> crop -> downsample -> net

Verifiable form
---------------
Every model is **linear in its bounded parameters** with the nominal frame fixed, so each
is one prepended linear layer for a bound propagator, exactly as in `perturbations.py`.
Clamping to [0,1] is applied as monotone piecewise-linear ReLU ops (see that module for
why sound saturation modelling is not optional).

Parameters are **measured meteorological quantities**, not fitted constants:

  fog   : meteorological optical range MOR (m); beta = ln(20)/MOR
  rain  : MOR (weak veiling) + streak amplitude; wet-road darkening
  snow  : MOR (veiling toward white) + flake amplitude
  night : ambient road illuminance relative to headlight peak, + sensor noise

Shared physical core: every condition imposes a VISIBILITY LIMIT that destroys far-field
information (this is what a global contrast change cannot do), plus condition-specific
near-field structure.

Geometry: flat road, d(row) = h*f/(row - horizon), from each platform's known camera.
"""
import numpy as np
import cv2

# CARLA model camera (config.py): 640x480, FOV 90 -> f = 320 px, z = 1.2 m, level.
CARLA_GEOM = dict(f_px=320.0, h_cam_m=1.2, horizon_row=240.0)


# ---------------------------------------------------------------- shared core
MAX_DEPTH_M = 400.0     # a real road does not extend to infinity in view


def depth_by_row(h, f_px, h_cam_m, horizon_row, max_depth_m=MAX_DEPTH_M):
    """Flat-road depth per image row, capped at a finite maximum.

    Without the cap, depth at the horizon row is infinite, so transmission is exactly
    zero there for ANY visibility and the top of the crop is painted pure airlight even
    in light rain. That is an artefact of the flat-infinite-road idealisation: in reality
    terrain, curvature and the road's own geometry bound how far the surface is visible.
    """
    rows = np.arange(h, dtype=np.float64) + 0.5
    below = rows - horizon_row
    d = np.full(h, max_depth_m)
    np.divide(h_cam_m * f_px, below, out=d, where=below > 0)
    return np.minimum(d, max_depth_m)


def transmission(h, mor_m, geom=CARLA_GEOM):
    """Koschmieder transmission per image row. t = exp(-beta*d), beta = ln(20)/MOR.
    Above the horizon d is infinite so t = 0, i.e. the sky becomes pure airlight, which
    is physically correct."""
    beta = np.log(20.0) / float(mor_m)
    d = depth_by_row(h, **geom)
    with np.errstate(over="ignore"):
        t = np.exp(-beta * d)
    t[~np.isfinite(t)] = 0.0
    return t


def _veil(img, t_rows, airlight):
    """x' = A + t(row) * (x - A). Linear in t; destroys far-field information as t -> 0."""
    A = np.asarray(airlight, np.float32).reshape(1, 1, -1)
    return A + t_rows.astype(np.float32).reshape(-1, 1, 1) * (img - A)


# ---------------------------------------------------------------- structure bases
def streak_layer(h, w, amplitude, density=6e-4, length=26, angle_deg=12.0, seed=0):
    """Bright oriented rain streaks at FULL resolution.

    A falling drop images as a short bright streak whose length is set by drop velocity
    and exposure time. The pattern is fixed and only its amplitude is bounded, which keeps
    the model linear; that covers a family of intensities rather than every placement,
    which is a stated approximation.
    """
    rng = np.random.RandomState(seed)
    lay = np.zeros((h, w), np.float32)
    dy, dx = np.cos(np.radians(angle_deg)), np.sin(np.radians(angle_deg))
    for _ in range(max(1, int(density * h * w))):
        y0, x0 = rng.randint(0, h), rng.randint(0, w)
        L = int(length * rng.uniform(0.6, 1.4))
        for k in range(L):
            y, x = int(y0 + k * dy), int(x0 + k * dx)
            if 0 <= y < h and 0 <= x < w:
                lay[y, x] = 1.0
    lay = cv2.GaussianBlur(lay, (0, 0), 0.7)          # drops are not one pixel wide
    if lay.max() > 0:
        lay /= lay.max()
    return (amplitude * lay)[..., None]


def flake_layer(h, w, amplitude, density=2.5e-4, r_min=1, r_max=5, seed=0):
    """Bright snow flakes at FULL resolution.

    Flakes *occlude*: they replace scene content rather than adding to it. Modelling them
    as a bounded bright additive layer over-approximates in the bright direction and
    under-approximates full replacement. That gap is the honest edge of what this
    paradigm can certify, and it is why snow is the hardest of the four.
    """
    rng = np.random.RandomState(seed)
    lay = np.zeros((h, w), np.float32)
    for _ in range(max(1, int(density * h * w))):
        y, x = rng.randint(0, h), rng.randint(0, w)
        r = rng.randint(r_min, r_max + 1)
        cv2.circle(lay, (x, y), r, 1.0, -1)
    lay = cv2.GaussianBlur(lay, (0, 0), 0.8)
    if lay.max() > 0:
        lay /= lay.max()
    return (amplitude * lay)[..., None]


def headlight_field(h, w, geom=CARLA_GEOM, beam_m=55.0, sharpness=3.0, lateral_deg=34.0):
    """Relative road irradiance from the ego low beams.

    A bare point source would give 1/d^3 on the road (1/d^2 irradiance times the h/r
    incidence cosine), which produces a tight blazing spot at the bumper and darkness
    everywhere else. Real low beams are **aimed**: the luminous intensity I(theta) rises
    toward the horizontal precisely to compensate that falloff, which is why a real beam
    pattern looks like a broad, fairly even pool out to its design range and then cuts
    off. Modelling the bare inverse-cube law is a mistake that makes night look nothing
    like night.

    We therefore model the *designed* result directly: roughly uniform illumination to
    `beam_m`, then a rolloff of order `sharpness`.
    """
    d = depth_by_row(h, **geom)
    with np.errstate(over="ignore", invalid="ignore"):
        g = 1.0 / (1.0 + (d / float(beam_m)) ** sharpness)
    g[~np.isfinite(g)] = 0.0
    cols = np.arange(w) + 0.5 - w / 2.0
    phi = np.degrees(np.arctan2(cols, geom["f_px"]))
    lat = np.exp(-(phi / lateral_deg) ** 2)
    L = g[:, None] * lat[None, :]
    return (L / L.max()) if L.max() > 0 else L


# ---------------------------------------------------------------- road accumulation
def lane_masks(h, w, geom=CARLA_GEOM, track_half_m=0.80, tire_half_m=0.12,
               lane_half_m=1.75, soften=2.5):
    """Where water and snow accumulate on the road, from lane geometry.

    The ego holds one lane for the whole route, so the accumulation pattern is FIXED in
    the image and can be a fixed basis with a bounded amplitude, which keeps the model
    linear and verifiable.

    At depth d a lateral offset y images at column w/2 + f*y/d, so the wheel paths trace
    two bands converging on the vanishing point. Water pools IN the worn wheel ruts;
    snow survives OUTSIDE them, in the strip between the tracks and beyond the lane
    edges, because tyres clear only what they run over.

    Returns (ruts, verge): the worn wheel ruts where water pools, and the
    off-lane verge where snow accumulates.
    """
    d = depth_by_row(h, **geom)[:, None]
    cols = (np.arange(w)[None, :] - w / 2.0)
    y = np.abs(cols * d / geom["f_px"])                      # lateral distance, metres
    on_road = (np.arange(h)[:, None] > geom["horizon_row"]) & (y < lane_half_m)

    ruts = ((y > track_half_m - tire_half_m) & (y < track_half_m + tire_half_m) & on_road)

    # Snow accumulates OUTSIDE the travelled lane, on the verge and the lane boundary.
    # It does not sit in white stripes within the lane: traffic clears the lane surface,
    # which is why ACDC's snow scenes show a dark slushy lane with white at the edges.
    below = (np.arange(h)[:, None] > geom["horizon_row"])
    verge = (y > lane_half_m * 0.92) & (y < lane_half_m * 3.0) & below

    ruts = cv2.GaussianBlur(ruts.astype(np.float32), (0, 0), soften)
    verge = cv2.GaussianBlur(verge.astype(np.float32), (0, 0), soften * 1.6)
    return ruts, verge


def puddle_layer(h, w, geom=CARLA_GEOM, coverage=0.45, seed=0, s_offset_m=0.0,
                 span_m=140.0, lane_half_m=1.9, r_min_m=0.25, r_max_m=1.1):
    """Standing water placed in WORLD coordinates and projected into the image.

    Puddles are static features of the road, not of the image. Generating them in image
    space makes them jump between frames; generating them in world coordinates and
    projecting through the known camera geometry makes them flow toward the camera
    exactly as perspective dictates, so temporal consistency is free. `s_offset_m` is the
    distance travelled along the route, so advancing it animates the scene correctly.

    Rain streaks need no such treatment: a drop crosses the frame in milliseconds, so
    real streaks genuinely are uncorrelated between frames.
    """
    rng = np.random.RandomState(seed)
    lay = np.zeros((h, w), np.float32)
    n = max(1, int(coverage * 34))
    # world positions fixed once; only the along-track offset changes as we drive
    s0 = rng.uniform(2.0, span_m, n)
    lat = rng.uniform(-lane_half_m, lane_half_m, n)
    rad = rng.uniform(r_min_m, r_max_m, n)
    f, hc, hor = geom["f_px"], geom["h_cam_m"], geom["horizon_row"]
    for s_w, y_w, r_w in zip(s0, lat, rad):
        d = s_w - (s_offset_m % span_m)
        if d < 1.5 or d > span_m:
            d += span_m if d < 1.5 else 0.0
            if d < 1.5 or d > span_m:
                continue
        row = hor + hc * f / d
        col = w / 2.0 + f * y_w / d
        ax = max(1, int(f * r_w / d))                 # lateral half-extent, pixels
        ay = max(1, int(0.42 * f * hc * r_w / (d * d) * 6.0))   # foreshortened
        if 0 <= row < h:
            cv2.ellipse(lay, (int(col), int(row)), (ax, ay), 0, 0, 360, 1.0, -1)
    lay = cv2.GaussianBlur(lay, (0, 0), 2.0)
    return np.clip(lay, 0, 1)


# ---------------------------------------------------------------- the four models
def apply_fog(bgr, mor_m=150.0, airlight=(0.78, 0.78, 0.76), geom=CARLA_GEOM):
    """Koschmieder veiling toward a bright airlight."""
    x = bgr.astype(np.float32) / 255.0
    t = transmission(x.shape[0], mor_m, geom)
    return np.clip(_veil(x, t, airlight[::-1]), 0, 1)


def apply_rain(bgr, mor_m=1200.0, streaks=0.10, wet=0.38, specular=0.30,
               pooling=0.45, s_offset_m=0.0,
               airlight=(0.66, 0.66, 0.64), geom=CARLA_GEOM, seed=0):
    """Rain on a forward road camera.

    The dominant effect is **the road surface, not the airborne drops**: wet asphalt is
    darker and strongly specular, so it darkens overall while gaining bright smeared
    reflections. Streaks are present but faint at normal driving exposure, which is
    visible in both ACDC rain and CARLA's rendered rain. Veiling is weak; rain scatters
    far less than fog per unit visibility.
    """
    x = bgr.astype(np.float32) / 255.0
    t = transmission(x.shape[0], mor_m, geom)
    y = _veil(x, t, airlight[::-1])
    y = y * (1.0 - wet)                                   # wet asphalt is darker
    if specular > 0:                                      # smeared vertical reflections
        sm = cv2.GaussianBlur(y, (0, 0), 1.0, 9.0)
        y = y + specular * np.clip(sm - y.mean(), 0, None)
    if pooling > 0:
        pd = puddle_layer(x.shape[0], x.shape[1], geom, coverage=pooling,
                          seed=seed, s_offset_m=s_offset_m)[..., None]
        sky = cv2.GaussianBlur(y, (0, 0), 2.0, 14.0)
        y = y * (1.0 - 0.45 * pd) + 0.65 * pd * sky
    y = y + streak_layer(x.shape[0], x.shape[1], streaks,
                         density=3e-4, length=14, seed=seed)
    return np.clip(y, 0, 1)


def apply_snow(bgr, mor_m=1000.0, flakes=0.22, wet=0.20, specular=0.14,
               accumulation=0.80, snow_albedo=(0.92, 0.93, 0.95),
               airlight=(0.86, 0.86, 0.88), geom=CARLA_GEOM, seed=0):
    """Falling snow over a wet, partly-covered road.

    ACDC snow shows a **slushy dark road with snow at the verges**, not a whiteout: the
    travelled lane is cleared by traffic and is wet, while accumulation sits off-lane.
    Airborne flakes are present but sparse at driving exposure. Modelling snow as heavy
    veiling toward white is what a stationary observer in a blizzard sees, not what a
    forward road camera sees.
    """
    x = bgr.astype(np.float32) / 255.0
    t = transmission(x.shape[0], mor_m, geom)
    y = _veil(x, t, airlight[::-1])
    y = y * (1.0 - wet)
    if specular > 0:
        sm = cv2.GaussianBlur(y, (0, 0), 1.0, 7.0)
        y = y + specular * np.clip(sm - y.mean(), 0, None)
    if accumulation > 0:
        # snow survives where tyres do not sweep: the strip between the wheel tracks and
        # the lane edges, sitting at near-white. This is the visual signature of a snowy
        # road and it can bury or mimic lane markings, which is the real hazard.
        _, verge = lane_masks(x.shape[0], x.shape[1], geom)
        u = (accumulation * verge)[..., None]
        snow_col = np.asarray(snow_albedo, np.float32).reshape(1, 1, -1)[..., ::-1]
        y = y * (1.0 - u) + u * snow_col
    y = y + flake_layer(x.shape[0], x.shape[1], flakes, density=1.2e-4,
                        r_min=1, r_max=3, seed=seed)
    return np.clip(y, 0, 1)


def apply_night(bgr, ambient=0.10, noise=0.004, geom=CARLA_GEOM,
                auto_exposure=True, seed=0):
    """Scene lit only by the ego headlights plus a small ambient term, then AUTO-EXPOSED.

    An AV camera auto-exposes, so the raw illumination drop is largely restored and what
    reaches the network is the *structure* that survives: a bright near-field pool, an
    unlit far field, and elevated sensor noise from the exposure gain.
    """
    x = bgr.astype(np.float32) / 255.0
    L = headlight_field(x.shape[0], x.shape[1], geom)[..., None]
    y = x * (L + ambient) / (1.0 + ambient)
    if auto_exposure:
        y = y * (x.mean() / max(y.mean(), 1e-6))
    if noise > 0:
        y = y + np.random.RandomState(seed).normal(0, noise, y.shape).astype(np.float32)
    return np.clip(y, 0, 1)


# ---------------------------------------------------------------- output level
# Measured on ACDC (road ROI, train, 400 frames/condition): the ratio of adverse road
# level to that condition's own clear-reference road level. Because an AV camera
# auto-exposes, the ABSOLUTE level a network receives is set by the exposure control, not
# by the raw illumination drop; this ratio is what actually survives to the sensor output.
# The meteorological standard supplies the disturbance STRUCTURE (visibility, spatial
# profile); ACDC supplies the LEVEL. That is the division of labour we settled on:
# standards calibrate, ACDC validates.
# All referenced to the SAME clean daylight baseline (the fog condition's reference set,
# road-ROI mean 0.412), not to each condition's own reference. Night's own reference set
# is contaminated with dusk and twilight frames (V2_FINDINGS F11), so using it would make
# modelled night 1.13x BRIGHTER than clear, which is plainly wrong.
_ACDC_ADVERSE_LEVEL = {"fog": 0.291, "rain": 0.232, "night": 0.274, "snow": 0.346}
_ACDC_CLEAR_BASELINE = 0.412
ACDC_LEVEL_RATIO = {k: round(v / _ACDC_CLEAR_BASELINE, 3)
                    for k, v in _ACDC_ADVERSE_LEVEL.items()}

ROAD_TOP, ROAD_BOT = 240, 450          # the region the network is cropped to


def match_level(disturbed, clear_bgr, cond, top=ROAD_TOP, bot=ROAD_BOT):
    """Rescale so the road-region mean equals the ACDC-measured ratio times the clear
    road mean, i.e. apply the exposure control an AV camera would apply."""
    clear = clear_bgr.astype(np.float32) / 255.0
    target = ACDC_LEVEL_RATIO[cond] * float(clear[top:bot].mean())
    cur = float(disturbed[top:bot].mean())
    if cur < 1e-6:
        return disturbed
    return np.clip(disturbed * (target / cur), 0, 1)


MODELS = {"fog": apply_fog, "rain": apply_rain, "snow": apply_snow, "night": apply_night}

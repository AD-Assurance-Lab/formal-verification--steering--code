"""
Clean CARLA interface: connection, world/sync setup, spawning, a PHYSICS-HONEST
constant-speed controller (throttle/brake, not a velocity override), and image
helpers. The velocity-override approach in the legacy code corrupted lateral
dynamics and could stall the vehicle; a speed controller keeps physics intact so
the CTE we measure is real.
"""
import math
import queue

import carla
import numpy as np

import config as C
from config import (
    HOST, PORT, CLIENT_TIMEOUT_S, MAP_NAME, VEHICLE_BLUEPRINT,
    CAM_WIDTH, CAM_HEIGHT, CAM_FOV, CAM_X, CAM_Y, CAM_Z,
    TARGET_SPEED_MS, MPH_PER_MS, FIXED_DT,
)
# Re-export the shared image helpers so existing callers (env.raw_to_bgr,
# env.preprocess_for_model) keep working while the definition lives in imaging.
from imaging import raw_to_bgr, preprocess_for_model  # noqa: F401


# ── Connection / world ───────────────────────────────────────────────────────

def connect():
    client = carla.Client(HOST, PORT)
    client.set_timeout(CLIENT_TIMEOUT_S)
    return client


def load_study_map(client, fresh=True):
    """Return a world for config.MAP_NAME (STUDY_MAP; default Town04).

    With fresh=True (default) the world is reloaded on every connect, clearing any
    accumulated actors/state from prior runs on a long-lived CARLA server (which can
    silently corrupt closed-loop results).
    """
    world = client.get_world()
    if world.get_map().name.split("/")[-1] != MAP_NAME:
        return client.load_world(MAP_NAME)      # loads a fresh map
    return client.reload_world() if fresh else world  # already right map -> reload fresh


# Name kept so existing entry points and the published study read unchanged. It now
# honours STUDY_MAP, which is the whole point: one pipeline, two maps.
load_town04 = load_study_map


def enable_sync_mode(world):
    """
    Enable fixed-step synchronous mode. Returns original settings to restore.

    CARLA requires  fixed_delta_seconds <= max_substep_delta_time * max_substeps,
    or physics silently advances less than the full step (the car covers half the
    distance its velocity implies). We size the substeps to cover the full dt.
    """
    original = world.get_settings()
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = FIXED_DT
    settings.substepping = True
    # CARLA requires max_substeps in [1,16] AND max_substep_delta_time*max_substeps
    # >= fixed_delta_seconds (else physics silently advances less than the full step).
    settings.max_substeps = 16
    settings.max_substep_delta_time = FIXED_DT / 16   # 0.0125 for dt=0.2 -> full 0.2s
    world.apply_settings(settings)
    return original


# ── Conditions ───────────────────────────────────────────────────────────────
#
# A preset is built by CONSTRUCTING a fresh WeatherParameters and setting every field
# explicitly. It is NOT built by reading the live weather and editing it.
#
# That distinction is the whole bug this replaced. `world.set_weather()` is applied by
# the simulator on the NEXT TICK, so a `world.get_weather()` issued immediately after
# returns the PREVIOUS condition's values. The old code cleared fog, read back the stale
# (still-foggy) parameters, set the sun angle on that object and pushed it -- which
# reinstated fog. Night therefore ran at fog_density 70, verified live:
# sun_altitude_angle -25 with fog_density 70. Caught by Zach watching the render.
#
# Same shape as trap 2, where CARLA's sensor queue runs a frame behind: a read issued
# straight after a write returns the old value, and nothing errors.
#
# Building from a constructed object makes presets genuinely order-independent, which is
# what the design rule in CLAUDE.md requires -- one axis per condition, and nothing
# inherited from whatever ran before.

CLEAR_BASELINE = dict(
    cloudiness=80.0,              # flat, shadowless overcast
    sun_azimuth_angle=0.0,
    sun_altitude_angle=90.0,      # sun overhead: no cast shadows
    precipitation=0.0,
    precipitation_deposits=0.0,
    wetness=0.0,
    wind_intensity=0.0,
    fog_density=0.0,
    fog_distance=0.0,
    fog_falloff=0.0,
    scattering_intensity=0.0,
    mie_scattering_scale=0.0,
    dust_storm=0.0,
)

# Each condition moves exactly ONE physical axis off the clear baseline.
CONDITION_DELTAS = {
    "clear":   {},
    "fog":     dict(fog_density=70.0, fog_distance=10.0, fog_falloff=0.2),
    "rain":    dict(precipitation=85.0, precipitation_deposits=70.0, wetness=80.0),
    "night":   dict(sun_altitude_angle=-25.0),
    "shadows": dict(sun_altitude_angle=15.0),
}


def _density_override(name, w):
    """FOG_DENSITY_OVERRIDE lets a run sample intermediate fog without editing presets.

    Stage 5 asks whether the policies degrade at visibilities closed loop has never driven.
    That needs fog at densities other than the single preset value, and it must be the SAME
    code path the ledger uses, so the comparison is like-for-like."""
    import os
    v = os.environ.get("FOG_DENSITY_OVERRIDE")
    if v and name == "fog":
        w.fog_density = float(v)
    return w


def _sun_override(w):
    """SUN_ALTITUDE_OVERRIDE exposes the axis the three lighting conditions already lie on.

    `clear`, `shadows` and `night` are not separate phenomena -- they are sun_altitude_angle
    90, 15 and -25 of one continuous physical parameter. Sweeping it turns a three-point
    comparison into a curve, which is what makes a transition point predictable in advance
    and therefore falsifiable. Headlights still key off the CONDITION, not the angle, so a
    swept `shadows` run stays lights-off exactly as the preset is.
    """
    import os
    v = os.environ.get("SUN_ALTITUDE_OVERRIDE")
    if v:
        w.sun_altitude_angle = float(v)
    return w


def weather_params(name):
    """Fully-specified WeatherParameters for a condition. No live state is read."""
    if name not in CONDITION_DELTAS:
        raise ValueError(f"unknown condition {name!r}; "
                         f"expected one of {sorted(CONDITION_DELTAS)}")
    w = carla.WeatherParameters()
    for field, value in {**CLEAR_BASELINE, **CONDITION_DELTAS[name]}.items():
        setattr(w, field, value)
    return _sun_override(_density_override(name, w))


def set_clear_weather(world):
    """The clear baseline.

    DELIBERATE scope choice: flat and shadowless. Swapping it for CARLA's shipped
    ClearNoon (sun at 45 degrees, so cast shadows) made the v1 clear teacher depart the
    lane at 33.54 ft CTE where it otherwise held 0.43 ft. Shadows are a studied condition
    here, not a property of the baseline.
    """
    world.set_weather(weather_params("clear"))


# Headlights: low beam + position lights, what a real vehicle runs at night. v1 drove
# at night with these OFF, which is physically impossible and makes any night result an
# artefact of the setup rather than a property of the model.
LIGHTS_ON = None   # built lazily; carla enums are not available at import in all paths


def _lights(on):
    global LIGHTS_ON
    if on:
        return carla.VehicleLightState(carla.VehicleLightState.LowBeam
                                       | carla.VehicleLightState.Position)
    return carla.VehicleLightState(carla.VehicleLightState.NONE)


def headlights_on(sun_altitude_deg):
    """Headlights follow the SUN, not the preset name (trap 19).

    Keying off the name alone would drive a swept -10 degree scene with lights off,
    reintroducing the v1 artefact where night ran with headlights off. A pure function
    so the rule is testable without a live simulator (conformance/test_traps.py)."""
    return sun_altitude_deg < 0.0


def set_weather(world, name, vehicle=None):
    """Apply a condition preset and, if a vehicle is given, the matching lights.

    Presets are fully specified and order-independent -- see the note above
    CLEAR_BASELINE for why they are constructed rather than read-modify-written.

    Headlights follow the condition. v1 drove at night with them off, which is
    physically impossible for a real vehicle and made any night result an artefact.
    """
    w = weather_params(name)
    world.set_weather(w)
    if vehicle is not None:
        # The presets already encode the rule headlights_on states -- clear 90 and
        # shadows 15 are daylight with lights off, night -25 is below the horizon
        # with lights on.
        vehicle.set_light_state(_lights(headlights_on(w.sun_altitude_angle)))


def set_condition(world, vehicle, name, camera=None):
    """Apply a condition AND the camera exposure it declares. Returns (camera, queue).

    Exposure is a blueprint attribute, so it cannot be changed on a live sensor -- the
    camera must be respawned when the condition's declared exposure differs. Callers
    that switch conditions mid-run must use this rather than `set_weather`, or they will
    capture the new condition through the previous condition's exposure.

    Pass the existing `camera` to have it destroyed and replaced.
    """
    set_weather(world, name, vehicle)
    if camera is not None:
        camera.destroy()
    cam, q = spawn_camera(world, vehicle, condition=name)
    verify_condition(world, name)
    return cam, q


def verify_condition(world, name, tick=True):
    """Read the weather BACK and confirm it is the one that was asked for.

    world.set_weather() applies on the NEXT TICK, and nothing errors if a caller reads or
    renders before that tick. In the Town04 generation a fog run followed by a night run
    left fog in the night frames, so the "night" cells were really fog+night. Nothing in
    the results can reveal that -- the numbers are simply wrong and look fine.

    So the condition is not trusted, it is checked: tick once so the write lands, read
    the weather back, and compare the fields that DEFINE the conditions this study uses.
    A mismatch raises rather than warns, because a warning in a long unattended run is a
    warning nobody reads.
    """
    if tick:
        world.tick()
    want, got = weather_params(name), world.get_weather()
    fields = ("fog_density", "sun_altitude_angle", "precipitation",
              "precipitation_deposits", "cloudiness", "fog_distance", "wetness")
    bad = []
    for f in fields:
        w_, g_ = getattr(want, f, None), getattr(got, f, None)
        if w_ is None or g_ is None:
            continue
        if abs(float(w_) - float(g_)) > 1e-3:
            bad.append(f"{f}: asked {float(w_):.3f}, got {float(g_):.3f}")
    if bad:
        raise RuntimeError(
            f"CONDITION MISMATCH for '{name}' -- the simulator is not rendering what was "
            f"requested, so every frame from here is mislabelled:\n    "
            + "\n    ".join(bad))
    return got


# ── Spawning ─────────────────────────────────────────────────────────────────

def make_transform(spawn):
    return carla.Transform(
        carla.Location(x=spawn["x"], y=spawn["y"], z=spawn["z"]),
        carla.Rotation(yaw=spawn["yaw"]),
    )


def spawn_vehicle(world, spawn):
    bp = world.get_blueprint_library().filter(VEHICLE_BLUEPRINT)[0]
    tf = make_transform(spawn)
    vehicle = world.try_spawn_actor(bp, tf)
    if vehicle is None:
        tf.location.z += 0.5
        vehicle = world.spawn_actor(bp, tf)
    return vehicle


def set_tire_friction(vehicle, friction):
    """Set all wheels' tire friction (snow/ice ~0.5-1.5 vs dry ~3+). Models the
    traction loss of winter driving -- a vehicle-dynamics hazard that a perception
    -> steering verifier cannot capture."""
    pc = vehicle.get_physics_control()
    wheels = pc.wheels
    for w in wheels:
        w.tire_friction = friction
    pc.wheels = wheels
    vehicle.apply_physics_control(pc)


def _apply_exposure(bp, shutter=None, iso=None, fstop=None, gamma=None, mode=None):
    """Pin the camera's exposure.

    D1. The previous generation set only image size and FOV, leaving CARLA's default
    per-frame HISTOGRAM auto-exposure active for every capture. Auto-exposure
    re-normalizes each frame AFTER the weather is rendered, which destroys exactly the
    absolute photometry a disturbance model is calibrated against -- the same defect
    that disqualified ACDC. Any measurement taken through an auto-exposed camera is a
    measurement of the auto-exposure loop as much as of the weather.
    """
    bp.set_attribute("exposure_mode", mode or C.EXPOSURE_MODE)
    bp.set_attribute("shutter_speed", str(shutter if shutter is not None else C.EXPOSURE_SHUTTER_SPEED))
    bp.set_attribute("iso", str(iso if iso is not None else C.EXPOSURE_ISO))
    bp.set_attribute("fstop", str(fstop if fstop is not None else C.EXPOSURE_FSTOP))
    bp.set_attribute("gamma", str(gamma if gamma is not None else C.EXPOSURE_GAMMA))


def spawn_camera(world, vehicle, exposure=None, condition=None):
    """Spawn the RGB camera.

    `exposure` overrides everything (used by the calibration sweeps). Otherwise
    `condition` selects the declared per-condition exposure; omitting both gives the
    daylight setting.
    """
    if exposure is None and condition is not None:
        exposure = C.exposure_for(condition)
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(CAM_WIDTH))
    bp.set_attribute("image_size_y", str(CAM_HEIGHT))
    bp.set_attribute("fov", str(CAM_FOV))
    _apply_exposure(bp, **(exposure or {}))
    tf = carla.Transform(carla.Location(x=CAM_X, y=CAM_Y, z=CAM_Z))
    camera = world.spawn_actor(bp, tf, attach_to=vehicle)
    img_queue = queue.Queue()
    camera.listen(img_queue.put)
    return camera, img_queue


def spawn_depth_camera(world, vehicle):
    """Depth camera at the IDENTICAL transform as the RGB camera (D4).

    Ground-truth depth is what makes the fog transmission t(d) measurable per pixel
    instead of assumed from flat-road geometry, and every identifiability failure in the
    previous generation traced back to not having it.

    Trap 2 applies to BOTH sensors: CARLA's sensor queue runs a frame behind, so each
    must be matched on the frame id `world.tick()` returns, not simply popped per tick.
    """
    bp = world.get_blueprint_library().find("sensor.camera.depth")
    bp.set_attribute("image_size_x", str(CAM_WIDTH))
    bp.set_attribute("image_size_y", str(CAM_HEIGHT))
    bp.set_attribute("fov", str(CAM_FOV))
    tf = carla.Transform(carla.Location(x=CAM_X, y=CAM_Y, z=CAM_Z))
    camera = world.spawn_actor(bp, tf, attach_to=vehicle)
    q = queue.Queue()
    camera.listen(q.put)
    return camera, q


def decode_depth_metres(raw_bgra):
    """CARLA depth encoding -> metres. (R + G*256 + B*256^2) / (256^3 - 1) * 1000."""
    b = raw_bgra[:, :, 0].astype(np.float64)
    g = raw_bgra[:, :, 1].astype(np.float64)
    r = raw_bgra[:, :, 2].astype(np.float64)
    return ((r + g * 256.0 + b * 256.0 * 256.0) / (256.0 ** 3 - 1)) * 1000.0


# ── Speed control (physics-honest) ───────────────────────────────────────────

def speed_ms(vehicle):
    v = vehicle.get_velocity()
    return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)


def speed_mph(vehicle):
    return speed_ms(vehicle) * MPH_PER_MS


class SpeedController:
    """
    PI controller on speed error -> (throttle, brake). The integral term removes
    the steady-state offset a pure-P controller leaves (so we hold the target
    speed exactly, satisfying the fixed-speed requirement). Anti-windup clamps
    the integral. Call reset() at the start of each drive.
    """

    def __init__(self, target_ms=TARGET_SPEED_MS, kp=0.5, ki=0.4, dt=FIXED_DT):
        self.target = target_ms
        self.kp, self.ki, self.dt = kp, ki, dt
        self.integ = 0.0

    def reset(self):
        self.integ = 0.0

    def control(self, vehicle):
        err = self.target - speed_ms(vehicle)
        # Conditional integration: only accumulate near the setpoint so the
        # integral can't wind up during the large-error warmup acceleration
        # (which otherwise overshoots to ~27 mph before settling).
        if abs(err) < 1.5:
            self.integ = max(-3.0, min(3.0, self.integ + err * self.dt))
        else:
            self.integ = 0.0
        u = self.kp * err + self.ki * self.integ
        return (min(1.0, u), 0.0) if u >= 0 else (0.0, min(1.0, -u))


def teleport(vehicle, spawn):
    """Reposition and zero out motion (for direction switches)."""
    vehicle.set_target_velocity(carla.Vector3D(0, 0, 0))
    vehicle.set_target_angular_velocity(carla.Vector3D(0, 0, 0))
    tf = make_transform(spawn)
    tf.location.z += 0.3
    vehicle.set_transform(tf)


def warmup_to_speed(world, vehicle, img_queue, speed_ctrl, steer_fn=None,
                    settle_ticks=15, max_accel_ticks=80):
    """
    Let physics settle (held by brake), then accelerate to target speed while
    STEERING along the lane via steer_fn (default straight). Steering during
    warmup keeps the car centered on curved spawn lanes so recording starts
    on-center instead of recovering from a warmup-induced drift.
    """
    speed_ctrl.reset()
    for _ in range(settle_ticks):
        vehicle.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0, steer=0.0))
        update_spectator(world, vehicle)   # else the view freezes for the whole warmup
        world.tick()
        _drain(img_queue)
    for _ in range(max_accel_ticks):
        steer = steer_fn(vehicle) if steer_fn else 0.0
        thr, brk = speed_ctrl.control(vehicle)
        vehicle.apply_control(carla.VehicleControl(throttle=thr, brake=brk, steer=steer))
        update_spectator(world, vehicle)
        world.tick()
        _drain(img_queue)
        if speed_ms(vehicle) >= 0.98 * TARGET_SPEED_MS:
            break


def _drain(img_queue):
    try:
        img_queue.get(timeout=1.0)
    except queue.Empty:
        pass


def drain_frame(img_queue):
    """Discard one frame. For loops that tick but do not USE the image (the pure-pursuit
    oracle), where there is no pose/image pairing to get wrong. Anything that consumes
    the image must use grab_frame instead."""
    _drain(img_queue)


class FrameDesync(RuntimeError):
    pass


def grab_frame(img_queue, expected_frame, timeout=5.0):
    """Pop the image belonging to the tick that produced `expected_frame`.

    Trap 2, closed properly. The bare pattern

        world.tick()
        try:    image = img_queue.get(timeout=2.0)
        except: continue

    is correct while it works and silently wrong the moment it does not. A single
    timeout leaves that tick's frame in the queue, the loop ticks again, and from then on
    every `get()` returns the PREVIOUS frame -- pairing image[t-1] with pose[t] for the
    rest of the lap. Nothing errors, the frames look plausible, and the entire dataset is
    mislabelled by one step (1.79 m at 20 mph).

    Matching on the frame id `world.tick()` returns makes desync impossible to enter and
    impossible to miss: an older frame is discarded, a newer one raises.
    """
    while True:
        try:
            image = img_queue.get(timeout=timeout)
        except queue.Empty:
            raise FrameDesync(
                f"no sensor frame for tick {expected_frame} within {timeout}s. "
                "Do not swallow this and continue -- the queue would desync by one and "
                "every subsequent frame would be paired with the wrong pose."
            )
        if image.frame == expected_frame:
            return image
        if image.frame > expected_frame:
            raise FrameDesync(
                f"tick {expected_frame} requested but queue is already at {image.frame}; "
                "a frame was dropped and pose/image pairing is no longer trustworthy."
            )
        # older than requested: a stale frame from before the loop, discard and keep going


# ── Spectator / images / cleanup ─────────────────────────────────────────────

def update_spectator(world, vehicle):
    """Chase camera, placed one tick ahead to cancel a MEASURED one-tick lag.

    Measured 2026-08-11 against a live run, after guessing wrong about this twice. Sampling
    the spectator-to-vehicle offset at 50 Hz while the car drove:

        mean  -7.81 m   against a nominal placement of -6.00 m
        values alternate cleanly between -7.80 m and -9.60 m, a 1.80 m swing

    1.80 m is exactly one tick of travel at 20 mph and dt = 0.2 s. So the camera sits a
    systematic ONE TICK behind, and intermittently TWO -- which is the visible
    forward-then-back snap.

    Cause: the transform is set before `world.tick()` and CARLA applies it ON that tick,
    the same tick that moves the car, so the camera always lands where the car WAS.
    Extrapolating by velocity * FIXED_DT cancels the systematic term.

    Honest limit: this fixes the constant 1.8 m lag, NOT the occasional second tick. That
    comes from RPC timing jitter -- whether the set_transform reaches the server before it
    processes the tick -- and a client that is not synchronised to the render cannot
    control it. Expect the view to be centred correctly and still twitch sometimes.

    Also inherent and unrelated: FIXED_DT is the control rate the study is defined at, so
    motion is genuinely five discrete 1.79 m steps per second.

    Purely cosmetic -- the spectator is not the sensor camera. But eyeballing the render is
    what caught the fog-in-night preset bug, so a watchable view has real diagnostic value.
    """
    try:
        tf = vehicle.get_transform()
        v = vehicle.get_velocity()
        lead = carla.Location(x=v.x * FIXED_DT, y=v.y * FIXED_DT, z=0.0)
        fwd = tf.get_forward_vector()
        loc = tf.location + lead - 6.0 * fwd + carla.Location(z=3.5)
        rot = carla.Rotation(pitch=-15.0, yaw=tf.rotation.yaw)
        world.get_spectator().set_transform(carla.Transform(loc, rot))
    except Exception:
        pass


def cleanup(actors, world=None, original_settings=None):
    for a in actors:
        try:
            a.destroy()
        except Exception:
            pass
    if world is not None and original_settings is not None:
        try:
            world.apply_settings(original_settings)
        except Exception:
            pass

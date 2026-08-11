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


def load_town04(client, fresh=True):
    """Return a Town04 world. With fresh=True (default) the world is reloaded on
    every connect, clearing any accumulated actors/state from prior runs on a
    long-lived CARLA server (which can silently corrupt closed-loop results)."""
    world = client.get_world()
    if world.get_map().name.split("/")[-1] != MAP_NAME:
        return client.load_world(MAP_NAME)      # loads a fresh map
    return client.reload_world() if fresh else world  # already Town04 -> reload fresh


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


def set_clear_weather(world):
    """Flat, shadowless clear: cloudiness 80 with the sun overhead.

    This is a DELIBERATE scope choice, not an oversight. The study is about formally
    verifying a small ReLU-only policy, and verifiability is bought with capacity that
    scene complexity would otherwise consume. Measured: swapping this for CARLA's
    shipped ClearNoon (sun at 45 degrees, so shadows) makes the v1 clear teacher depart
    the lane at step 435 with 33.54 ft CTE, where under this preset it holds 0.43 ft.
    Shadows alone break it. Keep the preset flat and spend the capacity on the weather
    disturbances, which are what the paper is about.
    """
    w = world.get_weather()
    w.cloudiness = 80.0
    w.precipitation = 0.0
    w.precipitation_deposits = 0.0
    w.sun_azimuth_angle = 0.0
    w.sun_altitude_angle = 90.0
    w.fog_density = 0.0
    w.wetness = 0.0
    world.set_weather(w)


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


def set_weather(world, name, vehicle=None):
    """Apply a condition preset and, if a vehicle is given, the matching lights.

    **Every preset is the clear baseline with exactly ONE axis moved.** This is the
    design rule from CLAUDE.md -- train, closed-loop test and verify over one axis per
    condition -- and the inherited presets violated it:

        fog:  cloudiness 80->90, sun_altitude 90->45, fog_density 0->70
        rain: cloudiness 80->90, sun_altitude 90->40, precipitation 0->85

    So a clear-vs-fog measurement taken from them conflated fog scattering with a lower
    sun and heavier cloud. [MEASURED 2026-08-10, scripts/fog_isolation.py] at 20 poses:
    the old preset moved the road ROI mean by -0.060, while fog_density=70 with the
    clear illumination HELD FIXED moves it by only -0.024. More than half of the
    apparent darkening was the sun angle, not the fog.

    Presets remain order-independent because each one restores the full clear baseline
    before moving its own axis -- otherwise night applied after rain would silently
    inherit rain's puddles and wet-road sheen.

    Headlights follow the condition (the ego drove at night with them off in v1, which
    is physically impossible and made any night result an artefact of the setup).
    """
    if name == "clear":
        set_clear_weather(world)
    else:
        # Start from the clear baseline every time, then move ONE axis. See the
        # note above on why the inherited presets could not be used as-is.
        set_clear_weather(world)
        w = world.get_weather()
        if name == "fog":
            w.fog_density, w.fog_distance, w.fog_falloff = 70.0, 10.0, 0.2
        elif name == "rain":
            w.precipitation, w.precipitation_deposits, w.wetness = 85.0, 70.0, 80.0
        elif name == "night":
            w.sun_altitude_angle = -25.0
        elif name == "shadows":
            w.sun_altitude_angle = 15.0
        else:
            raise ValueError(name)
        world.set_weather(w)
    if vehicle is not None:
        vehicle.set_light_state(_lights(name == "night"))


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


def spawn_camera(world, vehicle, exposure=None):
    """Spawn the RGB camera. `exposure` overrides the config defaults, for sweeps."""
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
        world.tick()
        _drain(img_queue)
    for _ in range(max_accel_ticks):
        steer = steer_fn(vehicle) if steer_fn else 0.0
        thr, brk = speed_ctrl.control(vehicle)
        vehicle.apply_control(carla.VehicleControl(throttle=thr, brake=brk, steer=steer))
        world.tick()
        _drain(img_queue)
        if speed_ms(vehicle) >= 0.98 * TARGET_SPEED_MS:
            break


def _drain(img_queue):
    try:
        img_queue.get(timeout=1.0)
    except queue.Empty:
        pass


# ── Spectator / images / cleanup ─────────────────────────────────────────────

def update_spectator(world, vehicle):
    try:
        tf = vehicle.get_transform()
        fwd = tf.get_forward_vector()
        loc = tf.location - 6.0 * fwd + carla.Location(z=3.5)
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

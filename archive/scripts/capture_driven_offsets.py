#!/usr/bin/env python3
"""Capture frames from a MOVING vehicle held off the centerline, not a teleported one.

WHY THIS EXISTS (F42). The (offset x heading) grid used by every loop-verification attempt
comes from teleporting the vehicle to an offset and settling it under physics. Measured
against 198 frames the car actually met, those static frames differ from driven ones by
0.0258 in steering and 0.0142 per pixel -- 5x the disturbance effect a rollout integrates,
and about 10% of night's entire disturbance. A per-frame verdict never accumulates that
error, so the per-frame certificate is unaffected; a rollout does, which is why every
rollout so far has been dominated by capture error rather than by the disturbance.

HOW. The EXPERT drives, not the student: pure pursuit tracks a laterally shifted copy of
the route, so the vehicle is genuinely driving at an offset, carrying the suspension state,
sensor motion and camera pose that go with it. The student never touches the loop; it is
evaluated offline on the recorded frames.

The shift is sinusoidal along the path rather than constant:

    d(s) = A sin(2 pi s / lambda + phi)

which buys the heading dimension for free -- heading error is d'(s), so at any pose the
runs sweep a circle in (offset, heading) rather than a line, and a local plane fit is
well conditioned. Running several phases puts several (offset, heading, steering) samples
at every pose.

Stores the projected 3x28x84 network input, the same fixed projection used by every other
capture in the study, plus the MEASURED offset and heading relative to the true centerline
(what the vehicle actually achieved, never what was commanded).

    python scripts/capture_driven_offsets.py --direction eastbound --condition clear \
        --phases 8 --amp 1.2 --wavelength 60
"""
import argparse
import math
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))

import carla  # noqa: E402
import carla_env as env  # noqa: E402
import config as C  # noqa: E402
import verifiable_disturbance as vd  # noqa: E402
from route import load_route, signed_cte_route, pure_pursuit_route, nearest_index  # noqa: E402

SPAWNS = {"eastbound": C.SPAWN_EASTBOUND, "westbound": C.SPAWN_WESTBOUND}


def shifted_route(route, amp, wavelength, phase):
    """route displaced laterally by d(s) = amp*sin(2 pi s/wavelength + phase).

    The displacement is along the LEFT normal of the local tangent, so it is a genuine
    lateral offset rather than a translation, and it stays lateral through curves.
    """
    xy = np.asarray(route, dtype=np.float64)[:, :2]
    seg = np.diff(xy, axis=0, append=xy[:1])
    ln = np.hypot(seg[:, 0], seg[:, 1])
    ln[ln < 1e-9] = 1e-9
    tx, ty = seg[:, 0] / ln, seg[:, 1] / ln
    nx, ny = -ty, tx                      # left normal
    s = np.concatenate([[0.0], np.cumsum(ln)[:-1]])
    d = amp * np.sin(2.0 * math.pi * s / wavelength + phase)
    out = xy.copy()
    out[:, 0] += d * nx
    out[:, 1] += d * ny
    return out, d


def path_yaw(route, i):
    """heading of the reference path at index i, degrees"""
    n = len(route)
    a, b = route[i % n], route[(i + 1) % n]
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def drive_capture(world, vehicle, cam_queue, route, shifted, direction, max_steps):
    """One lap under EXPERT control of the shifted path, recording every frame."""
    hint = hint_s = None
    speed_ctrl = env.SpeedController()
    speed_ctrl.reset()
    env.teleport(vehicle, SPAWNS[direction])
    env.warmup_to_speed(
        world, vehicle, cam_queue, speed_ctrl,
        steer_fn=lambda veh: pure_pursuit_route(shifted, veh.get_transform())[0],
    )
    spawn = SPAWNS[direction]
    start = carla.Location(x=spawn["x"], y=spawn["y"], z=spawn["z"])

    frames, offs, heads, xs, ys, yaws = [], [], [], [], [], []
    left = False
    for _ in range(max_steps):
        env.update_spectator(world, vehicle)
        fid = world.tick()
        image = env.grab_frame(cam_queue, fid)
        tf = vehicle.get_transform()
        loc = tf.location

        # EXPERT drives the shifted path; the student is never in this loop.
        steer, _, hint_s = pure_pursuit_route(shifted, tf, hint_s)
        thr, brk = speed_ctrl.control(vehicle)
        vehicle.apply_control(carla.VehicleControl(throttle=thr, brake=brk, steer=steer))

        # Record what the vehicle ACHIEVED against the true centerline, not the command.
        cte, hint = signed_cte_route(route, loc.x, loc.y, hint)
        if cte is None:
            continue
        i = nearest_index(route, loc.x, loc.y, hint)
        he = wrap(tf.rotation.yaw - path_yaw(route, i))

        frames.append(vd._project(env.raw_to_bgr(image).astype(np.float32) / 255.0,
                                  84, 28).reshape(3, 28, 84))
        offs.append(float(cte))
        heads.append(float(he))
        xs.append(float(loc.x))
        ys.append(float(loc.y))
        yaws.append(float(tf.rotation.yaw))

        d0 = loc.distance(start)
        if d0 > 50.0:
            left = True
        if left and d0 < 12.0:
            break
    return (np.asarray(frames, dtype=np.float32), np.asarray(offs), np.asarray(heads),
            np.asarray(xs), np.asarray(ys), np.asarray(yaws))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--direction", default="eastbound")
    ap.add_argument("--condition", default="clear")
    ap.add_argument("--phases", type=int, default=8)
    ap.add_argument("--amp", type=float, default=1.2, help="lateral amplitude, m")
    ap.add_argument("--wavelength", type=float, default=60.0, help="m per cycle")
    ap.add_argument("--max-steps", type=int, default=1800)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    route = load_route(args.direction)
    client = env.connect()
    world = env.load_town04(client, fresh=False)
    original = env.enable_sync_mode(world)
    vehicle = camera = None
    try:
        vehicle = env.spawn_vehicle(world, SPAWNS[args.direction])
        camera, cam_queue = env.set_condition(world, vehicle, args.condition)
        sun = os.environ.get("SUN_ALTITUDE_OVERRIDE", "default")
        print(f"driven-offset capture: {args.direction} / {args.condition} / sun {sun}")
        print(f"  amplitude {args.amp} m, wavelength {args.wavelength} m "
              f"-> heading swing +-{math.degrees(args.amp*2*math.pi/args.wavelength):.1f} deg")
        print(f"  {args.phases} phases", flush=True)

        F, O, H, X, Y, W, P = [], [], [], [], [], [], []
        for k in range(args.phases):
            phase = 2.0 * math.pi * k / args.phases
            sh, _ = shifted_route(route, args.amp, args.wavelength, phase)
            fr, off, he, x, y, yw = drive_capture(world, vehicle, cam_queue, route, sh,
                                                  args.direction, args.max_steps)
            F.append(fr); O.append(off); H.append(he); X.append(x); Y.append(y); W.append(yw)
            P.append(np.full(len(off), phase))
            print(f"  phase {k}: {len(off)} frames, offset {off.min():+.2f}..{off.max():+.2f} m, "
                  f"heading {he.min():+.1f}..{he.max():+.1f} deg", flush=True)

        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            out,
            frames=np.concatenate(F), offset=np.concatenate(O), heading=np.concatenate(H),
            x=np.concatenate(X), y=np.concatenate(Y), yaw=np.concatenate(W),
            phase=np.concatenate(P), condition=args.condition, direction=args.direction,
            sun=os.environ.get("SUN_ALTITUDE_OVERRIDE", ""))
        n = sum(len(o) for o in O)
        print(f"\nwrote {out}  ({n} driven frames, "
              f"{out.stat().st_size / 1e6:.1f} MB)")
    finally:
        for label, fn in (("camera", lambda: camera and camera.destroy()),
                          ("vehicle", lambda: vehicle and vehicle.destroy()),
                          ("settings", lambda: world.apply_settings(original))):
            try:
                fn()
            except Exception as exc:
                print(f"  cleanup: {label} failed ({type(exc).__name__}); continuing")


if __name__ == "__main__":
    main()

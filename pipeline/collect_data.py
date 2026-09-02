#!/usr/bin/env python3
"""
Milestone-1, step 3: collect behavior-cloning data by driving the full Town04
loop (both directions) with the pure-pursuit EXPERT and recording, per frame,
the raw camera image paired with the expert steering label.

Image[t] is paired with pose[t]/label[t] by ticking FIRST, then reading pose and
computing the label from the same frame — exact image/label alignment.

Saves raw 640x480 RGB PNGs (preprocessing deferred to train time) plus a single
manifest CSV. Usage:
    python collect_data.py --dataset clear --laps 2 --direction both
"""
import os
from pathlib import Path
import sys
import csv
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2  # noqa: E402
import carla  # noqa: E402

import config as C  # noqa: E402
import carla_env as env  # noqa: E402
from route import (load_route, signed_cte_route, pure_pursuit_route,  # noqa: E402
                   lap_finished)

# Sections, not a hardcoded pair (Town06 has six; Town04 has its two directions).
SPAWNS = C.SPAWNS
FIELDS = ["image", "weather", "direction", "lap", "step", "steer", "steer_rad",
          "cte_m", "speed_mph", "x", "y", "yaw"]


def collect_lap(world, world_map, vehicle, img_queue, weather, direction, lap, out_dir, max_steps):
    spawn = SPAWNS[direction]
    route = load_route(direction)
    hint = None
    speed_ctrl = env.SpeedController()
    env.teleport(vehicle, spawn)
    env.warmup_to_speed(
        world, vehicle, img_queue, speed_ctrl,
        steer_fn=lambda veh: pure_pursuit_route(route, veh.get_transform())[0],
    )

    seg = f"{weather}_{direction}_lap{lap:02d}"
    frames_dir = os.path.join(out_dir, seg, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    start = carla.Location(x=spawn["x"], y=spawn["y"], z=spawn["z"])
    print(f"  [{weather}/{direction} lap{lap:02d}] start speed={env.speed_mph(vehicle):.1f} mph")

    rows, left_start = [], False
    for step in range(max_steps):
        env.update_spectator(world, vehicle)
        frame = world.tick()                      # advance -> frame t
        image = env.grab_frame(img_queue, frame)   # image[t], matched on frame id
        tf = vehicle.get_transform()              # pose[t]
        loc = tf.location
        cte, hint = signed_cte_route(route, loc.x, loc.y, hint)
        steer, steer_rad, _ = pure_pursuit_route(route, tf, hint)  # label[t]

        # STOP AT THE END OF AN OPEN ROUTE, BEFORE RECORDING.
        #
        # The loop-closure test below cannot fire on the Town06 lap (start and end are
        # 174 m apart), so this ran to its step budget and drove past the last vertex,
        # where pure pursuit's lookahead is clamped onto the final point and the label
        # degenerates. Measured on the mixed collection: 13 of 15,360 frames carried
        # |steer| up to 0.754 against a lap maximum of 0.086, all in the last three
        # steps, at |CTE| 0.001 m -- perfectly on the line, and the label garbage.
        # The break is BEFORE the write, so the bad frame is never recorded at all.
        if lap_finished(route, hint):
            print(f"    reached the end of the open route at step {step} "
                  f"({len(rows)} frames)")
            break

        rel = os.path.join(seg, "frames", f"{step:05d}.png")
        cv2.imwrite(os.path.join(out_dir, rel), env.raw_to_bgr(image))
        rows.append(dict(
            image=rel, weather=weather, direction=direction, lap=lap, step=step,
            steer=steer, steer_rad=steer_rad, cte_m=cte,
            speed_mph=env.speed_mph(vehicle), x=loc.x, y=loc.y, yaw=tf.rotation.yaw,
        ))

        env.apply_control(vehicle, carla.VehicleControl(*_ctrl(speed_ctrl, vehicle, steer)))

        d0 = loc.distance(start)
        if d0 > 50.0:
            left_start = True
        if left_start and d0 < 12.0:
            print(f"    loop closed at step {step} ({len(rows)} frames)")
            break
    return rows


def _ctrl(speed_ctrl, vehicle, steer):
    thr, brk = speed_ctrl.control(vehicle)
    return thr, steer, brk  # VehicleControl(throttle, steer, brake)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="clear")
    ap.add_argument("--weathers", default="clear",
                    help="comma-separated weather presets to collect (clear,fog,rain,night)")
    ap.add_argument("--laps", type=int, default=2)
    ap.add_argument("--direction", default="both",
                    help="section name, or 'both'/'all' for every section")
    ap.add_argument("--max-steps", type=int, default=2500)
    args = ap.parse_args()

    out_dir = os.path.join(C.DATASET_DIR, args.dataset)
    os.makedirs(out_dir, exist_ok=True)
    weathers = args.weathers.split(",")

    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)
    world_map = world.get_map()

    # Spawn INSIDE the try: a failure here would otherwise skip the finally and leave
    # the server hung in synchronous mode with no ticking client (trap 3b).
    vehicle = camera = img_queue = None
    dirs = list(C.SECTIONS) if args.direction in ("both", "all") else [args.direction]
    all_rows = []
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
        camera, img_queue = env.spawn_camera(world, vehicle)
        for weather in weathers:
            # Respawn the camera: exposure is declared per condition and is a
            # blueprint attribute, so it cannot be changed on a live sensor.
            camera, img_queue = env.set_condition(world, vehicle, weather, camera)
            # Lap indices continue after whatever this weather already has on disk.
            # `range(args.laps)` always restarted at 0, so a SECOND collection for the
            # same weather rewrote lap00.. with new images while the manifest kept the
            # old rows pointing at those same paths -- old labels, new pixels, no error.
            # Appending is only safe across weathers, which get distinct directories.
            base_lap = 0
            for d in dirs:
                existing = sorted(Path(out_dir).glob(f"{weather}_{d}_lap*"))
                if existing:
                    base_lap = max(base_lap,
                                   max(int(x.name.rsplit("lap", 1)[1]) for x in existing) + 1)
            if base_lap:
                print(f"  {weather}: {base_lap} lap(s) already on disk, "
                      f"collecting lap{base_lap:02d}..lap{base_lap + args.laps - 1:02d}")
            for lap in range(base_lap, base_lap + args.laps):
                for d in dirs:
                    all_rows += collect_lap(world, world_map, vehicle, img_queue,
                                            weather, d, lap, out_dir, min(args.max_steps, C.steps_for(d)))
    finally:
        env.cleanup([camera, vehicle], world, original)

    # APPEND if the dataset already has a manifest, so a collection can be run one
    # weather at a time and still produce a single coherent dataset. Frame paths are
    # namespaced by weather/direction/lap (see `seg`), so there are no collisions.
    manifest = os.path.join(out_dir, "manifest.csv")
    prior = []
    if os.path.exists(manifest):
        # KEEP EVERY PRIOR LAP THIS RUN DID NOT REWRITE, INCLUDING THE SAME WEATHER'S.
        #
        # This dropped every prior row whose weather was being collected again, on the
        # reasoning that "appending is only safe across weathers, which get distinct
        # directories". That was true when `range(args.laps)` restarted at lap00 and a
        # second collection overwrote the first's images -- old labels, new pixels. Lap
        # numbering now CONTINUES from what is on disk (`base_lap` above), so a re-collect
        # writes new directories and the old rows still describe real, untouched frames.
        #
        # Left as it was, "top up this dataset from 4 laps to 8" silently REPLACED it:
        # 8 lap directories on disk, a manifest referencing only laps 4-7, and the first
        # four laps' labels gone. The dataset did not grow, and nothing said so.
        #
        # The guard that matters is not the weather, it is whether this run rewrote that
        # lap -- so that is what is checked, plus the frame still existing on disk.
        written = {(r["weather"], r["direction"], str(r["lap"])) for r in all_rows}
        with open(manifest, newline="") as f:
            for r in csv.DictReader(f):
                key = (r.get("weather"), r.get("direction"), str(r.get("lap")))
                if key in written:
                    continue                      # this run replaced that lap
                if not os.path.exists(os.path.join(out_dir, r["image"])):
                    continue                      # frames are gone; the row is a lie
                prior.append(r)
        print(f"  appending to existing manifest ({len(prior)} prior rows kept, "
              f"{len(written)} lap(s) written this run)")
    with open(manifest, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(prior + all_rows)
    all_rows = prior + all_rows

    steers = [float(r["steer"]) for r in all_rows]   # CSV rows read back are strings
    n_straight = sum(1 for s in steers if abs(s) <= 0.01)
    print(f"\nCollected {len(all_rows)} frames -> {manifest}")
    print(f"  straight (|steer|<=0.01): {n_straight} ({100*n_straight/len(all_rows):.0f}%) | "
          f"left: {sum(1 for s in steers if s>0.01)} | right: {sum(1 for s in steers if s<-0.01)}")
    print(f"  steer range: [{min(steers):.3f}, {max(steers):.3f}]")


if __name__ == "__main__":
    # One CARLA client per port. Two synchronous clients on one world interleave ticks
    # and silently corrupt each other -- see pipeline/carla_lock.py for the run this
    # cost. Every entry point that ticks the world takes the lock, in both directions:
    # it refuses to start over someone else's run, and its own run is visible to them.
    from carla_lock import carla_lock, CarlaBusy
    try:
        with carla_lock(owner=" ".join(sys.argv[:3])):
            main()
    except CarlaBusy as exc:
        raise SystemExit(str(exc))

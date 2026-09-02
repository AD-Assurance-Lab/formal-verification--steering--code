#!/usr/bin/env python3
"""Assert the SERVER RENDERS AT THE SAME BRIGHTNESS it rendered when the study began.

    STUDY_MAP=Town06 python3 scripts/check_render_photometry.py            # check
    STUDY_MAP=Town06 python3 scripts/check_render_photometry.py --write    # set reference

WHY. The determinism preflight (D-1..D-11) verifies HOW the server was launched, and
verify_condition() reads the weather struct back. Both passed, every run, while the
server rendered the identical scene 15% darker for half a day.

Measured, 2026-09-02: `pipeline/data/dagger_clear_t06lap` holds two renderings of the
same road under the same declared condition. Rounds 00-05 average 0.2508-0.2537 on the
network's input; rounds 06-14 average 0.2140-0.2141. At matched poses 0.5 m apart the
frames are geometrically identical and uniformly 0.84x -- a photometric gain, not
content. The BC sets that seed both teachers are on the dark side (0.2136 / 0.2147); a
collection run today reproduces the bright side (0.2526, within 0.3% of a driven lap).

So every Town06 lap teacher was trained on frames systematically darker than the frames
it is scored on, and DAgger aggregated both renderings into one set. That is a
train/test shift in the images themselves -- the same class of defect as A-2's texture
streaming, and the reason A-2 forced recollection rather than re-evaluation.

Nothing in a result reveals it. The condition still classifies as itself, the weather
struct still reads back correct, the determinism preflight is still green, and the
policy simply fails to converge on the darkest conditions while clear looks fine.

WHAT THIS CHECKS, and why it is a fixed pose rather than a lap. The quantity at risk is
the RENDERER's response, not the route. A fixed camera transform, no vehicle and no
physics, isolates it completely and costs about two seconds -- so it can run on every
fresh server, which is the only cadence that would have caught this.

TOLERANCE. Headless and windowed servers driving the same lap agree to 4e-5 relative
(measured 2026-09-02), so the render's own floor is far below anything structural. The
default 1% gate is ~250x the noise floor and ~15x smaller than the drift it exists to
catch: it cannot fire on render noise and cannot miss another 0.84x.
"""
import argparse
import json
import math
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, os.path.join(REPO, "pipeline"))

import carla  # noqa: E402
import carla_determinism as cd  # noqa: E402
import carla_env as env  # noqa: E402
import config as C  # noqa: E402
from imaging import preprocess_for_model  # noqa: E402
from student import student_preprocess  # noqa: E402
from condition_signature import identify  # noqa: E402

REF_PATH = os.path.join(REPO, "results", "photometry_reference.json")

# Settle before measuring. The camera is spawned and the weather written in the same
# breath, and CARLA applies both on the NEXT tick -- the repo's oldest trap. A handful
# of ticks also lets any first-frame transient out of the pipe.
SETTLE_TICKS = 12
MEASURE_TICKS = 5


def measure(condition="clear"):
    """Mean of the network's input at a fixed pose. No vehicle, no physics, no route."""
    client = cd.bind_client(carla.Client("127.0.0.1", C.PORT))
    client.set_timeout(120.0)
    world = env.load_study_map(client)
    original = world.get_settings()
    env.enable_sync_mode(world)
    camera = None
    try:
        spawn = C.SPAWNS[C.SECTIONS[0]]
        # The camera goes where the ego's camera would be, at the study's own spawn, so
        # the number is comparable to the frames the study actually trains on.
        # Put the lens where the ego's lens would be: the spawn, plus the camera's
        # own body offset rotated into world axes. A reference taken 1.6 m behind the
        # real one still measures the renderer, but it stops being comparable to the
        # frames the study trains on, and someone would eventually compare them.
        yaw = math.radians(float(spawn.get("yaw", 0.0)))
        tf = carla.Transform(
            carla.Location(x=float(spawn["x"]) + env.CAM_X * math.cos(yaw)
                                              - env.CAM_Y * math.sin(yaw),
                           y=float(spawn["y"]) + env.CAM_X * math.sin(yaw)
                                              + env.CAM_Y * math.cos(yaw),
                           z=float(spawn["z"]) + float(env.CAM_Z)),
            carla.Rotation(yaw=float(spawn.get("yaw", 0.0))))
        env.set_weather(world, condition)
        camera, q = env.spawn_camera_at(world, tf, condition=condition)
        for _ in range(SETTLE_TICKS):
            env.grab_frame(q, world.tick())
        means, labels = [], []
        for _ in range(MEASURE_TICKS):
            image = env.grab_frame(q, world.tick())
            bgr = env.raw_to_bgr(image)
            a = np.asarray(preprocess_for_model(bgr), dtype=np.float32)
            means.append(float(a.mean()))
            # FREE EARLY WARNING for R-SIM-4. evaluate.py asserts identify() on the
            # STUDENT's view of a frame at this same spawn pose and RAISES on a mismatch,
            # aborting the run. On this lap clear sits near condition_signature's
            # fog/clear boundary -- the student's crop is road only, so where the spawn
            # has no dark pixels p01 rises past fog's 0.120 threshold. The frame is
            # stationary and deterministic, so this cannot flicker mid-campaign: either
            # it is fine for every run or it aborts every run of that condition, and
            # this says which BEFORE the campaign spends hours finding out.
            sv = np.asarray(student_preprocess(bgr, C.TOWN06_INPUT_W, C.TOWN06_INPUT_H),
                            dtype=np.float32)
            labels.append(identify(sv)[0])
        return float(np.mean(means)), float(np.std(means)), labels
    finally:
        try:
            if camera:
                camera.destroy()
        except Exception:
            pass
        world.apply_settings(original)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", default="clear")
    ap.add_argument("--tol", type=float, default=0.01, help="relative tolerance")
    ap.add_argument("--write", action="store_true",
                    help="record the CURRENT render as the reference for this map")
    args = ap.parse_args()

    mean, std, labels = measure(args.condition)
    want_label = env.canonical_condition(args.condition)
    if any(l != want_label for l in labels):
        print(f"  *** WARNING: the spawn frame classifies as "
              f"{'/'.join(sorted(set(labels)))}, not '{want_label}'. evaluate.py asserts "
              f"this and RAISES, so every run of '{want_label}' would abort at the spawn "
              f"(R-SIM-4). The rendering may be fine -- the discriminator's threshold is "
              f"what is close here. Check before starting a campaign.")
    ref = json.load(open(REF_PATH)) if os.path.exists(REF_PATH) else {}
    key = f"{C.STUDY_MAP}/{args.condition}"

    if args.write:
        ref[key] = dict(mean=mean, std=std, tol=args.tol,
                        spawn_classifies_as=sorted(set(labels)),
                        server_cmdline=cd.server_cmdline(C.PORT))
        os.makedirs(os.path.dirname(REF_PATH), exist_ok=True)
        json.dump(ref, open(REF_PATH, "w"), indent=2, sort_keys=True)
        print(f"  photometry reference for {key}: {mean:.6f} (+/- {std:.6f}) -> {REF_PATH}")
        return 0

    if key not in ref:
        # REFUSE rather than pass. A missing reference is exactly the state the server
        # was in for half a day, and a check that silently skips itself is worse than
        # no check: it reports green.
        print(f"FATAL: no photometry reference for {key} in {REF_PATH}.\n"
              f"  Record one on a server you trust:\n"
              f"    STUDY_MAP={C.STUDY_MAP} python3 scripts/check_render_photometry.py --write")
        return 2

    want = float(ref[key]["mean"])
    rel = abs(mean - want) / want
    tol = float(ref[key].get("tol", args.tol))
    print(f"  photometry {key}: {mean:.6f} vs reference {want:.6f} "
          f"({100 * rel:.3f}% off, tol {100 * tol:.1f}%)")
    if rel > tol:
        print(f"FATAL: THE SERVER IS RENDERING AT A DIFFERENT BRIGHTNESS.\n"
              f"  measured {mean:.6f}, reference {want:.6f}, {100 * rel:.2f}% off.\n"
              f"  Frames captured now are not comparable to the study's existing data\n"
              f"  (A-2/D-11). Do not collect, train, gate or score against this server.\n"
              f"  reference server: {ref[key].get('server_cmdline')}\n"
              f"  this server     : {cd.server_cmdline(C.PORT)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

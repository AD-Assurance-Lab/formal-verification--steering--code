#!/usr/bin/env python3
"""Capture steering response over a (lateral offset x heading error) grid.

WHY YAW HAD TO BE ADDED (F23). Every earlier capture placed the vehicle at lateral offsets
with its heading ALIGNED to the path, so the policy's response to heading error was never
observed. Closing the loop on offset feedback alone makes it an undamped oscillator, and
forward Euler then puts the discrete spectral radius above one:

    k_psi   0.0   -> |lambda| 1.115  diverges
    k_psi  -0.2   -> |lambda| 1.040  diverges
    k_psi  -0.5   -> |lambda| 0.915  stable

which is exactly what the tube did -- every condition, including clear weather where the
real vehicle holds 0.13 m. The divergence was a missing state, not a loose bound: the spring
was measured and the damper was not.

GRID. Offsets span the lane; yaws span the heading errors a lane-keeper actually sees. Both
are needed jointly rather than separately because the steering response to offset depends on
heading (a car pointed back toward the lane needs less correction than one pointed away),
and treating them as additive would discard precisely that coupling.

Saves projected model inputs (3x28x84), the same fixed separable projection used everywhere
else in the study.

    python scripts/capture_offset_yaw.py [--poses 40] [--segment A]
"""
import sys
import csv
import json
import math
import argparse
import signal
from pathlib import Path

import os
import numpy as np
import carla

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
import carla_env as env  # noqa: E402
import verifiable_disturbance as vd  # noqa: E402
from imaging import raw_to_bgr  # noqa: E402
from carla_lock import carla_lock  # noqa: E402

# OY_OFFSETS / OY_YAWS let the nominal-only capture (offset 0, yaw 0) run cheaply: the
# for-all-disturbance coverage claim is per-frame and needs no state grid, so it costs
# 3,200 frames per condition-direction instead of 72,000.
OFFSETS = np.array([float(x) for x in os.environ.get(
    "OY_OFFSETS", "-1.5,-1.0,-0.6,-0.3,0.0,0.3,0.6,1.0,1.5").split(",")])
YAWS = np.array([float(x) for x in os.environ.get(
    "OY_YAWS", "-6.0,-3.0,0.0,3.0,6.0").split(",")])   # degrees of heading error
CONDS = os.environ.get("OY_CONDS", "clear,fog,night,shadows").split(",")
OUT = REPO / os.environ.get("OY_OUT", "results/calibration/offset_yaw.npz")
# Model input size. Defaults to the published 84x28, so Town04 captures are unchanged.
# It is read here rather than hardcoded because the captures ARE the verifier's input:
# a student at a different resolution needs its own capture set.
# Default to the REGISTRY, not to Town04's 84x28. These captures ARE the verifier's
# input, so a stale default silently certifies a different network than the one that
# drives: this produced 84-wide frames while the registry was at 168, and nothing
# errored -- the arrays are simply the wrong shape for the student.
IN_W = int(os.environ.get("OY_IN_W", str(getattr(C, "TOWN06_INPUT_W", 84))
                          if getattr(C, "SECTION_BASED", False) else "84"))
IN_H = int(os.environ.get("OY_IN_H", str(getattr(C, "TOWN06_INPUT_H", 28))
                          if getattr(C, "SECTION_BASED", False) else "28"))


def _die_cleanly(signum, frame):
    """SIGTERM must run the cleanup, or the actors outlive the process.

    A killed capture left its vehicle and camera alive in the world, and the NEXT
    capture then photographed a road with a parked car in it -- invisible in the
    resulting arrays, which are the right shape and full of plausible frames. Python
    does not run `finally` on the default SIGTERM handler; raising turns the signal into
    a normal unwind so the existing teardown executes.
    """
    raise KeyboardInterrupt(f"signal {signum}")


def main():
    signal.signal(signal.SIGTERM, _die_cleanly)
    signal.signal(signal.SIGINT, _die_cleanly)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--poses", type=int, default=40)
    ap.add_argument("--start-m", type=float, default=0.0)
    # DEFAULT IS THE WHOLE ROUTE, not a 160 m slice.
    #
    # It defaulted to 160 m, which is a calibration-probe length, and a caller who passed
    # --poses without --length-m silently got 200 poses packed into 5.6% of a 2,861 m lap.
    # That happened: the Town04 redo's verification captures covered 160 m against the
    # published 2,861, and the certificate computed off them reproduced exactly -- so
    # nothing downstream complained, and a 160 m certificate was compared against full-lap
    # driving and reported as 6/6 agreement.
    #
    # A default that silently narrows the evidence is worse than no default. Pass
    # --length-m explicitly to capture a slice, and say why.
    ap.add_argument("--length-m", type=float, default=None,
                    help="metres of route to cover; default is the ENTIRE route. Pass a "
                         "value only for a deliberate slice (calibration probes).")
    # Town04 has two directions; Town06 has six named sections. Hardcoding the Town04
    # pair here made every Town06 capture die at argparse with "invalid choice: 's00'".
    ap.add_argument("--direction", default=C.SECTIONS[0],
                    choices=list(C.SECTIONS),
                    help="several sun-altitude failures are direction-specific: the sun's\n                          azimuth is fixed, so travelling east or west puts it ahead or\n                          behind. Verification measured in one direction cannot see a\n                          failure that only occurs in the other.")
    args = ap.parse_args()

    # THE ROUTE IS THE POSE SOURCE ON EVERY MAP.
    #
    # This was section-based maps only; Town04 read poses from the `live_pairs` dataset
    # instead. Two reasons it now reads the route as well:
    #
    #   1. The reason already given below and never applied to Town04 -- the route is the
    #      same geometry the closed-loop runs follow, so capture poses and driving agree
    #      by construction rather than by coincidence.
    #   2. `live_pairs` is a captured DATASET. Under D-11 the Town04 redo may not reuse
    #      data collected on the violating harness, and it was archived; making the
    #      verification captures depend on it would have reintroduced exactly the coupling
    #      the redo exists to remove. The routes are geometry, are tracked in git, and are
    #      unchanged.
    #
    # The poses therefore differ slightly from the published run's. That is a declared
    # difference of the redo, not a defect: it is the same road, sampled from the
    # definition of the road rather than from one drive along it.
    if True:
        from route import load_route, arc_lengths, route_length_m
        rt = np.asarray(load_route(args.direction), dtype=float)
        dx = np.diff(rt[:, 0], append=rt[0, 0])
        dy = np.diff(rt[:, 1], append=rt[0, 1])
        yaw_deg = np.degrees(np.arctan2(dy, dx))
        rows = [dict(x=rt[i, 0], y=rt[i, 1], yaw=yaw_deg[i]) for i in range(len(rt))]
        # X AND Y ONLY. Town04's routes are (N, 2) and this read them whole; Town06's LAP
        # route is (N, 3) and the third column is YAW IN DEGREES. Feeding all three
        # columns to a Euclidean norm made the lap's arc-length 5,299 m instead of
        # 2,289 m -- so every "metres along the route" lookup landed at roughly 40% of the
        # distance it named, and the capture would have covered the first ~920 m of a
        # 2,119 m scored road while its recorded span (computed from x and y alone) said
        # so. It would have been caught by the certifier's coverage floor rather than
        # silently, but only after a full capture run.
        xy = rt[:, :2]
    else:
        base = REPO / "pipeline" / "data" / "live_pairs"
        with open(base / "manifest.csv") as fh:
            rows = [r for r in csv.DictReader(fh)
                    if r["weather"] == "clear" and r["direction"] == args.direction]
        xy = np.array([[float(r["x"]), float(r["y"])] for r in rows])
    if args.length_m is None:
        # THE SCORED LENGTH, which is not the same as the route's geometry.
        #
        # Defaulting to the raw geometry is wrong in the opposite direction to the 160 m
        # bug and just as much a scope error. Town04's route is a closed 3,042 m loop, but
        # the study's scored prefix is LAP_END_M = 2,861 m: the last 181 m run through a
        # western traffic-light intersection that is a real ODD boundary, where the lane
        # centreline is undefined and which every closed-loop and verification number in
        # the study excludes. The published captures span exactly 2,861 m. Capturing the
        # full loop would certify 181 m of road the study does not claim, and the
        # certificate would not be comparable to the drives it is validated against.
        #
        # Town06's SIX SECTIONS were already built to their scored length, so there the
        # two agreed and this changed nothing. THE LAP IS DIFFERENT and the comment above
        # stopped being true when the route became one: the lap's geometry is 2,289 m and
        # its SCORED road is 2,119 m, because the two intersections are driven by pure
        # pursuit and excluded from every CTE. Capturing the geometry would certify 170 m
        # of intersection that no closed-loop cell scores -- the same error as Town04's
        # 181 m ODD-boundary tail, in the same direction, on the other map.
        geom = route_length_m(xy)
        scored = C.scored_len_m(args.direction) or geom
        args.length_m = min(scored, geom)
        note = "" if abs(geom - args.length_m) < 1.0 else \
            f" (route geometry is {geom:.0f} m; the tail is outside the scored prefix)"
        print(f"  --length-m not given: covering the whole SCORED route, "
              f"{args.length_m:.0f} m{note}", flush=True)
    if len(xy) < 2:
        sys.exit(f"no poses for direction '{args.direction}' -- refusing to capture")
    d = arc_lengths(xy)

    # SAMPLE THE SCORED ROAD, NOT THE ROUTE.
    #
    # `linspace` over route arc-length puts poses inside the bridged intersections, which
    # are not scored and therefore must not be certified. Sampling uniformly over SCORED
    # arc-length and mapping each sample back through the bridges keeps the poses evenly
    # spread over exactly the road the drives are graded on.
    bridges = sorted(C.bridge_spans_for(args.direction))

    def _to_route(s_scored):
        """scored arc-length -> route arc-length, stepping over each bridge."""
        r = args.start_m + s_scored
        for a, b in bridges:
            if r >= a:
                r += (b - a)
            else:
                break
        return r

    skipped_m = float(sum(b - a for a, b in bridges))
    if bridges:
        want = np.array([_to_route(s) for s in
                         np.linspace(0.0, args.length_m, args.poses)])
        print(f"  excluding {len(bridges)} bridged span(s), {skipped_m:.0f} m: poses are "
              f"spread over the {args.length_m:.0f} m of SCORED road, not the "
              f"{args.length_m + skipped_m:.0f} m of route", flush=True)
    else:
        want = np.linspace(args.start_m, args.start_m + args.length_m, args.poses)

    if bridges:
        # Snapping a target to the NEAREST route point can still land inside a bridge
        # when the target sits within a step of its edge. Mask the bridged points out of
        # the candidate set instead of hoping the snap misses them.
        ok = np.ones(len(d), dtype=bool)
        for a, b in bridges:
            ok &= ~((d >= a) & (d <= b))
        cand = np.flatnonzero(ok)
        idx = sorted({int(cand[np.argmin(np.abs(d[cand] - w))]) for w in want})
    else:
        idx = sorted({int(np.argmin(np.abs(d - w))) for w in want})
    poses = [rows[i] for i in idx]

    # REFUSE rather than warn. A pose inside a bridge is road the study does not claim,
    # and by the time it reaches the certificate nothing downstream can tell.
    if bridges:
        inside = [float(d[i]) for i in idx if any(a <= d[i] <= b for a, b in bridges)]
        if inside:
            sys.exit(f"REFUSING to capture: {len(inside)} pose(s) fall inside a bridged "
                     f"span at {['%.0f' % m for m in inside[:5]]} m. Bridged road is "
                     f"driven by pure pursuit and scored by nothing, so certifying it "
                     f"would not be comparable to the drives.")
    # A capture stores every CONTROL-RATE pose; the frozen stride of 8 is applied by the
    # certifier when it consumes them. So `--poses` is routinely larger than the number
    # of route points available (the lap asks for 1,280 against 1,147 points at 2 m), and
    # deduplicating to fewer is normal, not a fault. What is NOT normal is selecting far
    # fewer than the route can offer, which is what a broken arc-length lookup looks
    # like -- so the floor is measured against what is AVAILABLE, not what was asked.
    n_avail = int(np.count_nonzero(
        (d >= args.start_m) & (d <= args.start_m + args.length_m + skipped_m)
    )) - int(sum(np.count_nonzero((d >= a) & (d <= b)) for a, b in bridges))
    if len(poses) < 0.9 * min(args.poses, n_avail):
        sys.exit(f"REFUSING to capture: selected {len(poses)} poses, against "
                 f"{args.poses} requested and {n_avail} available on the scored road. "
                 f"That gap is what a broken arc-length lookup looks like.")

    n = len(CONDS) * len(poses) * len(OFFSETS) * len(YAWS)
    frames = np.zeros((len(CONDS), len(poses), len(OFFSETS), len(YAWS), 3, IN_H, IN_W),
                      np.float32)
    print(f"capturing {n} frames: {len(CONDS)} cond x {len(poses)} poses x "
          f"{len(OFFSETS)} offsets x {len(YAWS)} yaws")

    with carla_lock(owner="offset-yaw capture"):
        cl = carla.Client(C.HOST, C.PORT)
        cl.set_timeout(120.0)
        # LOAD THE CONFIGURED MAP. `get_world()` returns whatever is loaded, and a freshly
        # launched CARLA serves its DEFAULT map (Town10HD_Opt), not Town04. Placing the
        # vehicle at Town04 coordinates inside Town10 put it below grade for the whole lap
        # (settled z -2.60..1.09 m, pitch +-11 deg, 47 fallbacks) -- which looks exactly
        # like a broken settle and is not. Earlier runs only worked because a previous
        # closed-loop run had already loaded Town04.
        world = env.load_town04(cl, fresh=False)
        # enable_sync_mode also provisions bounded substepping. Hand-rolled settings here
        # left CARLA's defaults (0.01 x 10 = 0.1 s of physics per 0.2 s tick), so the
        # per-pose gravity settle ran under different physics than the driving pipeline --
        # and this capture feeds verification.
        orig = env.enable_sync_mode(world)
        v = cam = None
        try:
            # SPAWNS is keyed by section on a section-based map; the westbound /
            # eastbound pair is the Town04 special case.
            _spawn = (C.SPAWNS[args.direction] if getattr(C, "SECTION_BASED", False)
                      else (C.SPAWN_WESTBOUND if args.direction == "westbound"
                            else C.SPAWN_EASTBOUND))
            v = env.spawn_vehicle(world, _spawn)
            env.apply_control(v, carla.VehicleControl(brake=1.0))
            for _ in range(40):
                world.tick()
            z0 = v.get_transform().location.z

            # ROAD ATTITUDE PER POSE, measured by letting physics settle the vehicle.
            #
            # Freezing physics at the SPAWN ride height and restoring yaw only was wrong
            # wherever the road is not level with the spawn. Measured: the eastbound
            # stretch climbs 7.17 m over its first 195 m, and the capture there failed
            # validation at 0.202 against a 0.05 threshold -- the vehicle was floating or
            # buried metres above or below the road. Westbound passed at 0.016 only because
            # its first 195 m happens to be flat. Settling under gravity fixed both
            # (eastbound 0.007, westbound 0.014), so the road, not the arithmetic, has to
            # decide the ride height.
            #
            # Settling at all 72,000 placements would cost ~1.8M ticks, so it is done ONCE
            # PER POSE and reused across that pose's offsets and yaws: the offsets span
            # +-1.5 m laterally, over which the surface is effectively the same.
            # Drop from the PREVIOUS settled height, not from the map's waypoint. Town04's
            # highway is a figure-8 with an overpass, so `get_waypoint(project_to_road=True)`
            # can snap to the wrong deck; dropping from there sent the vehicle through the
            # world and recorded nonsense (z -25.07..11.00 m, pitch -78..+51 deg over a lap).
            # The route is continuous, so the previous pose's height is always a safe
            # reference, and every result is validated before it is accepted.
            def settle(x, y, yaw, ref_z, ticks=20):
                v.set_transform(carla.Transform(
                    carla.Location(x=x, y=y, z=ref_z + 0.5),
                    carla.Rotation(yaw=yaw)))
                v.set_target_velocity(carla.Vector3D(0, 0, 0))
                v.set_target_angular_velocity(carla.Vector3D(0, 0, 0))
                env.apply_control(v, carla.VehicleControl(brake=1.0))
                for _ in range(ticks):
                    world.tick()
                t = v.get_transform()
                return t.location.z, t.rotation.pitch, t.rotation.roll

            # ANCHOR ON THE ROAD AT EVERY POSE, do not chain from the previous one alone.
            # Chaining has no reference to the actual surface, so one bad seed propagates for
            # the whole lap and never recovers: on a freshly loaded map this produced
            # z -2.60..-1.79 m with pitch +-11.5 deg and 21 fallbacks, the vehicle rendering
            # from below grade for 2861 m. The running height is passed as the waypoint's z
            # HINT, which is what disambiguates Town04's overpass -- the failure that made
            # naive waypoint lookup unusable in the first place. Continuity now only picks
            # the deck; the road decides the height.
            cmap = world.get_map()
            ref = None
            attitude, rejected = [], 0
            # KEEP THE VIEWPORT ALIVE DURING SETTLING TOO.
            #
            # The chase camera was only driven inside the capture loop below, so for the
            # whole settling pass -- minutes, now that a lap is 1,492 poses -- a working
            # capture looked exactly like a hung one. That is the same failure the capture
            # loop's spectator call exists to prevent; it just was not applied to the phase
            # that happens first, which is the phase someone watching actually sees.
            _settle_seen = 0
            for r in poses:
                x, y, yaw = float(r["x"]), float(r["y"]), float(r["yaw"])
                hint = z0 if ref is None else ref
                wpz = cmap.get_waypoint(carla.Location(x=x, y=y, z=hint),
                                        project_to_road=True).transform.location.z
                az, ap, ar = settle(x, y, yaw, max(wpz, hint if ref else wpz))
                ap = ((ap + 180) % 360) - 180
                ar = ((ar + 180) % 360) - 180
                # a highway vehicle does not pitch or roll steeply, and it sits ON its road,
                # so a large tilt or a big gap from the surface means it fell or tumbled
                bad = abs(ap) > 12 or abs(ar) > 12 or abs(az - wpz) > 3.0
                if bad:
                    az, ap, ar = settle(x, y, yaw, wpz, ticks=40)
                    ap = ((ap + 180) % 360) - 180
                    ar = ((ar + 180) % 360) - 180
                    if abs(ap) > 12 or abs(ar) > 12 or abs(az - wpz) > 3.0:
                        # fall back to the road itself plus the settled ride height
                        az = wpz + (attitude[-1][0] - wpz if attitude else 0.3)
                        ap, ar = (attitude[-1][1], attitude[-1][2]) if attitude else (0.0, 0.0)
                        rejected += 1
                attitude.append((az, ap, ar))
                ref = az
                _settle_seen += 1
                if _settle_seen % 50 == 0:
                    try:
                        v.set_transform(carla.Transform(
                            carla.Location(x=float(r["x"]), y=float(r["y"]), z=az),
                            carla.Rotation(yaw=float(r["yaw"]))))
                        env.update_spectator(world, v)
                        world.tick()
                    except Exception:
                        pass      # cosmetic only; never let the viewport break a capture
            zs = [a[0] for a in attitude]
            ps = [a[1] for a in attitude]
            print(f"  settled {len(attitude)} poses: z {min(zs):.2f}..{max(zs):.2f} m, "
                  f"pitch {min(ps):+.2f}..{max(ps):+.2f} deg, {rejected} fell back",
                  flush=True)
            v.set_simulate_physics(False)
            for ci, cond in enumerate(CONDS):
                if cam is not None:
                    cam.destroy()
                cam, q = env.set_condition(world, v, cond)
                for _ in range(25):
                    f = world.tick()
                    try:
                        env.grab_frame(q, f)
                    except Exception:
                        pass
                for pi, r in enumerate(poses):
                    yaw0 = float(r["yaw"])
                    nx = -math.sin(math.radians(yaw0))
                    ny = math.cos(math.radians(yaw0))
                    # Keep the chase camera on the car. Without this the viewport stays
                    # frozen wherever it was while the vehicle teleports along the route,
                    # so a capture that is working looks identical to one that has hung --
                    # and eyeballing the render is what caught the fog-in-night preset bug.
                    env.update_spectator(world, v)
                    for oi, offv in enumerate(OFFSETS):
                        for yi, dy in enumerate(YAWS):
                            az, apitch, aroll = attitude[pi]
                            v.set_transform(carla.Transform(
                                carla.Location(x=float(r["x"]) + nx * offv,
                                               y=float(r["y"]) + ny * offv, z=az),
                                carla.Rotation(pitch=apitch, yaw=yaw0 + float(dy),
                                               roll=aroll)))
                            for _ in range(4):
                                world.tick()
                            while True:
                                fid = world.tick()
                                try:
                                    img = raw_to_bgr(env.grab_frame(q, fid))
                                    break
                                except Exception:
                                    pass
                            frames[ci, pi, oi, yi] = vd._project(
                                img.astype(np.float32) / 255.0, IN_W, IN_H).reshape(3, IN_H, IN_W)
                print(f"  {cond}: {len(poses)*len(OFFSETS)*len(YAWS)} frames", flush=True)
        finally:
            try:
                if cam:
                    cam.destroy()
                if v:
                    v.destroy()
            except Exception:
                pass
            world.apply_settings(orig)

    # RECORD THE COVERAGE IN THE FILE. A capture that silently covers 5.6% of the route
    # looks exactly like one that covers all of it, from the outside and from downstream:
    # the shapes are the same, the certificate computes fine, and the number it produces is
    # wrong about a different thing than it claims. Writing the span means a consumer can
    # check, and certify_* now does.
    # MEASURE THE POSES THAT WERE CAPTURED, not the route they were drawn from.
    #
    # This read the whole route, so it recorded the ROUTE's length as the capture's
    # coverage. Every capture would then claim full coverage no matter how short it was,
    # which defeats the guard this field exists to feed: the certifiers TRUST
    # route_span_m when it is present and only measure the pose track when it is absent.
    # The 160 m captures were caught solely because they predate the field.
    # ONE definition of "metres of scored road these poses span" (route.scored_span_m),
    # so the number recorded here is the number the certifier and the audit recompute.
    # This used to subtract each bridge chord with its own arithmetic; the certifier and
    # the audit each summed consecutive poses naively, and the three disagreed by 178 m.
    from route import scored_span_m
    _cov = scored_span_m([float(r["x"]) for r in poses], [float(r["y"]) for r in poses])
    print(f"  scored-road coverage: {args.length_m:.0f} m requested, {_cov:.0f} m "
          f"actually spanned by {len(poses)} captured poses"
          + (f" (excluding {skipped_m:.0f} m of bridge)" if bridges else ""), flush=True)
    np.savez_compressed(
        OUT, frames=frames, offsets=OFFSETS, yaws=YAWS, conds=np.array(CONDS),
        route_span_m=_cov, length_m_requested=args.length_m,
        bridged_m_excluded=skipped_m,
        pose_x=np.array([float(r["x"]) for r in poses]),
        pose_y=np.array([float(r["y"]) for r in poses]),
        pose_yaw=np.array([float(r["yaw"]) for r in poses]))
    print(f"\nwrote {OUT}  ({OUT.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

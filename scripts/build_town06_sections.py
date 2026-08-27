#!/usr/bin/env python3
"""Build the Town06 deployment-test route as a set of clean SECTIONS.

Town04 gives the policy one 2861 m lap driven in two directions, because its highway has
dedicated multi-lane eastbound and westbound carriageways. Town06 does not: its outer
loop is a ring whose lanes wrap around, so "the opposing carriageway" is a local property
rather than a property of a lane, and the longest stretch clean in BOTH directions at
once is only 430 m.

What the experiment actually needs is a real functioning policy driving a few miles of
clean road. Direction pairing is not a requirement, so this builds a SET of disjoint
clean sections totalling the target distance instead.

A section is contiguous road that is:
  - lane-marked on BOTH sides             (the policy steers off its two lane lines. The
                                           original test rejected a waypoint only when
                                           BOTH markings were absent, so road keeping one
                                           line and losing the other passed as clean --
                                           s02 ran 385 m of its 628 m, 61%, with only one
                                           line, and s04 lost one for 33 m at its spawn)
  - on a MULTI-LANE carriageway           (highway, not a ramp connector. Ramps beside
                                           the route are fine; driving one is not.
                                           Excluding every junction-flagged waypoint was
                                           too blunt and left 1,116 m, because ramp
                                           junction areas span the highway lanes too.
                                           Dashed markings alone were too weak: connector
                                           lanes carry them, and five of six sections then
                                           started inside a junction, three on single-lane
                                           connectors. Lane count separates them: a
                                           connector is 1, this highway is 3-6)
  - DASHED on both sides                  (the policy learns to follow two dashed lane
                                           lines and nothing else. Only an INTERIOR lane
                                           has dashed on both sides -- the rightmost has
                                           a solid edge line, the leftmost a solid
                                           centreline -- so this also keeps the ego out
                                           of the rightmost lane, where ramps merge and
                                           where four of the six first sections had put
                                           it. s01 was a single-lane road with no dashed
                                           context at all)
  - not on a signal-controlled lane
  - lane width 3.500 m                    (the CTE budget is derived from it)

Junctions are NOT excluded as such. CARLA's is_junction covers on-ramps, off-ramps and
merges as well as crossroads, and ramps are legitimate highway road: 505 m of the first
selection was flagged is_junction while only 73 m was true crossing-traffic intersection.
What matters is whether the EGO LANE keeps its two markings, which the marking test above
decides directly and without having to classify junction geometry.

Sections are de-duplicated geometrically: adjacent lanes of the same carriageway trace
almost the same line, and counting them separately would inflate the distance without
adding any new road.

    CARLA_PORT=3000 python3 scripts/build_town06_sections.py [--target-km 4.0] [--dry-run]
"""
import argparse
import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "pipeline"))
sys.path.insert(0, _HERE)

import carla  # noqa: E402
import config as C  # noqa: E402
from carla_lock import carla_lock  # noqa: E402
from survey_map_routes import trace, curvature  # noqa: E402
from build_study_route import controlled_waypoints, dstats, REF, LANE_W, LANE_W_TOL  # noqa: E402

MAP = "Town06"
NONE_MARK = carla.LaneMarkingType.NONE
MIN_SECTION_M = 350.0
# Dashed on both sides is the requirement. Only an interior lane can have it, so this
# also keeps the ego out of the rightmost lane where ramps merge.
DASHED_MARKS = {carla.LaneMarkingType.Broken, carla.LaneMarkingType.BrokenBroken}
MIN_CARRIAGEWAY_LANES = 3   # a ramp connector is 1; Town06's highway is 3-6
TAIL_M = 300.0            # stored past the scored end so pure pursuit never wraps
DEDUP_M = 25.0            # two sections closer than this along their length are the same road
ROUTES_DIR = os.path.join(C.DATASET_DIR, f"routes_{MAP.lower()}")


def same_direction_lanes(wp):
    """Total driving lanes of the carriageway this waypoint belongs to."""
    n = 1
    w = wp
    while True:
        nxt = w.get_left_lane()
        if (nxt is None or nxt.lane_type != carla.LaneType.Driving
                or (nxt.lane_id > 0) != (wp.lane_id > 0)):
            break
        n += 1
        w = nxt
    w = wp
    while True:
        nxt = w.get_right_lane()
        if (nxt is None or nxt.lane_type != carla.LaneType.Driving
                or (nxt.lane_id > 0) != (wp.lane_id > 0)):
            break
        n += 1
        w = nxt
    return n


def lanes_from_left(wp):
    """How many same-direction driving lanes lie to the left of this one. 0 = leftmost."""
    n, w = 0, wp
    while True:
        nxt = w.get_left_lane()
        if (nxt is None or nxt.lane_type != carla.LaneType.Driving
                or (nxt.lane_id > 0) != (wp.lane_id > 0)):
            return n
        n += 1
        w = nxt


def clean_mask(wmap, r, CTL):
    ok = np.ones(len(r), bool)
    for i, (x, y) in enumerate(r):
        wp = wmap.get_waypoint(carla.Location(x=float(x), y=float(y), z=0.5),
                               project_to_road=True, lane_type=carla.LaneType.Driving)
        lm = wp.left_lane_marking.type if wp.left_lane_marking else NONE_MARK
        rm = wp.right_lane_marking.type if wp.right_lane_marking else NONE_MARK
        # DASHED on BOTH sides. This is the whole requirement: the policy learns to
        # follow two dashed lane lines and nothing else, so every other variable is kept
        # off the road rather than trained around.
        #
        # It subsumes the lane-position rule it replaces. A dashed line on both sides can
        # only occur on an INTERIOR lane -- the rightmost lane has a solid edge line and
        # the leftmost a solid centreline -- so requiring dashed automatically excludes
        # the rightmost lane, which is where ramps merge and where four of the six first
        # sections had put the ego. Pinning the index instead was a proxy for this, and a
        # worse one: it cut the available road to 2,020 m after de-duplication, while the
        # dashed test leaves 196 runs of 350 m or more, the longest 896 m.
        # A MULTI-LANE CARRIAGEWAY, not a connector. This is the highway-versus-ramp
        # distinction, and it is the one that matters: ramps joining and leaving beside
        # the route are ordinary highway furniture, but the ego must not be DRIVING one.
        #
        # Excluding every junction-flagged waypoint was too blunt -- Town06's ring is
        # punctuated by ramp junctions whose areas span the highway lanes themselves, so
        # it fragmented the highway and left 1,116 m. Requiring dashed markings alone was
        # too weak -- connector lanes carry Broken markings, and five of six sections then
        # started inside a junction, three on single-lane connectors. Lane COUNT separates
        # them cleanly: a connector is one lane, the highway is three to six.
        if same_direction_lanes(wp) < MIN_CARRIAGEWAY_LANES:
            ok[i] = False
        elif lm not in DASHED_MARKS or rm not in DASHED_MARKS:
            ok[i] = False
        elif abs(wp.lane_width - LANE_W) > LANE_W_TOL:
            ok[i] = False
    if len(CTL):
        d = np.hypot(CTL[:, 0][None, :] - r[:, 0][:, None],
                     CTL[:, 1][None, :] - r[:, 1][:, None]).min(axis=1)
        ok &= (d >= 3.0)
    return ok


def runs(ok, min_m):
    out, s = [], None
    for i, v in enumerate(ok):
        if v and s is None:
            s = i
        elif not v and s is not None:
            if (i - 1 - s) * 2.0 >= min_m:
                out.append((s, i - 1))
            s = None
    if s is not None and (len(ok) - 1 - s) * 2.0 >= min_m:
        out.append((s, len(ok) - 1))
    return sorted(out, key=lambda t: -(t[1] - t[0]))


def overlaps(a, b, tol=DEDUP_M, frac=0.5):
    """True if `a` mostly retraces `b` -- adjacent lanes of one carriageway do."""
    d = np.hypot(b[:, 0][None, :] - a[:, 0][:, None],
                 b[:, 1][None, :] - a[:, 1][:, None]).min(axis=1)
    return float((d < tol).mean()) >= frac


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-km", type=float, default=4.0,
                    help="total scored distance to reach (default 4.0 km ~ 2.5 miles)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    target_m = args.target_km * 1000.0

    with carla_lock(owner="build_town06_sections"):
        cl = carla.Client(C.HOST, C.PORT)
        cl.set_timeout(300.0)
        world = cl.load_world(MAP)
        wmap = world.get_map()
        CTL = controlled_waypoints(world)
        sl = np.array([[l.location.x, l.location.y]
                       for l in world.get_lightmanager().get_all_lights(carla.LightGroup.Street)])

        seeds = [w for w in wmap.generate_waypoints(40.0) if not w.is_junction]
        seen, found = set(), []
        for sd in seeds:
            key = (sd.road_id, sd.lane_id)
            if key in seen:
                continue
            seen.add(key)
            try:
                r, _, _ = trace(wmap, sd, max_pts=6000)
            except Exception:
                continue
            if len(r) < 200:
                continue
            ok = clean_mask(wmap, r, CTL)
            for a, b in runs(ok, MIN_SECTION_M):
                found.append(((b - a) * 2.0, key, r, a, b))
        found.sort(key=lambda t: -t[0])
        print(f"{len(found)} clean runs >= {MIN_SECTION_M:.0f} m before de-duplication")

        chosen, total = [], 0.0
        for ln, key, r, a, b in found:
            seg = r[a:b + 1]
            if any(overlaps(seg, c["pts"]) for c in chosen):
                continue
            wp0 = wmap.get_waypoint(carla.Location(x=float(seg[-1][0]), y=float(seg[-1][1]), z=0.5),
                                    project_to_road=True, lane_type=carla.LaneType.Driving)
            tail = []
            wp = wp0
            for _ in range(int(TAIL_M / 2.0)):
                nxt = wp.next(2.0)
                if not nxt:
                    break
                wp = nxt[0]
                tail.append([wp.transform.location.x, wp.transform.location.y])
            full = np.vstack([seg, np.asarray(tail)]) if tail else seg
            st = dstats(curvature(seg)[0])
            lit = (float((np.hypot(sl[:, 0][None, :] - seg[:, 0][:, None],
                                   sl[:, 1][None, :] - seg[:, 1][:, None]).min(axis=1) < 30).mean())
                   if len(sl) else 0.0)
            chosen.append(dict(pts=seg, full=full, road=int(key[0]), lane=int(key[1]),
                               length_m=float(ln), lit=lit, **st))
            total += ln
            if total >= target_m:
                break

        if total < target_m * 0.75:
            sys.exit(f"only {total:.0f} m of distinct clean road found, target {target_m:.0f} m")

        print(f"\n{len(chosen)} distinct sections, {total:.0f} m total "
              f"({total/1609.34:.2f} miles)   [Town04: 2861 m x 2 directions]")
        print(f"{'name':>8} {'road/lane':>11} {'len_m':>7} {'smax':>7} {'lit':>5}")
        for i, c in enumerate(chosen):
            c["name"] = f"s{i:02d}"
            hd = math.degrees(math.atan2(float(c["full"][1][1] - c["full"][0][1]),
                                         float(c["full"][1][0] - c["full"][0][0])))
            c["spawn"] = dict(x=float(c["full"][0][0]), y=float(c["full"][0][1]),
                              z=0.5, yaw=hd)
            print(f"{c['name']:>8} {c['road']:>6}/{c['lane']:<4} {c['length_m']:>7.0f} "
                  f"{c['smax']:>7.4f} {c['lit']:>5.2f}")
        print(f"{'':>8} {'Town04':>11} {'2861':>7} {REF['smax']:>7.4f} {'1.00':>5}")

        # Re-verify: every stored section must be 100 % clean.
        for c in chosen:
            ok = clean_mask(wmap, c["pts"], CTL)
            if ok.mean() < 1.0:
                sys.exit(f"FAILED: {c['name']} only {ok.mean()*100:.1f}% clean")
        print("\nall sections verified 100% clean")

        if args.dry_run:
            print("[dry-run] nothing written")
            return
        os.makedirs(ROUTES_DIR, exist_ok=True)
        for c in chosen:
            np.save(os.path.join(ROUTES_DIR, f"{c['name']}.npy"), c["full"])
        meta = dict(
            map=MAP, step_m=2.0, town04_reference=REF,
            sections=[dict(name=c["name"], road=c["road"], lane=c["lane"],
                           length_m=c["length_m"], scored_len_m=c["length_m"],
                           lit=c["lit"], spawn=c["spawn"],
                           s50=c["s50"], s90=c["s90"], s99=c["s99"], smax=c["smax"])
                      for c in chosen],
            total_scored_m=float(total),
            scored_len_m=float(min(c["length_m"] for c in chosen)),
            spawns={c["name"]: c["spawn"] for c in chosen},
            rationale="Town06 has no dedicated opposing carriageways on its outer loop, "
                      "so the route is a set of disjoint clean sections totalling a few "
                      "miles rather than one lap driven both ways",
            selection="geometry only; no policy behaviour used")
        json.dump(meta, open(os.path.join(ROUTES_DIR, "route_meta.json"), "w"), indent=2)
        print(f"wrote {ROUTES_DIR} ({len(chosen)} sections)")


if __name__ == "__main__":
    main()

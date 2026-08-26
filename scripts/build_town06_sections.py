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
  - lane-marked on at least one side      (what a lane keeper follows; the first Town06
                                           route failed here, 7.55 % unmarked, and its
                                           teacher failed all six DAgger rounds while the
                                           oracle drove the same route at 0.43 ft)
  - not on a signal-controlled lane
  - lane width 3.500 m                    (the CTE budget is derived from it)

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
TAIL_M = 300.0            # stored past the scored end so pure pursuit never wraps
DEDUP_M = 25.0            # two sections closer than this along their length are the same road
ROUTES_DIR = os.path.join(C.DATASET_DIR, f"routes_{MAP.lower()}")


def clean_mask(wmap, r, CTL):
    ok = np.ones(len(r), bool)
    for i, (x, y) in enumerate(r):
        wp = wmap.get_waypoint(carla.Location(x=float(x), y=float(y), z=0.5),
                               project_to_road=True, lane_type=carla.LaneType.Driving)
        lm = wp.left_lane_marking.type if wp.left_lane_marking else NONE_MARK
        rm = wp.right_lane_marking.type if wp.right_lane_marking else NONE_MARK
        if (lm == NONE_MARK and rm == NONE_MARK) or abs(wp.lane_width - LANE_W) > LANE_W_TOL:
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

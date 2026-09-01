#!/usr/bin/env python3
"""Build the Town06 lap from a HUMAN-DRIVEN track, snapped to the lane centreline.

Why from a driven track rather than traced from the lane graph: the graph lies in ways
that matter here. Across one junction the carriageway gains a lane AND shifts 2.3 m
laterally, so "lane -4" means a different physical lane on each side -- driving straight
through puts the car on a marking. A tracer following lane ids takes that wrong turn
silently. A human driving it does not.

What the track supplies: which lane, and where the ODD boundaries are. What the map
supplies: the exact centreline. The driven position is never used directly -- it is only
the choice of lane -- so the driver does not need to be centred.

Lanes are chosen by MARKINGS, not by id: a lane-follower needs a marking on both sides,
and the id is exactly the thing that changes meaning across a junction.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/build_town06_lap_from_track.py
"""
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
import numpy as np                                            # noqa: E402
import carla                                                  # noqa: E402
import config as C                                            # noqa: E402

TRACK = REPO / "results" / "town06_logs" / "ego_track.csv"
OUT = REPO / "pipeline" / "data" / "routes_town06"
STEP_M = 2.0
USABLE = {"Broken", "SolidBroken", "BrokenBroken", "BrokenSolid", "Solid"}

# The points Zach marked while driving, in order.
START = (660.20, 24.29)
BRIDGES = [((62.15, -15.78), (-25.32, -15.42)),      # bridge 1
           ((-56.91, 243.08), (25.37, 240.76))]      # bridge 2, the 2.3 m lateral shift
END = (661.19, 195.01)                                # cut before the double intersection


def usable(wp):
    lm = str(wp.left_lane_marking.type).split(".")[-1]
    rm = str(wp.right_lane_marking.type).split(".")[-1]
    return lm in USABLE and rm in USABLE


def best_lane(m, x, y):
    """The lane the driver was in, or the nearest one with markings on both sides."""
    wp = m.get_waypoint(carla.Location(x=x, y=y, z=0.5), project_to_road=True)
    if usable(wp):
        return wp
    for grab in ("get_left_lane", "get_right_lane"):
        w = getattr(wp, grab)()
        hops = 0
        while w is not None and w.lane_type == carla.LaneType.Driving and hops < 3:
            if usable(w):
                return w
            w = getattr(w, grab)()
            hops += 1
    return wp


def main():
    client = carla.Client("127.0.0.1", int(C.PORT)); client.set_timeout(60.0)
    m = client.get_world().get_map()

    # TRACE THE LANE GRAPH FROM THE MARKED START, GOING STRAIGHT.
    #
    # The driven track is not used for geometry at all, and does not need to be: once the
    # lap was cut before the double intersection it contains no turns, so "follow the lane,
    # keep straight at forks" reproduces it exactly -- and gives clean centrelines instead
    # of a human's manoeuvring. Three attempts at deriving geometry from the track failed
    # in three different ways (doubling back, corner-cutting, and lapping), all because a
    # positioning car reverses and re-aligns and a route must not.
    #
    # The track remains authoritative for the things only a human could decide: WHERE the
    # lap starts and ends, WHICH lane keeps dashed lines on both sides, and where the ODD
    # boundaries are. Those are the marked points at the top of this file.
    start_wp = best_lane(m, *START)
    print(f"start: road {start_wp.road_id} lane {start_wp.lane_id} "
          f"({start_wp.transform.location.x:.1f}, {start_wp.transform.location.y:.1f})")

    # AT A FORK, GO WHERE THE HUMAN WENT.
    #
    # "Keep the least-turning branch" is not enough: at the central intersection it took
    # the northbound road, drove 1,200 m up and back down, and rejoined -- a detour that
    # looks like a plausible route in the numbers and is obvious the moment it is plotted.
    #
    # The track disambiguates it. Scoring a candidate by its distance to the NEAREST track
    # sample needs no cursor and cannot stall, which is how the earlier attempt failed:
    # a branch that leaves the driven path is immediately far from all of it.
    track_pts = np.array([[float(r["x"]), float(r["y"])] for r in
                          csv.DictReader(open(TRACK))])

    def near_track(wp):
        q = np.array([wp.transform.location.x, wp.transform.location.y])
        return float(np.linalg.norm(track_pts - q, axis=1).min())

    def look_ahead_cost(wp, steps=12):
        """How far a branch strays from the driven track over the next ~24 m.

        Scoring the immediate successor is useless: at a fork both branches start within
        2 m of the track and the choice is a coin flip. That is how the route took the
        northbound connector at the central intersection and drove 1,200 m up and back.
        A branch reveals itself a few steps in.
        """
        cost, w = 0.0, wp
        for _ in range(steps):
            nx = w.next(STEP_M)
            if not nx:
                break
            w = nx[0]
            cost += near_track(w)
        return cost

    def straight_on(wp):
        nxts = wp.next(STEP_M)
        if not nxts:
            return None
        if len(nxts) == 1:
            return nxts[0]
        return min(nxts, key=look_ahead_cost)

    wps, wp = [start_wp], start_wp
    endp = np.array(END)
    for _ in range(3000):
        nxt = straight_on(wp)
        if nxt is None:
            print("  lane ended"); break
        wp = nxt
        wps.append(wp)
        here = np.array([wp.transform.location.x, wp.transform.location.y])
        if len(wps) > 100 and float(np.linalg.norm(here - endp)) < 4.0:
            print(f"  reached the marked end after {len(wps)} points"); break

    route = np.array([[w.transform.location.x, w.transform.location.y,
                       w.transform.rotation.yaw] for w in wps])
    seg = np.linalg.norm(np.diff(route[:, :2], axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    print(f"route: {len(route)} points, {arc[-1]:.0f} m long")

    def arc_at(pt):
        return float(arc[int(np.argmin(np.linalg.norm(route[:, :2] - np.array(pt), axis=1)))])
    spans = [sorted([arc_at(a), arc_at(b)]) for a, b in BRIDGES]
    scored = arc[-1] - sum(b - a for a, b in spans)
    print(f"  scored (policy): {scored:7.0f} m  {100*scored/arc[-1]:.0f}%")
    for a, b in spans:
        print(f"  BRIDGE (PPC):    {a:7.0f} -> {b:7.0f} m   ({b-a:.0f} m)")

    OUT.mkdir(parents=True, exist_ok=True)
    np.save(OUT / "lap.npy", route)
    (OUT / "lap_meta.json").write_text(json.dumps(dict(
        length_m=float(arc[-1]), n_points=int(len(route)), step_m=STEP_M,
        scored_m=float(scored), bridges=spans,
        start=list(START), end=list(END),
        built_from="human-driven track, snapped to lane centreline",
        note="lanes chosen by MARKINGS not lane_id: the carriageway gains a lane and "
             "shifts 2.3 m laterally across bridge 2, so ids change meaning across it",
    ), indent=2))
    print(f"\n  wrote {OUT/'lap.npy'} and lap_meta.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

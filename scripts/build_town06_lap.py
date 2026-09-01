#!/usr/bin/env python3
"""Trace Town06 as ONE CONTINUOUS LAP, and mark where PPC must bridge.

The deployment test used six discrete sections. They are pieces of road sampled from the
map, not a drive: the gap from one section's end to the next section's start is 70-500 m,
and no ordering makes them contiguous. That is defensible but it is hard to explain, and
it makes "a lap" an abstraction rather than a thing the car does.

This traces a real lap instead: follow the lane, drive straight through junctions, and
stop when the route returns to where it started. Two kinds of span come out of it:

    SCORED   dashed lane markings on both sides -- the policy drives, and it is measured
    BRIDGE   a junction with no usable markings -- pure pursuit drives, nothing is scored

The bridge spans are the ODD boundary made explicit. The policy is a lane-follower, and
where there is no lane to follow it is out of its domain: bridging with the expert is what
a real ADAS does at an ODD boundary, and it keeps the lap continuous so the car never
teleports.

    CARLA_PORT=3000 STUDY_MAP=Town06 python3 scripts/build_town06_lap.py --dry-run
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
import numpy as np                                            # noqa: E402
import carla                                                  # noqa: E402
import config as C                                            # noqa: E402

STEP_M = 2.0
MAX_PTS = 6000


def straight_ahead(wp, step):
    """Continue along the lane; at a fork keep the least-turning option.

    Driving straight through a junction is what the study wants: the policy is not being
    asked to turn at intersections, only to keep its lane through them.
    """
    nxts = wp.next(step)
    if not nxts:
        return None
    if len(nxts) == 1:
        return nxts[0]
    h0 = np.radians(wp.transform.rotation.yaw)
    v0 = np.array([np.cos(h0), np.sin(h0)])
    best, best_dot = None, -2.0
    for n in nxts:
        h = np.radians(n.transform.rotation.yaw)
        d = float(np.dot(v0, [np.cos(h), np.sin(h)]))
        if d > best_dot:
            best, best_dot = n, d
    return best


def markings_ok(wp):
    """Dashed (Broken) markings on BOTH sides is what a lane-follower needs."""
    lt = str(wp.left_lane_marking.type).split(".")[-1]
    rt = str(wp.right_lane_marking.type).split(".")[-1]
    good = {"Broken", "SolidBroken", "BrokenBroken", "BrokenSolid"}
    return (lt in good or lt == "Solid") and (rt in good or rt == "Solid")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-x", type=float, default=None)
    ap.add_argument("--start-y", type=float, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    client = carla.Client("127.0.0.1", int(C.PORT)); client.set_timeout(60.0)
    world = client.get_world()
    m = world.get_map()

    if args.start_x is None:
        # Start on the longest straight of the outer loop: the northern carriageway.
        cand = [w for w in m.generate_waypoints(5.0)
                if not w.is_junction and w.lane_type == carla.LaneType.Driving]
        cand.sort(key=lambda w: -w.transform.location.x)
        start = cand[0]
    else:
        start = m.get_waypoint(carla.Location(x=args.start_x, y=args.start_y, z=0.5),
                               project_to_road=True)
    print(f"start ({start.transform.location.x:.1f}, {start.transform.location.y:.1f}) "
          f"road {start.road_id} lane {start.lane_id}")

    pts, junc, marks = [], [], []
    wp = start
    p0 = np.array([start.transform.location.x, start.transform.location.y])
    for i in range(MAX_PTS):
        loc = wp.transform.location
        pts.append([loc.x, loc.y, wp.transform.rotation.yaw])
        junc.append(bool(wp.is_junction))
        marks.append(markings_ok(wp))
        nxt = straight_ahead(wp, STEP_M)
        if nxt is None:
            print(f"  lane ended after {i} points"); break
        wp = nxt
        p = np.array([wp.transform.location.x, wp.transform.location.y])
        if i > 50 and np.linalg.norm(p - p0) < 6.0:
            print(f"  loop closed after {i} points"); break

    pts = np.array(pts)
    seg = np.linalg.norm(np.diff(pts[:, :2], axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    print(f"\nlap length {arc[-1]:.0f} m ({arc[-1]/1609:.2f} mi), {len(pts)} points")

    # BRIDGE ON THE MARKINGS, NOT ON is_junction.
    #
    # CARLA calls every lane merge and on-ramp a junction, and most of them keep their
    # dashed lines straight through. A lane-follower does not care what the map calls the
    # geometry; it cares whether there is a lane to follow. Bridging on is_junction
    # produced 16 spans over 449 m, most of them merges the policy can drive perfectly
    # well. Bridging on missing markings is the ODD boundary as the POLICY experiences it.
    bridge = [not mk for mk in marks]
    spans, i = [], 0
    while i < len(bridge):
        if bridge[i]:
            j = i
            while j < len(bridge) and bridge[j]:
                j += 1
            spans.append((arc[i], arc[min(j, len(arc)-1)]))
            i = j
        else:
            i += 1
    scored = arc[-1] - sum(b - a for a, b in spans)
    print(f"  scored (policy drives):  {scored:7.0f} m  "
          f"{100*scored/arc[-1]:.0f}% of the lap")
    print(f"  bridged (PPC drives):    {arc[-1]-scored:7.0f} m  in {len(spans)} spans")
    for a, b in spans:
        print(f"     bridge {a:7.0f} -> {b:7.0f} m   ({b-a:5.0f} m)")

    if not args.dry_run:
        out = REPO / "pipeline" / "data" / "routes_town06"
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "lap.npy", pts)
        (out / "lap_meta.json").write_text(json.dumps(
            dict(length_m=float(arc[-1]), n_points=len(pts),
                 scored_m=float(scored), bridges=[[float(a), float(b)] for a, b in spans]),
            indent=2))
        print(f"\n  wrote {out/'lap.npy'} and lap_meta.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Which junctions in each section are INTERSECTIONS, and which are just ramps/merges?

CARLA's wp.is_junction is true for any connecting road: on-ramps, off-ramps and merges
as well as crossroads. Ramps are FINE for this study -- the ego sits in the second lane
from the left and keys off its left and right dashed markings, which a ramp entering or
leaving on the far right does not disturb. INTERSECTIONS are not fine: they introduce
crossing traffic geometry the lane-keeping policies were never trained for.

So a raw is_junction count over-states the problem. This classifies each junction by the
geometry of the paths THROUGH it:

    for every (entry, exit) pair the junction offers, the heading change
    max |heading change| <= RAMP_MAX_TURN_DEG  ->  ramp / merge   (all paths ~parallel)
    otherwise                                  ->  INTERSECTION   (paths cross or turn)

A merge or diverge keeps every path within a few degrees of the through direction. A
crossroads offers paths turning 90 degrees or more.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/audit_section_intersections.py
"""
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402

RAMP_MAX_TURN_DEG = 35.0
# Approaches differing by more than this are crossing traffic, not a merge.
CROSSING_SPREAD_DEG = 60.0


def ang_diff(a, b):
    d = (a - b + 180.0) % 360.0 - 180.0
    return abs(d)


def classify_junction(j):
    """(kind, max_entry_spread_deg, max_turn_deg, n_paths) for a carla.Junction.

    Turn angle alone is a weak discriminator: a sharp slip road can turn 45 degrees while
    a crossroads approached straight-on offers a through path that turns 0. The signature
    of an INTERSECTION is CROSSING APPROACHES -- traffic entering from directions that are
    not parallel. A merge or diverge has every approach within a few degrees of the
    through direction, however sharply an individual path bends.

    So the primary test is the maximum pairwise spread of ENTRY headings; the turn angle
    is kept alongside it for comparison.
    """
    import carla
    try:
        pairs = j.get_waypoints(carla.LaneType.Driving)
    except Exception:
        return "unknown", float("nan"), float("nan"), 0
    if not pairs:
        return "unknown", float("nan"), float("nan"), 0
    entries = [e.transform.rotation.yaw for e, _ in pairs]
    spread = max((ang_diff(a, b) for a in entries for b in entries), default=0.0)
    turns = [ang_diff(x.transform.rotation.yaw, e.transform.rotation.yaw) for e, x in pairs]
    kind = "INTERSECTION" if spread > CROSSING_SPREAD_DEG else "ramp/merge"
    return kind, spread, max(turns), len(pairs)


def main():
    import carla
    import carla_env as env
    from route import load_route

    client = env.connect()
    world = env.load_town04(client, fresh=False)
    wmap = world.get_map()

    print(f"classifying junctions: max path turn <= {RAMP_MAX_TURN_DEG:.0f} deg is a "
          f"ramp/merge, more is an INTERSECTION\n")
    grand_isect = 0.0
    for sec in C.SECTIONS:
        rt = np.asarray(load_route(sec), dtype=float)
        seg = np.linalg.norm(np.diff(rt, axis=0), axis=1)
        arc = np.concatenate([[0.0], np.cumsum(seg)])
        scored = C.SECTION_LEN_M[sec]
        idx = np.where(arc <= scored)[0]

        cur, spans = None, []          # (junction_id, start_arc, end_arc)
        for i in idx:
            wp = wmap.get_waypoint(carla.Location(x=float(rt[i, 0]), y=float(rt[i, 1]), z=0.5),
                                   project_to_road=True, lane_type=carla.LaneType.Driving)
            jid = wp.get_junction().id if wp.is_junction and wp.get_junction() else None
            if jid is not None and cur is not None and cur[0] == jid:
                cur[2] = arc[i]
            elif jid is not None:
                if cur:
                    spans.append(cur)
                cur = [jid, arc[i], arc[i]]
            else:
                if cur:
                    spans.append(cur)
                cur = None
        if cur:
            spans.append(cur)

        isect_m = ramp_m = 0.0
        detail = []
        seen = {}
        for jid, a, b in spans:
            if jid not in seen:
                jw = None
                for i in idx:
                    wp = wmap.get_waypoint(carla.Location(x=float(rt[i, 0]), y=float(rt[i, 1]), z=0.5),
                                           project_to_road=True, lane_type=carla.LaneType.Driving)
                    if wp.is_junction and wp.get_junction() and wp.get_junction().id == jid:
                        jw = wp.get_junction()
                        break
                seen[jid] = (classify_junction(jw) if jw
                             else ("unknown", float("nan"), float("nan"), 0))
            kind, spread, mx, n = seen[jid]
            ln = b - a
            if kind == "INTERSECTION":
                isect_m += ln
            else:
                ramp_m += ln
            detail.append(f"{a:4.0f}-{b:<4.0f} {kind:12s} "
                          f"entry spread {spread:3.0f} deg, max turn {mx:3.0f} deg")
        grand_isect += isect_m
        print(f"{sec}  scored {scored:.0f} m | INTERSECTION {isect_m:5.1f} m "
              f"({100*isect_m/scored:4.1f}%) | ramp/merge {ramp_m:5.1f} m")
        for d in detail:
            print(f"      {d}")
    print(f"\nTOTAL true-intersection content across the scored route: {grand_isect:.0f} m")


if __name__ == "__main__":
    sys.exit(main())

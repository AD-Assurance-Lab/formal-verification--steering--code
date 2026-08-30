#!/usr/bin/env python3
"""Choose and cache a deployment-test route on any CARLA map, both directions.

Supersedes build_town06_routes.py, whose criterion was inadequate. The route is chosen
on MAP GEOMETRY ALONE, before any model exists for it.

WHAT THE CRITERION LEARNED (each item cost a measurement)
---------------------------------------------------------
1. Mean curvature is not enough. Town04 and the first Town06 window matched on mean
   (0.00306 vs 0.00300) and on straight-fraction while having opposite distributions:
   Town04 median 0.00091, Town06 median 0.00000. Match the DISTRIBUTION of steering
   DEMAND -- the normalised steer a bicycle model needs at 20 mph -- not a summary.

2. Junction-freedom is not the criterion. Town04's scored lap is 18 % is_junction
   vertices: CARLA marks grade-separated highway merges as junctions and the study
   drives through them.

3. Distance to a traffic light is not the criterion either. Town04's own scored lap
   passes within 11 m of one. A 50 m exclusion rejects the published route.

4. The criterion that matters is LANE MARKINGS. config.py gives the real reason Town04
   excludes its one intersection: "the lane centreline is undefined through it". A
   lane-keeper needs something to see. Measured: Town04 scored lap has 0.00 % / 0.77 %
   of vertices with no lane marking on either side; the rejected Town06 window has
   7.55 % / 4.46 %, and its teacher failed all six DAgger rounds.

5. Signal-controlled lanes are excluded too, via each light's OWN affected waypoints
   rather than proximity. Town04: 0 of 1424. This study has no other traffic, so a
   signal governs nothing directly -- but a signalised lane reliably indicates the
   at-grade arterial geometry that item 4 rejects.

6. Store the FULL closed loop rotated to the window start, and score a prefix.
   pure_pursuit_route indexes with (i + lookahead) % n, so an open segment wraps the
   lookahead across a discontinuity and throws the oracle off the road at the seam.

Usage:
    CARLA_PORT=3000 python3 scripts/build_study_route.py --map Town12
    CARLA_PORT=3000 python3 scripts/build_study_route.py --map Town12 --dry-run
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
from survey_map_routes import trace, curvature, STEP_M  # noqa: E402

TARGET_LEN_M = 2861.0
WHEELBASE, MAXSTEER = 3.005, 1.2217
NONE_MARK = carla.LaneMarkingType.NONE

# Town04, measured over the committed centrelines (0-2861 m).
REF = dict(s50=0.0023, s90=0.0168, s99=0.0467, smax=0.0467)
SMAX_CAP = 0.060        # steering demand regime that actually trained on Town04
UNMARKED_MAX = 0.010    # Town04 scored lap: 0.0000 and 0.0077
LANE_W, LANE_W_TOL = 3.500, 0.01


def demand(ak):
    return np.arctan(WHEELBASE * ak) / MAXSTEER


def dstats(ak):
    d = demand(ak)
    return dict(s50=float(np.percentile(d, 50)), s90=float(np.percentile(d, 90)),
                s99=float(np.percentile(d, 99)), smax=float(d.max()))


def score(p):
    """Distance from Town04's steering-demand distribution. Tail weighted: the tail is
    what defeated training on the rejected route."""
    return (abs(p['s50'] - REF['s50']) / REF['s50']
            + abs(p['s90'] - REF['s90']) / REF['s90']
            + 2 * abs(p['s99'] - REF['s99']) / REF['s99']
            + 3 * abs(p['smax'] - REF['smax']) / REF['smax'])


def controlled_waypoints(world):
    A = []
    for tl in world.get_actors().filter("traffic.traffic_light*"):
        try:
            for wp in tl.get_affected_lane_waypoints():
                A.append([wp.transform.location.x, wp.transform.location.y])
        except Exception:
            pass
    return np.array(A) if A else np.zeros((0, 2))


def unmarked_frac(wmap, pts, stride=3):
    n = miss = 0
    for x, y in pts[::stride]:
        wp = wmap.get_waypoint(carla.Location(x=float(x), y=float(y), z=0.5),
                               project_to_road=True, lane_type=carla.LaneType.Driving)
        l = wp.left_lane_marking.type if wp.left_lane_marking else NONE_MARK
        r = wp.right_lane_marking.type if wp.right_lane_marking else NONE_MARK
        n += 1
        if l == NONE_MARK and r == NONE_MARK:
            miss += 1
    return miss / max(n, 1)


def opposing_start(wmap, x, y, heading, radius_m=90.0, wps=None):
    hx, hy = heading
    nrm = math.hypot(hx, hy) or 1.0
    hx, hy = hx / nrm, hy / nrm
    best = None
    for w in (wps if wps is not None else wmap.generate_waypoints(2.0)):
        loc = w.transform.location
        d = math.hypot(loc.x - x, loc.y - y)
        if d > radius_m:
            continue
        f = w.transform.get_forward_vector()
        fn = math.hypot(f.x, f.y) or 1.0
        if (f.x / fn) * hx + (f.y / fn) * hy > -0.85:
            continue
        if best is None or d < best[0]:
            best = (d, w)
    return best[1] if best else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-check", type=int, default=60,
                    help="candidates to run the expensive lane-marking check on")
    args = ap.parse_args()
    n_win = int(round(TARGET_LEN_M / STEP_M)) + 1
    routes_dir = os.path.join(C.DATASET_DIR, f"routes_{args.map.lower()}")

    with carla_lock(owner="build_study_route"):
        client = carla.Client(C.HOST, C.PORT)
        client.set_timeout(300.0)
        world = client.load_world(args.map)
        wmap = world.get_map()
        CTL = controlled_waypoints(world)
        sl = np.array([[l.location.x, l.location.y]
                       for l in world.get_lightmanager().get_all_lights(carla.LightGroup.Street)])
        print(f"{args.map}: {len(CTL)} signal-controlled waypoints, {len(sl)} street lights")

        seeds = [w for w in wmap.generate_waypoints(40.0) if not w.is_junction]
        seen, cands = set(), []
        for sd in seeds:
            k = (sd.road_id, sd.lane_id)
            if k in seen:
                continue
            seen.add(k)
            try:
                r, j, lw = trace(wmap, sd, max_pts=6000)
            except Exception:
                continue
            if len(r) < n_win + 10:
                continue
            ak, _ = curvature(r)
            for i0 in range(0, len(ak) - n_win, 50):
                seg_lw = lw[i0:i0 + n_win]
                if abs(seg_lw.mean() - LANE_W) > LANE_W_TOL or seg_lw.std() > 0.05:
                    continue
                st = dstats(ak[i0:i0 + n_win])
                if st['smax'] > SMAX_CAP:
                    continue
                seg = r[i0:i0 + n_win]
                if len(CTL):
                    d = np.hypot(CTL[:, 0][None, :] - seg[:, 0][:, None],
                                 CTL[:, 1][None, :] - seg[:, 1][:, None]).min(axis=1)
                    if (d < 3.0).any():
                        continue
                st.update(road=int(k[0]), lane=int(k[1]), i0=int(i0))
                cands.append((score(st), st, r, j, lw, sd))
        cands.sort(key=lambda t: t[0])
        print(f"{len(cands)} windows pass lane width, steering cap and signal control")
        if not cands:
            sys.exit("no admissible window on this map")

        chosen = None
        tested = set()
        for sc, st, r, j, lw, sd in cands:
            kk = (st['road'], st['lane'], st['i0'] // 600)
            if kk in tested:
                continue
            tested.add(kk)
            seg = r[st['i0']:st['i0'] + n_win]
            um = unmarked_frac(wmap, seg)
            lit = (float((np.hypot(sl[:, 0][None, :] - seg[:, 0][:, None],
                                   sl[:, 1][None, :] - seg[:, 1][:, None]).min(axis=1) < 30).mean())
                   if len(sl) else 0.0)
            print(f"  road{st['road']:>5}/lane{st['lane']:<3} i0={st['i0']:>5} "
                  f"score={sc:.2f} unmarked={um*100:5.2f}% lit={lit:.2f}")
            if um <= UNMARKED_MAX:
                st.update(score=sc, unmarked=um, lit=lit)
                chosen = (st, r, j, lw)
                break
            if len(tested) >= args.max_check:
                break
        if chosen is None:
            sys.exit(f"no window with <= {UNMARKED_MAX*100:.1f}% unmarked vertices "
                     f"(Town04 scored lap: 0.00-0.77%)")

        st, r, j, lw = chosen
        i0 = st['i0']
        print(f"\nCHOSEN road{st['road']}/lane{st['lane']} i0={i0}")
        for k in ("s50", "s90", "s99", "smax", "score", "unmarked", "lit"):
            print(f"    {k:<10} {st[k]:.5f}      (Town04 {REF.get(k, '')})")

        eb = np.roll(r, -i0, axis=0)
        fwd = eb[1] - eb[0]
        ow = opposing_start(wmap, eb[0][0], eb[0][1], (fwd[0], fwd[1]),
                            wps=wmap.generate_waypoints(2.0))
        if ow is None:
            sys.exit("no opposing carriageway at the chosen start")
        wb, wbj, wblw = trace(wmap, ow, max_pts=6000)
        if len(wb) < n_win:
            sys.exit(f"opposing trace too short: {len(wb)} < {n_win}")

        def closed(a):
            return math.hypot(a[-1, 0] - a[0, 0], a[-1, 1] - a[0, 1]) < 12.0

        def length(a):
            d = np.diff(a, axis=0)
            return float(np.hypot(d[:, 0], d[:, 1]).sum())

        wb_um = unmarked_frac(wmap, wb[:n_win])
        wb_st = dstats(curvature(wb)[0][:n_win])
        print(f"\nopposing road{ow.road_id}/lane{ow.lane_id}: "
              f"smax={wb_st['smax']:.4f} unmarked={wb_um*100:.2f}%")
        if wb_um > UNMARKED_MAX or wb_st['smax'] > SMAX_CAP:
            sys.exit("opposing carriageway fails the same criterion")
        for nm, a in (("eastbound", eb), ("westbound", wb)):
            print(f"stored {nm}: {len(a)} pts, {length(a):.0f} m, closed={closed(a)}")
            if not closed(a):
                sys.exit("stored route is not a closed loop (see item 6 in the docstring)")

        spawns = {}
        for nm, a in (("eastbound", eb), ("westbound", wb)):
            wp = wmap.get_waypoint(carla.Location(x=float(a[0][0]), y=float(a[0][1]), z=0.5),
                                   project_to_road=True, lane_type=carla.LaneType.Driving)
            spawns[nm] = dict(x=float(a[0][0]), y=float(a[0][1]), z=0.5,
                              yaw=float(wp.transform.rotation.yaw))
        if args.dry_run:
            print("\n[dry-run] nothing written")
            return
        os.makedirs(routes_dir, exist_ok=True)
        np.save(os.path.join(routes_dir, "eastbound.npy"), eb)
        np.save(os.path.join(routes_dir, "westbound.npy"), wb)
        json.dump(dict(map=args.map, target_len_m=TARGET_LEN_M, step_m=STEP_M,
                       town04_reference=REF, window=st,
                       opposing=dict(road=int(ow.road_id), lane=int(ow.lane_id),
                                     unmarked=wb_um, **wb_st),
                       spawns=spawns, scored_len_m=min(TARGET_LEN_M, length(eb[:n_win])),
                       selection="geometry only; no policy behaviour used"),
                  open(os.path.join(routes_dir, "route_meta.json"), "w"), indent=2)
        print(f"\nwrote {routes_dir}")
        for k, v in spawns.items():
            print(f"    {k}: {v}")


if __name__ == "__main__":
    main()

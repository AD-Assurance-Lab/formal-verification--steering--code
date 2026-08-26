#!/usr/bin/env python3
"""Choose and cache the Town06 deployment-test route, both directions.

The route is selected on MAP GEOMETRY ALONE, before any Town06 model exists. Nothing
about how a policy drives may enter this choice, or the deployment test stops being a
test. Concretely, the selection uses only: curvature profile, scored length, lane-width
constancy, junction character, and street-light proximity, each compared against the
committed Town04 centrelines.

Method
------
1. Trace Town06's outer highway loop (~8.3 km, 1044 x 566 m extent -- the analogue of
   Town04's grade-separated loop).
2. Slide a TARGET_LEN_M window along it and keep the window whose curvature profile is
   closest to Town04's.
3. Find the opposing carriageway at the chosen start and trace the same length back, so
   the two directions cover the same physical road, as they do on Town04.
4. Write eastbound/westbound .npy files under a map-scoped routes directory.

Usage:
    CARLA_PORT=3000 python3 scripts/build_town06_routes.py
    CARLA_PORT=3000 python3 scripts/build_town06_routes.py --dry-run
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

MAP = "Town06"
TARGET_LEN_M = 2861.0          # identical scored length to Town04
STRAIGHT_RADIUS_M = 500.0

# Town04 reference profile over 0-2861 m, averaged across the two committed directions.
T04 = dict(straight_frac=0.536, kappa_mean=0.00306, kappa_p90=0.00682)

# Town04's study route is unambiguously highway and the Town06 window must be too.
# [MEASURED] over the committed centrelines: 4 driving lanes per direction on ~99 % of
# sampled vertices, dominant posted limit 90 kph. Lane count and speed limit are map
# facts, so using them keeps the selection geometry-only.
T04_LANES_PER_DIR = 4
T04_SPEED_KPH = 90.0
MIN_LANE_FRAC = 0.80        # fraction of sampled vertices at >= T04_LANES_PER_DIR
# Speed limit is ADVISORY, not a filter. [MEASURED] Town06's outer loop carries no
# OpenDRIVE type-274 speed-limit landmarks at all (415/415 vertices return none), so the
# posted limit cannot discriminate on this map. It is still recorded for the record.
# Lane count carries the highway signature instead: Town04 is exactly 4 lanes/dir,
# Town06's loop is 4-5, so the criterion is ">= 4", satisfied on 81 % of the loop.

ROUTES_DIR = os.path.join(C.DATASET_DIR, "routes_town06")


def window_profile(route, junc, lane_w, i0, n_win):
    """Curvature/geometry profile of a contiguous vertex window."""
    seg = route[i0:i0 + n_win]
    if len(seg) < n_win:
        return None
    ak, s = curvature(seg)
    if not len(ak):
        return None
    lw = lane_w[i0:i0 + len(ak)]
    return dict(
        start_idx=int(i0),
        scored_len_m=float(s[-1]),
        straight_frac=float((ak < 1.0 / STRAIGHT_RADIUS_M).mean()),
        kappa_mean=float(ak.mean()),
        kappa_p90=float(np.percentile(ak, 90)),
        kappa_max=float(ak.max()),
        min_radius_m=float(1.0 / max(ak.max(), 1e-9)),
        junction_frac=float(junc[i0:i0 + len(ak)].mean()),
        lane_width_mean=float(lw.mean()),
        lane_width_std=float(lw.std()),
    )


def lanes_same_dir(wp):
    """Driving lanes on the same side of the carriageway as `wp`."""
    n, w = 1, wp
    for _ in range(10):
        w = w.get_left_lane()
        if w is None or w.lane_type != carla.LaneType.Driving or w.lane_id * wp.lane_id < 0:
            break
        n += 1
    w = wp
    for _ in range(10):
        w = w.get_right_lane()
        if w is None or w.lane_type != carla.LaneType.Driving or w.lane_id * wp.lane_id < 0:
            break
        n += 1
    return n


def highway_profile(wmap, pts, stride=10):
    """Lane count and posted speed limit over a window. Map facts only."""
    lanes, speeds = [], []
    for x, y in pts[::stride]:
        wp = wmap.get_waypoint(carla.Location(x=float(x), y=float(y), z=0.5),
                               project_to_road=True, lane_type=carla.LaneType.Driving)
        lanes.append(lanes_same_dir(wp))
        try:
            lms = wp.get_landmarks_of_type(60.0, "274")     # OpenDRIVE speed-limit sign
            speeds.append(lms[0].value if lms else None)
        except Exception:
            speeds.append(None)
    lane_frac = float(np.mean([l >= T04_LANES_PER_DIR for l in lanes])) if lanes else 0.0
    sv = [v for v in speeds if v]
    speed_frac = float(np.mean([v == T04_SPEED_KPH for v in sv])) if sv else 0.0
    return dict(lanes_per_dir_mode=int(max(set(lanes), key=lanes.count)) if lanes else 0,
                lane_match_frac=lane_frac,
                speed_kph_mode=(float(max(set(sv), key=sv.count)) if sv else None),
                speed_match_frac=speed_frac)


def match_score(p):
    return (abs(p["straight_frac"] - T04["straight_frac"]) / T04["straight_frac"]
            + abs(p["kappa_mean"] - T04["kappa_mean"]) / T04["kappa_mean"]
            + abs(p["kappa_p90"] - T04["kappa_p90"]) / T04["kappa_p90"])


def outer_loop(wmap):
    """The longest closed trace on the map: Town06's outer highway loop."""
    seeds = [w for w in wmap.generate_waypoints(40.0) if not w.is_junction]
    seen, best = set(), None
    for w in seeds:
        key = (w.road_id, w.lane_id)
        if key in seen:
            continue
        seen.add(key)
        r, j, lw = trace(wmap, w, max_pts=6000)
        if len(r) < 200:
            continue
        if math.hypot(r[-1, 0] - r[0, 0], r[-1, 1] - r[0, 1]) > 12.0:
            continue                      # not a closed loop
        d = np.diff(r, axis=0)
        L = float(np.hypot(d[:, 0], d[:, 1]).sum())
        if best is None or L > best[0]:
            best = (L, r, j, lw, w)
    return best


def opposing_start(wmap, x, y, heading_xy, radius_m=70.0, wps=None):
    """A driving waypoint near (x, y) whose forward vector opposes `heading_xy`.

    A divided highway has a non-driving median between carriageways, so walking
    get_left_lane()/get_right_lane() stops at the barrier and never reaches the other
    side. Scan the map's own waypoint set spatially instead, and take the nearest
    antiparallel one: that is the opposing carriageway of the same road.
    """
    hx, hy = heading_xy
    n = math.hypot(hx, hy) or 1.0
    hx, hy = hx / n, hy / n
    best = None
    for w in (wps if wps is not None else wmap.generate_waypoints(2.0)):
        loc = w.transform.location
        d = math.hypot(loc.x - x, loc.y - y)
        if d > radius_m:
            continue
        f = w.transform.get_forward_vector()
        fn = math.hypot(f.x, f.y) or 1.0
        if (f.x / fn) * hx + (f.y / fn) * hy > -0.85:      # not antiparallel enough
            continue
        if best is None or d < best[0]:
            best = (d, w)
    return best[1] if best else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = ap.parse_args()

    n_win = int(round(TARGET_LEN_M / STEP_M)) + 1

    with carla_lock(owner="build_town06_routes"):
        client = carla.Client(C.HOST, C.PORT)
        client.set_timeout(C.CLIENT_TIMEOUT_S)
        world = client.load_world(MAP)
        wmap = world.get_map()
        lm = world.get_lightmanager()
        sl = np.array([[l.location.x, l.location.y]
                       for l in lm.get_all_lights(carla.LightGroup.Street)])

        L, route, junc, lane_w, seed = outer_loop(wmap)
        print(f"outer loop: road {seed.road_id}/lane {seed.lane_id}, {L:.0f} m, "
              f"{len(route)} vertices")

        # Two-stage: cheap geometric filter first, then the expensive per-vertex
        # highway check (lane count + posted limit) on the survivors only.
        geo = []
        for i0 in range(0, len(route) - n_win, 5):
            p = window_profile(route, junc, lane_w, i0, n_win)
            if p is None or p["lane_width_std"] > 0.05:
                continue
            geo.append((match_score(p), p))
        geo.sort(key=lambda t: t[0])
        print(f"{len(geo)} windows pass the lane-width filter; "
              f"checking highway character on the best {min(len(geo), 60)}")

        # Cache the map's waypoint set once; opposing_start scans it per candidate.
        allwps = wmap.generate_waypoints(2.0)

        best, ow = None, None
        for sc, p in geo[:200]:
            i0 = p["start_idx"]
            hp = highway_profile(wmap, route[i0:i0 + n_win])
            if hp["lane_match_frac"] < MIN_LANE_FRAC:
                continue
            # The two driven directions must be the SAME physical road, as on Town04.
            # Town06's outer loop only has an opposing carriageway on ~54 % of its
            # length (median separation 55 m), so this is a real filter, not a formality.
            fwd_i = route[i0 + 1] - route[i0]
            cand = opposing_start(wmap, route[i0][0], route[i0][1],
                                  (fwd_i[0], fwd_i[1]), wps=allwps)
            if cand is None:
                continue
            p.update(hp)
            best, ow = (sc, p), cand
            break                      # geo is sorted, so the first survivor is the best
        if best is None:
            sys.exit("no window satisfies the Town04 highway signature "
                     f"(>= {T04_LANES_PER_DIR} lanes/dir on {MIN_LANE_FRAC:.0%} of vertices)")
        s, p = best
        i0 = p["start_idx"]
        fwd = route[i0 + 1] - route[i0]
        print(f"\nbest {TARGET_LEN_M:.0f} m window: start vertex {i0}  match score {s:.3f}")
        for k in ("scored_len_m", "straight_frac", "kappa_mean", "kappa_p90",
                  "min_radius_m", "junction_frac", "lane_width_mean", "lane_width_std",
                  "lanes_per_dir_mode", "lane_match_frac", "speed_kph_mode",
                  "speed_match_frac"):
            print(f"    {k:<20} {p[k]}")
        print(f"    {'Town04 straight%':<18} {T04['straight_frac']:.5f}   "
              f"kappa_mean {T04['kappa_mean']:.5f}  kappa_p90 {T04['kappa_p90']:.5f}")

        eb = route[i0:i0 + n_win].copy()

        wb_full, wb_j, wb_lw = trace(wmap, ow, max_pts=6000)
        if len(wb_full) < n_win:
            sys.exit(f"opposing trace too short: {len(wb_full)} < {n_win}")
        wb = wb_full[:n_win].copy()
        wp = window_profile(wb_full, wb_j, wb_lw, 0, n_win)
        wp.update(highway_profile(wmap, wb))
        print(f"\nopposing carriageway: road {ow.road_id}/lane {ow.lane_id}")
        for k in ("scored_len_m", "straight_frac", "kappa_mean", "kappa_p90",
                  "min_radius_m", "junction_frac", "lane_width_mean",
                  "lanes_per_dir_mode", "speed_kph_mode"):
            print(f"    {k:<20} {wp[k]}")

        out = {}
        for name, arr in (("eastbound", eb), ("westbound", wb)):
            if len(sl):
                d = np.hypot(sl[:, 0][None, :] - arr[:, 0][:, None],
                             sl[:, 1][None, :] - arr[:, 1][:, None]).min(axis=1)
                print(f"\n{name}: street-light distance med={np.median(d):.0f} m "
                      f"min={d.min():.0f} m  within 30 m = {(d < 30).mean()*100:.0f}% "
                      f"(Town04: med 12-13 m, 100%)")
            wpt = wmap.get_waypoint(carla.Location(x=float(arr[0][0]), y=float(arr[0][1]), z=0.5),
                                    project_to_road=True, lane_type=carla.LaneType.Driving)
            out[name] = dict(
                x=float(arr[0][0]), y=float(arr[0][1]), z=0.5,
                yaw=float(wpt.transform.rotation.yaw))

        if args.dry_run:
            print("\n[dry-run] nothing written")
            return
        os.makedirs(ROUTES_DIR, exist_ok=True)
        np.save(os.path.join(ROUTES_DIR, "eastbound.npy"), eb)
        np.save(os.path.join(ROUTES_DIR, "westbound.npy"), wb)
        meta = dict(map=MAP, target_len_m=TARGET_LEN_M, step_m=STEP_M,
                    town04_reference=T04, window=p, opposing=wp, spawns=out,
                    selection="geometry only; no policy behaviour used")
        with open(os.path.join(ROUTES_DIR, "route_meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
        print(f"\nwrote {ROUTES_DIR}/{{eastbound,westbound}}.npy and route_meta.json")
        print("\nSPAWNS for config:")
        for k, v in out.items():
            print(f"    {k}: {v}")


if __name__ == "__main__":
    main()

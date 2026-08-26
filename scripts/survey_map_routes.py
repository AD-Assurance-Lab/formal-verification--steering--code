#!/usr/bin/env python3
"""Survey a CARLA map for a route that matches the Town04 study route.

The Town06 deployment test needs a route that is a fair analogue of the Town04 one,
chosen on GEOMETRY ALONE and before any model exists for it. Choosing a route after
seeing how a policy drives it would import the answer into the experiment, so this
script reports only map geometry: length, curvature profile, lane width, and where
junctions fall.

Target profile, measured from the committed Town04 centrelines over 0-2861 m:

    length             ~2860 m scored
    straight (R>500m)  51-56 %
    mean |kappa|       0.0027-0.0034 1/m
    p90  |kappa|       0.0064-0.0072 1/m
    min radius         45-63 m
    lane width         3.500 m, std 0.0000
    is_junction        18.1-18.5 % of vertices

That last number matters and is easy to get wrong. Town04's scored lap is 18 % junction
vertices: CARLA marks grade-separated highway on/off-ramp merges as junctions, and the
study drove straight through them. What Town04 EXCLUDED (via LAP_END_M) was one at-grade
signalised intersection, where the lane centreline is undefined. So the criterion is not
"junction-free" -- it is "same junction character as Town04, and no traffic lights".

Usage:
    CARLA_PORT=3000 python3 scripts/survey_map_routes.py --map Town06
    CARLA_PORT=3000 python3 scripts/survey_map_routes.py --map Town06 --json out.json
"""
import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))

import carla  # noqa: E402
import config as C  # noqa: E402
from carla_lock import carla_lock  # noqa: E402

STEP_M = 2.0
CURV_WINDOW = 10          # +/- vertices for the curvature estimate (~40 m base)
STRAIGHT_RADIUS_M = 500.0
TARGET_LEN_M = 2861.0


def trace(world_map, start_wp, step=STEP_M, max_pts=4000):
    """Trace a lane centreline with the same straightest-at-junction policy the study
    uses (pipeline/route.build_route), recording junction hits as we go."""
    pts = [(start_wp.transform.location.x, start_wp.transform.location.y)]
    junc = [bool(start_wp.is_junction)]
    lane_w = [float(start_wp.lane_width)]
    wp, total = start_wp, 0.0
    for _ in range(max_pts):
        nxts = wp.next(step)
        if not nxts:
            break
        if len(nxts) == 1:
            wp = nxts[0]
        else:
            f = wp.transform.get_forward_vector()
            wp = max(nxts, key=lambda c: f.x * c.transform.get_forward_vector().x
                                        + f.y * c.transform.get_forward_vector().y)
        total += step
        p = (wp.transform.location.x, wp.transform.location.y)
        pts.append(p)
        junc.append(bool(wp.is_junction))
        lane_w.append(float(wp.lane_width))
        if total > 150 and math.hypot(p[0] - pts[0][0], p[1] - pts[0][1]) < 8.0:
            break
    return np.asarray(pts, np.float64), np.asarray(junc, bool), np.asarray(lane_w, np.float64)


def curvature(route):
    """|dheading/ds| per vertex, smoothed over +/- CURV_WINDOW vertices."""
    d = np.diff(route, axis=0)
    seg = np.hypot(d[:, 0], d[:, 1])
    s = np.concatenate([[0.0], np.cumsum(seg)])
    hd = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    k = np.zeros(len(hd))
    for i in range(len(hd)):
        a, b = max(0, i - CURV_WINDOW), min(len(hd) - 1, i + CURV_WINDOW)
        ds = s[b] - s[a]
        k[i] = (hd[b] - hd[a]) / ds if ds > 1e-6 else 0.0
    return np.abs(k), s


def profile(route, junc, lane_w, limit_m=None):
    ak, s = curvature(route)
    n = len(ak)
    keep = np.ones(n, bool) if limit_m is None else (s[:n] <= limit_m)
    ak_k = ak[keep]
    if not len(ak_k):
        return None
    straight = float((ak_k < 1.0 / STRAIGHT_RADIUS_M).mean())
    lw = lane_w[:n][keep]
    return dict(
        n_pts=int(len(route)),
        length_m=float(s[-1]),
        scored_len_m=float(s[:n][keep][-1]),
        kappa_mean=float(ak_k.mean()),
        kappa_p50=float(np.percentile(ak_k, 50)),
        kappa_p90=float(np.percentile(ak_k, 90)),
        kappa_max=float(ak_k.max()),
        min_radius_m=float(1.0 / max(ak_k.max(), 1e-9)),
        straight_frac=straight,
        junction_frac=float(junc[:n][keep].mean()),
        first_junction_m=(float(s[:n][keep][junc[:n][keep]][0])
                          if junc[:n][keep].any() else None),
        lane_width_mean=float(lw.mean()),
        lane_width_std=float(lw.std()),
    )


def min_traffic_light_dist(route, tls, limit_m=None):
    """Closest approach (m) between the scored window and any traffic light."""
    if not len(tls):
        return float("inf")
    d = np.diff(route, axis=0)
    s = np.concatenate([[0.0], np.cumsum(np.hypot(d[:, 0], d[:, 1]))])
    pts = route if limit_m is None else route[s <= limit_m]
    if not len(pts):
        return float("inf")
    best = float("inf")
    for tx, ty in tls:
        best = min(best, float(np.min(np.hypot(pts[:, 0] - tx, pts[:, 1] - ty))))
    return best


def score(p):
    """Distance from the Town04 target profile. Lower is better. Geometry only.

    Deliberately does NOT look at anything a policy does on the route: the route is
    chosen before any Town06 model exists, so only map geometry may enter.
    """
    if p is None:
        return 1e9
    tgt_straight, tgt_kmean, tgt_kp90 = 0.536, 0.00306, 0.00682
    return (abs(p["straight_frac"] - tgt_straight) / tgt_straight
            + abs(p["kappa_mean"] - tgt_kmean) / tgt_kmean
            + abs(p["kappa_p90"] - tgt_kp90) / tgt_kp90
            + abs(p["scored_len_m"] - TARGET_LEN_M) / TARGET_LEN_M)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default="Town06")
    ap.add_argument("--seed-step", type=float, default=40.0,
                    help="spacing (m) between candidate seed waypoints")
    ap.add_argument("--json", default=None)
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()

    with carla_lock(owner="survey_map_routes"):
        client = carla.Client(C.HOST, C.PORT)
        client.set_timeout(C.CLIENT_TIMEOUT_S)
        world = client.load_world(args.map)
        wmap = world.get_map()
        print(f"loaded {wmap.name}")

        tls = [(a.get_location().x, a.get_location().y)
               for a in world.get_actors().filter("traffic.traffic_light*")]
        print(f"{len(tls)} traffic lights on this map")

        seeds = wmap.generate_waypoints(args.seed_step)
        seeds = [w for w in seeds if not w.is_junction]
        print(f"{len(seeds)} non-junction seed waypoints at {args.seed_step} m spacing")

        seen, cands = set(), []
        for i, w in enumerate(seeds):
            key = (w.road_id, w.lane_id)
            if key in seen:
                continue
            seen.add(key)
            route, junc, lane_w = trace(wmap, w)
            if len(route) < 100:
                continue
            full = profile(route, junc, lane_w)
            if full is None:
                continue
            # Scored window = the first TARGET_LEN_M of the trace. Junctions are NOT a
            # disqualifier (Town04 is 18 % junction vertices); traffic lights are, and
            # are checked separately below.
            pref = profile(route, junc, lane_w, limit_m=min(full["length_m"], TARGET_LEN_M))
            if pref is None or pref["scored_len_m"] < TARGET_LEN_M * 0.9:
                continue
            if pref["lane_width_std"] > 0.05:
                continue      # Town04 holds 3.500 m exactly; a varying lane invalidates
                              # the CTE budget, which is derived from lane width
            pref["tl_min_dist_m"] = min_traffic_light_dist(route, tls, limit_m=TARGET_LEN_M)
            cands.append(dict(
                road_id=int(w.road_id), lane_id=int(w.lane_id),
                seed=dict(x=float(w.transform.location.x), y=float(w.transform.location.y),
                          z=float(w.transform.location.z) + 0.5,
                          yaw=float(w.transform.rotation.yaw)),
                full=full, usable=pref, score=score(pref)))

        cands.sort(key=lambda c: c["score"])
        print(f"\n{len(cands)} distinct (road, lane) candidates\n")
        hdr = (f"{'road/lane':>11} {'len_m':>7} {'straight%':>9} {'k_mean':>8} "
               f"{'k_p90':>8} {'Rmin':>6} {'lane_w':>7} {'junc%':>6} {'tl_m':>7} {'score':>6}")
        print(hdr); print("-" * len(hdr))
        for c in cands[:args.top]:
            u = c["usable"]
            tl = u.get("tl_min_dist_m", float("inf"))
            print(f"{c['road_id']:>6}/{c['lane_id']:<4} {u['scored_len_m']:>7.0f} "
                  f"{u['straight_frac']*100:>8.1f}% {u['kappa_mean']:>8.5f} "
                  f"{u['kappa_p90']:>8.5f} {u['min_radius_m']:>6.0f} "
                  f"{u['lane_width_mean']:>7.3f} {u['junction_frac']*100:>5.1f}% "
                  f"{tl:>7.0f} {c['score']:>6.2f}")

        if args.json:
            with open(args.json, "w") as f:
                json.dump(dict(map=args.map, target_len_m=TARGET_LEN_M,
                               candidates=cands[:args.top * 4]), f, indent=2)
            print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()

"""
Fixed reference route = the intended lane centerline, traced once and cached.

Why this exists: CARLA's get_waypoint(project_to_road) snaps to the NEAREST
driving lane, so when the vehicle drifts into an adjacent lane the CTE collapses
toward ~0 (measured against the wrong lane). Measuring against a FIXED reference
polyline instead makes a lane departure read as a correctly-large CTE.

The same reference path also drives DAgger recovery: pure_pursuit_route() aims at
a point ahead on the INTENDED centerline, so from any off-center state it steers
smoothly back to the intended lane (unlike map-nearest pure-pursuit, which would
happily keep driving in the drifted-into lane).
"""
import os
import math

import numpy as np
import carla

from config import DATASET_DIR, WHEELBASE_M, LOOKAHEAD_M, MAX_STEER_RAD, ROUTES_SUBDIR

# Map-scoped: Town04 keeps "routes", the Town06 deployment test reads
# "routes_town06". Selected by config.STUDY_MAP so a run cannot silently load the
# wrong map's centreline -- which would produce a plausible, wrong CTE.
ROUTES_DIR = os.path.join(DATASET_DIR, ROUTES_SUBDIR)
STEP_M = 2.0  # route vertex spacing


def build_route(world_map, spawn, step=STEP_M, max_pts=4000):
    """Trace the intended lane centerline from a spawn using a straightest-at-
    junction policy until the loop closes. Returns an (N, 2) array of (x, y)."""
    start = world_map.get_waypoint(
        carla.Location(x=spawn["x"], y=spawn["y"], z=spawn["z"]),
        project_to_road=True, lane_type=carla.LaneType.Driving)
    pts = [(start.transform.location.x, start.transform.location.y)]
    wp, total = start, 0.0
    for _ in range(max_pts):
        nxts = wp.next(step)
        if not nxts:
            break
        if len(nxts) == 1:
            wp = nxts[0]
        else:  # at a junction, keep the straightest continuation
            f = wp.transform.get_forward_vector()
            wp = max(nxts, key=lambda c: f.x * c.transform.get_forward_vector().x
                                        + f.y * c.transform.get_forward_vector().y)
        total += step
        p = (wp.transform.location.x, wp.transform.location.y)
        pts.append(p)
        if total > 150 and math.hypot(p[0] - pts[0][0], p[1] - pts[0][1]) < 8.0:
            break
    return np.asarray(pts, dtype=np.float64)


def save_route(name, route):
    os.makedirs(ROUTES_DIR, exist_ok=True)
    np.save(os.path.join(ROUTES_DIR, f"{name}.npy"), route)


def load_route(name):
    """Load a route. `ROUTE_ROLL` rotates the index origin without touching geometry.

    Diagnostic only, default 0 (identical behaviour). It exists to separate two
    explanations that coincide on this map: the western intersection occupies the LAST 16
    of 1522 westbound indices, so "failures at the junction" and "failures at the route's
    index seam, where nearest_index wraps and pure pursuit's lookahead crosses a
    discontinuity" are the same observation. Rolling the origin moves the seam to a
    straight while leaving the path, the spawn and the lap-termination test unchanged, so
    whichever the failures follow is the cause. See D-09.
    """
    route = np.load(os.path.join(ROUTES_DIR, f"{name}.npy"))
    roll = int(os.environ.get("ROUTE_ROLL", "0"))
    return np.roll(route, roll, axis=0) if roll else route


# --- open vs closed routes -------------------------------------------------
# Town04's lap closes on itself (start and end 7.9 m apart) so index arithmetic
# modulo len(route) is correct there, and every route helper below was written
# that way. The Town06 lap does NOT close: its start and end are 173.8 m apart,
# because Zach cut the route before a double intersection that sits outside the
# ODD. On an open route the wrap is not a wrap, it is a teleport to a point two
# city blocks away -- pure pursuit aims at it and CTE is measured against a
# segment that spans the gap. Both happen in the last few steps of every lap,
# which is exactly where the run is scored.
CLOSURE_TOL_M = 25.0   # >> Town04's 7.9 m, << Town06's 173.8 m


def route_is_closed(route, tol_m=CLOSURE_TOL_M):
    """True when the route's end rejoins its start, so index wrap is meaningful."""
    return bool(math.hypot(float(route[0][0] - route[-1][0]),
                           float(route[0][1] - route[-1][1])) <= tol_m)


def lap_finished(route, hint, margin=2):
    """Has the vehicle reached the usable end of an OPEN route?

    On a CLOSED route the lap ends when the vehicle returns to its start, and every
    driving loop tests that with `left_start and distance_to_start < 12 m`.

    ON AN OPEN ROUTE THAT TEST CAN NEVER FIRE. The Town06 lap's start and end are 174 m
    apart, so the loop runs to its step budget instead and drives past the last vertex --
    where pure pursuit's lookahead is clamped onto the final point and the commanded
    steering degenerates. Measured on the mixed collection: 13 of 15,360 frames carried
    |steer| up to 0.754 against a lap maximum of 0.086, every one of them in the last
    three steps, at the route's end point, with |CTE| of 0.001 m. The vehicle was
    perfectly on the line and the EXPERT LABEL was garbage.

    That is 0.08% of frames, and it is not harmless: they are all at one place, they are
    behaviour-cloning LABELS, and the place is the end of the scored road. A policy
    trained on them learns to jerk in the last few metres of every lap.

    gate_teacher_lap.py already stopped at `hint >= n_route - 2` for exactly this reason.
    The collectors did not, so every dataset and every DAgger round carried it.

    `margin` is the number of trailing vertices treated as unusable, matching the gate.
    """
    if hint is None or route_is_closed(route):
        return False
    return int(hint) >= len(route) - int(margin)


def _step_idx(route, i, k):
    """Advance index i by k vertices: wrapping on a closed route, clamped on an
    open one so we never aim at, or measure against, the far side of the gap."""
    n = len(route)
    return (i + k) % n if route_is_closed(route) else max(0, min(n - 1, i + k))


def nearest_index(route, x, y, hint=None, window=80):
    """Index of the nearest route vertex. With a hint (previous index), search
    only a local window (handles wraparound) — faster and robust to nearby lanes."""
    n = len(route)
    if hint is None:
        d2 = (route[:, 0] - x) ** 2 + (route[:, 1] - y) ** 2
        return int(np.argmin(d2))
    if route_is_closed(route):
        idxs = np.array([(hint + k) % n for k in range(-window, window)])
    else:
        idxs = np.arange(max(0, hint - window), min(n, hint + window))
    seg = route[idxs]
    d2 = (seg[:, 0] - x) ** 2 + (seg[:, 1] - y) ** 2
    return int(idxs[int(np.argmin(d2))])


def signed_cte_route(route, x, y, hint=None):
    """Signed perpendicular distance (m) from the vehicle to the reference path.
    + = left of the route direction, - = right. Returns (cte, nearest_index)."""
    i = nearest_index(route, x, y, hint)
    n = len(route)
    a, b = route[i], route[_step_idx(route, i, 1)]
    seg = b - a
    L = math.hypot(seg[0], seg[1])
    if L < 1e-6:
        a, b = route[_step_idx(route, i, -1)], route[i]
        seg = b - a
        L = math.hypot(seg[0], seg[1])
    ux, uy = seg[0] / L, seg[1] / L
    dx, dy = x - a[0], y - a[1]
    return float(ux * dy - uy * dx), i


def pure_pursuit_route(route, vehicle_transform, hint=None, lookahead=LOOKAHEAD_M):
    """Pure-pursuit steering toward a point `lookahead` m ahead on the reference
    path. Recovers to the intended centerline from off-center states.
    Returns (steer_norm, steer_rad, nearest_index)."""
    loc = vehicle_transform.location
    i = nearest_index(route, loc.x, loc.y, hint)
    n = len(route)
    n_ahead = max(1, int(round(lookahead / STEP_M)))
    if route_is_closed(route) or i + n_ahead <= n - 1:
        tgt = route[(i + n_ahead) % n] if route_is_closed(route) else route[i + n_ahead]
    else:
        # Open route, lookahead past the last vertex. Clamping to route[n-1] is
        # wrong twice over: it shortens the lookahead, and at i == n-1 the target
        # IS the vehicle, so ld -> 0 and the steer saturates. Extrapolate along
        # the final segment instead -- keep going straight past the end, which is
        # what the road does. The run should already be over by here; this only
        # keeps the last few steps sane.
        d = route[n - 1] - route[n - 2]
        L = math.hypot(float(d[0]), float(d[1])) or 1.0
        over = (i + n_ahead) - (n - 1)
        tgt = route[n - 1] + d * (over * STEP_M / L)

    dx, dy = tgt[0] - loc.x, tgt[1] - loc.y
    ld = math.hypot(dx, dy)
    yaw = math.radians(vehicle_transform.rotation.yaw)
    alpha = math.atan2(dy, dx) - yaw
    alpha = (alpha + math.pi) % (2.0 * math.pi) - math.pi
    steer_rad = math.atan2(2.0 * WHEELBASE_M * math.sin(alpha), max(ld, 1e-3))
    steer = max(-1.0, min(1.0, steer_rad / MAX_STEER_RAD))
    return steer, steer_rad, i

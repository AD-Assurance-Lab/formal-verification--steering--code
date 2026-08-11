"""
Pure-pursuit expert (the DAgger label oracle). Uses CARLA HD-map waypoints to
compute the geometrically-correct steering command from the vehicle pose. This
is privileged (map-based) — the neural policy must later reproduce it from
camera pixels alone.
"""
import math

import carla

from config import WHEELBASE_M, LOOKAHEAD_M, MAX_STEER_RAD


def nearest_waypoint(world_map, vehicle_location):
    """Driving-lane waypoint nearest the vehicle (projected to road center)."""
    return world_map.get_waypoint(
        vehicle_location, project_to_road=True, lane_type=carla.LaneType.Driving
    )


def pure_pursuit_steer(world_map, vehicle_transform, lookahead=LOOKAHEAD_M):
    """
    Normalized pure-pursuit steering in [-1, 1].

    δ = atan( 2 L sin(α) / ld ),  normalized by the vehicle's max steer angle,
    where α is the heading error to a waypoint `ld` meters ahead along the lane.

    Returns (steer_norm, steer_rad, waypoint). waypoint is reused for CTE.
    """
    loc = vehicle_transform.location
    wp = nearest_waypoint(world_map, loc)
    if wp is None:
        return 0.0, 0.0, None

    ahead = wp.next(lookahead)
    if not ahead:
        return 0.0, 0.0, wp
    # At junctions wp.next() branches; pick the successor whose heading best
    # continues the current lane (straightest) so we follow the highway loop
    # instead of diverting onto a ramp.
    fwd = wp.transform.get_forward_vector()
    best = max(ahead, key=lambda c: fwd.x * c.transform.get_forward_vector().x
                                    + fwd.y * c.transform.get_forward_vector().y)
    target = best.transform.location

    dx = target.x - loc.x
    dy = target.y - loc.y
    yaw = math.radians(vehicle_transform.rotation.yaw)
    alpha = math.atan2(dy, dx) - yaw
    alpha = (alpha + math.pi) % (2.0 * math.pi) - math.pi  # wrap to [-π, π]

    steer_rad = math.atan2(2.0 * WHEELBASE_M * math.sin(alpha), lookahead)
    steer_norm = max(-1.0, min(1.0, steer_rad / MAX_STEER_RAD))
    return steer_norm, steer_rad, wp

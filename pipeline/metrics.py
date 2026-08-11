"""
Cross-track error and safety-criteria math. Pure functions (no CARLA import at
module load beyond the carla types passed in), so the geometry is unit-testable.
"""
import math

from config import CTE_BUDGET_M, STEER_CORRIDOR_RAD


def signed_cte(waypoint, vehicle_location):
    """
    Signed perpendicular distance (m) from lane center to the vehicle reference
    point, in the lane's frame.

      + : vehicle is LEFT of lane center (looking along the driving direction)
      - : vehicle is RIGHT of lane center

    Computed as the z-component of (lane_forward x displacement). Because
    lane_forward is a unit vector, this cross product IS the signed perpendicular
    distance. Uses the vehicle CENTER, consistent with the center-to-center
    CTE budget in config.
    """
    if waypoint is None:
        return None
    wp = waypoint.transform.location
    fwd = waypoint.transform.get_forward_vector()
    dx = vehicle_location.x - wp.x
    dy = vehicle_location.y - wp.y
    return float(fwd.x * dy - fwd.y * dx)


def within_budget(cte_m):
    """True if |CTE| is within the lane-departure budget."""
    return cte_m is not None and abs(cte_m) <= CTE_BUDGET_M


def within_corridor(steer_dev_rad):
    """True if a steering-angle deviation (rad) is within the verification corridor."""
    return abs(steer_dev_rad) <= STEER_CORRIDOR_RAD


def summarize_cte(cte_series_m):
    """Aggregate a list of signed CTE samples (m) into a pass/fail report dict."""
    vals = [c for c in cte_series_m if c is not None]
    if not vals:
        return {"n": 0}
    abs_vals = [abs(c) for c in vals]
    n_over = sum(1 for a in abs_vals if a > CTE_BUDGET_M)
    return {
        "n": len(vals),
        "max_abs_cte_m": max(abs_vals),
        "mean_abs_cte_m": sum(abs_vals) / len(abs_vals),
        "rms_cte_m": math.sqrt(sum(c * c for c in vals) / len(vals)),
        "n_over_budget": n_over,
        "frac_over_budget": n_over / len(vals),
        "passed": n_over == 0,
    }

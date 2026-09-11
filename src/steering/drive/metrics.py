"""
Cross-track error and safety-criteria math. Pure functions (no CARLA import at
module load beyond the carla types passed in), so the geometry is unit-testable.
"""
import math

from steering.config import CTE_BUDGET_M


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

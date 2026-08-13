"""Shared equilibrium-root solver.

Kept in one place so the pass/fail criterion and the fraction-of-lap predictor cannot
drift apart: they must agree on what counts as a settling point."""
import numpy as np


def stable_root(off, d):
    """Smallest-|o| STABLE root of D(o), by linear interpolation between grid points.

    Stable means D DECREASES through the crossing. CARLA's frame is left-handed, so the
    capture normal points right of the lane and a restoring policy answers a positive
    offset with left (negative) steering; `S_clear` under clear weather drives the route
    without departing and its gain is negative, which fixes the sign empirically. An
    increasing crossing is a divergence point, not an equilibrium, and returning it as one
    would invert the verdict."""
    best = None
    for i in range(len(off) - 1):
        a, b = float(d[i]), float(d[i + 1])
        if a == 0.0:
            r = float(off[i])
            dec = (d[min(i + 1, len(d) - 1)] - d[max(i - 1, 0)]) < 0
        elif a * b < 0:
            r = float(off[i] + (off[i + 1] - off[i]) * (-a) / (b - a))
            dec = b < a
        else:
            continue
        if dec and (best is None or abs(r) < abs(best)):
            best = r
    return best

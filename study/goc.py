"""Gradient orientation coherence -- the alignment check that gates every paired fit.

Trap 1. In the previous study, three separate airlight estimates were computed on frames
that turned out not to be pixel-aligned, and all three were withdrawn. The failure is
silent: unaligned frames produce a confident, wrong fit. ACDC's adverse/reference pairs sit
at the unrelated-image null, and -- the part that surprised us -- so do two separately
driven CARLA laps (0.235 against a 0.242 null). Only pose-matched capture produces aligned
pairs.

Call `require_aligned()` before ANY paired photometric fit, including on simulator output.
"""

import cv2
import numpy as np

# Same-pose captures measured 0.721; offset-pose measured 0.097; the unrelated-image null
# sits near 0.24. The threshold is set well above the null and below the observed
# same-pose value.
ALIGNMENT_THRESHOLD = 0.50

MIN_MASK_PIXELS = 1000


def goc(a, b, mask):
    """Magnitude-weighted mean of cos(2*dtheta) between two images' gradient fields.

    Doubling the angle makes this invariant to local contrast reversal, and using only
    orientation (not magnitude) makes it invariant to any monotone photometric map. It
    therefore measures geometric alignment alone -- which is what lets it validate a pair
    whose whole point is that its photometry differs. Range [-1, 1].
    """
    if mask.sum() < MIN_MASK_PIXELS:
        return float("nan")

    ax = cv2.Sobel(a, cv2.CV_32F, 1, 0, ksize=3)
    ay = cv2.Sobel(a, cv2.CV_32F, 0, 1, ksize=3)
    bx = cv2.Sobel(b, cv2.CV_32F, 1, 0, ksize=3)
    by = cv2.Sobel(b, cv2.CV_32F, 0, 1, ksize=3)

    ma = np.sqrt(ax * ax + ay * ay)
    mb = np.sqrt(bx * bx + by * by)

    # cos(2t) = (gx^2 - gy^2)/|g|^2, sin(2t) = 2*gx*gy/|g|^2 -- avoids atan2 entirely.
    ea = np.maximum(ma * ma, 1e-8)
    eb = np.maximum(mb * mb, 1e-8)
    ca, sa = (ax * ax - ay * ay) / ea, (2 * ax * ay) / ea
    cb, sb = (bx * bx - by * by) / eb, (2 * bx * by) / eb

    cos2d = ca * cb + sa * sb
    w = np.where(mask, np.minimum(ma, mb), 0.0)

    total = w.sum()
    if total < 1e-6:
        return float("nan")
    return float((w * cos2d).sum() / total)


class NotAlignedError(RuntimeError):
    pass


def require_aligned(a, b, mask, threshold=ALIGNMENT_THRESHOLD, context=""):
    """Return the GOC score, or raise if the pair is not aligned enough to fit against.

    Refusing is the point. A warning gets ignored and the fit gets published.
    """
    score = goc(a, b, mask)
    if not np.isfinite(score) or score < threshold:
        raise NotAlignedError(
            f"GOC {score:.3f} below threshold {threshold:.3f}{' for ' + context if context else ''}. "
            "These frames are not pixel-aligned; any paired photometric fit on them is invalid."
        )
    return score

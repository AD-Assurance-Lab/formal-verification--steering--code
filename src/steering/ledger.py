"""Where a ledger writes, and the interval its rates are reported with.

Split out of closed_loop_ledger.py so the aggregator can reuse both without
importing one script from another.
"""
import pathlib

from steering import REPO_ROOT as _REPO_ROOT

from steering import config as C
from steering.study import town06_design as _D

REPO = pathlib.Path(_REPO_ROOT)

# Town06 scopes its ledger by pass and tag; Town04 keeps the published directory.
LEDGER = (REPO / _D.LEDGER_SUBDIR if C.STUDY_MAP != "Town04"
          else pathlib.Path(C.LEDGER_DIR))


def wilson(k, n, z=1.96):
    """Wilson score interval for a binomial proportion.

    Used rather than the normal approximation because it stays inside [0,1] and behaves
    at k=0 and k=n, which is exactly where these rates land.
    """
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))

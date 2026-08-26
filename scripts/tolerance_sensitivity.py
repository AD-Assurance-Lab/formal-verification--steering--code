#!/usr/bin/env python3
"""How much does the 12/12 depend on the one parameter that was calibrated?

`T_CLOSED_LOOP_S` is back-solved so the tolerance reproduces the measured stability
cliff, and that cliff was measured on the same closed-loop runs the certificate is
validated against. The criterion therefore has exactly one fitted parameter, fitted on
the validation labels, and the study must not claim otherwise (F45).

This makes the dependence measurable instead of arguable. The certified BOUNDS do not
depend on the tolerance at all -- alpha-CROWN never sees it -- so the whole sweep is
exact arithmetic over the committed `sustained_bound.json`, with no re-certification:

    tolerance(T) = (2 L B) / (v^2 T^2) / MAX_STEER_RAD
    CERTIFIED    iff  -tolerance <= lo and hi <= tolerance

Two things are worth reading off the output. The ordering of the cells is correct at
EVERY T -- the separation gap is a ratio and is invariant -- so what T buys is the
placement of the threshold inside that gap. And the failure mode at small T is
UNSOUND CERTIFICATION, not a false alarm: at the a-priori one-second horizon the
criterion declares two cells safe that depart on every run.

    python scripts/tolerance_sensitivity.py
"""
import sys
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402

BOUNDS = REPO / "results" / "calibration" / "sustained_bound.json"
SWEEP = (0.75, 1.00, 1.23, 1.25, 1.50, 1.75, 1.85, 2.00, 2.13, 2.25, 2.50, 3.00)


def tolerance(T):
    return (2.0 * C.WHEELBASE_M * C.CTE_BUDGET_M) / (
        C.TARGET_SPEED_MS ** 2 * T ** 2) / C.MAX_STEER_RAD


def main():
    if not BOUNDS.exists():
        print(f"missing {BOUNDS}; run scripts/certify_sustained_bound.py first",
              file=sys.stderr)
        return 2
    cells = {k: v for k, v in json.loads(BOUNDS.read_text()).items()
             if not k.startswith("_")}

    print(f"\nTOLERANCE SENSITIVITY over {len(cells)} committed cells")
    print(f"  bounds are independent of T; only the threshold moves\n")
    print(f"  {'T (s)':>7} {'tolerance':>10} {'score':>7}   failures")
    for T in SWEEP:
        tol = tolerance(T)
        bad = []
        for k, c in cells.items():
            cert = (c["hi"] <= tol and c["lo"] >= -tol)
            if cert != (c["truth"] == "PASS"):
                d, m, cond = k.split("/")
                # An UNSOUND CERT is a model declared safe that departs. A false alarm is
                # merely conservative. These are not equally bad and are not merged.
                bad.append(f"{d[:4]}/{m}/{cond}:{'UNSOUND CERT' if cert else 'false alarm'}")
        mark = "" if not bad else "   " + "; ".join(bad)
        print(f"  {T:7.2f} {tol:10.5f} {len(cells) - len(bad):4d}/{len(cells)}{mark}")

    # The window is exact: certification needs the threshold above every certified
    # magnitude and below every falsified escape.
    worst_cert = max(max(abs(c["lo"]), abs(c["hi"]))
                     for c in cells.values() if c["truth"] == "PASS")
    least_fals = min(abs(c["lo"]) for c in cells.values() if c["truth"] == "FAIL")
    k = 2.0 * C.WHEELBASE_M * C.CTE_BUDGET_M / (C.TARGET_SPEED_MS ** 2 * C.MAX_STEER_RAD)
    lo_T, hi_T = math.sqrt(k / least_fals), math.sqrt(k / worst_cert)

    print(f"\n  worst certified magnitude   {worst_cert:.5f}"
          f"  ({worst_cert / C.CLOSED_LOOP_TOLERANCE:.2f}x tol)")
    print(f"  least-escaping falsified    {least_fals:.5f}"
          f"  ({least_fals / C.CLOSED_LOOP_TOLERANCE:.2f}x tol)")
    print(f"  separation gap              {least_fals / worst_cert:.2f}x   (invariant in T)")
    print(f"\n  ADMISSIBLE WINDOW  T in ({lo_T:.3f}, {hi_T:.3f}) s")
    print(f"  in use             T  =  {C.T_CLOSED_LOOP_S} s")
    assert abs(lo_T - C.T_CLOSED_LOOP_ADMISSIBLE_S[0]) < 5e-3 and \
           abs(hi_T - C.T_CLOSED_LOOP_ADMISSIBLE_S[1]) < 5e-3, \
        "config.T_CLOSED_LOOP_ADMISSIBLE_S is stale relative to the committed bounds"
    print("  (config.T_CLOSED_LOOP_ADMISSIBLE_S agrees)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""The scored scope of a route, recomputed from its GEOMETRY. No CARLA, no models.

WHY THIS EXISTS. `build_study_route.py` declares, before any Town06 model existed:

    REF      = dict(s50=0.0023, s90=0.0168, s99=0.0467, smax=0.0467)   # Town04's lap
    SMAX_CAP = 0.060        # steering demand regime that actually trained on Town04

and `build_town06_sections.py` ENFORCED that cap -- every stored section came in at
smax <= 0.0596. `build_town06_lap_from_track.py`, which superseded the sections, never
mentions it. The lap's smax is 0.0670.

So the lap scores 86 m of road demanding more steering than the regime the criterion was
calibrated in, and 134 m demanding more than Town04's scored lap ever did. That is not a
new judgement made after seeing a result: it is a constant this repo declared first and
then stopped applying when the route was rebuilt.

WHAT IT IS NOT. This does not decide that out-of-regime road should be excluded. It
reports where that road is, so a verdict can be scored with it and without it and the
DIFFERENCE reported. Excluding it happens to make the Town06 mixed student look better,
which is exactly why the choice must not be made silently by one tool.

The demand statistic is `build_study_route.demand`, unchanged:

    demand(kappa) = arctan(WHEELBASE * kappa) / MAX_STEER

NO DILATION. A span is the contiguous run of vertices over the threshold and nothing
more. Padding it by a reaction distance would be a knob, and a knob on a scope definition
is how a study picks the road that flatters it. Measured: all three of the Town06 mixed
student's peak-|CTE| locations already fall strictly inside the undilated spans.

    STUDY_MAP=Town06 python3 scripts/scored_scope.py
    STUDY_MAP=Town06 python3 scripts/scored_scope.py --json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "scripts"))

import config as C  # noqa: E402
from route import load_route  # noqa: E402

# The two declared thresholds, both from build_study_route.py. SMAX_CAP is the one the
# section builder ENFORCED, so it defines the capped scope; REF_SMAX is Town04's own
# maximum and is reported beside it as a sensitivity, never as a second answer.
SMAX_CAP = 0.060
REF_SMAX = 0.0467

SCOPES = ("full", "capped")


def demand_profile(route, step_m=None):
    """(arc, demand) per interior vertex. Recomputed from the route's POINTS.

    Arc length comes from the vertex spacing actually stored, not from `step_m`: the
    builder targets 2.0 m and lands within a few cm, and reading the nominal step would
    make this a restatement of the config rather than a measurement of the road.
    """
    rt = np.asarray(route, dtype=float)[:, :2]
    seg = np.linalg.norm(np.diff(rt, axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    hd = np.unwrap(np.arctan2(np.diff(rt[:, 1]), np.diff(rt[:, 0])))
    # kappa at interior vertex i uses the heading change across it over the segment
    # length after it, which is the same discretisation build_study_route uses.
    kappa = np.abs(np.diff(hd)) / np.maximum(seg[1:], 1e-9)
    d = np.arctan(C.WHEELBASE_M * kappa) / C.MAX_STEER_RAD
    return arc[1:-1], d


def spans_over(arc, d, threshold, step_m=2.0):
    """Contiguous arc-length spans whose demand exceeds `threshold`.

    Returned as closed intervals [a, b] in metres, matching BRIDGE_SPANS' convention so
    a consumer can test membership the same way for both.
    """
    idx = np.flatnonzero(d > threshold)
    if idx.size == 0:
        return []
    out, run = [], [idx[0]]
    for i in idx[1:]:
        if i == run[-1] + 1:
            run.append(i)
        else:
            out.append(run)
            run = [i]
    out.append(run)
    return [(float(arc[r[0]]), float(arc[r[-1]])) for r in out]


def excluded_spans(section="lap", threshold=SMAX_CAP):
    """The spans a `capped` scope excludes, on top of BRIDGE_SPANS."""
    arc, d = demand_profile(load_route(section))
    return spans_over(arc, d, threshold)


def in_spans(here_m, spans):
    return any(a <= here_m <= b for a, b in spans)


def scope_spans(section="lap", scope="capped"):
    """Every arc-length span EXCLUDED from scoring under `scope`.

    `full` excludes only the ODD bridges, which is what the committed Town06 result
    used. `capped` additionally excludes road over SMAX_CAP.
    """
    if scope not in SCOPES:
        sys.exit(f"unknown scope {scope!r}; expected one of {SCOPES}")
    bridges = [tuple(b) for b in getattr(C, "BRIDGE_SPANS", [])]
    if scope == "full":
        return bridges
    return bridges + excluded_spans(section, SMAX_CAP)


def scored_length_m(section="lap", scope="capped"):
    """Metres of road scored under `scope`, recomputed from the route's own vertices."""
    rt = np.asarray(load_route(section), dtype=float)[:, :2]
    seg = np.linalg.norm(np.diff(rt, axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    spans = scope_spans(section, scope)
    # A segment counts when its MIDPOINT is outside every excluded span, so a segment is
    # never half-counted and the two scopes always partition the same road.
    mid = 0.5 * (arc[:-1] + arc[1:])
    keep = np.array([not in_spans(float(m), spans) for m in mid])
    return float(seg[keep].sum())


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--section", default="lap")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    route = load_route(args.section)
    arc, d = demand_profile(route)
    rec = dict(
        map=C.STUDY_MAP, section=args.section,
        route_length_m=float(arc[-1]),
        demand=dict(s50=float(np.percentile(d, 50)), s90=float(np.percentile(d, 90)),
                    s99=float(np.percentile(d, 99)), smax=float(d.max())),
        town04_reference=dict(smax=REF_SMAX), smax_cap=SMAX_CAP,
        bridges=[list(b) for b in getattr(C, "BRIDGE_SPANS", [])],
        over_cap=[list(s) for s in spans_over(arc, d, SMAX_CAP)],
        over_town04_smax=[list(s) for s in spans_over(arc, d, REF_SMAX)],
        scored_m={s: scored_length_m(args.section, s) for s in SCOPES},
    )
    if args.json:
        print(json.dumps(rec, indent=2))
        return 0

    print(f"\n{C.STUDY_MAP} '{args.section}'  route {rec['route_length_m']:.1f} m")
    print(f"  steering demand   s50 {rec['demand']['s50']:.4f}  s90 {rec['demand']['s90']:.4f}"
          f"  s99 {rec['demand']['s99']:.4f}  smax {rec['demand']['smax']:.4f}")
    print(f"  Town04 reference smax {REF_SMAX}      SMAX_CAP {SMAX_CAP}")
    if rec["demand"]["smax"] > SMAX_CAP:
        print(f"  *** this route EXCEEDS SMAX_CAP, which build_town06_sections.py "
              f"enforced and the lap builder does not ***")
    for label, key in (("over SMAX_CAP", "over_cap"),
                       ("over Town04 smax", "over_town04_smax")):
        spans = rec[key]
        tot = sum(b - a for a, b in spans)
        print(f"\n  {label}: {len(spans)} span(s), {tot:.0f} m")
        for a, b in spans:
            m = (arc >= a) & (arc <= b)
            print(f"      arc {a:7.1f} - {b:7.1f} m  ({b - a:5.1f} m)  "
                  f"peak demand {d[m].max():.4f}")
    print(f"\n  scored road:  full {rec['scored_m']['full']:.0f} m"
          f"   capped {rec['scored_m']['capped']:.0f} m"
          f"   (difference {rec['scored_m']['full'] - rec['scored_m']['capped']:.0f} m)")
    print("\n  Neither scope is the answer. Score both and report the difference.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

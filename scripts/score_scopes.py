#!/usr/bin/env python3
"""Score the SAME driven laps under both scored scopes. No CARLA, no models.

The Town06 result was scored on the full lap, which includes 78 m of road whose steering
demand exceeds `SMAX_CAP` -- the constant `build_study_route.py` declares as "steering
demand regime that actually trained on Town04" and `build_town06_sections.py` enforced.
All three of the mixed student's peak-|CTE| locations are on that road.

Excluding it makes the mixed student look better. That is precisely why this tool does
not choose: it scores every lap both ways from ONE set of drives and prints the
difference. A study that reported only the capped number would be choosing its scope
after seeing which cells were marginal, and no reader could tell.

It reads the per-step TRACES the ledger now always writes. It cannot be run against the
first Town06 pass, whose runs kept only a max and its location -- that is why re-driving
was needed at all, and it is recorded here so the next person does not pay for it twice.

    STUDY_MAP=Town06 python3 scripts/score_scopes.py
    STUDY_MAP=Town06 python3 scripts/score_scopes.py --write
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "scripts"))

import config as C  # noqa: E402
import scored_scope as ss  # noqa: E402
from study import town06_design as D  # noqa: E402

LEDGER = REPO / D.LEDGER_SUBDIR
TRACES = LEDGER / "runs" / "traces"


def _route_arc():
    """TRUE cumulative arc length per route vertex, from the vertices themselves."""
    from route import load_route  # noqa: E402
    rt = np.asarray(load_route("lap"), float)[:, :2]
    seg = np.linalg.norm(np.diff(rt, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(seg)])


def load_trace(path):
    """(true_arc, cte, in_bridge_as_driven, n_steps) for one lap.

    TWO PARAMETERISATIONS, and mixing them is a real bug that this function exists to
    stop. The driver records `here_m = route_index * step_m` -- index times the NOMINAL
    2.0 m spacing. `scored_scope`'s spans, and `BRIDGE_SPANS` in the route metadata, are
    TRUE arc length, cumsum of the actual vertex spacing, which averages 1.9974 m.

    Over 1,147 vertices the two drift by up to 6.8 m and end 3.0 m apart. Scored against
    `here_m`, low_sun/S_mixed's peak at true arc 2284.9 m reads as 2288.0 m and falls
    OUTSIDE the 2249.2-2287.0 exclusion -- so the capped scope silently excluded nothing
    and printed margins identical to the full scope, which is exactly what a working
    comparison of two identical scopes looks like.

    So the index is recovered and mapped through the route's own arc array. `step_m` is
    read from the metadata rather than assumed, because the recovery is only exact while
    the driver's multiplier and this divisor are the same number.
    """
    with open(path) as fh:
        rows = list(csv.DictReader(fh))
    arc = _route_arc()
    step = float(C.LAP_META.get("step_m", 2.0))
    here = np.full(len(rows), np.nan)
    for i, r in enumerate(rows):
        if r["here_m"] == "":
            continue
        idx = int(round(float(r["here_m"]) / step))
        here[i] = arc[min(max(idx, 0), len(arc) - 1)]
    cte = np.array([float(r["cte_m"]) if r["cte_m"] != "" else np.nan for r in rows])
    br = np.array([int(r["in_bridge"]) for r in rows], dtype=bool)
    return here, cte, br, len(rows)


def score_run(here, cte, br, scope):
    """(max_abs_cte, frac_over_budget, n_scored) for one lap under `scope`.

    A step counts when it has a CTE, is not bridged, and lies outside every span the
    scope excludes. The bridge test uses the flag the DRIVER recorded rather than
    recomputing it, because that flag is what actually decided whether pure pursuit
    steered -- recomputing could disagree with the run that happened.
    """
    spans = ss.excluded_spans("lap", ss.SMAX_CAP) if scope == "capped" else []
    ok = ~br & ~np.isnan(cte) & ~np.isnan(here)
    for a, b in spans:
        ok &= ~((here >= a) & (here <= b))
    if not ok.any():
        return float("inf"), 1.0, 0
    a = np.abs(cte[ok])
    return float(a.max()), float((a > C.CTE_BUDGET_M).mean()), int(ok.sum())


def aggregate(laps):
    """PROTOCOL A-4: three laps is a REPRODUCIBILITY CHECK, not a rate.

    All pass -> PASS. All fail -> FAIL. Mixed -> VOID, and it stays void until the cause
    is found and written down. Never a majority vote: that turns an identified defect
    into a plausible failure rate and loses it.
    """
    passed = [l["passed"] for l in laps]
    if all(passed):
        v = "PASS"
    elif not any(passed):
        v = "FAIL"
    else:
        v = "VOID"
    worst = max(l["max_cte_m"] for l in laps)
    return v, worst, (C.CTE_BUDGET_M - worst) / C.CTE_BUDGET_M


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true",
                    help="write per-scope ledger cells beside the traces")
    args = ap.parse_args()

    if not TRACES.is_dir() or not any(TRACES.glob("*.csv")):
        sys.exit(f"no traces in {TRACES}.\n"
                 "  The first Town06 pass kept only a max per run and cannot be\n"
                 "  re-scored. Drive with the current closed_loop_ledger.py, which\n"
                 "  always writes a trace, then run this.")

    cells = defaultdict(lambda: defaultdict(list))
    for p in sorted(TRACES.glob("*.csv")):
        cond, ck, section, rep = p.stem.split("__")
        here, cte, br, n = load_trace(p)
        rj = p.parent.parent / (p.stem + ".json")
        departed = False
        if rj.exists():
            departed = bool(json.loads(rj.read_text())["run"].get("departed", False))
        for scope in ss.SCOPES:
            mx, frac, ns = score_run(here, cte, br, scope)
            cells[(cond, ck)][scope].append(dict(
                rep=int(rep.replace("rep", "")), max_cte_m=mx, frac_over_budget=frac,
                n_scored=ns, n_steps=n, departed=departed,
                passed=(not departed) and mx <= C.CTE_BUDGET_M))

    print(f"\nTOWN06 -- one set of drives, scored under both scopes")
    print(f"  budget {C.CTE_BUDGET_M:.3f} m   "
          f"full {ss.scored_length_m('lap','full'):.0f} m   "
          f"capped {ss.scored_length_m('lap','capped'):.0f} m\n")
    hdr = (f"  {'condition':9s} {'student':13s} | {'FULL scope':>22s} | "
           f"{'CAPPED scope':>22s} | changed")
    print(hdr); print("  " + "-" * (len(hdr) - 2))
    out = {}
    for (cond, ck), by_scope in sorted(cells.items()):
        row, verd = {}, {}
        for scope in ss.SCOPES:
            laps = sorted(by_scope[scope], key=lambda l: l["rep"])
            v, worst, margin = aggregate(laps)
            verd[scope] = v
            row[scope] = dict(verdict=v, laps=len(laps),
                              laps_failed=sum(1 for l in laps if not l["passed"]),
                              worst_cte_m=worst, margin_frac=margin,
                              scored_m=ss.scored_length_m("lap", scope),
                              scope=scope,
                              laps_detail=laps,
                              # `runs` as well, in the shape the aggregator writes it.
                              # compare_town06.py counts laps from this key, and a cell
                              # carrying only `laps_detail` reported "PASS 0/0" with a
                              # Wilson interval of [0,100]% -- a verdict with no visible
                              # evidence behind it, which reads as a cell nobody drove.
                              runs=[dict(rep=l["rep"], direction="lap",
                                         max_cte_m=l["max_cte_m"],
                                         frac_over_budget=l["frac_over_budget"],
                                         departed=l["departed"], passed=l["passed"])
                                    for l in laps])
        f, c = row["full"], row["capped"]
        print(f"  {cond:9s} {ck.split('_t06')[0]:13s} | "
              f"{f['verdict']:5s} {f['laps_failed']}/{f['laps']} "
              f"{f['worst_cte_m']:.3f} m {f['margin_frac']*100:+6.1f}% | "
              f"{c['verdict']:5s} {c['laps_failed']}/{c['laps']} "
              f"{c['worst_cte_m']:.3f} m {c['margin_frac']*100:+6.1f}% | "
              f"{'YES' if verd['full'] != verd['capped'] else '-'}")
        out[f"{cond}/{ck}"] = row

    # CROSS-CHECK: the FULL-scope re-scoring must reproduce the verdict the ledger wrote
    # while driving. The trace is a second recording of the same run, so if the two ever
    # disagree, one of them is not measuring the cell -- and a scope comparison built on
    # a trace that does not reproduce its own drive would be comparing two different
    # things and calling the difference a scope effect.
    drift = []
    for key, row in out.items():
        cond, ck = key.split("/")
        live = LEDGER / f"{cond}__{ck}__closed_loop.json"
        if not live.exists():
            continue
        d = json.loads(live.read_text())
        if (d.get("verdict") != row["full"]["verdict"]
                or abs(d.get("worst_cte_m", 0) - row["full"]["worst_cte_m"]) > 1e-6):
            drift.append(f"{key}: ledger {d.get('verdict')} "
                         f"{d.get('worst_cte_m'):.6f} m vs trace "
                         f"{row['full']['verdict']} {row['full']['worst_cte_m']:.6f} m")
    if drift:
        print("\n  FATAL: the trace does not reproduce the ledger's own full-scope "
              "verdict:")
        for x in drift:
            print(f"    {x}")
        sys.exit(1)
    print(f"\n  cross-check: full-scope re-scoring reproduces the ledger's own verdict "
          f"and margin on all {len(out)} cell(s).")

    changed = [k for k, v in out.items() if v["full"]["verdict"] != v["capped"]["verdict"]]
    print(f"\n  {len(changed)} of {len(out)} cells change verdict with the scope.")
    for k in changed:
        print(f"    {k}: {out[k]['full']['verdict']} -> {out[k]['capped']['verdict']}")
    print("\n  Report BOTH. The difference is the measurement: how much of a "
          "certificate-vs-driving\n  comparison is decided by where the scored road was "
          "cut.\n")

    if args.write:
        for scope in ss.SCOPES:
            # Inside the PASS's own directory. Spelled as results/town06/ledger_<scope>
            # these would be shared across passes, so pass 3 would silently overwrite
            # pass 2's re-scoring while its raw runs sat safely in their own folder --
            # the same collision TOWN06_PASS exists to prevent, one level down.
            d = REPO / D.LEDGER_SUBDIR / f"scored_{scope}"
            d.mkdir(parents=True, exist_ok=True)
            for key, row in out.items():
                cond, ck = key.split("/")
                (d / f"{cond}__{ck}__closed_loop.json").write_text(
                    json.dumps(row[scope], indent=2))
            print(f"  wrote {d.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Did any training lap come off a DEGRADED server? Measure, do not assume.

`collect_data.py` takes no CARLA restarts, so each base dataset was collected in one
server session -- the R-SIM-1 exposure. Whether that matters for TRAINING (as opposed to
measurement) is an empirical question, and this answers it instead of arguing it.

A degraded server has a specific, recorded signature, and it is not "looks odd":

    sections drove 14-62% of their length at 1.3-5.6 m/s while speed_mph
    reported 20.0 throughout

So the tell is the DISAGREEMENT between reported speed and actual displacement. The
manifest carries both -- speed_mph, and the pose at every step -- so the check is exact:

    actual m/s   = path length between consecutive poses / (steps * FIXED_DT)
    reported m/s = mean speed_mph * 0.44704

On a healthy server these agree. On a degraded one the reported figure keeps saying 20 mph
while the car barely moves. Lap length is also compared against the section's scored
length, since a lap that covered 40% of the road is short whatever the speeds say.

    python3 scripts/audit_training_data.py
"""
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import numpy as np                                            # noqa: E402
import config as C                                            # noqa: E402

MPH_TO_MS = 0.44704
SPEED_AGREEMENT_FLOOR = 0.80      # actual/reported below this is the degradation tell
LENGTH_FLOOR = 0.80               # of the section's scored length

# A LABEL THE EXPERT COULD NOT HAVE MEANT.
#
# Pure pursuit on this study's routes commands at most ~0.09 at 20 mph; the physical
# demand of the tightest curve is far below the actuator limit. A label an order of
# magnitude above that is not a hard corner, it is the lookahead degenerating -- on the
# open Town06 lap it clamps onto the final vertex and the label blows up while |CTE| is
# 0.001 m, i.e. the car is perfectly on the line. 13 of 15,360 frames, all in the last
# three steps of a lap, all at the route end.
#
# 0.08% of a dataset sounds ignorable and is not: they are behaviour-cloning LABELS, they
# are all at ONE place, and that place is the end of the scored road. route.lap_finished()
# stops the collectors before recording them; this is the check that says so on the data
# rather than on the source.
STEER_LABEL_CEILING = 0.25


def audit(ds_dir):
    man = ds_dir / "manifest.csv"
    if not man.exists():
        return None
    laps = defaultdict(list)
    with open(man) as fh:
        for r in csv.DictReader(fh):
            laps[(r["weather"], r["direction"], r["lap"])].append(r)
    rows = []
    for key, recs in sorted(laps.items()):
        recs.sort(key=lambda r: int(r["step"]))
        xy = np.array([[float(r["x"]), float(r["y"])] for r in recs])
        if len(xy) < 3:
            continue
        path = float(np.linalg.norm(np.diff(xy, axis=0), axis=1).sum())
        secs = (len(recs) - 1) * C.FIXED_DT
        actual = path / secs if secs > 0 else 0.0
        reported = float(np.mean([float(r["speed_mph"]) for r in recs])) * MPH_TO_MS
        ratio = actual / reported if reported > 1e-6 else float("nan")
        want = getattr(C, "SECTION_LEN_M", {}).get(key[1])
        cover = path / want if want else float("nan")
        st = np.array([abs(float(r["steer"])) for r in recs])
        n_wild = int((st > STEER_LABEL_CEILING).sum())
        rows.append((key, len(recs), path, actual, reported, ratio, cover, n_wild,
                     float(st.max())))
    return rows


def main():
    datasets = [p for p in sorted((REPO / "pipeline" / "data").iterdir())
                if p.is_dir() and (p / "manifest.csv").exists()]
    bad = []
    for ds in datasets:
        rows = audit(ds)
        if not rows:
            continue
        print(f"\n{ds.name}  ({len(rows)} laps)")
        print(f"  {'weather':8s} {'sec':6s} {'lap':4s} {'frames':>7s} {'path m':>8s} "
              f"{'actual':>7s} {'report':>7s} {'ratio':>6s} {'cover':>6s} {'|st|max':>8s}")
        for key, n, path, actual, reported, ratio, cover, n_wild, st_max in rows:
            flag = ""
            if n_wild:
                flag += f"  <-- {n_wild} WILD LABEL(S), max |steer| {st_max:.3f}"
                bad.append((ds.name, key, "steer_label", st_max))
            if ratio == ratio and ratio < SPEED_AGREEMENT_FLOOR:
                flag += "  <-- SPEED DISAGREES"
                bad.append((ds.name, key, "speed", ratio))
            if cover == cover and cover < LENGTH_FLOOR:
                flag += "  <-- SHORT LAP"
                bad.append((ds.name, key, "length", cover))
            print(f"  {key[0]:8s} {key[1]:6s} {key[2]:4s} {n:7d} {path:8.0f} "
                  f"{actual:7.2f} {reported:7.2f} {ratio:6.2f} "
                  f"{cover if cover == cover else float('nan'):6.2f} {st_max:8.3f}{flag}")

    print("\n" + "=" * 70)
    if bad:
        print(f"  {len(bad)} lap(s) carry a defect signature:")
        for ds, key, kind, val in bad[:20]:
            print(f"    {ds} {key} {kind}={val:.2f}")
        print("\n  These datasets should be recollected before anything trained on them\n"
              "  is trusted (D-11).")
        return 1
    print("  No lap shows the degraded-server signature: reported speed and actual\n"
          "  displacement agree everywhere, and every lap covered its section.\n"
          "  collect_data.py takes no restarts, so this was the open question -- it is\n"
          "  now measured rather than argued. Retraining is NOT indicated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

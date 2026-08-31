#!/usr/bin/env python3
"""BOUND the sustained steering bias over the whole declared disturbance interval.

F34 established the criterion by MEASURING the persistent bias at the rendered condition.
This bounds it instead, over every intensity in the declared range, which is the claim
scenario-based testing cannot make:

    x(s) = x_clear + s * (x_cond - x_clear),   s in [0, 1]

    for EVERY s, at EVERY pose on the lap:
        persistent bias = mean over poses of ( steer(x(s)) - steer(x(0)) )
        SAFE iff |persistent bias| <= CLOSED_LOOP_TOLERANCE

s = 0 is clear and s = 1 the measured CARLA condition, so the interval covers every
intensity in between -- including the ones no closed-loop run will ever sample.

WHY THE PER-POSE BOUNDS MAY BE AVERAGED. alpha-CROWN gives steer(x_i(s)) in [lo_i, hi_i] for
all s at pose i. Averaging those endpoints bounds the mean while letting s differ BETWEEN
poses, so the certificate covers spatially varying disturbance -- fog thicker in a hollow,
shadow only under the trees -- which is strictly more general than a single global intensity
and is what a real ODD looks like.

VERDICTS -- and read this, because one of the two names is doing more work than it should

    CERTIFIED  the whole bias interval lies inside the corridor. This is a PROOF: safe at
               every intensity in [0,1], for any per-pose choice of s.

    FALSIFIED  emitted whenever the interval is not wholly inside the corridor. The name is
               inherited and it OVERSTATES what is known. A sound over-approximation can
               certify; it cannot falsify. The honest reading is NOT CERTIFIED -- the bound
               does not decide -- and the four cells carrying this verdict agree with
               closed-loop failure without proving it. Turning one into a genuine
               falsification means exhibiting a witness s* whose sampled lap-mean deviation
               exceeds tolerance, which this repo can do cheaply and does not yet do.
               Two independent reviewers raised this; see F45.

Interpolating the stored 84x28 projections is exact rather than approximate: `_project` is
linear and a convex combination of two valid images needs no clamp (measured agreement
1.2e-7). This is why s is declared on [0,1] and never extrapolated.

    python scripts/certify_sustained_bound.py
"""
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
from route import load_route  # noqa: E402
import certify_cell as cc  # noqa: E402
from student import StudentNet  # noqa: E402

# FROM CONFIG, not hardcoded. This tuple duplicated config.STUDENTS with the PUBLISHED
# checkpoint names, so under TOWN04_REDO the certifier silently certified the PUBLISHED
# students while the ledger drove the redo's -- two runs produced byte-identical bounds
# across all 12 cells, which is what exposed it. A registry that exists in config must be
# read from config; a second copy is a second thing to forget to update.
STUDENTS = C.STUDENTS
# Under TOWN04_REDO the hardcoded outcomes below belong to DIFFERENT students and must
# not be used; see the REDO branch in the verdict loop.
REDO = os.environ.get("TOWN04_REDO", "0") == "1"

# A CELL POOLED FROM A HANDFUL OF POSES, OR FROM A SLIVER OF THE ROUTE, IS NOT A
# CERTIFICATE OF ANYTHING. certify_town06.py has carried MIN_POSES_PER_CELL since the
# pose-axis bug; this script never did, and that is how the Town04 redo certified 160 m of
# a 2,861 m lap and reported the result as agreement with full-lap driving.
#
# The pose count alone would NOT have caught it -- 81 densely packed poses clear any
# sensible count threshold. What distinguishes a lap from a probe is how much ROUTE the
# poses span, so both are checked.
MIN_POSES_PER_CELL = 60
MIN_ROUTE_COVERAGE = 0.80        # fraction of the scored route the capture must span

TRUTH = {("S_clear", "fog"): "PASS", ("S_clear", "night"): "FAIL",
         ("S_clear", "shadows"): "FAIL", ("S_mixed", "fog"): "PASS",
         ("S_mixed", "night"): "PASS", ("S_mixed", "shadows"): "PASS"}
# Branch-and-bound sub-intervals of s. At 4 the bound on S_mixed/night reads -0.0128 while
# direct sampling of the interval peaks at -0.0039 -- 3.3x conservative, enough to falsify a
# model that is safe at every intensity. The relaxation is the only thing between them, so
# splitting further is the fix.
NSPLIT = int(os.environ.get("NSPLIT", "16"))


def nominal(path, cond):
    z = np.load(path, allow_pickle=True)
    conds = [str(c) for c in z["conds"]]
    if cond not in conds:
        return None
    fr = z["frames"][conds.index(cond)]
    oi = int(np.argmin(np.abs(z["offsets"])))
    yi = int(np.argmin(np.abs(z["yaws"])))
    fr = fr[:, oi, yi]
    px, py = z["pose_x"], z["pose_y"]
    d = np.concatenate([[0], np.cumsum(np.hypot(np.diff(px), np.diff(py)))])
    return fr[:int(np.searchsorted(d, 2861.0))]


def baseline_for(cond_path, fallback):
    """The s = 0 endpoint, preferring a clear baseline from the SAME capture session.

    x_p(s) interpolates between clear and the condition, so the clear endpoint defines
    the disturbance just as much as the condition endpoint does. Taking the two from
    different CARLA sessions puts whatever drifted between them -- sun altitude,
    exposure, a weather field the previous run left set -- inside (x_cond - x_clear),
    where the certificate bounds it as if it were weather.

    Measured, on the one capture that carries both (F43): the two eastbound `clear`
    captures differ by a uniform +0.049 per pixel at identical poses, which is 83% of
    the fog disturbance itself and inverts its sign (fog reads +0.015 against the
    foreign baseline, -0.034 against its own, versus -0.035 westbound). Certifying
    eastbound fog against its own clear moves S_clear from -0.82x to -0.45x.

    So: if the condition capture recorded its own `clear`, that is the baseline.
    Which one was used is printed, never chosen silently.
    """
    own = nominal(cond_path, "clear")
    return (own, "paired") if own is not None else (fallback, "foreign")


def git_head():
    """Commit the result was produced at, or None outside a checkout."""
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def check_coverage(path, direction):
    """Refuse a capture that spans a sliver of the route.

    The Town04 redo's captures covered 160 m of a 2,861 m lap because
    capture_offset_yaw's --length-m defaulted to 160. Nothing downstream noticed: the
    array shapes are identical, the bound computes cleanly, and the certificate
    reproduces exactly -- it is simply a certificate about 5.6% of the road, compared
    afterwards against full-lap driving.

    Older captures predate the route_span_m field; those are measured from their own
    pose track rather than trusted.
    """
    import numpy as _np
    z = _np.load(path, allow_pickle=True)
    # MEASURE, then cross-check what the file claims. Trusting route_span_m was a single
    # point of failure: the field was written from the whole route rather than the
    # captured poses, so a short capture would have declared full coverage and this guard
    # would have waved it through. A self-reported scope is a claim, not evidence.
    span = None
    if "pose_x" in z.files:
        x, y = _np.asarray(z["pose_x"], float), _np.asarray(z["pose_y"], float)
        span = float(_np.hypot(_np.diff(x), _np.diff(y)).sum())
    claimed = float(z["route_span_m"]) if "route_span_m" in z.files else None
    if span is not None and claimed is not None and abs(claimed - span) > 25.0:
        sys.exit(f"REFUSING to certify from {path.name}: it records route_span_m "
                 f"{claimed:.0f} m but its poses span {span:.0f} m. The capture "
                 f"disagrees with itself; recapture before trusting either number.")
    if span is None:
        span = claimed
    if span is None:
        return
    # Compare against the SCORED length, not the route's geometry. Town04's route is a
    # closed 3,042 m loop whose scored prefix is 2,861 m -- the tail runs through an ODD
    # boundary the study excludes -- so a correct full-coverage capture is 2,861 m and
    # measuring it against 3,042 would report 94% for a capture that is exactly right.
    rt = _np.asarray(load_route(direction), dtype=float)
    geom = float(_np.linalg.norm(_np.diff(rt, axis=0), axis=1).sum())
    full = float(getattr(C, "SECTION_LEN_M", {}).get(direction, geom))
    if full > 0 and span < MIN_ROUTE_COVERAGE * full:
        sys.exit(f"REFUSING to certify from {path.name}: it spans {span:.0f} m of a "
                 f"{full:.0f} m scored route ({100*span/full:.1f}%), below the "
                 f"{100*MIN_ROUTE_COVERAGE:.0f}% floor. Recapture without --length-m.")
    # Over-coverage is a scope error too: it certifies road the study does not claim.
    if full > 0 and span > full + 25.0:
        sys.exit(f"REFUSING to certify from {path.name}: it spans {span:.0f} m against a "
                 f"{full:.0f} m scored route. The excess is outside the scored prefix "
                 f"(ODD boundary) and is not comparable to the drives. Recapture.")



def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stride", type=int, default=8,
                    help="pose subsampling; 8 = every 8th pose of the lap (default 8)")
    ap.add_argument("--nsplit", type=int, default=NSPLIT,
                    help="branch-and-bound sub-intervals of s. CHANGES VERDICTS: at 4 the "
                         "bound falsifies a model that is safe at every intensity "
                         "(default %(default)s, or $NSPLIT)")
    ap.add_argument("--allow-missing", action="store_true",
                    help="continue when a capture is absent instead of refusing to run. "
                         "A partial run's score is not comparable to the published 12/12")
    args = ap.parse_args()
    stride, nsplit = args.stride, args.nsplit

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tol = C.CLOSED_LOOP_TOLERANCE
    # The redo reads and writes its OWN captures. results/calibration holds the
    # published ones, taken under the old harness -- D-11 says they are not reusable, and
    # overwriting them would destroy the record the redo is meant to be compared against.
    cal = (REPO / "results" / "town04_v2" / "calibration" if REDO
           else REPO / "results" / "calibration")
    cal.mkdir(parents=True, exist_ok=True)

    # Refuse to produce a partial score that reads like a complete one. A silent `continue`
    # here once printed a clean 6/6 that was indistinguishable from 12/12.
    captures = [(d, c) for d in ("westbound", "eastbound")
                for c in ("fog", "night", "shadows")]
    # One cell per (direction, condition, STUDENT): six captures, twelve cells.
    n_expected = len(captures) * len(STUDENTS)
    missing = [f"lap_{d}_{c}.npz" for d, c in captures if not (cal / f"lap_{d}_{c}.npz").exists()]
    missing += [f"lap_{d}_clear.npz" for d in ("westbound", "eastbound")
                if not (cal / f"lap_{d}_clear.npz").exists()]
    if missing and not args.allow_missing:
        print(f"\nREFUSING TO RUN: {len(missing)} capture(s) absent from {cal}:",
              file=sys.stderr)
        for m in missing:
            print(f"    {m}", file=sys.stderr)
        print("\nThese are gitignored (~1.7 GB each); regenerate with "
              "scripts/capture_offset_yaw.py, or pass --allow-missing to score a subset.",
              file=sys.stderr)
        return 2

    print(f"\nSUSTAINED-BIAS BOUND over s in [0,1]   tolerance {tol:.4f}")
    print(f"  stride {stride}, {nsplit}-way branch and bound, {n_expected} cells expected\n")
    print(f"  {'dir':10s} {'model':9s} {'cond':9s} {'base':8s} {'bias bound':>22s}"
          f" {'x tol':>12s}  verdict     drive")
    out, ok, n = {}, 0, 0
    for direction in ("westbound", "eastbound"):
        base = cal / f"lap_{direction}_clear.npz"
        if not base.exists():
            continue
        check_coverage(base, direction)
        fallback = nominal(base, "clear")
        # Baseline per CONDITION, not per direction: a capture that recorded its own
        # clear frames is paired against those. See baseline_for.
        bl = {}
        for cond in ("fog", "night", "shadows"):
            p = cal / f"lap_{direction}_{cond}.npz"
            if p.exists():
                bl[cond] = baseline_for(p, fallback)
        for nm, ck_base, ch, fc in STUDENTS:
            # CERTIFY THE POLICY, NOT THE DISTILLED INTERMEDIATE. Where a study runs
            # student DAgger -- Town04 does -- the checkpoint that IS the student is the
            # newest DAgger round, and config.final_student resolves it. This script
            # certified `ck` directly, and the Town04 redo certified the distilled model
            # while the ledger drove it too, so the two agreed with each other and
            # neither was the policy. That is exactly the failure final_student was
            # written to prevent, and neither this script nor the ledger called it.
            ck = C.final_student(ck_base)
            net = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
            net.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth",
                                           map_location=dev, weights_only=True))
            net.eval()
            bd = cc.Bounder(1, net, dev, 28, 84, method="CROWN")
            for cond in ("fog", "night", "shadows"):
                p = cal / f"lap_{direction}_{cond}.npz"
                if not p.exists():
                    print(f"  {direction:10s} {nm:9s} {cond:9s} {'capture missing':>22s}")
                    continue
                clr, origin = bl[cond]
                dis = nominal(p, cond)
                if dis is None or len(dis) != len(clr):
                    continue
                with torch.no_grad():
                    sc = net(torch.from_numpy(clr[::stride]).to(dev)
                             ).cpu().numpy().reshape(-1)
                los, his = [], []
                for i, k in enumerate(range(0, len(clr), stride)):
                    x0 = clr[k].reshape(-1).astype(np.float32)
                    x1 = dis[k].reshape(-1).astype(np.float32)
                    lo_i, hi_i = [], []
                    for j in range(nsplit):
                        a, b = j / nsplit, (j + 1) / nsplit
                        mid, half = 0.5 * (a + b), 0.5 * (b - a)
                        W = (half * (x1 - x0)).reshape(-1, 1)
                        l_, u_ = bd(W, x0 + mid * (x1 - x0),
                                    np.array([-1.0]), np.array([1.0]))
                        lo_i.append(l_)
                        hi_i.append(u_)
                    los.append(min(lo_i) - sc[i])
                    his.append(max(hi_i) - sc[i])
                if len(los) < MIN_POSES_PER_CELL:
                    sys.exit(f"REFUSING to certify {nm}/{cond} {direction}: {len(los)} "
                             f"poses, below the {MIN_POSES_PER_CELL} minimum. That is a "
                             f"capture or indexing fault, not a bound.")
                blo, bhi = float(np.mean(los)), float(np.mean(his))
                # The property is "safe for EVERY intensity in the interval", so ANY
                # violation falsifies it. Requiring the WHOLE bound to lie outside asks
                # instead whether it is unsafe at every intensity, which is a different
                # (and much weaker) statement -- that error scored 6 cells INCONCLUSIVE.
                v = "CERTIFIED" if (bhi <= tol and blo >= -tol) else "FALSIFIED"
                n += 1
                if REDO:
                    # TRUTH holds the PUBLISHED students' driven outcomes. Under the redo
                    # these are DIFFERENT students, so scoring new bounds against old
                    # outcomes would print an agreement that means nothing. The redo's own
                    # agreement is computed afterwards, from its own ledger, the way the
                    # Town06 deployment test does it.
                    out[f"{direction}/{nm}/{cond}"] = dict(lo=blo, hi=bhi, verdict=v,
                                                          baseline=origin)
                    print(f"  {direction:10s} {nm:9s} {cond:9s} {origin:8s} "
                          f"[{blo:+.5f},{bhi:+.5f}] [{blo/tol:+5.2f},{bhi/tol:+5.2f}]"
                          f"  {v:12s}", flush=True)
                else:
                    t = TRUTH[(nm, cond)]
                    match = (v == "CERTIFIED") == (t == "PASS")
                    ok += match
                    out[f"{direction}/{nm}/{cond}"] = dict(lo=blo, hi=bhi, verdict=v,
                                                          truth=t, baseline=origin)
                    print(f"  {direction:10s} {nm:9s} {cond:9s} {origin:8s} "
                          f"[{blo:+.5f},{bhi:+.5f}] [{blo/tol:+5.2f},{bhi/tol:+5.2f}]"
                          f"  {v:12s} {t:5s} {'agree' if match else '-'}", flush=True)
    if REDO:
        print(f"\n  {n} cells bounded. NO agreement column: these are different\n"
              f"  students from the published ones, so the hardcoded outcomes do not\n"
              f"  apply. Agreement comes from this redo's OWN ledger.")
    else:
        print(f"\n  decisive and correct: {ok}/{n} of {n_expected} expected")
    if n != n_expected:
        print(f"  WARNING: {n_expected - n} cell(s) did not run. This score is NOT "
              f"comparable to the published 12/12.")
    # Provenance travels with the numbers. NSPLIT and stride both change the result, and a
    # bare JSON of bounds cannot be checked against a paper table without them.
    # THE EXTENT TRAVELS WITH THE CERTIFICATE.
    #
    # This recorded nsplit, stride and tolerance but not WHICH ROAD the bounds cover, and
    # that is the one thing that changed underneath it: the scored prefix moved from
    # 2,861 m to 2,988 m. A certificate that does not state its own extent cannot be
    # compared against drives whose extent also moved -- which is the exact mismatch that
    # put half of every ledger run's worst |CTE| outside the verified road. Rule 7:
    # evidence states its own scope.
    _spans = {}
    for _d in ("westbound", "eastbound"):
        _f = cal / f"lap_{_d}_clear.npz"
        if _f.exists():
            _z = np.load(_f, allow_pickle=True)
            if "pose_x" in _z.files:
                _x, _y = np.asarray(_z["pose_x"], float), np.asarray(_z["pose_y"], float)
                _spans[_d] = round(float(np.hypot(np.diff(_x), np.diff(_y)).sum()), 1)
    out["_meta"] = dict(nsplit=nsplit, stride=stride, tolerance=tol,
                        cells_expected=n_expected, cells_scored=n, correct=ok,
                        lap_end_m=float(C.LAP_END_M),
                        capture_span_m=_spans,
                        town04_redo=bool(REDO),
                        git_commit=git_head(), device=dev,
                        torch=torch.__version__, numpy=np.__version__)
    (cal / "sustained_bound.json").write_text(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

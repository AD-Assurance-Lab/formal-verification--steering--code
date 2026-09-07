#!/usr/bin/env python3
"""Certify the Town06 students. BLIND: this tool has no truth table.

`certify_sustained_bound.py` carries a hardcoded TRUTH dict and prints an
agreement column, which is right for the Town04 discovery test, where the outcomes were
already known and the point was to score a criterion against them. It is exactly wrong
here. A held-out cell must not be scored by the tool that predicts it, so this script
cannot print agreement even if someone wants it to: there is nothing to compare against.

The bound math is IDENTICAL to the Town04 certifier, deliberately and line for line:
CROWN over the one-parameter family with `nsplit` branch-and-bound sub-intervals,
route-mean (sustained) bias, compared against config.CLOSED_LOOP_TOLERANCE. The frozen
constants come from PROTOCOL.md section 3 and this script refuses to run if the lock
has moved.

CROWN, not alpha-CROWN. This docstring said "alpha-CROWN" while the code passed
method="CROWN", and it was read that way into several follow-on findings documents
before being corrected -- the same slip `certify_cell.Bounder` carries a warning about.
`--method CROWN-Optimized` selects alpha-CROWN explicitly, may not write the canonical
certificate, and is recorded in the artifact's own `_meta.method`.

    STUDY_MAP=Town06 python3 scripts/verify/certify_town06.py

Then COMMIT the output before any scored closed-loop run.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent

from steering.protocol_lock import require_locked

from steering import config as C
from steering import certify as cc
from steering.gpu import require_cuda
from steering.student import StudentNet
from steering.study import town06_design as D

# One definition, in config.
#
# TOWN06_STUDENTS_OVERRIDE certifies checkpoints that are not the study's two shipped
# students -- a depth comparison needs the bound width of a 3-conv and a 5-conv net at
# matched ReLU count,
# on the SAME committed captures and through the SAME bound math, because re-implementing
# that math elsewhere is how two certifiers drift apart. Format:
#
#     name:checkpoint:c1,c2[,c3...]:fc;name2:...
#
# An overridden run may NOT write the canonical certificate: it is a different set of
# models, and a file at that path is expected to be about the shipped ones.
STUDENTS = C.TOWN06_STUDENTS
_OVERRIDE = os.environ.get("TOWN06_STUDENTS_OVERRIDE", "").strip()
if _OVERRIDE:
    STUDENTS = tuple(
        (f.split(":")[0], f.split(":")[1],
         tuple(int(x) for x in f.split(":")[2].split(",")), int(f.split(":")[3]))
        for f in _OVERRIDE.split(";") if f.strip())

from steering.captures import (CAPTURES, CANONICAL_CAPTURES,
                               baseline_for, nominal, scope_mask)

# One bound per (student, condition), pooling poses across all sections. The statistic
# is the deviation SUSTAINED along the route, so it is a mean over every scored pose --
# on Town04 that is a lap, here it is the six sections together (3874 m). Reporting a
# separate bound per section would make six stretches of one condition look like six
# independent measurements, which they are not.
OUT = REPO / D.CERT_ARTIFACT
# The published artifact, whatever scope is selected. The two refusals below protect
# THIS, not OUT: with TOWN06_LEDGER_TAG set, OUT is the exploratory certificate and
# comparing against it would have the guards refuse the very file the run is meant to
# write, while leaving the canonical one unguarded.
CANONICAL = REPO / D.CANONICAL_CERT_ARTIFACT


def _rel(p):
    """Repo-relative path for display, or the absolute path when --out is outside it.

    `Path.relative_to` RAISES for a path outside the repo, and it was called only to
    format a log line -- so `--out /tmp/x.json` wrote the certificate correctly and then
    died with ValueError on the very next statement, exiting nonzero on a good run.
    """
    try:
        return Path(p).relative_to(REPO)
    except ValueError:
        return Path(p)


# Sanity floor for a pooled cell. Each section contributes roughly len(section)/stride
# poses, so a correct run pools a few hundred; anything near the section COUNT means the
# pose axis collapsed.
MIN_POSES_PER_CELL = 60
MIN_ROUTE_COVERAGE = 0.80        # of the section's SCORED length


def check_coverage(path, sec):
    """REFUSE a capture that does not cover the section it claims to.

    Parity with certify_sustained_bound, and the reason parity matters: the two
    certifiers do the same job, this one carried MIN_POSES_PER_CELL and the other did
    not, and the Town04 redo ran the one without it and certified 160 m of a 2,861 m lap.
    A guard on one of two sibling tools is a guard that will eventually be bypassed.

    Coverage is MEASURED from the pose track. route_span_m is the capture's own claim
    about itself and is cross-checked, never trusted -- the first version of that field
    recorded the route's length instead of the captured poses', so a short capture would
    have declared full coverage.
    """
    z = np.load(path, allow_pickle=True)
    if "pose_x" not in z.files:
        return
    x, y = np.asarray(z["pose_x"], float), np.asarray(z["pose_y"], float)
    # SCORED road, not the naive pose-to-pose sum, which counts the gap across a bridged
    # span as covered road. route.scored_span_m is the one definition, computed from the
    # POSES ALONE so this remains a recomputation from primary data rather than a reading
    # of anything the artifact or the config asserts (standing rule 7).
    from steering.route import scored_span_m
    span = scored_span_m(x, y)
    claimed = float(z["route_span_m"]) if "route_span_m" in z.files else None
    if claimed is not None and abs(claimed - span) > 25.0:
        sys.exit(f"REFUSING to certify from {path.name}: it records route_span_m "
                 f"{claimed:.0f} m but its poses span {span:.0f} m.")
    # THE SCORED LENGTH, which on the lap is not the route's geometry: the two bridged
    # intersections (170 m) are driven by pure pursuit and scored by nothing, so the
    # capture excludes them and this must expect that. Comparing a correctly-scoped
    # capture against the raw geometry made this refuse a good capture at 93% of a
    # length it was right not to cover.
    want = C.scored_len_m(sec)
    if want <= 0:
        return
    if span < MIN_ROUTE_COVERAGE * want:
        sys.exit(f"REFUSING to certify from {path.name}: it spans {span:.0f} m of the "
                 f"{want:.0f} m section ({100*span/want:.1f}%). Recapture with "
                 f"scripts/capture/capture_town06_laps.sh.")
    if span > want + 25.0:
        sys.exit(f"REFUSING to certify from {path.name}: it spans {span:.0f} m against a "
                 f"{want:.0f} m SCORED section -- road the study does not claim. On the "
                 f"lap this is what a capture that included the bridged intersections "
                 f"would look like.")


def git_head():
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stride", type=int, default=8, help="pose subsampling (frozen: 8)")
    ap.add_argument("--nsplit", type=int, default=16, help="BaB sub-intervals (frozen: 16)")
    ap.add_argument("--allow-missing", action="store_true")
    ap.add_argument("--in-w", type=int, default=None, dest="in_w")
    ap.add_argument("--in-h", type=int, default=None, dest="in_h")
    # The bound METHOD, exposed rather than edited in place for a run (standing
    # rule 8: a number in a paper comes from a committed driver, not a hand edit).
    #
    # Default "CROWN" reproduces every committed certificate exactly. "CROWN-Optimized"
    # is alpha-CROWN: measured on this network at 6% tighter for 78x the cost, which is
    # why plain CROWN is the default everywhere -- but 6% on a MARGINAL cell is worth
    # buying, and it was bought on two cells rather than a sweep.
    ap.add_argument("--method", default="CROWN",
                    choices=("CROWN", "CROWN-Optimized"),
                    help="bound method (frozen default: CROWN; CROWN-Optimized is "
                         "alpha-CROWN, ~78x slower)")
    ap.add_argument("--scope", default="full", choices=("full", "capped"),
                    help="scored road the bound is pooled over. 'full' is the committed "
                         "Town06 certificate; 'capped' drops road over SMAX_CAP.")
    ap.add_argument("--allow-cpu", action="store_true",
                    help="certify on the CPU when no usable GPU is present. Bounds move "
                         "in the 4th significant figure between devices (see "
                         "docs/MIGRATION_2026-09-03.md), so this is for smoke-testing, "
                         "not for producing a certificate of record.")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing certificate. Refused by default: "
                         "results/arterial/certificate_town06.json is the pass-1 artifact "
                         "the protocol requires to stand, and this script's default "
                         "output path IS that file.")
    ap.add_argument("--out", default=None,
                    help="artifact path (default: the scope's own file)")
    args = ap.parse_args()

    require_locked()

    # COMPETENCE PRECONDITION. The bound is on Delta_p(s) = delta_p(s) - delta_p(0),
    # the change the disturbance induces relative to the model's OWN clear-weather
    # output. It never asks whether delta_p(0) is any good, so a network that ignores
    # its input and emits a constant angle has Delta_p identically zero and certifies
    # perfectly under every condition while driving off the road. Distillation is
    # exactly where that can arise: a student without the capacity to fit its teacher
    # can be uniformly wrong in a way that is STABLE across s, and stability is what
    # this criterion rewards. So refuse to certify a student whose clear-weather
    # competence has not been recorded.
    comp = REPO / "results" / "arterial" / "competence_clear.json"
    if not comp.exists():
        sys.exit("REFUSING: no clear-weather competence record.\n"
                 "  The certificate bounds deviation FROM clear and assumes the model\n"
                 "  drives clear weather. Run scripts/training/check_student_competence.py first.")
    rec = json.loads(comp.read_text())
    if not rec.get("all_competent"):
        bad = [k for k, v in rec.get("students", {}).items()
               if not v.get("competent")]
        sys.exit(f"REFUSING: not competent in clear weather: {', '.join(bad)}.\n"
                 "  Certifying would bound deviation from an output already wrong.\n"
                 "  Fix capacity / distillation / student-DAgger rounds first.")
    print(f"  clear-weather competence: OK for all students "
          f"(recorded at {rec.get('git_commit', '?')[:8]})")

    if C.STUDY_MAP != "Town06":
        sys.exit("run with STUDY_MAP=Town06")
    if (args.stride, args.nsplit) != (8, 16):
        sys.exit(f"the protocol freezes stride=8 and nsplit=16; "
                 f"got {args.stride}/{args.nsplit}. Changing either is an amendment.")

    # Resolve the destination and refuse BEFORE certifying, not after: the check used to
    # sit at the write site, so a bare re-run spent the full certification and only then
    # said it would not save the result.
    dest = Path(args.out) if args.out else (
        OUT if args.scope == "full"
        else OUT.with_name(OUT.stem + f"_{args.scope}" + OUT.suffix))
    if CAPTURES.resolve() != CANONICAL_CAPTURES.resolve() and dest == CANONICAL:
        sys.exit(f"REFUSING: TOWN06_CAPTURES_DIR is {_rel(CAPTURES)}, not the committed "
                 f"capture set.\n  The canonical certificate is about the shipped "
                 f"students on the committed frames.\n  Pass --out PATH.")
    if _OVERRIDE and dest == CANONICAL:
        sys.exit("REFUSING: TOWN06_STUDENTS_OVERRIDE is set, so this run is not about the "
                 "shipped students.\n  Pass --out to write it somewhere else; the "
                 "canonical certificate must describe config.TOWN06_STUDENTS.")
    # The canonical certificate is a PLAIN-CROWN artifact and the protocol requires it to
    # stand. A tighter method is a separate result reported alongside it, never a
    # replacement for it -- so the canonical path is refused for any non-default method
    # BEFORE the run, not at the write site hours later.
    if args.method != "CROWN" and dest == CANONICAL:
        sys.exit(f"REFUSING: --method {args.method} may not write the canonical "
                 f"certificate.\n"
                 f"  {_rel(CANONICAL)} is a plain-CROWN artifact and the protocol requires "
                 f"it to stand.\n"
                 f"  Pass --out PATH; every non-CROWN result is a separate artifact.")
    if dest.exists() and not args.force:
        sys.exit(f"REFUSING to overwrite {_rel(dest)}\n"
                 f"  It already exists, and the protocol requires the committed "
                 f"certificates to stand.\n"
                 f"  Write elsewhere with --out PATH, or pass --force if you really "
                 f"mean to replace it.")

    # NOT the is_available()-then-quietly-use-the-CPU idiom. That predicate lies in
    # both directions: it is False while CARLA initialises on the same device, and on the
    # On one machine it was TRUE on a card the installed torch had no kernels for
    # (RTX 5090 is sm_120; torch 2.5.1+cu121 builds sm_50..sm_90), so the certifier
    # selected CUDA and died mid-run. require_cuda allocates and operates on a real
    # tensor, which catches both. tries=1: nothing here races CARLA, so do not sit in a
    # two-minute retry loop -- but still refuse to certify silently on the CPU, because a
    # bound computed on a different device is a bound about a different computation.
    global IN_H, IN_W
    IN_H, IN_W = C.TOWN06_INPUT_H, C.TOWN06_INPUT_W
    if (args.in_w is None) != (args.in_h is None):
        sys.exit("--in-w and --in-h must be given together.")
    if args.in_w:
        IN_H, IN_W = args.in_h, args.in_w
        if CAPTURES.resolve() == CANONICAL_CAPTURES.resolve():
            sys.exit("REFUSING: a non-default input size with the COMMITTED capture set. "
                     "Those frames are 168x56; bounding them as another projection would "
                     "certify a network the frames do not depict.")
    print(f"  projection {IN_W}x{IN_H}, captures {_rel(CAPTURES)}")
    dev = require_cuda(tries=1, wait_s=0, allow_cpu=args.allow_cpu)
    tol = C.CLOSED_LOOP_TOLERANCE
    # THE CONDITION IS low_sun. The capture rig writes lap_<sec>_low_sun.npz, and this
    # asked for lap_<sec>_shadows.npz -- so with --allow-missing it would have certified
    # fog and night and silently dropped a third of the study, and without it the
    # certification stage would have died after every capture had already been taken.
    conds = ("fog", "night", "low_sun")

    need = [f"lap_{d}_{c}.npz" for d in D.SECTIONS for c in conds]
    need += [f"lap_{d}_clear.npz" for d in D.SECTIONS]
    missing = [m for m in need if not (CAPTURES / m).exists()]
    if missing and not args.allow_missing:
        print(f"REFUSING TO RUN: {len(missing)} capture(s) absent from {CAPTURES}:",
              file=sys.stderr)
        for m in missing:
            print(f"    {m}", file=sys.stderr)
        return 2

    n_expected = len(conds) * len(STUDENTS)
    print(f"\nTOWN06 DEPLOYMENT-TEST CERTIFICATE (blind)   tolerance {tol:.6f}")
    print(f"  stride {args.stride}, {args.nsplit}-way BaB, {n_expected} cells expected")
    print(f"  T_CLOSED_LOOP_S = {C.T_CLOSED_LOOP_S} (frozen, inherited from Town04)\n")
    print(f"  {'model':12s} {'cond':9s} {'poses':>4s}  {'bias bound':>22s}"
          f" {'x tol':>14s}  verdict")

    out, n = {}, 0
    for nm, ck_base, ch, fc in STUDENTS:
        # Certify the FINAL student -- the newest student-DAgger round -- not the
        # distilled intermediate. Bounding the wrong checkpoint would produce a
        # perfectly valid certificate about a policy that is not the one under study.
        # With an override the checkpoint name is given exactly; final_student() resolves
        # the study's DAgger'd policies and must not rewrite a name that has no rounds.
        ck = ck_base if _OVERRIDE else C.final_student(ck_base)
        wpath = Path(C.CHECKPOINT_DIR) / f"{ck}.pth"
        if not wpath.exists():
            sys.exit(f"missing checkpoint {wpath}")
        net = StudentNet(IN_H, IN_W, channels=ch, fc=fc).to(dev)
        net.load_state_dict(torch.load(wpath, map_location=dev, weights_only=True))
        net.eval()
        bd = cc.Bounder(1, net, dev, IN_H, IN_W, method=args.method)
        for cond in conds:
            los, his, per_section, origins = [], [], {}, set()
            for sec in D.SECTIONS:
                p = CAPTURES / f"lap_{sec}_{cond}.npz"
                base = CAPTURES / f"lap_{sec}_clear.npz"
                check_coverage(p, sec); check_coverage(base, sec)
                if not p.exists() or not base.exists():
                    continue
                mask = scope_mask(p, args.scope)
                bmask = scope_mask(base, args.scope)
                clr, origin = baseline_for(p, nominal(base, "clear", bmask), mask)
                origins.add(origin)
                dis = nominal(p, cond, mask)
                if dis is None or len(dis) != len(clr):
                    print(f"  {sec}/{nm}/{cond}: LENGTH MISMATCH, skipped")
                    continue
                with torch.no_grad():
                    sc = net(torch.from_numpy(clr[::args.stride]).to(dev)
                             ).cpu().numpy().reshape(-1)
                slo, shi = [], []
                for i, k in enumerate(range(0, len(clr), args.stride)):
                    x0 = clr[k].reshape(-1).astype(np.float32)
                    x1 = dis[k].reshape(-1).astype(np.float32)
                    lo_i, hi_i = [], []
                    for j in range(args.nsplit):
                        a, b = j / args.nsplit, (j + 1) / args.nsplit
                        mid, half = 0.5 * (a + b), 0.5 * (b - a)
                        W = (half * (x1 - x0)).reshape(-1, 1)
                        l_, u_ = bd(W, x0 + mid * (x1 - x0),
                                    np.array([-1.0]), np.array([1.0]))
                        lo_i.append(l_)
                        hi_i.append(u_)
                    slo.append(min(lo_i) - sc[i])
                    shi.append(max(hi_i) - sc[i])
                per_section[sec] = dict(lo=float(np.mean(slo)), hi=float(np.mean(shi)),
                                        poses=len(slo))
                los += slo
                his += shi
            if not los:
                print(f"  {nm:12s} {cond:9s} no captures")
                continue
            # A cell pooled from a handful of poses is not a certificate of anything.
            # The pose-axis bug produced exactly 6 -- one per section -- printed "6
            # poses" beside every verdict, and the run committed and started driving.
            # Nothing downstream questioned it, so the certifier questions it here.
            if len(los) < MIN_POSES_PER_CELL:
                sys.exit(f"REFUSING to certify {nm}/{cond}: {len(los)} poses pooled "
                         f"across {len(per_section)} section(s), below the "
                         f"{MIN_POSES_PER_CELL} minimum. That is a capture or indexing "
                         f"fault, not a bound.")
            blo, bhi = float(np.mean(los)), float(np.mean(his))
            v = "CERTIFIED" if (bhi <= tol and blo >= -tol) else "NOT_CERTIFIED"
            n += 1
            out[f"{nm}/{cond}"] = dict(lo=blo, hi=bhi, lo_x_tol=blo / tol,
                                       hi_x_tol=bhi / tol, verdict=v,
                                       poses=len(los), sections=per_section,
                                       baseline="/".join(sorted(origins)))
            print(f"  {nm:12s} {cond:9s} {len(los):>4d} poses  "
                  f"[{blo:+.5f},{bhi:+.5f}] [{blo/tol:+6.2f},{bhi/tol:+6.2f}]  {v}",
                  flush=True)

    print(f"\n  {n}/{n_expected} cells certified-or-not. NO agreement column: this is a "
          f"prediction,\n  and the closed-loop runs that test it have not happened yet.")
    if n != n_expected:
        print(f"  WARNING: {n_expected - n} cell(s) did not run.")

    out["_meta"] = dict(
        map=C.STUDY_MAP,
        checkpoints={nm: C.final_student(b) for nm, b, _, _ in STUDENTS},
        # 4ac6002: report ReLU count next to every certified rate, so bound looseness
        # from a larger model stays visible rather than being engineered away.
        input_size=[IN_W, IN_H], captures=str(_rel(CAPTURES)),
        relu={nm: C.relu_count(ch, fc, IN_H, IN_W)
              for nm, _, ch, fc in STUDENTS}, nsplit=args.nsplit, stride=args.stride, tolerance=tol,
        t_closed_loop_s=C.T_CLOSED_LOOP_S, lane_width_m=C.LANE_WIDTH_M,
        cte_budget_m=C.CTE_BUDGET_M, lap_end_m=C.LAP_END_M,
        cells_expected=n_expected, cells_scored=n, git_commit=git_head(), device=dev,
        # A certificate SAYS which method produced it. This repo has already had a
        # findings document read "alpha-CROWN" off a stale docstring while the code
        # ran plain CROWN; a bound is not interpretable without its method.
        method=args.method,
        torch=torch.__version__, numpy=np.__version__,
        blind="no truth table; agreement is not computable by this tool")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"\n  wrote {_rel(dest)}")
    print("  COMMIT THIS FILE before running any scored closed-loop cell.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

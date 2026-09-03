#!/usr/bin/env python3
"""Search the certified family for a FALSIFICATION WITNESS. No CARLA, no driving.

WHY. `certify_sustained_bound.py` says this in its own docstring, about the verdict it
emits when the bound does not fit inside the corridor:

    FALSIFIED  ... The name is inherited and it OVERSTATES what is known. A sound
               over-approximation can certify; it cannot falsify. The honest reading is
               NOT CERTIFIED -- the bound does not decide ... Turning one into a genuine
               falsification means exhibiting a witness s* whose sampled lap-mean
               deviation exceeds tolerance, which this repo can do cheaply and does not
               yet do. Two independent reviewers raised this; see F45.

This is that. It costs about a minute on one GPU and it is the difference between "we
could not prove this policy safe" and "here is the intensity at which it is unsafe".

WHAT IT COMPUTES. For a single GLOBAL intensity s -- one disturbance level applied to the
whole lap, which is what a rendered condition IS and what the ledger drives:

    lapmean(s) = mean over scored poses of [ steer(x_clear + s*(x_cond - x_clear))
                                             - steer(x_clear) ]

and searches s in [0,1] for |lapmean| > CLOSED_LOOP_TOLERANCE. A hit is a WITNESS: a
member of the declared family, exhibited, whose sustained bias exceeds the corridor.

WHAT IT IS NOT. It cannot certify. Dense sampling is a lower bound on the true worst
case, so finding nothing means "no witness found", never "safe" -- the certificate is
what makes the positive claim. It also carries no truth table and never reads a ledger,
so PROTOCOL R2 is untouched: it cannot print an agreement column because it has nothing
to compare against.

THE TWO READINGS OF THE FAMILY, and this is why the tool matters. The certifier bounds,
per pose, the worst case over s, and THEN averages over poses -- so s is free to vary
from pose to pose. That is deliberate and documented (it covers spatially varying
disturbance, fog thicker in a hollow) and it is sound. But it quantifies over a strictly
larger set than a single global intensity, so a NOT_CERTIFIED cell may have no witness at
all: sound, undecided, and not evidence that the policy fails anywhere the ledger could
ever drive.

    STUDY_MAP=Town06 python3 scripts/falsify_witness.py
    STUDY_MAP=Town06 python3 scripts/falsify_witness.py --scope capped --json out.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "scripts"))

import config as C  # noqa: E402
from student import StudentNet  # noqa: E402
from study import town06_design as D  # noqa: E402
from certify_town06 import nominal, scope_mask, CAPTURES  # noqa: E402

CONDS = ("fog", "night", "low_sun")


def lap_means(net, X0, Dl, svals, dev, chunk=16):
    """lapmean(s) for each s. One forward pass per s over all poses."""
    out = []
    with torch.no_grad():
        y0 = net(X0).reshape(-1)
        for i in range(0, len(svals), chunk):
            for s in svals[i:i + chunk]:
                y = net(X0 + float(s) * Dl).reshape(-1)
                out.append(float((y - y0).mean()))
    return np.array(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scope", default="full", choices=("full", "capped"))
    ap.add_argument("--grid", type=int, default=1001, help="coarse s samples")
    ap.add_argument("--refine", type=int, default=201, help="samples around each extremum")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    if C.STUDY_MAP != "Town06":
        sys.exit("run with STUDY_MAP=Town06")
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tol = C.CLOSED_LOOP_TOLERANCE
    cert_rel = (D.CERT_ARTIFACT if args.scope == "full"
                else getattr(D, "CAPPED_CERT_ARTIFACT", D.CERT_ARTIFACT))
    cert = json.loads((REPO / cert_rel).read_text())

    print(f"\nFALSIFICATION WITNESS SEARCH -- scope '{args.scope}', tolerance {tol:.6f}")
    print(f"  certificate: {cert_rel}")
    print(f"  a witness is a SINGLE GLOBAL s whose lap-mean bias exceeds tolerance\n")
    print(f"  {'student':13s} {'cond':8s} {'s=1 (driven)':>13s} {'worst s':>9s} "
          f"{'s*':>6s}  {'witness':8s} certificate")

    rec = {}
    for nm, ck_base, ch, fc in C.TOWN06_STUDENTS:
        ck = C.final_student(ck_base)
        net = StudentNet(C.TOWN06_INPUT_H, C.TOWN06_INPUT_W, channels=ch, fc=fc).to(dev)
        net.load_state_dict(torch.load(Path(C.CHECKPOINT_DIR) / f"{ck}.pth",
                                       map_location=dev, weights_only=True))
        net.eval()
        for cond in CONDS:
            cpath = CAPTURES / f"lap_lap_{cond}.npz"
            bpath = CAPTURES / "lap_lap_clear.npz"
            mask, bmask = scope_mask(cpath, args.scope), scope_mask(bpath, args.scope)
            dis, clr = nominal(cpath, cond, mask), nominal(bpath, "clear", bmask)
            if dis is None or clr is None or len(dis) != len(clr):
                sys.exit(f"capture mismatch for {cond}")
            ks = range(0, len(clr), 8)          # the frozen stride
            X0 = torch.from_numpy(np.stack([clr[k] for k in ks])).to(dev)
            Dl = torch.from_numpy(np.stack([dis[k] for k in ks])).to(dev) - X0

            g = np.linspace(0.0, 1.0, args.grid)
            m = lap_means(net, X0, Dl, g, dev)
            best = (float(g[int(np.argmax(np.abs(m)))]),
                    float(m[int(np.argmax(np.abs(m)))]))
            for i in (int(np.argmax(m)), int(np.argmin(m))):
                lo, hi = max(0.0, g[i] - 2e-3), min(1.0, g[i] + 2e-3)
                gg = np.linspace(lo, hi, args.refine)
                mm = lap_means(net, X0, Dl, gg, dev)
                j = int(np.argmax(np.abs(mm)))
                if abs(mm[j]) > abs(best[1]):
                    best = (float(gg[j]), float(mm[j]))
            s1 = float(m[-1])
            wit = abs(best[1]) > tol
            cv = cert.get(f"{nm}/{cond}", {}).get("verdict", "?")
            rec[f"{nm}/{cond}"] = dict(s_star=best[0], worst=best[1],
                                       worst_x_tol=best[1] / tol, s1=s1,
                                       s1_x_tol=s1 / tol, witness=bool(wit),
                                       certificate=cv, poses=len(list(ks)),
                                       scope=args.scope)
            print(f"  {nm:13s} {cond:8s} {s1/tol:+12.2f}x {best[1]/tol:+8.2f}x "
                  f"{best[0]:6.3f}  {'YES' if wit else 'no':8s} {cv}")

    n_wit = sum(1 for v in rec.values() if v["witness"])
    n_nc = sum(1 for v in rec.values() if v["certificate"] == "NOT_CERTIFIED")
    print(f"\n  {n_wit} witness(es) exhibited; {n_nc} cell(s) NOT_CERTIFIED.")
    undecided = [k for k, v in rec.items()
                 if v["certificate"] == "NOT_CERTIFIED" and not v["witness"]]
    if undecided:
        print(f"  {len(undecided)} NOT_CERTIFIED cell(s) with NO witness -- sound but "
              f"UNDECIDED.\n  Their verdict rests on the pose-wise-varying-s relaxation, "
              f"not on any\n  single intensity the ledger could drive:")
        for k in undecided:
            print(f"    {k}  (worst single-s {rec[k]['worst_x_tol']:+.2f}x tol "
                  f"at s={rec[k]['s_star']:.3f})")
    # The interesting direction: cells whose DRIVEN endpoint looks safe by this statistic
    # but whose interior does not. Certifying only at s=1 would have passed these.
    endpoint_safe = [k for k, v in rec.items()
                     if abs(v["s1_x_tol"]) <= 1.0 and v["witness"]]
    if endpoint_safe:
        print(f"\n  {len(endpoint_safe)} cell(s) are INSIDE the corridor at the driven "
              f"intensity s=1\n  but have a witness in the interior. Certifying only at "
              f"the rendered condition\n  would have issued a sound-looking certificate "
              f"on each of them:")
        for k in endpoint_safe:
            print(f"    {k}  s=1 {rec[k]['s1_x_tol']:+.2f}x tol, "
                  f"witness {rec[k]['worst_x_tol']:+.2f}x at s={rec[k]['s_star']:.3f}")
    if args.json:
        Path(args.json).write_text(json.dumps(rec, indent=2))
        print(f"\n  wrote {args.json}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

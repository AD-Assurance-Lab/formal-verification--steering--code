#!/usr/bin/env python3
"""Stand up and validate the verification stack. No CARLA, no collected data needed.

Runs the mandatory cross-checks on a real StudentNet before any certificate is computed,
because a verifier that is silently misconfigured produces confident wrong numbers -- the
previous generation published "SDP-CROWN" results that were actually alpha-CROWN, for
exactly that reason.

Three checks, all of which must pass:

  1. ZERO PERTURBATION returns the nominal output. If the bounds do not collapse to the
     forward pass at eps=0, the model wiring is wrong and nothing downstream is valid.
  2. SOUNDNESS: bounds contain a concrete sample of the input set. A bound that excludes
     a reachable point is unsound, which invalidates the tool rather than the experiment.
  3. TIGHTNESS ORDERING: IBP is contained by CROWN is contained by alpha-CROWN. If the
     ordering is violated, the methods are not doing what their names say.

It also records the pixel-space L-inf bound width, which is the baseline the physical
parameterization has to beat. The whole tractability argument is that a low-dimensional
theta is bounded far more tightly than a full-dimensional pixel ball.

    python scripts/verify_smoke.py --student S_clear_84x28
"""

import argparse
import os
import sys
from pathlib import Path

import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
from student import StudentNet  # noqa: E402

from auto_LiRPA import BoundedModule, BoundedTensor, PerturbationLpNorm  # noqa: E402


def bounds(model, x, eps, method):
    """(lower, upper) on the steering output over an L-inf ball of radius eps."""
    bounded = BoundedModule(model, torch.empty_like(x), device=x.device)
    ptb = PerturbationLpNorm(norm=float("inf"), eps=eps)
    bx = BoundedTensor(x, ptb)
    lb, ub = bounded.compute_bounds(x=(bx,), method=method)
    return float(lb.min()), float(ub.max())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--student", default="S_clear_84x28")
    ap.add_argument("--w", type=int, default=84)
    ap.add_argument("--h", type=int, default=28)
    ap.add_argument("--channels", default="8,16,16")
    ap.add_argument("--fc", type=int, default=32)
    ap.add_argument("--eps", type=float, default=1.0 / 255.0,
                    help="pixel-space L-inf radius for the baseline measurement")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = StudentNet(args.h, args.w,
                       channels=tuple(int(v) for v in args.channels.split(",")),
                       fc=args.fc).to(device)
    model.load_state_dict(torch.load(
        os.path.join(C.CHECKPOINT_DIR, f"{args.student}.pth"), map_location=device))
    model.eval()

    torch.manual_seed(0)
    x = torch.rand(1, 3, args.h, args.w, device=device)
    with torch.no_grad():
        nominal = float(model(x).item())

    print(f"student {args.student} on {device}: {model.num_relu_neurons()} ReLU neurons")
    print(f"input {tuple(x.shape)} = {x.numel()} dims | nominal steer {nominal:+.6f}\n")

    failures = []

    # 1 -- zero perturbation must collapse to the forward pass
    lb, ub = bounds(model, x, 0.0, "CROWN")
    ok = abs(lb - nominal) < 1e-4 and abs(ub - nominal) < 1e-4
    print(f"  [1] zero perturbation -> [{lb:+.6f}, {ub:+.6f}]  {'OK' if ok else 'FAIL'}")
    if not ok:
        failures.append("bounds do not collapse to nominal at eps=0")

    # 2 -- soundness against a concrete sample of the same input set
    lb, ub = bounds(model, x, args.eps, "CROWN")
    with torch.no_grad():
        corners = torch.cat([
            (x + args.eps * (torch.randint(0, 2, x.shape, device=device) * 2 - 1)).clamp(0, 1)
            for _ in range(64)
        ])
        concrete = model(corners)
    c_lo, c_hi = float(concrete.min()), float(concrete.max())
    ok = lb <= c_lo and ub >= c_hi
    print(f"  [2] soundness: bound [{lb:+.6f}, {ub:+.6f}] vs concrete "
          f"[{c_lo:+.6f}, {c_hi:+.6f}]  {'OK' if ok else 'UNSOUND'}")
    if not ok:
        failures.append("bounds do not contain a concrete sample -- UNSOUND")

    # 3 -- tightness ordering
    print()
    widths = {}
    for method in ("IBP", "CROWN", "CROWN-Optimized"):
        lb, ub = bounds(model, x, args.eps, method)
        widths[method] = ub - lb
        print(f"  [3] {method:16s} [{lb:+.6f}, {ub:+.6f}]  width {ub - lb:.6f}")
    ordered = widths["IBP"] >= widths["CROWN"] >= widths["CROWN-Optimized"] - 1e-6
    print(f"      IBP >= CROWN >= alpha-CROWN: {'OK' if ordered else 'VIOLATED'}")
    if not ordered:
        failures.append("tightness ordering violated")

    # Baseline for the tractability argument.
    print(f"\n  pixel-space L-inf at eps={args.eps:.5f} over {x.numel()} dims:")
    print(f"    alpha-CROWN width {widths['CROWN-Optimized']:.6f} against a closed-loop "
          f"tolerance of {C.CLOSED_LOOP_TOLERANCE:.4f}")
    ratio = widths["CROWN-Optimized"] / C.CLOSED_LOOP_TOLERANCE
    print(f"    ratio {ratio:.1f}x -- this is the baseline the physical parameterization")
    print("    has to beat, and why a full-dimensional pixel ball is not usable.")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("all verification cross-checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

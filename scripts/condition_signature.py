#!/usr/bin/env python3
"""Identify the rendered condition from ONE frame, and assert it is the one requested.

Why this rather than driving: a simulator check that DRIVES costs a full section and
keeps the server up longer, which is the exposure we are trying to avoid. The cheap,
correct check is to look at a single frame -- the conditions this study renders are
separable by simple image statistics, measured over the training set:

    condition   mean     sigma    p01     frac(<0.05)
    clear       0.3039   0.0636   0.0471     1.0%
    fog         0.2803   0.0601   0.1804     0.0%
    night       0.2002   0.1380   0.0000    13.8%
    shadows     0.1842   0.0559   0.0157     2.8%

Two of those are near-perfect discriminators and neither is brightness:
  - NIGHT is the only high-CONTRAST condition, sigma >= 0.10 against <= 0.065.
  - FOG is the only condition with NO dark pixels: airlight lifts the floor, p01 >= 0.12
    against <= 0.05. That is the veil, and it is what makes fog identifiable.
Clear and shadows are then separated by mean, 0.304 against 0.184.

Note that brightness alone would NOT work: shadows is DARKER than night.

    python3 scripts/condition_signature.py                 # validate on the captures
    from condition_signature import identify, assert_condition
"""
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent


def stats(frame):
    """frame: float array in [0,1], any shape (CHW or HWC)."""
    a = np.asarray(frame, dtype=np.float32)
    return dict(mean=float(a.mean()), sigma=float(a.std()),
                p01=float(np.percentile(a, 1)), p99=float(np.percentile(a, 99)),
                frac_dark=float((a < 0.05).mean()))


def identify(frame):
    """Return the condition name this frame looks like. Order matters."""
    s = stats(frame)
    if s["sigma"] >= 0.100:                 # night: the only high-contrast condition
        return "night", s
    if s["p01"] >= 0.120:                   # fog: airlight lifts the black floor
        return "fog", s
    if s["mean"] >= 0.250:                  # clear vs shadows, on mean
        return "clear", s
    return "shadows", s


def assert_condition(frame, want):
    """Raise unless the frame looks like `want`. Use after set_condition."""
    got, s = identify(frame)
    if got != want:
        raise RuntimeError(
            f"CONDITION MISMATCH: asked to render '{want}', the frame looks like "
            f"'{got}'.\n    mean={s['mean']:.4f} sigma={s['sigma']:.4f} "
            f"p01={s['p01']:.4f} frac_dark={s['frac_dark']:.3f}\n"
            f"    Every frame from here would be mislabelled. This is the Town04 "
            f"fog-into-night failure.")
    return got, s


def main():
    """Validate the rule against captures whose condition is known from their filename."""
    caps = sorted((REPO / "results" / "town06" / "captures").glob("lap_*.npz"))
    if not caps:
        print("no captures to validate against")
        return 1
    ok = bad = 0
    print(f"{'file':28s} {'want':9s} {'got':9s} {'mean':>7s} {'sigma':>7s} "
          f"{'p01':>7s} {'dark':>6s}")
    for p in caps:
        want = p.stem.rsplit("_", 1)[1]
        z = np.load(p, allow_pickle=True)
        conds = [str(c) for c in z["conds"]]
        if want not in conds:
            continue
        fr = z["frames"][conds.index(want)]
        frame = fr[fr.shape[0] // 2, 0, 0]          # a mid-section pose
        got, s = identify(frame)
        flag = "" if got == want else "   <-- MISCLASSIFIED"
        ok, bad = (ok + 1, bad) if got == want else (ok, bad + 1)
        print(f"{p.name:28s} {want:9s} {got:9s} {s['mean']:7.4f} {s['sigma']:7.4f} "
              f"{s['p01']:7.4f} {s['frac_dark']:6.3f}{flag}")
    print(f"\n  {ok} correct, {bad} misclassified out of {ok + bad}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

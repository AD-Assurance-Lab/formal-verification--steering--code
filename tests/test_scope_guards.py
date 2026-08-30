#!/usr/bin/env python3
"""Prove the scope guards REJECT bad captures. A guard is not in force until it fails.

Every guard written for the 160 m capture defect had a defect of its own, and each was
found by running it against real data rather than by reading it:

  * route_span_m recorded the ROUTE's length, not the captured poses', so any short
    capture would have declared full coverage -- and the certifiers trusted the field.
  * the coverage check was one-sided, so it caught under-coverage and was blind to
    capturing 181 m of ODD-boundary road the study excludes.
  * the parity check asserting that sibling certifiers carry the same guards was itself
    one-sided, and certify_town06 had no coverage guard at all.

So the guards are exercised here against synthetic captures whose scope is known to be
wrong. Each case asserts a REFUSAL, not just that the code runs.

    python3 tests/test_scope_guards.py
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent

# (label, certifier module, env, cell, scored length of that cell)
TARGETS = [
    ("certify_sustained_bound", "certify_sustained_bound",
     dict(STUDY_MAP="Town04", TOWN04_REDO="1"), "eastbound", 2861.0),
    ("certify_town06", "certify_town06",
     dict(STUDY_MAP="Town06"), "s00", 894.0),
]


def make_capture(path, span_m, claimed_span=None, n=200):
    """A straight pose track of exactly span_m metres, with an optional false claim."""
    x = np.linspace(0.0, span_m, n)
    y = np.zeros(n)
    kw = dict(conds=np.array(["clear"]), offsets=np.array([0.0]), yaws=np.array([0.0]),
              pose_x=x, pose_y=y, pose_yaw=np.zeros(n),
              frames=np.zeros((1, n, 1, 1, 3, 4, 4), dtype=np.float32))
    if claimed_span is not None:
        kw["route_span_m"] = float(claimed_span)
    np.savez_compressed(path, **kw)


def run_guard(module, env, path, cell):
    """Call the module's check_coverage in a subprocess; return (exitcode, output)."""
    code = (
        "import sys; sys.path.insert(0, 'scripts'); sys.path.insert(0, 'pipeline');"
        "sys.path.insert(0, '.');"
        f"import {module} as m;"
        f"m.check_coverage(__import__('pathlib').Path({str(path)!r}), {cell!r});"
        "print('ACCEPTED')"
    )
    e = dict(os.environ); e.update(env); e["CARLA_PORT"] = e.get("CARLA_PORT", "3000")
    p = subprocess.run([sys.executable, "-c", code], cwd=str(REPO), env=e,
                       capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


def main():
    failures = []
    with tempfile.TemporaryDirectory() as td:
        for label, module, env, cell, scored in TARGETS:
            cases = [
                # name,                span,          claimed,  must_reject
                ("full coverage",      scored + 1.0,  None,     False),
                ("the 160 m defect",   160.0,         None,     True),
                ("over-coverage",      scored + 200,  None,     True),
                ("lies about itself",  scored + 1.0,  scored * 1.4, True),
            ]
            for name, span, claimed, must_reject in cases:
                q = Path(td) / f"lap_{cell}_clear.npz"
                make_capture(q, span, claimed)
                rc, out = run_guard(module, env, q, cell)
                rejected = rc != 0 and "REFUSING" in out
                ok = rejected == must_reject
                verb = "rejects" if must_reject else "accepts"
                print(f"  {'PASS' if ok else 'FAIL'}  {label} {verb} {name}")
                if not ok:
                    failures.append(f"{label}/{name}: rc={rc} {out.strip()[:300]}")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  {f}")
        return 1
    print("  all scope guards demonstrated to refuse bad captures")
    return 0


if __name__ == "__main__":
    sys.exit(main())

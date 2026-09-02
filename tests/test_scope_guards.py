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
def _scored_len(study_map, cell, **env):
    """Ask the study what road it CLAIMS on `cell`. Not typed in here.

    The previous version said the length should come from the route rather than being
    hardcoded, and then hardcoded 2289.0 anyway -- which is the lap's GEOMETRY, not its
    scored road. The two differ by the 170 m of bridged intersection, so this test
    asserted that a capture covering 170 m of unscored road must be ACCEPTED, and it
    failed the moment the guard was corrected to refuse exactly that.
    """
    code = ("import os,sys;"
            + "".join(f"os.environ[{k!r}]={v!r};" for k, v in
                      dict(STUDY_MAP=study_map, **env).items())
            + "sys.path.insert(0,'pipeline');import config as C;"
              f"print(C.scored_len_m({cell!r}))")
    out = subprocess.run([sys.executable, "-c", code], cwd=str(REPO),
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


TARGETS = [
    ("certify_sustained_bound", "certify_sustained_bound",
     dict(STUDY_MAP="Town04", TOWN04_REDO="1"), "eastbound",
     _scored_len("Town04", "eastbound", TOWN04_REDO="1")),
    # Town06 is ONE LAP, and its scored road is the route MINUS the two bridged
    # intersections: pure pursuit drives them and nothing scores them, so a certificate
    # that covered them would not be comparable to the drives it is validated against.
    ("certify_town06", "certify_town06",
     dict(STUDY_MAP="Town06"), "lap", _scored_len("Town06", "lap")),
]


def _bridged_m(study_map, cell, env):
    """Metres of `cell` that are driven by pure pursuit and scored by nothing."""
    code = ("import os,sys;"
            + "".join(f"os.environ[{k!r}]={v!r};" for k, v in
                      dict(env, STUDY_MAP=study_map).items())
            + "sys.path.insert(0,'pipeline');import config as C;"
              f"print(sum(b-a for a,b in C.bridge_spans_for({cell!r})))")
    out = subprocess.run([sys.executable, "-c", code], cwd=str(REPO),
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


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
                # The lap's specific version of over-coverage: a capture that spans the
                # bridged intersections as well as the scored road. On Town04, where
                # there are no bridges, this is the same as "full coverage" and must be
                # accepted -- the case is generated from the map, not asserted blindly.
            ]
            bridged = _bridged_m(env.get("STUDY_MAP", "Town04"), cell, env)
            if bridged > 25.0:
                cases.append(("the bridged road as well", scored + bridged, None, True))
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


# --- open-route index arithmetic (G-9) -------------------------------------
# Every route helper was written for Town04's lap, which closes on itself, so
# index arithmetic ran modulo len(route). The Town06 lap is open: Zach cut it
# before a double intersection outside the ODD, leaving start and end 173.8 m
# apart. There the wrap is a teleport across the gap, and it lands in the last
# few steps of the lap -- inside the scored region.

def _routes():
    import numpy as np
    root = Path(__file__).resolve().parents[1] / "pipeline" / "data"
    return (np.load(root / "routes_town06" / "lap.npy"),
            np.load(root / "routes" / "eastbound.npy"))


def test_route_closure_is_detected():
    import sys; sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
    import route
    lap, eastbound = _routes()
    assert route.route_is_closed(eastbound), "Town04's lap closes (7.9 m) and must keep wrapping"
    assert not route.route_is_closed(lap), "the Town06 lap is open (173.8 m) and must not wrap"


def test_open_route_never_wraps_to_the_start():
    import sys; sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
    import route
    lap, eastbound = _routes()
    n = len(lap)
    for k in range(1, 8):
        assert route._step_idx(lap, n - 1, k) == n - 1, "open route advanced past its end"
        assert route._step_idx(lap, 0, -k) == 0, "open route stepped back past its start"
    m = len(eastbound)
    assert route._step_idx(eastbound, m - 1, 3) == 2, "closed route must still wrap"


def test_pure_pursuit_does_not_saturate_at_an_open_route_end():
    """Clamping the lookahead to the last vertex makes the target the vehicle's
    own position, ld -> 0, and the steer saturate. It must extrapolate instead."""
    import sys, math; sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
    import route
    lap, _ = _routes()
    n = len(lap)

    class _TF:
        def __init__(self, x, y, yaw):
            self.location = type("L", (), {"x": x, "y": y, "z": 0.0})()
            self.rotation = type("R", (), {"yaw": yaw})()

    for k in (4, 3, 2, 1):
        i = n - k
        a, b = lap[i - 1], lap[i]
        yaw = math.degrees(math.atan2(float(b[1] - a[1]), float(b[0] - a[0])))
        steer, _, _ = route.pure_pursuit_route(lap, _TF(float(b[0]), float(b[1]), yaw), hint=i)
        assert abs(steer) < 0.25, (
            f"pure pursuit commands {steer:+.3f} at i=n-{k} of an open route; "
            "a vehicle sitting on the path should be steering nearly straight")


def main_open_route():
    """The open-route guards (G-9). These are pure functions, so they run without
    a simulator -- there is no excuse for them not to run on every commit."""
    failures = []
    for fn in (test_route_closure_is_detected,
               test_open_route_never_wraps_to_the_start,
               test_pure_pursuit_does_not_saturate_at_an_open_route_end):
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as e:
            print(f"  FAIL  {fn.__name__}: {e}")
            failures.append(fn.__name__)
    return 1 if failures else 0


if __name__ == "__main__":
    rc = main_open_route()
    if "--open-route-only" in sys.argv:
        sys.exit(rc)
    sys.exit(main() or rc)

"""The helpers that moved out of scripts and into the library must still run.

Importing a module proves its imports resolve. It does not prove its functions do:
`wilson` was extracted from closed_loop_ledger.py without carrying `import math`, and
every import test passed, because nothing calls it at module scope. It would have failed
the first time somebody aggregated a ledger -- which happens after the driving, on the
lab machine, at the end of a long run.

So call them. These are cheap, need no simulator, and each one covers a function that
now lives somewhere other than where it was written.
"""
import math

import numpy as np
import pytest

from steering.drive.ledger import LEDGER, wilson


def test_wilson_matches_the_closed_form():
    """The interval, computed independently here, to the last digit."""
    for k, n in [(0, 3), (1, 3), (3, 3), (0, 10), (1, 10), (7, 12), (12, 12)]:
        z = 1.96
        d = 1.0 + z * z / n
        centre = (p := k / n, (p + z * z / (2 * n)) / d)[1]
        half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
        assert wilson(k, n) == (max(0.0, centre - half), min(1.0, centre + half))


def test_wilson_stays_inside_the_unit_interval():
    """Which is the reason it is used instead of the normal approximation: these rates
    land at k=0 and k=n, where the normal interval leaves [0,1]."""
    for n in range(1, 13):
        for k in range(n + 1):
            lo, hi = wilson(k, n)
            assert 0.0 <= lo <= hi <= 1.0


def test_wilson_of_nothing_is_no_information():
    assert wilson(0, 0) == (0.0, 1.0)


def test_ledger_directory_is_inside_the_repository():
    from steering import REPO_ROOT
    assert str(LEDGER).startswith(str(REPO_ROOT))


def test_scope_mask_full_keeps_every_pose(tmp_path):
    """`full` is what the committed certificate used, and it must not silently drop
    poses -- the capture rig already skips the bridges, so its poses ARE the scored
    road. A mask that quietly shortened this is the shape of the coverage defect."""
    from steering.verify.captures import scope_mask
    q = tmp_path / "lap_lap_clear.npz"
    n = 40
    np.savez_compressed(q, conds=np.array(["clear"]), offsets=np.array([0.0]),
                        yaws=np.array([0.0]), pose_x=np.linspace(0, 100, n),
                        pose_y=np.zeros(n), pose_yaw=np.zeros(n),
                        frames=np.zeros((1, n, 1, 1, 3, 4, 4), dtype=np.float32))
    m = scope_mask(q, "full")
    assert m.dtype == bool and m.shape == (n,) and m.all()


def test_scope_mask_refuses_a_capture_with_no_pose_track(tmp_path):
    """Without poses there is no way to say which road a capture covers, and guessing
    is how a certificate comes to describe 5.6% of a route without saying so."""
    from steering.verify.captures import scope_mask
    q = tmp_path / "lap_lap_clear.npz"
    np.savez_compressed(q, conds=np.array(["clear"]),
                        frames=np.zeros((1, 4, 1, 1, 3, 4, 4), dtype=np.float32))
    with pytest.raises(RuntimeError, match="no pose track"):
        scope_mask(q, "capped")


def test_nominal_returns_none_for_a_condition_the_capture_does_not_hold(tmp_path):
    from steering.verify.captures import nominal
    q = tmp_path / "lap_lap_clear.npz"
    np.savez_compressed(q, conds=np.array(["clear"]), offsets=np.array([0.0]),
                        yaws=np.array([0.0]),
                        frames=np.zeros((1, 4, 1, 1, 3, 4, 4), dtype=np.float32))
    assert nominal(q, "fog") is None


def test_nominal_keeps_the_pose_axis(tmp_path):
    """The bug this guards: indexing took the offset index off the POSE axis, returning
    one pose per section instead of the whole capture -- and reported "6 poses" as if
    that were normal. The shape check has to be on the pose count, not the rank."""
    from steering.verify.captures import nominal
    q = tmp_path / "lap_lap_fog.npz"
    n = 12
    np.savez_compressed(q, conds=np.array(["clear", "fog"]),
                        offsets=np.array([-0.5, 0.0, 0.5]),
                        yaws=np.array([-1.0, 0.0, 1.0]),
                        frames=np.zeros((2, n, 3, 3, 3, 4, 4), dtype=np.float32))
    out = nominal(q, "fog")
    assert out.shape == (n, 3, 4, 4)


def test_load_model_is_importable_from_the_library():
    """It moved out of scripts/training/evaluate.py, and gate_teacher_lap.py depends on it being
    reachable without importing another script."""
    pytest.importorskip("torch")
    from steering.networks.model import load_model
    assert callable(load_model)

"""The property that makes a certificate a certificate: the bound must CONTAIN the function.

Everything else in this repo checks process discipline. This checks the mathematics the
result rests on -- that alpha-CROWN's interval over the disturbance segment actually encloses
the network's output at points inside that segment.

Nothing here needs CARLA, a capture, or a trained checkpoint: the property is a property of
the bounding machinery, so a randomly initialized StudentNet exercises it exactly as well and
the test runs in seconds.

Why it exists: F43 was an input defect that no test could have caught, and the disposition
(D-12) records that the headline instrument had no automated coverage at all. This is the
minimum that closes that gap.

Run: pytest conformance/test_bound_soundness.py -v
"""

import sys
import importlib
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
for p in (str(REPO), str(REPO / "pipeline"), str(REPO / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

NSPLIT = 4          # fewer splits than production: a LOOSER bound, so a strictly harder test
N_SAMPLES = 256     # points drawn inside each sub-interval
H, W = 28, 84


def _deps():
    """Skip rather than fail where the verifier stack is not installed."""
    try:
        torch = importlib.import_module("torch")
        importlib.import_module("auto_LiRPA")
    except ImportError as e:                                  # pragma: no cover
        pytest.skip(f"verifier stack not installed ({e})")
    try:
        cc = importlib.import_module("certify_cell")
        student = importlib.import_module("student")
    except ImportError as e:                                  # pragma: no cover
        pytest.skip(f"repo modules not importable ({e})")
    return torch, cc, student


def _fixture(torch, student, seed=0):
    """A small student and two endpoint images, standing in for clear and a condition."""
    torch.manual_seed(seed)
    net = student.StudentNet(H, W, channels=(8, 16, 16), fc=32).eval()
    rng = np.random.default_rng(seed)
    x0 = rng.random(3 * H * W).astype(np.float32)
    # Endpoint separation comparable to a real condition (night measures ~0.14 per pixel).
    x1 = np.clip(x0 + rng.normal(0, 0.14, x0.shape).astype(np.float32), 0, 1)
    return net, x0, x1


def test_bound_encloses_sampled_output_on_the_disturbance_segment():
    """For every sub-interval of s, every sampled output must lie inside [lo, hi].

    This is the soundness claim itself. A violation means the certificate is worthless --
    not conservative, WRONG -- so the assertion is exact rather than tolerant.
    """
    torch, cc, student = _deps()
    net, x0, x1 = _fixture(torch, student)
    bd = cc.Bounder(1, net, "cpu", H, W, method="CROWN")
    rng = np.random.default_rng(1)

    worst_slack = np.inf
    for j in range(NSPLIT):
        a, b = j / NSPLIT, (j + 1) / NSPLIT
        mid, half = 0.5 * (a + b), 0.5 * (b - a)
        centre = x0 + mid * (x1 - x0)
        Wcol = (half * (x1 - x0)).reshape(-1, 1)

        lo, hi = bd(Wcol, centre, np.array([-1.0]), np.array([1.0]))
        assert lo <= hi, f"degenerate interval on [{a},{b}]: {lo} > {hi}"

        # t parameterizes the sub-interval; endpoints included deliberately.
        t = np.concatenate([rng.uniform(-1, 1, N_SAMPLES - 2), [-1.0, 1.0]])
        pts = centre[None, :] + t[:, None] * Wcol.reshape(1, -1)
        with torch.no_grad():
            out = net(torch.from_numpy(
                pts.reshape(-1, 3, H, W).astype(np.float32))).numpy().reshape(-1)

        assert out.min() >= lo, (
            f"UNSOUND on s in [{a},{b}]: sampled {out.min():.6f} < lower bound {lo:.6f}")
        assert out.max() <= hi, (
            f"UNSOUND on s in [{a},{b}]: sampled {out.max():.6f} > upper bound {hi:.6f}")
        worst_slack = min(worst_slack, out.min() - lo, hi - out.max())

    # Sanity on the other side: a bound that encloses everything by a mile is sound but
    # useless, and would make the assertions above pass vacuously.
    assert worst_slack < 1.0, f"bound is implausibly loose (slack {worst_slack:.3f})"


def test_splitting_tightens_or_holds_the_bound():
    """Branch and bound must not make the enclosure worse.

    The study's NSPLIT=16 is justified by exactly this monotonicity (a 4-split bound
    falsified a model that is safe at every intensity). If it does not hold, the recorded
    convergence table means nothing.
    """
    torch, cc, student = _deps()
    net, x0, x1 = _fixture(torch, student)
    bd = cc.Bounder(1, net, "cpu", H, W, method="CROWN")

    def enclosure(nsplit):
        los, his = [], []
        for j in range(nsplit):
            a, b = j / nsplit, (j + 1) / nsplit
            mid, half = 0.5 * (a + b), 0.5 * (b - a)
            lo, hi = bd((half * (x1 - x0)).reshape(-1, 1), x0 + mid * (x1 - x0),
                        np.array([-1.0]), np.array([1.0]))
            los.append(lo)
            his.append(hi)
        return min(los), max(his)

    lo1, hi1 = enclosure(1)
    lo8, hi8 = enclosure(8)
    tol = 1e-6
    assert lo8 >= lo1 - tol, f"splitting loosened the lower bound: {lo1} -> {lo8}"
    assert hi8 <= hi1 + tol, f"splitting loosened the upper bound: {hi1} -> {hi8}"


def test_zero_width_disturbance_is_exact():
    """At x1 == x0 the set is a point, so the bound must collapse onto the true output.

    This is the degenerate case the `clear` ledger cell records as vacuous. If it does not
    collapse, the bounding path has a width-independent error term and every margin in the
    study is inflated by it.
    """
    torch, cc, student = _deps()
    net, x0, _ = _fixture(torch, student)
    bd = cc.Bounder(1, net, "cpu", H, W, method="CROWN")

    lo, hi = bd(np.zeros((3 * H * W, 1), np.float32), x0,
                np.array([-1.0]), np.array([1.0]))
    with torch.no_grad():
        true = float(net(torch.from_numpy(
            x0.reshape(1, 3, H, W))).numpy().reshape(-1)[0])

    assert hi - lo < 1e-4, f"point set gave a non-degenerate interval, width {hi - lo:.2e}"
    assert lo - 1e-4 <= true <= hi + 1e-4, f"{true} outside [{lo}, {hi}]"

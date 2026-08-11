"""The traps, as runnable checks.

Each test encodes a mistake that cost real time in the previous study (docs/TRAPS.md).
Tests whose subject does not exist yet SKIP with the trap named -- they become live the
moment the corresponding module lands, so a transplanted file cannot bring its bug back in
unnoticed.

Run: pytest conformance/ -v
"""

import importlib
import time

import numpy as np
import pytest

from study.goc import ALIGNMENT_THRESHOLD, NotAlignedError, goc, require_aligned


def _module(name):
    """Import a pipeline module, or skip if it has not been transplanted yet."""
    try:
        return importlib.import_module(f"pipeline.{name}")
    except ImportError:
        pytest.skip(f"pipeline.{name} not transplanted yet")


# --- trap 1: alignment before any paired photometric fit ----------------------------

def test_goc_separates_aligned_from_unaligned():
    rng = np.random.default_rng(0)
    img = rng.random((240, 320)).astype(np.float32)
    img = np.clip(img + np.linspace(0, 1, 320, dtype=np.float32)[None, :], 0, 1)
    mask = np.ones_like(img, dtype=bool)

    # A photometric change must NOT reduce alignment -- that is the whole point.
    darker = (img * 0.5 + 0.1).astype(np.float32)
    assert goc(img, darker, mask) > 0.9

    # A geometric shift must.
    shifted = np.roll(img, 17, axis=1)
    assert goc(img, shifted, mask) < 0.5


def test_goc_refuses_rather_than_warns():
    rng = np.random.default_rng(1)
    a = rng.random((240, 320)).astype(np.float32)
    b = rng.random((240, 320)).astype(np.float32)
    mask = np.ones_like(a, dtype=bool)

    with pytest.raises(NotAlignedError):
        require_aligned(a, b, mask, context="unrelated frames")

    assert require_aligned(a, a.copy(), mask) > ALIGNMENT_THRESHOLD


# --- trap 8: sound clamp modelling --------------------------------------------------

def test_two_relu_clamp_matches_numpy_clip():
    """clamp01(v) = 1 - relu(1 - relu(v)). Omitting it makes bright additive layers look
    linear when they are not."""
    def relu(x):
        return np.maximum(x, 0.0)

    v = np.random.default_rng(2).uniform(-2.0, 3.0, size=100_000)
    assert np.allclose(1.0 - relu(1.0 - relu(v)), np.clip(v, 0.0, 1.0))


# --- trap 12: probe delta must clear uint8 quantisation ------------------------------

def test_linearity_probe_delta_clears_quantisation():
    """delta = 0.01 amplifies a +/-1/255 rounding error by 100x. The probe delta must be
    large enough that quantisation cannot dominate the measured nonlinearity."""
    quantisation = 1.0 / 255.0
    module = _module("verifiable_disturbance")
    delta = getattr(module, "PROBE_DELTA", None)
    assert delta is not None, "verifiable_disturbance must declare PROBE_DELTA"
    assert delta >= 10 * quantisation, (
        f"PROBE_DELTA {delta} amplifies uint8 quantisation by {quantisation / delta:.0f}x"
    )


# --- trap 13: legacy rows survive condition filtering --------------------------------

def test_manifest_rows_without_condition_field_survive_filtering():
    """`r.get("weather") in keep` silently discarded 6,783 pre-tracking frames and
    surfaced much later as an unrelated crash. The bug was fixed in one filter site and
    missed in the other, so this asserts on every site."""
    module = _module("dataset")
    rows = [
        {"path": "a.png", "condition": "clear"},
        {"path": "b.png", "condition": "fog"},
        {"path": "c.png"},  # legacy row, predates condition tracking
    ]
    kept = module.filter_conditions(rows, keep={"clear", "fog"})
    assert len(kept) == 3, "legacy rows without a condition field must not be dropped"


# --- trap 6: corridor centred on clear-weather steering ------------------------------

def test_corridor_is_centred_on_clear_steering():
    """Centring on the disturbed midpoint certifies only insensitivity to the disturbance
    parameter while permitting an arbitrary offset from what clear weather would produce --
    which is the actual hazard. This bug made night read 100% certified while failing 85%
    of closed-loop frames."""
    module = _module("verify_v2")
    clear_steer = 0.30
    lower, upper = -0.05, 0.05  # a disturbed output range offset far from clear
    centre = module.corridor_centre(clear_steer=clear_steer, bounds=(lower, upper))
    assert centre == pytest.approx(clear_steer), (
        "corridor must centre on clear-weather steering, not the disturbed midpoint"
    )


# --- trap 7: the closed-loop tolerance is derived, not a literal ----------------------

def test_closed_loop_tolerance_is_derived_from_primitives():
    """The per-frame corridor (0.041) is ~3.4x too permissive -- a vehicle departed the
    road with every frame inside it. The tolerance that matters is the closed-loop
    stability cliff, and it must be derived from measured primitives so it cannot drift
    away from them."""
    config = _module("config")
    assert hasattr(config, "CLOSED_LOOP_TOLERANCE"), (
        "config must define CLOSED_LOOP_TOLERANCE"
    )
    source = importlib.import_module("inspect").getsource(config)
    for line in source.splitlines():
        if line.strip().startswith("CLOSED_LOOP_TOLERANCE"):
            assert "0.012" not in line, (
                "CLOSED_LOOP_TOLERANCE is a hardcoded literal; derive it from primitives"
            )


# --- trap 17: parallel dataset preload -----------------------------------------------

def test_dataset_preload_completes_within_time_bound():
    """Single-threaded preload of 67k frames takes >10 min and silently outlasts the
    training it precedes."""
    module = _module("dataset")
    start = time.monotonic()
    module.preload_smoke_test(n_frames=2000)
    assert time.monotonic() - start < 30.0, "preload is too slow; parallelise it"


# --- trap 9: disturbances apply at full sensor resolution ----------------------------

def test_disturbance_applies_before_crop_and_downsample():
    """Applying a disturbance to the network input makes the disturbance model
    network-specific and averages ~57 source pixels into each student pixel."""
    models = _module("disturbance_models")
    config = _module("config")
    full = np.zeros((config.CAM_HEIGHT, config.CAM_WIDTH, 3), dtype=np.float32)
    out = models.apply(full, condition="fog", theta=400.0)
    assert out.shape[:2] == (config.CAM_HEIGHT, config.CAM_WIDTH), (
        "disturbance must be applied at full sensor resolution, before crop/downsample"
    )


# --- trap 18: path defaults resolve inside this repo ---------------------------------

def test_path_defaults_do_not_point_outside_the_repo():
    """A default pointing at v1 directories trained a v2 student on stale data."""
    from pathlib import Path

    config = _module("config")
    repo = Path(__file__).resolve().parent.parent
    for name in dir(config):
        if not name.endswith(("_DIR", "_PATH", "_ROOT")):
            continue
        value = Path(str(getattr(config, name))).resolve()
        assert repo in value.parents or value == repo, (
            f"config.{name} = {value} resolves outside {repo}"
        )

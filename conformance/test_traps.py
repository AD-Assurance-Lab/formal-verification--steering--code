"""The traps, as runnable checks.

Each test encodes a mistake that cost real time in the previous study (docs/TRAPS.md).
Tests whose subject does not exist yet SKIP with the trap named -- they become live the
moment the corresponding module lands, so a transplanted file cannot bring its bug back in
unnoticed.

Run: pytest conformance/ -v
"""

import importlib

import numpy as np
import pytest

from study.goc import ALIGNMENT_THRESHOLD, NotAlignedError, goc, require_aligned


def _module(name):
    """Import a pipeline module, or skip if it has not been transplanted yet."""
    try:
        return importlib.import_module(name)
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

def test_dataset_preload_is_parallel():
    """Single-threaded preload of 67k frames takes >10 min and silently outlasts the
    training it precedes.

    Asserted structurally rather than by wall clock: a timing test needs a real dataset,
    would be flaky on a loaded machine, and the regression to catch is someone replacing
    the pool with a plain loop.
    """
    import inspect

    module = _module("dataset")
    source = inspect.getsource(module.SteeringDataset.__init__)
    assert "ProcessPoolExecutor" in source or "ThreadPoolExecutor" in source, (
        "SteeringDataset preload must be parallel"
    )


# --- trap 9: disturbances apply at full sensor resolution ----------------------------

def test_disturbance_applies_before_crop_and_downsample():
    """Applying a disturbance to the network input makes the disturbance model
    network-specific and averages ~57 source pixels into each student pixel."""
    models = _module("disturbance_models")
    config = _module("config")
    full = np.full((config.CAM_HEIGHT, config.CAM_WIDTH, 3), 0.4, dtype=np.float32)
    for name in ("apply_fog", "apply_rain", "apply_night"):
        fn = getattr(models, name, None)
        assert fn is not None, f"disturbance_models must expose {name}"
        out = fn(full)
        assert out.shape[:2] == (config.CAM_HEIGHT, config.CAM_WIDTH), (
            f"{name} must apply at full sensor resolution "
            f"({config.CAM_HEIGHT}x{config.CAM_WIDTH}), before crop/downsample; "
            f"got {out.shape[:2]}"
        )


# --- presets must be order-independent and single-axis --------------------------------

def test_each_condition_moves_exactly_one_axis():
    """One axis per condition, and nothing inherited from whatever ran before.

    This failed in the worst possible way: presets were built by reading the live weather
    and editing it, but `world.set_weather()` applies on the NEXT TICK, so the read-back
    returned the PREVIOUS condition's values. Clearing fog then setting the sun angle
    reinstated fog, and night ran at fog_density 70 -- verified live as
    sun_altitude_angle -25 with fog_density 70. Nothing errored; it was caught by eye,
    watching the render.
    """
    env = _module("carla_env")

    signatures = {
        "fog": ("fog_density", lambda v: v > 0),
        "rain": ("precipitation", lambda v: v > 0),
        "night": ("sun_altitude_angle", lambda v: v < 0),
        "shadows": ("sun_altitude_angle", lambda v: 0 < v < 45),
    }
    for name in ("clear", "fog", "rain", "night", "shadows"):
        w = env.weather_params(name)
        for other, (field, is_active) in signatures.items():
            active = is_active(getattr(w, field))
            if other == name:
                assert active, f"{name} must set its own axis ({field})"
            else:
                assert not active, (
                    f"condition '{name}' has {other}'s axis active: {field}="
                    f"{getattr(w, field)}"
                )


def test_presets_are_independent_of_call_order():
    """weather_params must read no live state, so any order gives identical results."""
    env = _module("carla_env")
    fields = ("fog_density", "fog_distance", "fog_falloff", "precipitation",
              "precipitation_deposits", "wetness", "sun_altitude_angle", "cloudiness")

    def snapshot(name):
        w = env.weather_params(name)
        return tuple(round(float(getattr(w, f)), 6) for f in fields)

    direct = snapshot("night")
    for prior in ("fog", "rain", "shadows", "clear"):
        snapshot(prior)
        assert snapshot("night") == direct, f"night differs after building {prior}"


# --- condition switching must carry the declared exposure ----------------------------

def test_condition_switches_use_set_condition_not_set_weather():
    """Exposure is declared per condition (F5) and is a CARLA blueprint attribute, so the
    camera must be respawned on a condition change. `env.set_weather` alone leaves the
    previous condition's exposure in place -- silently, since the frames look plausible.

    This happened: collect_data, dagger and evaluate were converted and dagger_student was
    missed, so student-DAgger captured night through the DAYLIGHT exposure. That is trap
    13's lesson (grep every call site when fixing a bug like this) applied to a different
    bug, which is why it is asserted rather than remembered.
    """
    import re
    from pathlib import Path

    pipeline = Path(__file__).resolve().parent.parent / "pipeline"
    # carla_env defines both, and set_condition legitimately calls set_weather.
    offenders = []
    for path in sorted(pipeline.glob("*.py")):
        if path.name == "carla_env.py":
            continue
        for i, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#")[0]
            if re.search(r"\benv\.set_weather\s*\(", code):
                offenders.append(f"{path.name}:{i}")
    assert not offenders, (
        "call env.set_condition() instead of env.set_weather() at: " + ", ".join(offenders)
    )


# --- trap 2: capture must match on frame id ------------------------------------------

def test_no_bare_queue_get_outside_carla_env():
    """A drive loop must consume frames via grab_frame, never a bare queue.get().

    The bare pattern is correct while it works and silently wrong the moment it does not:

        world.tick()
        try:    image = img_queue.get(timeout=2.0)
        except: continue          # <- one timeout desyncs the queue permanently

    After a single timeout the loop ticks again with that frame still queued, and every
    subsequent get() returns the PREVIOUS frame -- pairing image[t-1] with pose[t] for
    the rest of the lap, at 1.79 m of error, with nothing logged and every frame looking
    plausible.
    """
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent
    offenders = []
    for path in sorted(list((repo / "pipeline").glob("*.py"))
                       + list((repo / "scripts").glob("*.py"))):
        if path.name == "carla_env.py":     # defines grab_frame and drain_frame
            continue
        for i, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#")[0]
            if re.search(r"_queue\.get\s*\(", code):
                offenders.append(f"{path.name}:{i}")
    assert not offenders, (
        "use env.grab_frame() (or env.drain_frame() if the image is discarded) at: "
        + ", ".join(offenders)
    )


# --- trap 17b: the OTHER preload path ------------------------------------------------

def test_kd_dataset_preload_is_parallel():
    """`dataset.SteeringDataset` was parallelised and `distill.KDDataset` was not, so the
    original trap-17 test passed while the actual bottleneck sat uncovered in a second
    class -- the same two-implementations problem as trap 13. KDDataset preloads 83,567
    frames single-threaded on every distill run.
    """
    import inspect

    module = _module("distill")
    source = inspect.getsource(module.KDDataset.__init__)
    assert "ProcessPoolExecutor" in source or "ThreadPoolExecutor" in source, (
        "KDDataset preload must be parallel"
    )


# --- trap 18: path defaults resolve inside this repo ---------------------------------

def test_path_defaults_do_not_point_outside_the_repo():
    """A default pointing at v1 directories trained a v2 student on stale data."""
    from pathlib import Path

    # Paths to externally installed tools are legitimately outside the repo.
    # Anything the pipeline *writes* is not.
    EXTERNAL = {"CARLA_ROOT"}

    config = _module("config")
    repo = Path(__file__).resolve().parent.parent
    checked = 0
    for name in dir(config):
        if not name.endswith(("_DIR", "_PATH", "_ROOT")) or name in EXTERNAL:
            continue
        value = Path(str(getattr(config, name))).resolve()
        assert repo in value.parents or value == repo, (
            f"config.{name} = {value} resolves outside {repo}"
        )
        checked += 1
    assert checked > 0, "no output paths found in config -- has it been renamed?"

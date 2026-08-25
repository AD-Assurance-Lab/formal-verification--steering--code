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

def test_pipeline_clamp_is_two_relus_and_matches_clip():
    """clamp01(v) = 1 - relu(1 - relu(v)). Omitting it makes bright additive layers look
    linear when they are not.

    This used to verify the numpy identity alone, which can never fail and did not touch
    the pipeline -- removing the clamp from the verified maps would still have passed.
    Assert on the actual module the pipeline uses, and that the verified maps use it.
    """
    import inspect

    import torch

    perturbations = _module("perturbations")
    clamp = perturbations.Clamp01()
    v = torch.from_numpy(
        np.random.default_rng(2).uniform(-2.0, 3.0, size=100_000).astype(np.float32))
    # atol 1e-6: `1 - relu(1 - x)` rounds at float32 (measured max 3e-8), and the
    # default allclose atol of 1e-8 is tighter than float32 itself.
    assert torch.allclose(clamp(v), torch.clamp(v, 0.0, 1.0), atol=1e-6), (
        "Clamp01 does not equal clip to [0,1]"
    )
    # Bound propagators need ReLU-only structure, not a clamp op.
    src = inspect.getsource(perturbations.Clamp01)
    assert src.count("ReLU") >= 2, "Clamp01 must be expressed as two ReLUs"

    vd = _module("verifiable_disturbance")
    vd_src = inspect.getsource(vd)
    assert "Clamp01" in vd_src, (
        "verifiable_disturbance no longer uses Clamp01 -- saturation must live inside "
        "the verified network (trap 8)"
    )


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
    of closed-loop frames.

    This test previously imported a module named `verify_v2` that never existed in this
    repo, so it skipped forever while claiming coverage -- the study's headline defense
    had no regression guard. The live corridor sits in scripts/certify_cell.py, whose
    import cost (auto_LiRPA, CUDA) makes a behavioural test impractical here, so assert
    the construction statically: the corridor must be built symmetrically around the
    output of clear_steer(), and nothing may centre it on a bound midpoint."""
    import re
    from pathlib import Path

    src = (Path(__file__).resolve().parent.parent / "scripts" /
           "certify_cell.py").read_text()
    assert re.search(r"\bcs\s*=\s*clear_steer\s*\(", src), (
        "certify_cell must compute the clear-weather steering (clear_steer)"
    )
    assert re.search(r"corridor\s*=\s*\(\s*cs\s*-\s*tol\s*,\s*cs\s*\+\s*tol\s*\)", src), (
        "certify_cell's corridor must be (cs - tol, cs + tol), centred on the "
        "clear-weather steering -- not on the disturbed bound midpoint (trap 6)"
    )
    assert not re.search(r"corridor\s*=\s*\(\s*\(\s*lo\s*\+\s*hi\s*\)", src), (
        "a corridor centred on (lo+hi)/2 has reintroduced trap 6"
    )


# --- trap 7: the closed-loop tolerance is derived, not a literal ----------------------

def test_closed_loop_tolerance_tracks_the_geometry_it_is_written_in():
    """The tolerance must MOVE when lane or vehicle geometry moves.

    This test used to assert only that the string "0.012" did not appear on the
    CLOSED_LOOP_TOLERANCE line, and called that "derived, not a literal". It passed while
    the property did not hold: the measured cliff is laundered through a square root one
    line above, as `T = 1.0 * sqrt(0.041/0.012) = 1.85`, so the literal was still there,
    just spelled differently. A test that can be satisfied by renaming is not a test.

    What actually matters is the property the comment claims -- that if lane width or
    vehicle width changes, the tolerance follows -- so assert that directly by perturbing
    the primitives and recomputing.
    """
    config = _module("config")
    assert hasattr(config, "CLOSED_LOOP_TOLERANCE")

    def tol(lane_w, veh_w, wheelbase, speed, T, max_steer):
        budget = (lane_w - veh_w) / 2.0
        return (2.0 * wheelbase * budget) / (speed ** 2 * T ** 2) / max_steer

    args = (config.LANE_WIDTH_M, config.VEHICLE_WIDTH_M, config.WHEELBASE_M,
            config.TARGET_SPEED_MS, config.T_CLOSED_LOOP_S, config.MAX_STEER_RAD)
    assert abs(tol(*args) - config.CLOSED_LOOP_TOLERANCE) < 1e-12, (
        "CLOSED_LOOP_TOLERANCE does not equal the formula it claims to come from"
    )

    # A wider lane means more room, so a larger admissible bias. A wider vehicle, less.
    wider_lane = tol(config.LANE_WIDTH_M + 0.5, *args[1:])
    wider_car = tol(args[0], config.VEHICLE_WIDTH_M + 0.5, *args[2:])
    assert wider_lane > config.CLOSED_LOOP_TOLERANCE, "tolerance ignores lane width"
    assert wider_car < config.CLOSED_LOOP_TOLERANCE, "tolerance ignores vehicle width"


def test_the_calibrated_horizon_is_labelled_as_calibrated():
    """T_CLOSED_LOOP_S is fitted on the closed-loop runs the certificate is validated
    against (F45). It is legitimate to use it; it is not legitimate to call the criterion
    unfitted. Guard the disclosure, because the claim outlived the correction twice.
    """
    config = _module("config")
    assert hasattr(config, "T_CLOSED_LOOP_ADMISSIBLE_S"), (
        "config must publish the range of T over which the verdicts hold"
    )
    lo, hi = config.T_CLOSED_LOOP_ADMISSIBLE_S
    assert lo < config.T_CLOSED_LOOP_S < hi, "T in use is outside its own admissible window"

    source = importlib.import_module("inspect").getsource(config)
    line = next(l for l in source.splitlines()
                if l.strip().startswith("T_CLOSED_LOOP_S"))
    assert "CALIBRATED" in line.upper(), (
        "T_CLOSED_LOOP_S must be labelled CALIBRATED, not MEASURED or derived: it is "
        "back-solved from the validation data"
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
            # The original pattern matched only variables literally named `*_queue`,
            # so a queue named `q` slipped past. A `.get(timeout=...)` is the
            # signature of a sensor-queue read regardless of the variable name;
            # dict .get() calls never take a timeout kwarg.
            if re.search(r"_queue\.get\s*\(|\.get\s*\(\s*timeout\s*=", code):
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


# --- read-modify-write weather: the bug that invalidated F3 ---------------------------

def test_no_get_weather_outside_carla_env():
    """`world.get_weather()` next to a write returns the PREVIOUS tick's weather, so any
    read-modify-write silently builds on stale state. This survived in
    scripts/fog_isolation.py (since deleted) long after the pipeline was fixed, because
    the old scan covered pipeline/ only and looked for env.set_weather, not the read.
    Weather is CONSTRUCTED (env.weather_params); nothing reads it back."""
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent
    offenders = []
    for path in sorted(list((repo / "pipeline").glob("*.py"))
                       + list((repo / "scripts").glob("*.py"))):
        if path.name == "carla_env.py":
            continue
        for i, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#")[0]
            if re.search(r"\.get_weather\s*\(", code):
                offenders.append(f"{path.name}:{i}")
    assert not offenders, (
        "construct weather with env.weather_params(); never read it back: "
        + ", ".join(offenders)
    )


# --- hand-rolled sync settings: under-provisioned substepping -------------------------

def test_sync_mode_is_only_configured_in_carla_env():
    """enable_sync_mode provisions bounded substepping
    (fixed_delta_seconds <= max_substep_delta_time * max_substeps). Two capture scripts
    hand-rolled `settings.synchronous_mode = True` without it and ran 0.1 s of physics
    per 0.2 s tick -- different physics than the driving pipeline, feeding verification.
    Every entry point must go through env.enable_sync_mode."""
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent
    offenders = []
    for path in sorted(list((repo / "pipeline").glob("*.py"))
                       + list((repo / "scripts").glob("*.py"))):
        if path.name == "carla_env.py":
            continue
        for i, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#")[0]
            if re.search(r"\.synchronous_mode\s*=", code):
                offenders.append(f"{path.name}:{i}")
    assert not offenders, (
        "use env.enable_sync_mode(world) instead of setting synchronous_mode by hand "
        "(substepping must be provisioned with it): " + ", ".join(offenders)
    )


# --- every CARLA client takes the lock ------------------------------------------------

def test_every_carla_entry_point_takes_the_lock():
    """Two synchronous clients on one port interleave ticks and silently corrupt each
    other's runs (a fake 20.69 ft departure in a ledger cell -- see carla_lock.py).
    An advisory lock protects only if every client participates in both directions,
    and at audit time only 3 of ~10 entry points did."""
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent
    # build_routes only reads the map: no sync mode, no ticking, no actors.
    EXEMPT = {"carla_env.py", "carla_lock.py", "build_routes.py"}
    offenders = []
    for path in sorted(list((repo / "pipeline").glob("*.py"))
                       + list((repo / "scripts").glob("*.py"))):
        if path.name in EXEMPT:
            continue
        text = path.read_text()
        uses_carla = re.search(r"env\.connect\s*\(|carla\.Client\s*\(", text)
        if uses_carla and "carla_lock" not in text:
            offenders.append(path.name)
    assert not offenders, (
        "these connect to CARLA without taking carla_lock: " + ", ".join(offenders)
    )


# --- trap 19: headlights follow the sun -----------------------------------------------

def test_headlights_follow_the_sun_not_the_preset_name():
    """v1 drove at night with headlights off, which is physically impossible and made
    every night result an artefact of the setup. The rule is keyed off the constructed
    sun altitude so swept angles stay physical."""
    env = _module("carla_env")
    assert hasattr(env, "headlights_on"), (
        "carla_env must expose the headlight rule as a pure function"
    )
    for name, lit in (("clear", False), ("shadows", False), ("night", True)):
        w = env.weather_params(name)
        assert env.headlights_on(w.sun_altitude_angle) == lit, (
            f"{name} (sun {w.sun_altitude_angle}) must have headlights "
            f"{'ON' if lit else 'OFF'}"
        )
    # Swept angles: -10 is below the horizon regardless of the preset carrying it.
    assert env.headlights_on(-10.0) and not env.headlights_on(+8.0)


# --- the pre-registered expectation table is pinned -----------------------------------

def test_expectation_table_is_pinned():
    """`design.expected()` is the pre-registration. A retro-edit of one line would turn
    a red cell green everywhere at once, and nothing checked it. This is the full
    20-cell table as a golden constant; changing the design now requires changing this
    test in the same commit, which is exactly the visibility an amendment should have."""
    from study.design import expected

    GOLDEN = {
        ("clear", "S_clear", "closed_loop"): "PASS",
        ("clear", "S_clear", "verify"): "CERTIFIED",
        ("clear", "S_mixed", "closed_loop"): "PASS",
        ("clear", "S_mixed", "verify"): "CERTIFIED",
        ("night", "S_clear", "closed_loop"): "FAIL",
        ("night", "S_clear", "verify"): "FALSIFIED",
        ("night", "S_mixed", "closed_loop"): "PASS",
        ("night", "S_mixed", "verify"): "CERTIFIED",
        ("fog", "S_clear", "closed_loop"): "FAIL",
        ("fog", "S_clear", "verify"): "FALSIFIED",
        ("fog", "S_mixed", "closed_loop"): "PASS",
        ("fog", "S_mixed", "verify"): "CERTIFIED",
        ("shadows", "S_clear", "closed_loop"): "FAIL",
        ("shadows", "S_clear", "verify"): "FALSIFIED",
        ("shadows", "S_mixed", "closed_loop"): "PASS",
        ("shadows", "S_mixed", "verify"): "CERTIFIED",
        ("rain", "S_clear", "closed_loop"): "FAIL",
        ("rain", "S_clear", "verify"): "FALSIFIED",
        ("rain", "S_mixed", "closed_loop"): "PASS",
        ("rain", "S_mixed", "verify"): "CERTIFIED",
    }
    for (cond, student, instrument), want in GOLDEN.items():
        got = expected(student, cond, instrument)
        assert got == want, (
            f"expected({student}, {cond}, {instrument}) = {got!r}, pre-registered "
            f"{want!r}. If this is a deliberate amendment, update the golden table in "
            f"the SAME commit and record why."
        )


def test_final_campaign_cells_are_registered_and_distinct():
    """FINAL_CLOSED_LOOP must cover every (condition, student) pair exactly once; a
    missing pair silently drops a cell from the final-campaign smell test."""
    from study.design import CONDITIONS, FINAL_CLOSED_LOOP, STUDENTS

    pairs = {(c.name, s) for c in CONDITIONS if c.status != "out_of_scope"
             for s in STUDENTS}
    assert set(FINAL_CLOSED_LOOP) == pairs, (
        "FINAL_CLOSED_LOOP does not cover the design's cells exactly"
    )
    stems = list(FINAL_CLOSED_LOOP.values())
    assert len(stems) == len(set(stems)), "two pairs share one final cell file"

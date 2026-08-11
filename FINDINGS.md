# Findings

Measured results, newest first. **Keep this short.** The previous generation's log grew
to 1,266 chronological entries containing claims later withdrawn, and it crowded out the
current state. If a finding is superseded, *edit it in place* and say so — do not append a
correction below and leave the original standing.

Ledger cells live in `results/ledger/` and are checked by `python -m study.ledger`. This
file is for characterization measurements, which are not ledger cells.

---

## F4. Fixed exposure across conditions is required by the method and is unrealistic as a camera

**Status: design note, with the tension stated rather than resolved. Watch item for M2/M3.**

A real automotive camera auto-exposes; it does not hold one exposure across a 10^4:1
illuminance range. We pin exposure anyway, and must, because the night disturbance model
is `x' = g*x0 + c*H` where `g` is the illuminance ratio. Under auto-exposure `g` is
absorbed by the exposure loop and becomes unmeasurable -- which is precisely the ACDC
failure (F1) and precisely why the previous night model came out inverted.

**So the choice is forced:** a certificate indexed by a physical illuminance requires that
illuminance to survive into the image, and auto-exposure destroys it.

Measured consequence at the chosen exposure (20 poses):

| condition | road mu | road sigma |
|---|---|---|
| clear | 0.290 | 0.0854 |
| night | 0.042 | 0.0580 |

Night sits at ~11/255. `sigma > mu` there, so structure survives -- the headlight-lit
region carries real signal -- but it is a marginal operating point for an 8-bit sensor and
is the most likely place for the mixed policy to struggle.

**What to state in the paper**, since a reviewer will raise it: the fixed exposure is a
*modelling commitment*, not an oversight. It makes the disturbance identifiable at the cost
of realism in the sensor's auto-exposure behaviour, and it bounds the claim to "a camera
with known, fixed response". Modelling auto-exposure as part of the disturbance is possible
in principle -- it is another parameter in `phi` -- and is out of scope here.

**If night training fails at M2/M3**, the options in order are: raise ISO for a
night-specific fixed exposure (still fixed, still identifiable, but then the exposure is
condition-dependent and must be declared), or accept the failure as a genuine ODD boundary.
Do not reach for auto-exposure.

## F3. CARLA's fog is not a constant-airlight veil at the pooled-ROI level

**Status: partial early answer to E8. Not conclusive — needs the depth-resolved fit (D4).**

`scripts/fog_isolation.py`, 20 poses, manual exposure, clear illumination held fixed
(cloudiness 80, sun_altitude 90), only `fog_density` varied:

| `fog_density` | road mu | d_mu | sigma ratio |
|---|---|---|---|
| 0 | 0.290 | — | 1.00 |
| 10 | 0.300 | **+0.010** | 0.86 |
| 25 | 0.314 | **+0.024** | 0.74 |
| 40 | 0.262 | −0.028 | 0.67 |
| 55 | 0.254 | −0.036 | 0.71 |
| 70 | 0.266 | −0.024 | 0.72 |
| 85 | 0.276 | −0.014 | 0.74 |
| 100 | 0.285 | −0.005 | 0.75 |

Contrast falls monotonically to density 40 and then recovers slightly. The mean
**brightens** at low density — consistent with airlight on a road darker than the
airlight, which is what Koschmieder predicts and is a good sign — then **turns around**
and darkens.

**Reading, with the caveat stated first.** Pooled ROI statistics are exactly what hid the
previous generation's identifiability failure, where near depth bands fit at R^2 = 0.91
with a physically impossible negative airlight while far bands fit at R^2 = 0.18. The ROI
spans a wide depth range and the turnaround could be near pixels darkening while far
pixels brighten. **Do not conclude from this table alone.**

That said, the shape is what you would expect if the renderer models fog as both adding
airlight *and* attenuating the illumination reaching the ground. Both are physical, but
together they mean **the airlight A is not constant across severities**, which is an
assumption Koschmieder makes and which the disturbance model inherits. That would explain
directly why A was unidentifiable in the previous generation.

**Next:** the per-pixel depth fit (D4). Fit `(beta, A)` independently at each density with
ground-truth depth and check whether A drifts. That is the pre-registered E8 test and it
is now the highest-value measurement available.

## F2. The inherited fog and rain presets confounded their own axis with the sun angle

**Status: fixed.**

`set_weather` inherited from the previous generation moved three fields at once:

    fog:   cloudiness 80->90, sun_altitude 90->45, fog_density 0->70
    rain:  cloudiness 80->90, sun_altitude 90->40, precipitation 0->85

against a clear baseline of cloudiness 80, sun_altitude 90. So every clear-vs-fog
measurement conflated fog scattering with a lower sun and heavier cloud.

**Magnitude:** at `fog_density = 70`, the old preset moved the road ROI mean by **−0.060**;
with illumination held fixed it moves by **−0.024**. Over half the apparent darkening was
the sun angle.

This violated the design rule in `CLAUDE.md` (one axis per condition, shared by training,
closed-loop testing and verification). `set_weather` now restores the full clear baseline
and moves exactly one axis, and a `shadows` preset was added on the solar-elevation axis.

**Open design question:** night and shadows are *the same physical knob* — solar elevation
— at different ranges (−25 deg vs +15 deg). They may be one condition on one continuous
axis from noon through dusk to night, or two conditions sharing an axis with different
disturbance-model forms (global dimming vs a spatially-varying shadow mask). Not decided.

## F1. The washed-out road and night's contrast inversion were auto-exposure artifacts

**Status: D1 diagnosis confirmed for night. Exposure fixed and pinned in `config.py`.**

`scripts/calibrate_exposure.py`, 20 poses. The previous generation left
`sensor.camera.rgb` with only `image_size` and `fov` set, so CARLA's default per-frame
histogram auto-exposure was active for every capture.

**Auto-exposure (the inherited configuration):**

| condition | road mu | road sigma |
|---|---|---|
| clear | 0.703 | 0.1226 |
| fog | 0.644 | 0.0649 |
| night | 0.270 | 0.1778 |

Clear road at **0.703** where a real road is ~0.31, under a flat overhead sun at
cloudiness 80 — diffuse light with no strong highlights, which should not wash out a road
surface. (The previous generation reported 0.81 for this quantity; the difference is the
preset, which was `ClearNoon` there and the flat preset here. The phenomenon reproduces;
the exact value does not.)

**Manual exposure**, swept over shutter/aperture at ISO 100. `shutter=800, f/2.8` and
`shutter=200, f/5.6` give identical results — they sit at the same exposure value, which
is a useful check that CARLA's photographic model behaves. Chosen setting puts the clear
road at **mu = 0.290, sigma = 0.0854**, inside the real-camera target [0.28, 0.34].

**E7 — CONFIRMED.** Night's contrast ratio versus clear:

    auto-exposure   1.45x   (contrast RISES as the scene darkens)
    manual          0.68x   (contrast falls, which is physical)

Contrast rising as a scene darkens was never physical. It was the auto-exposure loop
re-normalizing each frame after the weather was rendered — the same defect that
disqualified ACDC for photometry, present in the instrument and never checked. **This is
why the night disturbance model failed the fidelity gate "inverted".** The previous
generation measured a 2.1–3.7x rise; direction reproduces, magnitude differs with the
preset.

**Outstanding:** `TARGET_ROAD_SIGMA_RATIO` cannot be checked yet — the real-road sigma
reference has not been measured from ACDC. Only the mu criterion is currently enforced.

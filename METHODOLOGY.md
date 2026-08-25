# Methodology

**Living document.** The source of truth for what was actually done and measured, written
so the paper's Methodology section can be derived from it rather than reconstructed. Every
number here is measured; anything unmeasured says so.

Section order mirrors the intended paper structure. Sections marked *(pending)* are gated
on M5/M6.

---

## 1. Simulator instrumentation

*This section is a contribution, not preamble.* Three configuration defects were found in
the inherited setup, each of which silently corrupts photometric measurement, and each of
which produced a plausible-looking result that would have been published as a finding.
Anyone doing perception studies in CARLA is exposed to all three.

### 1.1 The camera must not auto-expose

CARLA's `sensor.camera.rgb` defaults to `exposure_mode='histogram'` -- per-frame histogram
auto-exposure. The inherited code set only `image_size_x/y` and `fov`, so every capture in
the previous generation passed through an uncontrolled exposure loop.

This is the same defect that disqualifies real adverse-weather datasets (ACDC) for
photometric calibration: auto-exposure re-normalizes each frame *after* the weather is
rendered, destroying the absolute levels a disturbance model is calibrated against. It was
diagnosed in the dataset and never checked in the instrument.

Measured effect, 20 poses, road ROI:

| | clear mu | night sigma / clear sigma |
|---|---|---|
| auto-exposure | 0.703 | **1.45x (contrast RISES as the scene darkens)** |
| manual exposure | 0.290 | 0.68x (contrast falls, as physics requires) |

Contrast rising as a scene darkens is not physical. **This artifact is why the previous
generation's night disturbance model failed its fidelity gate "inverted"** -- the model was
being compared against an exposure loop, not against night.

### 1.2 Exposure must be declared per condition

No single exposure spans the illuminance axis. Measured over 12 poses:

| shutter | clear road mu | night road clipped to 0 |
|---|---|---|
| 800 | 0.291 (in real-camera range) | **50.6%** |
| 200 | 0.601 | 12.5% |
| 25 | 0.938 (washed out) | 0.5% |

Clearing the clipping bound requires an exposure that washes the clear road out to 0.938,
which is the regime that made the previous generation's fog airlight unidentifiable. So
exposure is a **declared function of condition**: daylight at shutter 800, night at 200.

*What this costs, and the paper must state it.* The certificate reads "certified at X lux
**with the camera exposing as declared**". The night disturbance's gain carries the
exposure ratio as a known factor alongside the illuminance ratio -- both known because we
set them, so identifiability survives. A declared function is not auto-exposure; an
auto-exposure loop is opaque and destroys the mapping.

*Consequence, measured:* at the single global exposure the mixed teacher failed night in
all 6 DAgger rounds with `max|CTE|` up to 44 ft, clustered at one curve. With exposure
declared per condition and nothing else changed, it passes at 0.76 / 0.57 ft. **The
failure was the sensor configuration, not the policy.**

### 1.3 Presets must be constructed, not read-modify-written

`world.set_weather()` is applied by the simulator on the **next tick**, so
`world.get_weather()` issued immediately after returns the *previous* condition's values.
Building a preset by clearing the old condition and editing the read-back therefore
reinstates whatever was cleared. Verified live: night running at `sun_altitude_angle = -25`
**and** `fog_density = 70` simultaneously.

Presets are now built by constructing a fresh `WeatherParameters` and setting every field
explicitly from a baseline plus a single-axis delta. Order-independence becomes structural
rather than a property to be maintained.

### 1.4 The general rule

> A read or a placement issued next to a write does not see that write.

Four instances in this project, all silent, all the same next-tick semantics: the sensor
queue delivering the previous frame; weather presets reinstating cleared fields; the
spectator camera placed 1.79 m behind every frame; and a swallowed queue timeout pairing
`image[t-1]` with `pose[t]` for the rest of a lap. Sensor frames are now matched on the id
`world.tick()` returns, and a missing frame raises rather than being skipped.

---

## 2. Scenario, vehicle and route

Town04 highway loop, 3,042 m, traced once and cached as a fixed reference centreline
(immune to CARLA's lane-snapping). Tesla Model 3. Fixed 20 mph via a physics-honest PI
throttle/brake controller -- never a velocity override, which corrupts the lateral dynamics
CTE measures. Simulation at 5 Hz (`FIXED_DT = 0.2 s`) in synchronous mode.

Labels come from pure pursuit on the fixed centreline, not the CARLA autopilot, which
oscillates and would be cloned. Oracle verification: **max|CTE| 0.045 m eastbound and
0.041 m westbound against a 0.668 m budget, 0% over budget** -- a 15x margin, so the label
source is not a limiting factor.

## 3. Safety criteria, derived from measured primitives

Nothing here is a chosen constant; all derive from geometry and dynamics in `config.py`.

| quantity | value | derivation |
|---|---|---|
| CTE budget | 0.668 m (2.19 ft) | (lane 3.500 − vehicle 2.164) / 2 |
| per-frame steering corridor | 0.041 normalized | 2·L·CTE / (v²T²), T = 1 s |
| closed-loop tolerance | 0.0120 normalized | same relation at the measured bias horizon T = 1.85 s |

The per-frame corridor is **~3.4x too permissive** as a certification target: a vehicle
departed the road with every frame inside it. Certification uses the closed-loop tolerance,
expressed as an equivalent bias horizon so it tracks the geometry rather than being a
literal.

## 4. Conditions and their axes

Each condition moves exactly one physical axis off the clear baseline, and the same axis is
shared by training, closed-loop testing and verification. If those three disagree about
what a disturbance *is*, the study's central comparison is meaningless -- which is the
leading explanation for the previous generation's unresolved anomaly, where a student
trained on affine photometric boxes was verified against a Koschmieder fog model.

| condition | parameter | range | CARLA control |
|---|---|---|---|
| night | road illuminance (lux) | 10^4 -> 10 | `sun_altitude_angle` below horizon + headlights |
| fog | meteorological optical range (m) | 2000 -> 60 | `fog_density` |
| shadows | solar elevation (deg) | 60 -> 10 | `sun_altitude_angle` above horizon |

Snow is out of scope: CARLA renders none. Rain is out of scope: its rendering is
temporally stochastic, which the two-endpoint family cannot represent (see the
method-scope notes at the end of this file).

Baseline is flat and shadowless (`cloudiness 80`, `sun_altitude 90`) rather than
`ClearNoon`. This is deliberate: `ClearNoon`'s 45-degree sun casts shadows that made the
clear teacher depart the lane at 33.54 ft CTE where it otherwise held 0.43 ft. Shadows are
a studied condition, not a property of the baseline.

## 5. Policy pipeline

Behaviour cloning -> teacher DAgger -> knowledge distillation -> student DAgger, run
identically for both arms.

**Behaviour cloning alone never drives a full lap**, and this is not a tuning failure:
errors compound off the expert's state distribution. Measured -- the clear BC teacher
reached val RMSE 0.0042, comfortably inside the 0.0120 closed-loop tolerance, and still
departed the lane at step 1233 of ~1700. Offline loss and closed-loop competence are
different axes, which is a small argument for the study's own thesis.

DAgger requires three things the naive form lacks, each measured: warm start (from-scratch
retraining diverges on multi-condition data), beta-mixing (without it a weak policy departs
at step ~30 and a round collects ~30 frames instead of ~1700), and per-lap manifest
checkpointing (so an interrupted round is salvageable rather than silently degrading to
repeated behaviour cloning).

Teacher results on the clean data:

| teacher | rounds to converge | max\|CTE\| per condition |
|---|---|---|
| clear | 4 | 1.04 / 1.47 ft |
| mixed | *(pending rerun)* | previously 0.51-0.92 ft across all four |

### 5.1 The two arms must have identical architecture

`S_clear` and `S_mixed` differ **only** in training data -- same resolution, channel widths,
FC width, ReLU count. The previous generation's headline anomaly (a disturbance-trained
student certifying *worse* than the clear-only one) has two candidate causes that were
never separated, and one is that the disturbance-trained student was 2x width: 10,304 ReLU
against 5,152, with an UNKNOWN rate of 11.5% against 1.5%. Holding architecture equal
eliminates that by construction.

Capacity is not the binding constraint at four conditions. Width sweep, KD val RMSE:
1x 0.0338, 2x 0.0372, 3x 0.0327, 4x 0.0314 -- quadrupling the neurons buys 7%,
non-monotone. **KD RMSE is also a poor proxy for closed-loop competence**: 4x width barely
moved it while flipping a direction from failing to passing at 1.4 ft.

## 6. Closed-loop protocol

Every closed-loop number is a **failure rate over >= 10 repetitions with a Wilson 95%
interval**, never a single run. Near the stability cliff a single run gives the wrong
verdict roughly 1 in 8 times. A cell fails when the interval excludes zero, so one
departure in twenty laps is not a pass and a rate consistent with zero is not evidence of
failure.

A PASS at n = 20 bounds the failure rate below ~16%, not to zero; bounding below 5% needs
n ~ 60. Report it that way.

CARLA is relaunched before every measurement run: it leaks ~10.5 GiB over 11 h and degrades
results long before it crashes.

## 7. Verification

alpha-CROWN with input-space branch-and-bound over a low-dimensional physical parameter,
via upstream `auto_LiRPA`. **Not SDP-CROWN**: it is gated on an L2 ball, and with L-inf it
silently degrades to alpha-CROWN -- a previously published "SDP-CROWN" result was an
alpha-CROWN result. Given an L2 ball it explodes, because the library tracks a scalar
radius that cannot represent a low-rank ellipse.

Mandatory cross-checks, run before any certificate (`scripts/verify_smoke.py`), on
`S_clear_84x28` at 5,152 ReLU:

| check | result |
|---|---|
| zero perturbation returns nominal | `[+0.069682, +0.069682]` exact |
| bounds contain a concrete sample | `[-0.119838, +0.301609]` contains `[+0.059238, +0.078655]` |
| IBP >= CROWN >= alpha-CROWN | 9.358629 >= 0.421448 >= 0.381512 |

### 7.1 Why pixel-space verification is not usable

At a pixel-space L-inf ball of **eps = 1/255 -- one grey level** -- over 7,056 input
dimensions, alpha-CROWN returns a bound of width **0.381512** against a closed-loop
tolerance of **0.0120**. That is **31.8x too loose to certify anything**, at the smallest
perturbation an 8-bit sensor can represent.

This is the baseline the physical parameterization has to beat, and it is the quantitative
form of the paper's central technical argument: tractability comes from `theta` being
low-dimensional, not from the choice of verifier.

### 7.2 Disturbance models *(pending -- M5)*

See `docs/DISTURBANCE_MATH.md` for the derivation template. Constants are calibrated from
pose-matched CARLA capture with ground-truth depth; the linearity probe over all four
conditions is the gating measurement and has not yet run.

## 8. Threats to validity

1. **Image formation is CARLA's.** The parameters are real, the rendering is not. The
   certificate is *indexed* by a real-world quantity; we do not claim CARLA's fog at 85 m
   MOR looks like real fog at 85 m MOR.
2. **Closed loop is not independent of verification.** They share a parameterization by
   design; they are independent in *mechanism* (bound propagation vs rollout), not setup.
3. **Fixed per-condition exposure is a modelling commitment.** It bounds the claim to a
   camera with known, declared response.
4. **Transfer to a real camera is unproven.** The route to closing it is the DENSE
   family's Pixel Accurate Depth Benchmark: 17 measured fog-chamber visibility levels
   (20-100 m), 12-bit RGB, survey-scanner depth, and calibrated reflectance targets at
   known distances. Its chamber covers 20-100 m, so only the severe end of our declared
   2000-60 m fog range can be externally validated. See `docs/DENSE_ACCESS.md`.
5. **Verification covers the parameterized family only.** It replaces exhaustive sampling
   *within* a disturbance family, not scenario sampling across routes and manoeuvres.
6. **The ODD is narrow**: one route, one speed, one vehicle.

---

## 9. Verifying a policy without modelling the disturbance  *(supersedes 7.2)*

Section 7.2 anticipated a per-condition disturbance model that verification would bound
over. That approach was carried a long way and is now retired. What replaced it is simpler,
and the reasons are worth stating because they generalise to conditions this study has not
attempted.

### 9.1 Why per-frame criteria cannot work

Seven were built and six retired: analytic-model bias, measured-field bias, error
accumulation, restoring sign, restoring sign over a bounded tube, and equilibrium offset.
They failed for one reason, established twice independently. F21 showed the frames that
cause a departure are off-centre views that appear nowhere on the nominal trajectory. F22
tested the last of them directly -- predicted equilibrium against the CTE the vehicle
actually reached, at 263 route locations -- and found r = -0.053, with flagged locations
CLEANER than unflagged ones.

> Closed-loop departure is a property of the TRAJECTORY. The cross-track error at a
> location is set by where the vehicle came from, so no quantity evaluated at a single
> frame or pose can carry it.

A corollary that cost a day: a per-frame criterion can score 7/8 or 8/8 in-sample and still
be measuring nothing. Both times the apparent agreement came from which poses happened to be
sampled. In-sample agreement is not evidence; only a committed, out-of-sample prediction is.

### 9.2 Measure the policy's response, do not model the image

Every disturbance model in this study -- Koschmieder fog, per-pixel night gain, shadow
masks -- exists to answer one question: what does the policy DO under this condition. The
image model was only ever an intermediary, and a lossy one. Fitting it imposed real costs:
pose-paired frames, an image-fidelity gate, a behavioural-fidelity gate (F19, because image
R^2 alone passed a model that drove `S_mixed` 23.8x too hard), and a family-mismatch hazard
that CLAUDE.md blames for the entire previous study.

The alternative removes the intermediary. Place the vehicle at a known state, render
whatever the simulator renders, and measure the steering response:

    s(pose, o, psi)   for lateral offset o and heading error psi

Nothing is fitted and no disturbance family is declared. This works for ANY condition the
simulator can render, which is the property that matters for extending beyond fog, night and
shadows. It carries two conditions of its own:

- **Stochastic conditions need repeated samples.** Rain and snow differ between renders at
  the same pose, so the response becomes a distribution and bounds must cover the samples.
- **It sees perception only.** Conditions that change vehicle dynamics -- rain and snow
  change tire friction -- have a component no perception-to-steering verifier can observe.
  That boundary must be stated, not blurred; `set_tire_friction` exists for the other half.

### 9.3 Heading error is not optional

Captures placed the vehicle at lateral offsets with heading ALIGNED to the path, and every
reachability tube built on them diverged -- including under clear weather, where the real
vehicle holds 0.13 m. The cause was structural, not numerical: with offset-only feedback the
discrete spectral radius is 1.115, so the loop is an undamped oscillator that must diverge.
Damping enters through the policy's response to heading error, measured at k_psi = -1.0 to
-2.4 in daylight and never captured. The spring was measured; the damper was not.

> A lane-keeping loop has two states. Verifying one of them verifies a different system.

### 9.4 dt is the control period

The discrete dynamics must step at the controller's rate (`FIXED_DT`, 0.2 s), not at the
spacing of whatever poses were captured. Deriving dt from pose spacing over speed inflated
it to 0.4 s and then 1.2 s, which changed a criterion's score from 7/8 to a spurious 8/8 and
in the extreme case failed every cell including bright daylight. Pose spacing is a sampling
choice; the control period is physics.

### 9.5 Validate the surrogate before bounding it

Sound bounds on a surrogate that does not reproduce the system prove nothing about the
system. Before any verification result is trusted, the captured response must be checked
against what the vehicle actually did at the same locations:

    westbound   captured steer at offset 0 vs driven:  mean |diff| 0.025   USABLE
    eastbound   captured steer at offset 0 vs driven:  mean |diff| 0.208   REJECTED

The eastbound captures measured an inverted restoring gain and would have scored 7/8. They
are an artefact; static placement does not reproduce eastbound driving there, and the cause
is still unknown (manifest yaw agrees with the path tangent to 0.02 deg, so it is not that).
Verification in this study is therefore scoped to westbound, which is a stated limit rather
than a hidden one. **Run this check first.** It is cheap, and it fails fast.

### 9.6 Conditions lie on continuous axes, and the gaps are where models fail

`clear`, `shadows` and `night` are not three phenomena. They are `sun_altitude_angle` at
+90, +15 and -25 of one parameter. Sweeping it converts a three-point comparison into a
curve and makes transitions predictable in advance -- and it exposed a failure mode that
discrete presets hide entirely:

> `S_mixed` passes at all three altitudes it was TRAINED on and fails between them
> (+8, +3, 0 degrees), worst at 0 where the sun sits on the horizon and glare is maximal.

Training on discrete condition presets does not cover the continuum joining them. Any study
that tests only at its training conditions cannot see this.

Sweeping an axis requires everything keyed to that axis to follow it. Camera exposure and
headlights were keyed to the CONDITION NAME, so a swept sun altitude captured below-horizon
scenes through the daylight camera (night declares 4x exposure) and produced a result that
contradicted known ground truth. Both now key off `sun_altitude_angle < 0`, which reproduces
all three presets exactly.

### 9.7 The blind protocol, and what it is worth

Verification verdicts are committed to git before the closed-loop runs that test them
(`python -m study.ledger --check-order`). Two predictions have been committed and both were
refuted -- P-03 at 2/6, P-06 at 3/7 -- while the in-sample scores at the time were 14/14 and
7/8. That gap is the entire argument for the protocol. It is also why P-06 declared its one
known-wrong cell in advance: a prediction that quietly omits its weakest case is not a
prediction.

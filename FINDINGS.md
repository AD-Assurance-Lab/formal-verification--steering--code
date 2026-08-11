# Findings

Measured results, newest first. **Keep this short.** The previous generation's log grew
to 1,266 chronological entries containing claims later withdrawn, and it crowded out the
current state. If a finding is superseded, *edit it in place* and say so — do not append a
correction below and leave the original standing.

Ledger cells live in `results/ledger/` and are checked by `python -m study.ledger`. This
file is for characterization measurements, which are not ledger cells.

---

## F11. Width is the capacity lever; resolution loses on BOTH axes

**Status: measured. Settles a question I had reopened, and confirms the frozen repo's
conclusion for a different reason than it recorded.**

Distilled from `teacher_mixed_dagger_r07` over 102,938 frames, all four conditions:

| config | ReLU | KD val RMSE |
|---|---|---|
| 1x width, 84x28 | 5,152 | 0.0263 |
| 2x width, 84x28 | 10,304 | 0.0227 |
| **3x width, 84x28** | **15,456** | **0.0201** |
| 4x width, 84x28 | 20,608 | 0.0215 |
| 2x width, **112x38** | **21,504** | **0.0319** |

**Two results.**

1. **Width has a knee at 3x.** 4x costs 33% more neurons and is *worse* on the offline
   metric, so there is no case for paying that bound-looseness at M6.
2. **Resolution loses on both axes at once.** 112x38 needs more neurons than ANY width
   config -- 21,504 against 3x width's 15,456 -- for the worst KD RMSE in the sweep. It
   costs more of exactly what verification pays for and delivers less.

**I had reopened the resolution question and was wrong to.** `docs/CONSTRAINTS.md` item 8
argued resolution was viable again because the verifier's input is the physical parameter
rather than the image, so resolution no longer inflates the *perturbation* dimension. That
reasoning is correct and still stands. It is simply not the binding cost: resolution scales
ReLU count as `k^2` while width scales it as `k`, and ReLU count is what drives bound
looseness. Same conclusion as the frozen repo, arrived at for a different reason.

The 140x47 config was dropped rather than run -- strictly further along the same losing
trend at roughly 33,000 ReLU, and unattended time is scarce with the machine reaping
background jobs.

**KD RMSE remains a screen, not a decision.** Closed loop picks the config; this only
bounds the search to 1x-3x width at 84x28.

## F10. My branch-and-bound search order was wrong; the d=2 result is retracted

**Status: bug found and fixed. The k^d claim is still untested.**

I reported that night at d = 2 was "dramatically worse" than fog and called it the k^d cost
appearing for the first time. **That was my bug, not the method's.**

The BaB loop used `stack.pop()` -- LIFO, so it always popped the box it had just pushed,
i.e. the SMALLEST one. It burrowed into an ever-shrinking corner resolving negligible
volume while large undecided siblings sat untouched.

**The data said so and I nearly filed it as a finding instead of a bug.** Raising the
budget from 48 to 400 cells changed the resolved volume by *nothing* -- 33.2%, 81.6%, 4.2%
UNKNOWN, identical to three significant figures. Eight times the work for zero progress is
not a cost curve, it is a broken search. `bound_box` was verified sound in isolation first
(bound width 0.153 -> 0.087 -> 0.041 -> 0.0073 -> 0.0014 as the box shrinks), which
localized the fault to the search order.

Fixed to **largest-volume-first** via a heap, which maximises volume resolved per bound.
Same frames:

| frame (by clear steer) | LIFO @ 400 cells | largest-first @ **120** cells |
|---|---|---|
| +0.0040 | 33.2% UNKNOWN | **13.3%** |
| -0.0241 | 81.6% UNKNOWN | **46.9%** |
| +0.0062 | 4.2% UNKNOWN | **0.0%, fully certified** |

Less than a third of the budget, UNKNOWN roughly halved, and it is now converging.

**What can honestly be said:** d = 2 does cost more than d = 1 -- fog resolves with a median
of 15 bounds at 0.78% UNKNOWN, while night at 120 bounds still sits at 13.3% median. Whether
that ratio matches `k^d` needs night run to convergence and the bounds counted. Running.

**The withdrawn claim, kept visible:** "night at d=2 is dramatically worse, this is the k^d
cost showing up." Withdrawn 2026-08-11.

## F9. Verification is DECISIVE on this family: UNKNOWN rate under 2.5%

**Status: provisional inputs, but the tightness result is the point and survives them.**

`scripts/certify_fog.py`, 20 clear frames, adaptive bisection over MOR 2000-60 m to depth
7, corridor centred on clear-weather steering, per-row transmission (F8).

| | |
|---|---|
| certified fraction of the axis | median **98.0%**, mean 84.6%, range 5.5-100% |
| **UNKNOWN (bound looseness)** | median **0.78%**, max **2.34%** |
| bounds per frame | median 15, max 33; 322 total |
| frames fully certified 60-2000 m | 6/20 |
| frames < 50% certified | 3/20 |

**The UNKNOWN rate is the result.** The previous generation reported 11.5% UNKNOWN for its
disturbance-trained student -- the verifier frequently could not decide. Under 2.5%
worst-case here means the physical parameterization plus alpha-CROWN plus input-space
bisection returns a *decisive* verdict nearly everywhere. That is the core feasibility
claim of the approach, and unlike the certified fractions it does not depend on the
calibration constants being right.

**Non-monotone certificates, flagged not explained.** Frame 3 certifies
`[75,121] U [393,2000]`; frame 5 certifies `[60,105] U [1348,2000]`. Certified in dense fog
AND near-clear, falsified in between. There is a plausible physical story -- as MOR -> 0 the
image saturates toward uniform airlight and the network output may drift back toward its
clear value -- but it is equally consistent with the uncalibrated `A = 0.78` producing an
artifact. **Recheck once the airlight is measured (D4).**

**Do not oversell the efficiency argument from this.** Verification returns a per-frame
certified interval in ~16 bounds; closed loop returns pass/fail per lap. Different
granularities, so "322 bounds vs N laps" is not a like-for-like comparison. The efficiency
claim needs the M6 blind protocol to make it properly.

**Provisional inputs, unchanged from F8:** student distilled from pre-fix data, airlight
uncalibrated, flat-road row depth rather than the measured depth map.

## F8. The 6-band transmission discretization was the binding constraint on certifiability

**Status: measured, no CARLA needed. Changes M5's design.**

Fog reaches the verifier as a set of per-pixel transmissions driven by ONE scalar (beta,
hence MOR). The inherited machinery instead hands it a **box over six per-band
transmissions**, where `banded_transmission_box` takes `min`/`max` over the ROWS INSIDE
each band.

**That conflates two different things**: variation from the MOR interval, which is what we
want to bound, and variation from depth within the band, which is *fixed per pixel and not
a free parameter at all*. The consequence is that the perturbation does not shrink as the
MOR interval shrinks. Measured: at a **1-metre-wide** interval [60, 61] the banded model
still has `|W|max = 0.242`, essentially unchanged from the full [60, 2000] range.

That produced a hard floor. Bound width against the closed-loop tolerance 0.0120:

| MOR interval | banded box (6 dims) | banded rank-1 (1 dim) | **per-row rank-1 (1 dim)** |
|---|---|---|---|
| [60, 2000] | 9.488 | 1.218 | **0.198** |
| [60, 150] | — | 0.628 | **0.0507** |
| [60, 80] | — | 0.276 | **0.0370** |
| [60, 61] | — | 0.191 (floor) | **0.00129 -> CERTIFIED** |

Removing the banding removes the floor entirely: `|W|max` falls 0.301 -> 0.0024 as the
interval narrows, and **the bound converges to the concrete range** (0.0507 vs a concrete
0.0506 at [60,150]; 0.0370 vs 0.0370 at [60,80]). alpha-CROWN is essentially exact on this
family once the parameterization is right.

**So branch-and-bound does work here**, and the earlier reading that "splitting does not
help" was an artifact of the discretization, not a property of the problem.

**Two corrections to my own earlier claims, recorded rather than quietly fixed:**

1. `scripts/linearity_probe.py` reported all conditions "EXACT" at ~1e-6 residual. That
   result is close to tautological -- each model is parameterized *by construction* in a
   quantity it is linear in, so of course the residual is at float noise. The probe
   measured the wrong thing. Conservatism, not linearity, is what decides certifiability.
2. My first box-vs-rank1 run showed a floor at 0.19 and I nearly reported it as a limit of
   the approach. It was my own harness inheriting the banding.

**Consequence for M5:** do not band. Use per-pixel transmission from the measured depth map
(D4), with one scalar driving all of it. The band count is not a tuning parameter to
optimize -- banding is the error.

**Caveat:** this used flat-road row-based depth (`dm.transmission` with `CARLA_GEOM`), not
measured per-pixel depth. D4 replaces that. The finding is about per-pixel-vs-banded, and
holds either way.

**Open, and it is the real question now:** at [60, 2000] the *concrete* output range is
0.0494, already 4.1x the tolerance. No verifier can certify that interval, because the
network genuinely varies that much across it. Certification therefore has to come from
BaB over sub-intervals, and the certified result will be a set of MOR sub-ranges rather
than a single verdict -- which is exactly the "bounded region of the ODD" the study claims
to deliver. How many cells that takes is the next measurement.

## F7. S_mixed's closed-loop failure is the missing student-DAgger stage, not capacity

**Status: student-DAgger running. Two earlier hypotheses tested and both refuted.**

**Refuted 1 -- capacity.** Width sweep at 84x28 over 83,567 frames:

| width | ReLU | params | KD val RMSE |
|---|---|---|---|
| 1x | 5,152 | ~10k | 0.0338 |
| 2x | 10,304 | 39,809 | 0.0372 |
| 3x | 15,456 | 88,513 | 0.0327 |
| 4x | 20,608 | 156,417 | 0.0314 |

Quadrupling the neurons buys 7%, non-monotone through 2x. A capacity-starved model
improves steadily as capacity is added; this plateaus.

**Refuted 2 -- optimization / warm start.** Warm-started from `S_clear_84x28` at lr 5e-4,
1x width: KD val RMSE **0.0427**, worse than cold start's 0.0338. `distill_student` has
always had an `init_from` parameter documented as stabilizing multi-condition re-distill,
but it was never wired to the CLI, so the documented fix was unreachable from the command
line. Now exposed (with `--lr` and `--patience`) -- and it does not help.

**KD RMSE is a poor proxy, which is the methodological lesson here.** Closed loop on
CLEAR disagrees with it:

| student | KD RMSE | closed loop on clear (2 reps x 2 directions) |
|---|---|---|
| 1x width | 0.0338 | 4/4 failed (11.76, 3.63, 2.65, 3.21 ft) |
| 4x width | 0.0314 | 2/4 failed — westbound 1.42 / 1.40 ft **PASS**, eastbound 10.67 ft FAIL |

Width materially improves closed loop while barely moving KD RMSE. Two runs of the same
configuration in opposite directions give opposite verdicts, which is the usual reminder
that these are rates, not verdicts.

**The actual gap.** Neither student has had **student-DAgger**, the final stage of the
documented recipe: BC -> teacher-DAgger -> distillation -> student-DAgger. The teachers
needed it badly -- the clear teacher went 23.99 ft to 0.71 ft through DAgger alone. A
distilled student drifts into states its teacher's data never covered, and closing that
gap is precisely what student-DAgger is for.

**Process note, recorded because it is the more useful lesson than the result.** A width
sweep and a warm-start test were run before the next step that was already written in the
recipe. The `S_clear` control passing without student-DAgger was a real measurement, but
the inference drawn from it was wrong: clear is an easier task, which is not evidence that
`S_mixed` should also clear the bar without the stage. The control eliminated one
explanation and was treated as though it had confirmed another.

### superseded reading (kept so the correction is visible)

*5,152 ReLU holds one condition and not four -- isolated with the S_clear control*

Both students distilled at the identical architecture required by `STUDY.md`
(84x28, channels (8,16,16), fc 32, 5,152 ReLU), from their respective DAgger teachers,
neither having had student-DAgger yet.

| student | KD val RMSE | closed loop on CLEAR (2 reps x 2 directions) |
|---|---|---|
| `S_clear` | 0.0191 | **0/4 failed -> PASS** |
| `S_mixed` | 0.0338 | **4/4 failed -> FAIL** |

**The control is what makes this diagnostic.** A freshly distilled student failing closed
loop has two candidate causes -- insufficient capacity, or the missing student-DAgger
stage -- and `S_mixed` alone cannot separate them. `S_clear` passing under exactly the
same architecture and procedure eliminates the DAgger explanation.

Sweeping width at 2x, 3x, 4x. Per the design rule in `STUDY.md`, whichever width
`S_mixed` needs, `S_clear` is rebuilt at the same one. A capacity difference between the
arms is the exact confound that left the previous generation's headline anomaly
unresolved; a clear-only model carrying surplus capacity is harmless.

**Note for the verification stage:** width is the cheap lever for the *policy* and an
expensive one for the *verifier* -- more ReLU neurons means more relaxations and looser
bounds. If `S_mixed` needs 4x width, expect its UNKNOWN rate at M6 to rise accordingly,
and note that resolution is now an alternative lever in a way it was not before (see
`docs/CONSTRAINTS.md` item 8).

## F6. Night's closed-loop failure was sensor clipping, not headlight geometry

**Status: settled. The condition-dependent exposure (F5) is validated.**

The mixed teacher failed night in all 6 DAgger rounds at the single global exposure, with
`max|CTE|` up to 44 ft clustered at the east-end curve. Two explanations were live:
headlight geometry (on a curve the beams point straight while the road turns away, so the
lane is unlit where steering matters most -- a genuine ODD finding) or sensor clipping (a
rig artefact).

Nothing was changed but the camera's exposure. Result, `teacher_mixed_dagger_r04`,
converged at round 5, all eight legs 0% over budget against a 1.75 ft gate:

| condition | eastbound | westbound |
|---|---|---|
| clear | 0.51 ft | 0.92 ft |
| fog | 0.54 ft | 0.63 ft |
| **night** | **0.76 ft** | **0.57 ft** |
| shadows | 0.62 ft | 0.47 ft |

**It was the clipping.** Corroborated independently offline, without touching CARLA: the
mixed BC teacher's val RMSE improved 0.0044 -> 0.0042 on the recollected night data,
matching the clear-only teacher exactly.

**The near miss worth recording:** accepting the first result would have published a
false ODD boundary -- "the policy cannot drive at night" -- that was a property of the
camera configuration, not the policy. This is the third time in this project's history
that a rig artefact nearly became a finding (headlights off, auto-exposure, this).

## F5. No single exposure spans the illuminance axis; exposure becomes condition-dependent

**Status: decided by Zach, implemented, validated by F6.**

`scripts/exposure_dynamic_range.py`, 12 poses:

| shutter | clear mu | night mu | night clipped to 0 |
|---|---|---|---|
| 800 | 0.291 (in target) | 0.043 | **50.6%** |
| 200 | 0.601 | 0.201 | 12.5% |
| 25 | 0.938 (washed out) | 0.614 | 0.5% |

Clearing the clipping bound needs shutter 25, which puts the clear road at mu = 0.938 --
back in the washed-out regime that made the fog airlight unidentifiable. The two
requirements are incompatible, so exposure is now a **declared function of condition**:
daylight conditions at shutter 800, night at 200 (a 4.0x ratio).

Measured at the declared settings: clear mu 0.290 / sigma 0.0858 / 3.4% clipped; night
mu 0.200 / sigma 0.1520 / 12.6% clipped, no blown highlights. Night stays DARKER than
clear, so it remains a dimming disturbance rather than an auto-exposure-style
normalization.

**What it costs, and the paper must say it:** the certificate reads "certified at X lux
**with the camera exposing as declared**". The night disturbance's gain carries the
exposure ratio as a known factor alongside the illuminance ratio. Both are known because
we set them, so identifiability -- the entire reason for pinning exposure -- survives. A
declared function is not auto-exposure; an auto-exposure loop is opaque and destroys the
mapping.

Implementation note: exposure is a CARLA blueprint attribute and cannot be changed on a
live sensor, so `env.set_condition()` respawns the camera. Using `set_weather` alone would
capture each new condition through the PREVIOUS condition's exposure -- silent, and a
close cousin of trap 2.

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

# Findings

Measured results, newest first. **Keep this short.** The previous generation's log grew
to 1,266 chronological entries containing claims later withdrawn, and it crowded out the
current state. If a finding is superseded, *edit it in place* and say so — do not append a
correction below and leave the original standing.

Ledger cells live in `results/ledger/` and are checked by `python -m study.ledger`. This
file is for characterization measurements, which are not ledger cells.

---

## F21. Closed-loop failure here is feedback divergence, not bias accumulation on the nominal path

The study's premise is that per-frame analysis of a policy, evaluated on the frames of a
nominal trajectory, predicts whether it departs the road. Tested directly, that premise
fails, and the test does not depend on bound tightness because it uses the REAL measured
per-frame biases rather than verified bounds.

Bicycle model, no tuned parameter: a bias `d` sustained for `N` frames departs iff
`d*(N*dt)^2 >= 2L*budget/(v^2*MAX_STEER) = 0.0411`. Longest same-signed run measured on
CARLA frames, against the actual outcome:

| fog density | `S_clear` run | score | predicts | actual |
|---|---|---|---|---|
| 25 | N=8 at 0.0031 | 0.0080 | ok | **FAIL 20/20** |
| 40 | N=10 at 0.0066 | 0.0263 | ok | **FAIL 20/20** |
| 55 | N=16 at 0.0012 | 0.0120 | ok | **FAIL 20/20** |
| 70 | N=74 at 0.0010 | 0.2088 | DEPART | FAIL 20/20 |

`S_mixed` scores below threshold at every density and passes every density, 4/4.

> **SUPERSEDED IN PART (2026-08-25, D-14).** The `S_clear` FAIL 20/20 rows above are
> full-lap-protocol cells whose departures all originate inside the western
> intersection (max-CTE at steps 1703–1705; 98.8% of frames in budget) — the junction
> ODD boundary of D-09, not a fog failure. Under the amended open-road protocol
> (F28) the same checkpoint at the same densities is clean, 0/60 departures
> (`fog___openfog_*`). The mechanism argument below survives for the conditions that
> genuinely fail (night, shadows); the fog rows no longer support it.

**So the nominal-path model explains one of four failures.** At 25-55 the real biases reverse
sign every 8-16 frames while the vehicle leaves the road on every run. Whatever removes it
from the lane is not a steady pull.

**The mechanism it misses.** A policy makes an error, ends up off-centre, and then sees a
view that does not occur anywhere on the nominal trajectory -- and its response there is
what decides the lap. The frames that cause the departure are, by construction, absent from
the set being verified. This is why `S_clear` can look almost benign frame-by-frame on the
clear lap (median deviation 0.0029-0.0081, inside the corridor) and still depart 20/20.

**What this bounds.** Per-frame verification over nominal-trajectory frames can support a
NECESSARY condition -- a large sustained bias does imply departure, and that is how density
70 is caught -- but not a sufficient one. Certifying a policy safe on this evidence is
unsound, and the study produced exactly that error once (`S_clear` at density 55, CERTIFIED,
departs 20/20).

**What would close it,** and it is the vehicle-dynamics extension already identified as
future work: propagate the state. Verify over a reachable TUBE around the nominal path
rather than the path itself, so the off-centre states the policy actually visits are inside
the verified set. That is closed-loop reachability, not per-frame bounding, and it is a
different and larger piece of machinery.

---

## F19. Image fidelity is not behavioural fidelity, and the gap is worst for the GOOD model

A disturbance model can reproduce CARLA's images well and still be useless for verifying a
policy trained on the real thing. Measured, comparing each student's steering response to
REAL CARLA frames against the same student's response to the MODELLED disturbance:

| condition, model | image R^2 | real vs modelled steering response |
|---|---|---|
| fog, `S_clear` | 0.848 | 1.2x — faithful |
| fog, `S_mixed` | 0.848 | **23.8x — useless** |
| night, `S_clear` | 0.243 | 3.0x |
| night, `S_mixed` | 0.243 | **27x** |

**The mechanism.** `S_mixed` was trained on CARLA's real fog and night, so it keys on
features specific to how CARLA renders them, and is acutely sensitive to exactly the
residual the analytic model fails to reproduce. `S_clear` never learned those features, so
modelled and real disturbances look about the same to it. The consequence is perverse: the
analytic model is *most* wrong about the *best* policy, which is precisely backwards for a
tool meant to certify good policies.

**So an image-fidelity gate is necessary but NOT sufficient**, and D3 as written would have
passed fog. A behavioural check -- does the policy respond to the modelled disturbance as
it does to the real one -- belongs alongside it.

**Fixed by measuring the disturbance rather than assuming its form**, per condition:

| condition | model | image R^2 | `S_mixed` behavioural |
|---|---|---|---|
| night | analytic ambient + assumed beam | 0.243 | 27x |
| night | **measured illumination field** | **0.832** | ~1x |
| fog | analytic Koschmieder + k | 0.848 | 23.8x |
| fog | **measured affine field** | **0.950** | **0.8x** |

At CARLA's measured night this turns verification from useless into exact discrimination:
`S_clear` falsified 10/10, `S_mixed` certified 10/10, matching closed loop both ways.

---

## F20. Verification flags intermediate severities that closed loop never drives

`S_mixed` certifies at CARLA's actual night and fog levels but falsifies over the FULL
declared axis. That is not a false alarm -- it is the two instruments answering different
questions. Closed loop drives one point per condition; verification covers the continuum
between clear and that point.

Measured empirically, steering deviation versus visibility for `S_mixed`:

    MOR 2000 m   5% of frames over corridor
    MOR  500 m  10%
    MOR  250 m  20%
    MOR  140 m  50%
    MOR   90 m  55%   <- CARLA's fog level

so degradation is monotone in fog thickness for the mixed model, and the axis contains
regions never simulated. **This makes a falsifiable prediction**: drive CARLA at a fog
density corresponding to an intermediate MOR the verifier flags, and the mixed model should
degrade there. That is the S1 interpolation stretch goal, promoted from "nice if it lands"
to the natural next experiment -- and it is the strongest available argument for
verification as a tool, because it is the one claim closed-loop testing cannot make without
running every point.

---

## F18. The training dataset was rendered with a DIFFERENT clear preset than the code now produces

Chasing D-04's sky discrepancy to its root. At the same pose, same nominal condition:

    dataset frame (2026-08-11 12:28)   sky 0.0021   road ROI 0.3135
    fresh world, current code          sky 0.2577   road ROI 0.2205

Confirmed on a **freshly loaded Town04** with the weather set before any actor exists, and
the live weather reads back exactly `CLEAR_BASELINE` (`scattering 0.0, mie 0.0, sun_alt 90,
cloud 80`). So this is not world drift, not settling, and not the harness.

**Cause.** `CLEAR_BASELINE` was introduced by commit `ae3ec28` at 12:28 — the same minute
the dataset's first frame was written. Before it, `set_clear_weather` was a
**read-modify-write**: `w = world.get_weather()` followed by setting a handful of fields,
leaving `scattering_intensity`, `mie_scattering_scale` and the rest at whatever the world
already held. That is the very pattern `ae3ec28` was written to eliminate, and the dataset
was collected on the wrong side of it.

**The sky part is harmless.** `CROP_TOP = 180` removes it before the network, and the
dataset's first non-black row is 146, so no sky reaches the model.

**The road part is not.** The road ROI is inside the crop, and it differs by **30%**
(0.3135 trained versus 0.2205 rendered today). The students were trained on frames
measurably brighter than what closed-loop testing now renders. Every closed-loop cell in
this ledger was driven under that mismatch.

**What it does and does not explain.**

- It does **not** invalidate the ledger. Both students faced the identical mismatch, and
  `S_mixed` still passes clear, night and shadows at 0/20, so the policies tolerate it. The
  `S_clear`-versus-`S_mixed` contrast is unaffected because it is a within-comparison.
- It **does** bias the photometric calibration, which is how it surfaced. The fog fits used
  dataset frames (old preset) while the static sweep used live renders (new preset), each
  internally consistent but not consistent with each other. **That is the root of D-04's
  `k` disagreement** — 0.72 from dataset pairs against ~1.14 from live pairs.
- It **may** contribute to the marginal excursions, since a 30% darker road is a domain
  shift the students never trained on. Untested.

**MEASURED, and it is bigger than the disturbances under study.** Feeding each student the
dataset frame and the live render of the *same pose*, and comparing their steering:

    tolerance 0.0120
    S_clear   median 0.0109   p90 0.3038   max 0.3290   over tolerance on 40% of frames
    S_mixed   median 0.0036   p90 0.1537   max 0.1710   over tolerance on 30% of frames

For scale, `S_clear` exceeds the corridor on 37% of frames under **shadows** and 23.7% under
**fog**. The preset change on its own reaches 40%. The domain shift is not a detail beside
the weather effects; it is the same size.

**Why this matters for the ledger's central comparison.** Verification reads **dataset**
frames (old preset). Closed loop drives **live renders** (new preset). Those two visual
domains differ by more than the certification tolerance on 30–40% of frames, so the two
instruments are not being applied to the same images. Tonight's agreements — most
importantly `night / S_clear`, FALSIFIED then 20/20 failure — are still agreements, and
falsification is robust because it only needs one real violating region. But the *general*
claim "verification predicts closed loop" is being made across a domain gap that nobody
declared, and that gap has to close before the claim is airtight.

**This raises the priority of the fix from tidiness to blocking.**

**The cause is NOT the weather preset — corrected after bisecting it.** I attributed this
to `ae3ec28` replacing a read-modify-write `set_clear_weather` with a constructed
`CLEAR_BASELINE`. Testing the fields that commit newly pins:

    TARGET (dataset)           sky 0.0021   road 0.3135
    current CLEAR_BASELINE     sky 0.2575   road 0.2205
    mie_scattering_scale=0.03  sky 0.2575   road 0.2206
    scattering_intensity=1.0   sky 0.2575   road 0.2206
    cloudiness=0               sky 0.1886   road 0.1460   (wrong direction)

None of them move it. A 100x sky difference is not reachable from any scattering parameter,
and a **pure black** sky is not physical under manual exposure with an overcast preset — it
is a sky that is not being rendered at all.

**Leading hypothesis, STILL UNTESTED: the server's graphics quality level.** I attempted it
— launched a second, short-lived CARLA on port 3001 at `-quality-level=Low` so the running
Epic server on :3000 was untouched — but it failed for a mundane reason worth
recording: **CARLA binds `rpc-port`, `+1` AND `+2`.** The Epic server on 3000 already owned
3001 and 3002, so the Low server had a port conflict from the start, and my client
"connecting to :3001" was talking to the Epic server's streaming port. Retried on port 3010, clear of that conflict, and the precise behaviour is: **a second concurrent
CARLA starts as a process but never binds its RPC port** while another server is running.
The binary is there in `ps` with `carla-rpc-port=3010`, the log stays empty, and nothing
ever listens on 3010-3012. So the blocker is not the port — testing a different quality level requires
stopping the running server first, and that is a shared resource, so it is not something to
do unilaterally.

**No measurement was obtained; do not read this as evidence either way.** The retry is one
CARLA restart at `-quality-level=Low`, one frame capture at a known pose, comparing the sky
mean against the dataset's 0.0021 and the Epic server's 0.2575. Tonight's runs launch
CARLA with `-quality-level=Epic`; a Low-quality server disables volumetric sky and
atmosphere, which would give exactly a black sky, and would also change how the road is lit.
The timing coincidence with `ae3ec28` misled me — the commit landed the same minute
collection began, which made it look causal.

**So "pin the old preset" is not the fix.** The difference is outside the weather
parameters entirely, and the recollection decision below should be taken on the basis that
the *rendering environment* differed, not the preset. Confirming it costs one CARLA restart
at a different quality level and one frame capture.

**Recommended fix, and it is Zach's call because it costs a recollection:** re-collect the
`conditions` dataset under the current constructed presets, or pin the old preset
explicitly. Do not leave the two silently different. Until then, any photometry must use
dataset frames on **both** sides of a comparison — which the fog route-frame calibration
already does, which is why it remains the one to trust.

---

## F17. The M6 aggregation rule, not the verifier, produced an unsound certificate

`shadows / S_clear / verify` returned CERTIFIED. Closed loop then failed **20/20, 16 runs
departing, median max-CTE 21.3 ft**. That is the one outcome that invalidates the tool
rather than the experiment, and it was my pre-registered blind prediction.

**It is not the disturbance model.** Shadows reconstructs CARLA almost exactly at `s = 1`:
D3 (a),(b),(c),(f) all **12/12**, median ROI R^2 **+0.996**, reconstruction error 0.0008 on
the road ROI, and only 0.7% of the frame (0.0% of the road ROI) is brighter under shadows
than clear, which is the only thing the multiplicative form cannot represent.

**It is not the verifier.** alpha-CROWN bounds are sound for the frames they are given.

**It is the sampling.** The pre-registered rule evaluates `VERIFY_FRAMES = 12` frames and
takes the MEDIAN. Measured directly on 400 pose-matched on-route frames, `S_clear` under
shadows exceeds the steering corridor on **37.8%** of them, p99 = 0.20, max 0.36 — up to
30x tolerance. A median over 12 frames cannot see a 38% tail, and a lap has ~1700 frames.
The certificate was never wrong about what it examined; it was silent about the 99.3% of
the route it never looked at, and the aggregation rule turned that silence into CERTIFIED.

**The corridor itself is strongly predictive once measured densely.** Fraction of on-route
frames whose steering deviates beyond the corridor, against closed-loop outcome:

| model | condition | frames over corridor | closed loop |
|---|---|---|---|
| S_clear | night | 86.0% | FAIL 20/20 |
| S_clear | shadows | 37.0% | FAIL 20/20 |
| S_clear | fog | 23.7% | *predicted FAIL, not yet run* |
| S_mixed | night | 8.0% | PASS 0/20 |
| S_mixed | shadows | 3.3% | PASS 0/20 |
| S_mixed | fog | 3.0% | FAIL 1/20 (the marginal cell, D-01) |

Every cell above 23% fails; every cell at or below 8% passes, with the single marginal
exception that D-01 is already about. So the per-frame corridor is a good surrogate for lap
safety — the study's premise holds — and the defect is entirely in how the sweep was
summarised.

**CONFIRMED IN ADVANCE, 2026-08-12 01:05.** F17 predicted the sparse protocol would
produce a *second* unsound certificate, and P-02 named the cell and the outcome before the
drive. `fog / S_clear`:

    verify (12 frames, median)   CERTIFIED, 72.3% certified, 0% falsified
    dense corridor breach        23.7% of on-route frames  ->  predicted FAIL with departures
    closed loop                  FAIL 20/20, ALL 20 runs departed, median max-CTE 92.3 ft

So the sparse protocol certified a policy that leaves the road on every single run, and the
dense statistic called it correctly beforehand. Two unsound certificates now, both from the
same defect, one of them predicted. That is as strong as this diagnosis can get.

**Consequence: no verification cell produced by the 12-frame median protocol should be
reported as a certificate.** The FALSIFIED cells survive (existence claims, argued below);
the CERTIFIED ones do not. `study.design.VERIFY_FRAMES` and `verify_verdict` need replacing
before M6 can be claimed.

**DIRECT TEST: the disturbance model DOES predict; only the frame selection was wrong.**
Zach asked the right question — if verification does not predict closed loop, in what sense
is the model correct? Answered by verifying the frames that actually matter instead of an
even sample. Screening 120 pose-matched shadows pairs for `S_clear`, **41 (34%) already
violate the corridor empirically**. Running the same model and the same verifier on the six
worst:

| frame | empirical deviation | verification |
|---|---|---|
| 0 | 0.2088 (17x tol) | **79.0% falsified** |
| 1 | 0.1459 (12x tol) | **78.1% falsified** |
| 2 | 0.1360 (11x tol) | **70.1% falsified** |
| 3 | 0.1261 (10x tol) | **78.8% falsified** |
| 4 | 0.1112 (9x tol) | **67.3% falsified** |
| 5 | 0.1093 (9x tol) | **67.9% falsified** |

**6/6 falsified, none UNKNOWN.** So the physics is right and the verifier is capable — the
sweep simply never looked at these frames. Two corrections follow:

1. It is **not** enough to change how frames are aggregated; the frame **selection** is the
   defect. Twelve evenly-spaced frames cannot represent a 1700-frame lap where a third of
   the route violates. Sampling must be dense, or deliberately include worst-case frames.
2. My earlier statement that the fix "only converts CERTIFIED to UNKNOWN, which is not
   prediction" was true of the even sample and **wrong in general**. With frames chosen
   properly the verdict is FALSIFIED, and FALSIFIED before the drive is exactly the
   prediction the study claims.

**And it means tuning the disturbance model would have been the wrong repair** — it already
reproduces CARLA at ROI R^2 0.996 and already falsifies the failing frames. Adjusting it to
make verdicts agree would have fitted the answer while breaking a model that was correct.

**Fix, and it is a pre-registration change so it is Zach's call.** The verification
statistic should be a COVERAGE over the route — the fraction of frames whose *bound* stays
inside the corridor, over a large frame sample — not a median over a handful. `CERTIFIED`
should then require that fraction to be near 1, and the frame count should be justified
against the number of frames in a lap rather than chosen for runtime.

**THE PROPOSED FIX IS VALIDATED ON DATA ALREADY COLLECTED.** Re-scoring tonight's six
non-vacuous verify cells with a coverage rule — `CERTIFIED` requires **every** sampled
frame fully certified, not the median — costs nothing and gives:

| cell | current rule | proposed rule | closed loop | |
|---|---|---|---|---|
| fog / S_clear | CERTIFIED | UNKNOWN | FAIL 20/20 | unsound → fixed |
| fog / S_mixed | CERTIFIED | UNKNOWN | FAIL 1/20 | unsound → fixed |
| shadows / S_clear | CERTIFIED | UNKNOWN | FAIL 20/20 | unsound → fixed |
| shadows / S_mixed | CERTIFIED | CERTIFIED | PASS 0/20 | correct |
| night / S_clear | FALSIFIED | FALSIFIED | FAIL 20/20 | correct |
| night / S_mixed | FALSIFIED | FALSIFIED | PASS 0/20 | over-strict (F16 axis) |

**All three unsound certificates disappear, and the one correct CERTIFIED survives.** The
cost is honest: two cells drop to UNKNOWN rather than becoming FALSIFIED, because 12 frames
genuinely cannot support a positive claim about a 1700-frame lap. UNKNOWN is the right
answer there.

`shadows / S_clear` is the instructive one — 11 of 12 frames were fully certified and a
single frame carried a falsified region. The median discarded that frame; requiring all
frames catches it. That is F17 in one line: the tail is the whole signal, and a median is
built to ignore tails.

The remaining disagreement (`night / S_mixed`) is the F16 axis misalignment, not the
aggregation rule, and it is in the conservative direction.

**What this does not touch.** `night / S_clear` was FALSIFIED and failed 20/20, and
falsification is an existence claim: finding a violating region on any frame is enough, so
sparse sampling can only make it miss violations, never invent them. The confirmed blind
prediction stands. It is CERTIFIED that sparse sampling can fabricate, which is exactly the
asymmetry the pre-registered rule was written around — the rule got the asymmetry right and
the sample size wrong.

---

## F16. The declared night axis does not contain the night CARLA actually renders

Fitting the night model to pose-paired frames at `sun_altitude_angle = -25`:

    ambient   0.553      declared axis 0.02 - 0.50   -> OUTSIDE, on the mild side
    a_retro  -4.23       declared axis 0.0 - 3.0     -> OUTSIDE, and WRONG SIGN
    rmse      0.101

**The axis excludes the operating point.** Larger `ambient` means more ambient light, so
CARLA's night is *milder* than the mildest point on our declared axis. Verification has
therefore been sweeping a region the closed loop never visits, and the two instruments are
answering different questions. This is the concrete form of the calibration debt recorded
in `STUDY.md`, and it was predicted in direction (P-01) before being measured.

**The retro term does not exist in this simulator.** `a_retro` fits strongly negative, i.e.
lane markings get *darker* relative to asphalt at night rather than brighter. That is what
a scene with no headlights looks like, and CARLA's night having no headlights is already a
known defect. Retroreflection was added to the model precisely because a pure brightness
scale "does not look like night"; in CARLA it is unphysical, and the fitted amplitude is
the model straining against a term whose premise is absent.

**D3 partial, road ROI, 10 frames:**

| check | result |
|---|---|
| (a) delta-mu sign | **10/10 pass** — rendered -0.1033, model -0.1063 |
| (b) delta-mu magnitude | **10/10 pass** |
| (c) delta-sigma ratio | 0/10 fail |
| (f) ROI R^2 >= 0.5 | 0/10 fail, median +0.243 |

So night is the opposite failure to fog's: fog got the road's mean shift *backwards*
(F14) while night gets the mean right and the *structure* wrong. Night is closer to usable,
but neither passes as it stands.

**Consequence for the ledger.** The committed night verify cells stand as run, over the
pre-registered axis, because amending a pre-registered axis after seeing results is not
mine to do. They should be read as "falsified over the declared axis", not as a statement
about CARLA's night. A calibrated re-run over an interval containing ambient 0.553 is
recorded separately as a diagnostic, so the comparison is available without rewriting the
pre-registration.

---

## F15. CARLA condition frames are pose-paired, so disturbance masks can be measured

The ego drives the same scripted route under each condition and the manifest records
`(x, y, yaw)`. Nearest-pose matching gives **median position error 0.039 m eastbound /
0.129 m westbound, yaw 0.03 deg**. A 0.04 m longitudinal offset moves a point 5 m ahead by
about 0.6 px, so these are genuinely pixel-aligned pairs.

This is the opposite of the ACDC situation and is easy to conflate with it. ACDC was
rejected for paired photometry because its condition pairs have **no** pixel
correspondence, which is what invalidated the previous generation's paired R^2. That is a
statement about ACDC, not about paired photometry.

**What it unlocks:** disturbance masks measured rather than declared; D3 checks (a), (b),
(c), (f) computable with no depth camera; and the preset-to-axis calibration that lets
closed loop and verification be evaluated at the same place on an axis.

**Shadows is calibrated for free by it.** With `S` the raw per-pixel per-channel dimming
`1 - shadows/clear`, the model `x' = x0 * (1 - s*S)` reproduces the observed CARLA shadows
frame exactly at `s = 1`. So the closed-loop operating point sits at exactly `s = 1` on the
declared `[0, 1]` axis.

**Masks must be per frame, not pooled.** Cast shadows are static in the world and therefore
move through the image as the ego drives, so a mask averaged over 400 poses blurs them into
a smooth global dimming. Measured: pooled relative spatial structure (std/mean) 0.36 versus
0.93 per frame — pooling discards roughly two thirds of it. The map stays affine in `s`
either way, because for a given frame the mask is a constant image.

---

## F14. Plain Koschmieder fails D3 on CARLA fog; the missing term is surface illumination

**The falsifier D3(a) exists for exactly this, and it fired.** Fitting pose-paired frames
at `fog_density=70`, road ROI:

    rendered  delta-mu  -0.0309     (CARLA fog DARKENS the road)
    modelled  delta-mu  +0.0150     (Koschmieder veiling BRIGHTENS it)
    ROI R^2   -0.030               (worse than predicting the mean)

Opposite signs. Full-frame rmse looks acceptable at 0.053 only because the sky dominates:
CARLA fog brightens the sky by **+0.42** while darkening the road by **-0.03** at the same
time, and no single global airlight can do both. This is the pooled-statistics trap D3(d)
was written to catch.

**Why this was dangerous.** `CLAUDE.md` names train/verify family mismatch as one of the two
never-ruled-out causes of the previous study's inverted fog result. Our students train on
CARLA-rendered fog, and we were about to certify them against a model that moves the road
the wrong way.

**The physics.** Fog also attenuates the sunlight reaching the road surface, so the surface
radiance itself drops. Fixed-radiance Koschmieder omits this. Adding it:

    x' = A*(1 - t) + t * k * x0

| model | MOR | rmse | ROI R^2 | (a) sign | (b) magnitude | (f) R^2 |
|---|---|---|---|---|---|---|
| Koschmieder | 250 m | 0.0529 | -0.030 | 0/8 | 0/8 | 0/8 |
| + illumination | **61 m** | 0.0314 | **+0.870** | **8/8** | **8/8** | **8/8** |

Every computable D3 check passes, and the operating point moves from the mild half of the
axis to **MOR ~ 61 m**, its severe end. `k ~ 0.70` at that density.

**Airlight is now measured, not assumed (D4).** `A ~ [0.47, 0.44, 0.43]`, against the 0.78
the previous generation assumed — off by about 1.7x.

**Verifiability is preserved at d = 1.** Giving `k` the same Koschmieder form over an
effective sun path, `k(MOR) = exp(-ln20 * d_sun / MOR)`, makes it a function of MOR alone,
so a sub-interval stays rank-1 in one scalar rather than needing a second bounded
dimension.

**Still open:** `k(MOR)` is a one-parameter law and needs validating across densities, which
`scripts/fog_density_sweep.py` measures. And the rank-1 chord is only as sound as the true
curve's bow away from it is small — `DISTURBANCE_MATH.md` asserts that deviation shrinks
quadratically but nothing measured it, so `fog_map_illum.deviation` now reports it per cell.

---

## F12. Model size is NOT the binding constraint on verifiability; input dimension is

**Status: measured. Settles the architecture question and answers the scaling question.**

Fog axis, adaptive BaB, corridor on clear-weather steering, 5 frames each:

| student | ReLU | UNKNOWN (mean) | bounds/frame |
|---|---|---|---|
| `S_clear` | 5,152 | 0.78% | 15 |
| `S_mixed_w2` | 10,304 | **0.94%** | 10 |
| `S_mixed_w3` | 15,456 | **2.5%** | 16 |

**Tripling the network barely moved decisiveness.** All three stay far from the ~11% UNKNOWN
where certification stops being useful. Architecture size is not what to optimise, which
is the call Zach made on scope and the measurement supports.

**What DOES determine verifiability is input dimensionality**, and the controlled comparison
is in F9/F8: the SAME 5,152-neuron network is

- **31.8x too loose to certify anything** under a pixel-space L-inf ball at eps=1/255 over
  7,056 input dimensions
- **decisive at 0.78% UNKNOWN** under the 1-dimensional physical parameter

Same network, same verifier, same day. The entire difference is the dimension of the
perturbation set.

**Consequence for scaling to bigger models** (Zach is building a 5090 box for exactly this):
GPU buys memory and branch-and-bound throughput, not tightness. Compute converts to
tightness only through BaB, which is linear gain against exponential need. Scale the
NETWORK freely; do not scale the PERTURBATION DIMENSION. Prefer wider over deeper, since
relaxation error compounds with depth in a way it does not with width -- consistent with a
3x width increase costing almost nothing here.

**Flagged, unresolved:** one w3 frame returns **100% FALSIFIED** across the whole visibility
range -- a decisive negative, not looseness. `w2`'s worst frame is 3.1% falsified on the same
five frames. Genuine w3 weakness or a hard frame is not yet distinguishable, and absolute
certified rates are untrustworthy until the airlight is calibrated (D4). Recorded, not
explained.

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

> **RETROSPECTIVE NOTE (2026-08-25, code audit).** The script behind this table,
> `scripts/fog_isolation.py`, contained the read-modify-write weather bug this repo
> documents in `carla_env.py`: it called `set_clear_weather()` and then immediately
> `world.get_weather()`, which returns the PREVIOUS tick's weather — so the "clear
> illumination held fixed" premise was never established, and the sweep plausibly ran
> under the map's default illumination. The table below is therefore unreliable beyond
> its own caveat. The fog behaviour that survives into the current record was
> re-measured by clean instruments (`scripts/fog_density_sweep.py`, constructed
> weather + settle ticks, and F46's interpolation test), and the non-monotonicity
> claim rests on those, not on this table. The script has been deleted; it is
> recoverable from git history at this commit's parent.

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

## F22 -- static-pose equilibrium does not predict local CTE (criterion retired)

The equilibrium criterion (`o* = ` where the disturbed policy emits the control that held
the lane) scored 7/8 on uniform poses, 6/8 on strength-stratified poses, and 3/8 as a
fraction-of-lap predictor. Rather than keep adjusting the pose sampling, its core
assumption was tested directly: at 263 route locations, compare the predicted equilibrium
offset against the CTE the vehicle actually reached there, from logged closed-loop traces.

    pooled Pearson r = -0.053   (n = 263)
    real CTE where predicted IN lane   0.249 m   (n = 232)
    real CTE where predicted OUT       0.045 m   (n =  31)

No correlation, and the sign is backwards: locations flagged out-of-lane are locations the
vehicle drove cleanly, while the shadows departure -- real CTE averaging 2.128 m -- sat at
locations the criterion called safe. The 7/8 was which poses happened to be sampled, not a
predictive relationship. **Retired.**

Two caveats keep this from being stronger than it is. Passing runs hold CTE near 0.04 m
everywhere, so there is little variance to correlate against outside the departures; and
`S_clear`/night matched zero poses because the departed vehicle left the route entirely.
The result is nonetheless sufficient to stop refining the criterion: a predictor whose
flagged locations are *cleaner* than its unflagged ones is not being under-sampled.

### Why every pointwise criterion has failed

Six now: analytic-model bias, measured-field bias, accumulation, restoring sign, restoring
sign over a bounded tube, equilibrium offset. F21 already identified the reason and this
confirms it -- closed-loop departure is a property of the TRAJECTORY, not of any frame or
pose on it. CTE at a location is set by the vehicle's history, not by local conditions, so
no quantity evaluated at a single pose can carry the answer.

### What follows

Bound the closed loop itself. All the pieces now exist: dense measured offset->image data
(40 poses x 13 offsets x 4 conditions), the affine interpolation between offsets already
validated at 0.011 residual, and the alpha-CROWN machinery. With lateral offset as a 1-D
state, the image as a verified affine function of it, and the bicycle model closing the
loop, the reachable offset tube can be propagated along the route and compared against the
0.668 m budget. That is verification predicting a closed-loop outcome rather than a
per-frame proxy for one.

## F23 -- the missing state was HEADING, and it explains every diverging tube

Closed-loop reachability diverged under every condition including clear weather, where the
real vehicle holds 0.13 m. Not a loose bound: with offset-only feedback the discrete
spectral radius is 1.115, so the loop is an undamped oscillator that MUST diverge. Every
capture in this study had placed the vehicle at lateral offsets with its heading ALIGNED to
the path, so the policy's response to heading error had never been measured -- the spring
was measured, the damper was not. Stability needs k_psi <= -0.5; measured values are -1.0 to
-2.4 in daylight.

With (offset x yaw) captured, a linearized criterion with NO fitted parameters

    FAIL if |lambda(A)| >= 1   or   |bias| > |k_o| * CTE_BUDGET

scored 7/8 in-sample against the corrected ground truth, missing only `S_clear`/shadows.
Night is caught by a ~4x collapse in control authority (k_o -0.178 -> -0.045).

## F24 -- two corrections that changed the numbers

**dt was wrong.** It had been derived from pose spacing over speed rather than the 0.2 s
control period. At 0.4 s the criterion read 8/8, but the shadows FAIL it appeared to catch
came from |lambda| = 2.05, which collapses to 0.80 at the true rate. Corrected: 7/8.

**Exposure followed the preset name, not the sun.** Sweeping sun altitude under
`condition="clear"` captured below-horizon scenes through the daylight camera, while `night`
declares 4x exposure. It produced `S_mixed` FAILING at night, which ground truth contradicts
outright, and that contradiction is what exposed it. Headlights and exposure now both key
off `sun_altitude_angle < 0`, which reproduces all three presets exactly.

## F25 -- P-06 refuted: the criterion sees the night mechanism, not the shadow mechanism

The criterion was frozen and committed (6a414d5) before any intermediate-altitude run.
Prediction: `S_clear` PASS at sun >= +8, FAIL at <= +3; `S_mixed` PASS everywhere.

    sun    +85  +75  +60  +45  +30  +22  +15   +8   +3    0   -5
    pred  PASS PASS PASS PASS PASS PASS PASS PASS FAIL FAIL FAIL
    S_clr PASS FAIL PASS FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL      3/7 scored

`S_mixed` also failed at +8, +3 and 0 where it was predicted safe -- the unsafe direction,
declared in advance as the more serious error. So the in-sample 7/8 did NOT generalise. The
criterion detects control-authority collapse (darkness) and is blind to cast shadows, which
it reads as healthy gain and small bias at the lane centre.

**A genuine model finding, independent of the criterion.** `S_mixed` passes at all three
altitudes it was trained on (+90 clear, +15 shadows, -25 night) and FAILS between them
(+8, +3, 0). Training on discrete condition presets does not cover the continuum joining
them, and 0 degrees -- sun exactly on the horizon, maximum direct glare -- is the worst
point, failing 10/10 while -5 passes 0/10.

## F26 -- eastbound captures are invalid; verification is scoped to westbound

Several sun-altitude failures are direction-specific (fixed sun azimuth: travelling east or
west puts the sun ahead or behind), so eastbound frames were captured to cover them. They
measured an INVERTED restoring gain (k_o +0.03 against westbound -0.24), which would score
7/8 -- and is an artefact. Validated against what the vehicle actually steered at the same
locations:

    westbound  captured steer at offset 0 vs driven:  mean |diff| 0.025
    eastbound  captured steer at offset 0 vs driven:  mean |diff| 0.208   (sd 0.225 vs 0.008)

Static placement does not reproduce eastbound driving. Manifest yaw is not the cause
(agrees with the path tangent to 0.02 deg over the captured span). Cause UNKNOWN. The
eastbound result is withdrawn, and every verification number in this study is measured
westbound only -- stated as a scope limit, not a hidden one. The four canonical conditions
are unaffected in kind: night and shadows fail 5/5 in BOTH directions.

## F27 -- the surrogate rollout predicts all eight cells (8/8)

Seven criteria failed before this one. What changed is not the bound but the discipline: the
measured surrogate is VALIDATED against the closed loop before anything is computed on it.

    gate A  captured steer at (0,0) vs the steer the vehicle actually used
            clear 0.006, shadows 0.010     (eastbound scored 0.208 and was rejected, F26)
    gate B  a rollout on the measured surfaces reproduces the departure LOCATION
            shadows: predicted x=9.0 y=125.4, real x=8.1 y=123.9  (1.6 m)
            night:   predicted x=-408.6,      real x=-439.7       (31 m, conservative --
                     the rollout departs EARLIER than the vehicle; the verdict is right but
                     location accuracy is claimed only for shadows)

Peak |o| from a rollout started at the lane centre, against the pre-registered 0.668 m
budget. Nothing here is fitted: the budget comes from lane and vehicle geometry, the
dynamics are the kinematic bicycle with measured wheelbase and steer limits, and the
steering surface is measured rather than modelled.

    model     condition   peak |o|    verdict   closed loop
    S_clear   clear         0.158      PASS     PASS  0/10
    S_clear   fog           0.268      PASS     PASS  0/10
    S_clear   night         5.120      FAIL     FAIL 10/10
    S_clear   shadows       0.797      FAIL     FAIL 10/10
    S_mixed   clear         0.072      PASS     PASS  0/10
    S_mixed   fog           0.081      PASS     PASS  0/10
    S_mixed   night         0.161      PASS     PASS  0/10
    S_mixed   shadows       0.072      PASS     PASS  0/10

8/8. The margin is not marginal: every passing cell peaks at 0.072-0.268 m and every failing
cell at 0.797-5.120 m, so the budget sits in a 3x gap rather than between adjacent values.
Fog passes, which matters -- it is where P-03 and the restoring-sign criterion both
over-predicted, and where `S_clear` is genuinely robust at every density (0/60 departures).

### Three requirements, each found by violating it

1. **Heading is a state.** Captures with the vehicle aligned to the path measure the spring
   and not the damper; the loop is then an undamped oscillator (F23).
2. **Sample at the control rate.** The same rollout on 4-5 m pose spacing scores 2/8 and
   fails every cell, because it holds a stale steering command across control steps. At
   1.79 m (= v * FIXED_DT) it scores 8/8. This is a hard requirement, not a preference.
3. **Validate before computing.** Gate A rejected the eastbound captures, which would
   otherwise have contributed a 7/8 built on an artefact.

### What this is, and what it is not

It is a prediction of closed-loop outcome from STATIC placements, with no closed-loop data
used and no fitted parameter. It is NOT a sound certificate. Four bounding formulations were
built and all four blew up (F23 and `certify_maximal_invariant.py`), for a measured reason:
alpha-CROWN's relaxation gap over one captured cell is 0.029-0.088 in steering units against
a closed-loop tolerance of 0.0120, so any abstraction inflates a 1 degree heading box to
2.2-4.7 degrees in one step and no invariant set survives. A real error was found and fixed
along the way -- the lifted bilinear cross term ranged over [-1,1] regardless of box size,
roughly doubling the gap -- and halving it was still not enough. Closing the remaining
factor needs captured cells about 3x finer in offset and heading, which is ~9x the frames:
a quantified path, not an unknown one.

The 8/8 is also not blind. Ground truth existed when the rollout was run. The distinction
from the earlier 7/8 and 14/14 results is that those tuned an aggregation until it agreed,
whereas this has no aggregation and no threshold to tune -- but that argument is weaker than
a committed out-of-sample prediction, and one should be run before the claim is published.

## F28 -- verification must span the whole lap; segment scoping flipped two verdicts

Zach: "You can't clip the road into segments and just test segments, it must be the full lap
but no intersection." Correct, and it was not a technicality.

Every verification capture had covered a 195-400 m window while the closed-loop test drives
1600 steps = 2861 m (the junction begins at 3008 m and is out of scope). Scoring a
segment-scoped prediction against a full-lap run compares two different roads. Re-captured
over the whole lap at sun +5 degrees, on the SAME method and the same models:

    model     195 m capture      full lap (0-2861 m)        closed loop
    S_clear   PASS  0.288 m      FAIL 6.845 m at 2284 m     FAIL 5/5, onset 2286 m
    S_mixed   PASS  0.065 m      FAIL 6.569 m at 2293 m     FAIL 4/5, onset 2717 m

Both verdicts flip from wrong to right, and `S_clear`'s predicted departure lands within
2 m of the real one on a 2.86 km lap. The P-07 "missed failure" was therefore a coverage
limit and nothing else -- the method never examined the road where the vehicle left the lane.

**Consequence for P-07's score.** The in-scope/whole-route split reported earlier is
withdrawn as a way of scoring: a 195 m prediction cannot be scored against a full-lap run in
either direction. The honest number for P-07 as committed is 6/10, and the fair re-test is a
full-lap capture at each altitude, not a re-interpretation of the segment result.

**Cost of the fix.** A full lap at control-rate spacing is 1600 poses x 9 offsets x 5 yaws =
72,000 frames, about 80 minutes of CARLA per condition. That is the price of a verification
result that spans the same road as the driving test, and it is not optional.

## F29 -- eastbound rejection confirmed, and the cause narrowed (F26 superseded in part)

F26 rejected the eastbound captures on a validation failure. Zach pushed back: data must not
be discarded because it does not fit, and the cause has to be found. Two candidate
explanations were tested and both are refuted.

**Not a sun-altitude confound.** The original eastbound capture was taken at
SUN_ALTITUDE_OVERRIDE=75 and compared against a CLEAR (sun 90) drive, so cast shadows were
confounded with a capture fault. Re-captured at true clear, matching the trace exactly:

    direction   captured   driven   mean|diff|   sd cap   sd drv   verdict
    eastbound     -0.166   +0.000       0.195    0.140    0.008    REJECTED
    westbound     -0.035   -0.022       0.015    0.027    0.017    USABLE

Eastbound is essentially unchanged (0.195 against 0.208). The confound was real but not the
cause.

**Not the sharpest corner, and not a position error.** The captured eastbound stretch is
nearly straight (median curvature 0.001 deg/m, against 0.689 westbound); the sharpest bends
are at 696 m east and 2234 m west, both outside it. And the manifest poses sit 0.055 m from
the line the vehicle actually drives -- CLOSER than westbound's 0.585 m, which validates
fine. So the vehicle is being placed in the right spot, at the right heading, and still
renders a view that produces a -0.166 steering bias where the real vehicle steers 0.000.

**Leading hypothesis: vehicle ATTITUDE under frozen physics.** `make_transform` sets YAW
ONLY -- pitch and roll are forced to zero -- and z is the ride height settled at the SPAWN
point, held fixed because physics is disabled before teleporting. The manifest records no z,
pitch or roll, so none of it is restored. On a stretch whose elevation or camber differs from
its spawn, the camera is then tilted or floating relative to the road surface, which is
exactly what a constant steering bias with correct position and heading looks like.

**Test, once CARLA is free:** re-enable physics and let the vehicle settle at each pose
before capturing, then repeat gate A. If eastbound drops to the westbound figure, attitude
was the cause and the same correction should be applied to every capture in the study --
westbound may be passing gate A only because its stretch happens to match its spawn.

Until then eastbound remains unusable and every verification number is westbound-only. That
is a measured limitation with a named candidate cause, not an unexplained exclusion.


## F30 -- sound per-frame verification over the disturbance interval is too conservative

The coverage claim scenario testing cannot make is: for EVERY intensity s in [0,1], at EVERY
pose, the steering stays inside the corridor. It was computed with alpha-CROWN over the
one-scalar family x(s) = x_clear + s*(x_cond - x_clear), full lap, 4 sub-intervals per pose.

    model     condition   max |dsteer| over s   poses over tol   closed loop
    S_clear   fog                      0.1114        16/40       PASS  0/10
    S_clear   night                    0.4124        38/40       FAIL 10/10
    S_clear   shadows                  0.2275        27/40       FAIL 10/10
    S_mixed   fog                      0.0903         6/40       PASS  0/10
    S_mixed   night                    0.0757        21/40       PASS  0/10
    S_mixed   shadows                  0.2494         4/40       PASS  0/10

Every cell is FALSIFIED against the 0.0120 corridor -- deviations run 6x to 34x it -- while
four of the six drive cleanly. Worse, the magnitudes do not rank with the outcomes:
`S_mixed` deviates MORE under shadows (0.2494) than `S_clear` (0.2275), and one passes while
the other departs on every run.

**This is not a loose bound.** Input-space branch and bound converges the relaxation to the
network's genuine output variation (0.0165 -> 0.0116 measured on a state box), so there is
nothing left to tighten -- and it is why SDP-CROWN would add nothing: its advantage is L2
geometry in high dimensions, and this input set is one scalar.

**It is the criterion that is wrong, and the reason is temporal.** Closed-loop departure
depends on whether a steering deviation PERSISTS, not on how large it is: a large deviation
that reverses sign every few frames integrates to nothing, while a small persistent one
walks the vehicle out of the lane (F21). A per-frame bound has no access to that structure,
so it must either be vacuous or unsound, and soundness makes it vacuous.

**Consequence for the study.** The per-frame corridor formulation -- which is what much of
the neural-network verification literature assumes transfers to control -- cannot deliver a
useful closed-loop claim here, however tight the bound. The only route left is to verify the
LOOP: bound the steering over a set of vehicle states and propagate that set through the
vehicle dynamics. That requires the (offset x heading) captures, so they are necessary rather
than merely convenient.

## F31 -- formal verification PROVES a vulnerability that 40 closed-loop runs missed

This is the coverage-assurance result the study exists to demonstrate.

`S_mixed` is the good model. It passes every cell in the ledger: clear, fog, night and
shadows, 0/10 departures each, 40 runs, both directions, reproduced on a freshly restarted
simulator. Scenario-based testing says it is safe.

At 204-208 m and 215 m of the westbound lap, alpha-CROWN proves it is not:

    state box   o in [+0.30, +1.00] m (right of lane centre)
                psi in [+3.0, +6.0] deg (pointed further right)
    a restoring policy must steer LEFT (negative) everywhere in that box

        204 m   steer lower bound  +0.0598    PROVEN UNSAFE
        206 m   steer lower bound  +0.2365    PROVEN UNSAFE
        208 m   steer lower bound  +0.0138    PROVEN UNSAFE
        215 m   steer lower bound  +0.0727    PROVEN UNSAFE

A POSITIVE LOWER BOUND means every state in the continuous box -- uncountably many, not a
grid -- produces steering to the right while the vehicle is already right of centre and
pointed right. There is no restoring action anywhere in the set.

**Why testing cannot find it.** The vulnerability only exists at heading errors of roughly
3 degrees or more. In nominal driving `S_mixed` holds 0.13 m of cross-track error and a
fraction of a degree of heading, so its trajectories never enter the region. Scenario-based
testing samples TRAJECTORIES; this samples the STATE SPACE. No number of laps fixes that,
because the states are not on any lap the policy drives.

**Why it is not an artefact.** Found in the full-lap capture at 205-208 m, then reproduced
by an INDEPENDENT capture hours later with its own settle pass and finer heading resolution,
which put it at 204-208 m with the same sign and the same heading dependence. Grid evaluation
alone is not proof -- both checks are finite -- so the certificate bounds the response over
the continuous box rather than at points.

**Stated soundness gap.** The bound is sound with respect to the bilinear image patch between
the four captured corners, with the cross term lifted into its own input dimension over the
exact product interval, which over-approximates the true patch. It is NOT a claim about
images CARLA would render strictly between captured states; that residual is the same one
declared throughout this study.

**What this does not claim.** It does not show the vehicle will reach those states in normal
operation -- that is a reachability question. It shows that IF it does, the policy has no
corrective action there, which is exactly the class of latent defect an assurance argument
based on driven miles cannot rule out.

## F32 -- the vulnerability search generalises, and it INVERTS the safety ranking

The westbound finding (F31) could have been one quirk of one stretch. It is not. Running the
same certificate over the full EASTBOUND lap, 1600 poses, same state box (o in [0.30, 1.00] m
right of centre, psi in [3, 6] deg pointed right):

    S_mixed   PROVEN UNSAFE at 32 of 1600 poses
              124, 254, 415, 421, 428, 430, 458, 466, 473, 480, 487, 494, 501, 508, 516,
              560, 582, 619, 626, 633, 641, 1029, 1785, 1792, 1846, 1848, 2030, 2032,
              2062, 2069, 2091, 2098 m
    S_clear   PROVEN UNSAFE at 0 of 1600 poses

With westbound (S_mixed 4, S_clear 0) that is 36 proven-unsafe state regions in one model
and none in the other. The eastbound defects cluster (415-641 m contains 15 of them) rather
than scattering, which is what a real feature of the road-policy interaction looks like
rather than noise.

**The ranking inverts.** Scenario testing says `S_mixed` is the safe model: 0/10 departures
in all four conditions, 40 runs, while `S_clear` departs 10/10 under night and 10/10 under
shadows. Verification says the opposite about latent state-space defects: `S_mixed` has 36
regions where NO restoring action exists, `S_clear` has none anywhere on either lap.

**Why both statements are true and not contradictory.** They answer different questions.
Closed-loop testing asks "does this policy leave the lane on the trajectories it drives?"
Verification asks "does a corrective action exist at every state the vehicle could occupy?"
`S_mixed` never visits its defective states in nominal driving -- it holds 0.13 m of
cross-track error and a fraction of a degree of heading -- so testing cannot reach them, at
any mileage. `S_clear` fails visibly and often, which is arguably the safer failure mode:
its deficiency is discoverable by driving.

**The assurance argument.** A safety case built on driven miles would certify `S_mixed` and
reject `S_clear`. It would be right about behaviour on the nominal trajectory and blind to
36 states in which the certified policy has no corrective action. That blindness is
structural: sampling trajectories cannot cover a state space, and no confidence interval on
miles driven repairs it.

**Bounds of the claim.** PROVEN UNSAFE means no restoring action exists anywhere in the
state box; it does NOT mean the vehicle will reach that box, which is a separate reachability
question this study does not answer. The bound is sound with respect to the bilinear image
patch between captured corners, with the cross term lifted over its exact product interval.

## F33 -- CORRECTION to F32: counting proven regions is not a safety metric

Zach questioned a table showing `S_mixed` with more proven-unsafe regions in CLEAR weather
(2.0% of the lap) than `S_clear` has at NIGHT (1.1%) -- the trained-for condition of the good
model looking worse than the failing condition of the bad one. He was right to. The counts
are not comparable.

"PROVEN UNSAFE" requires a strictly positive LOWER bound. That conflates how bad the policy
is with how provable it is, and provability depends on bound width, which depends on network
size (8/16/16 against 24/48/48). Measuring the response directly inside the same box, with
no bounds involved:

    model     condition   measured non-restoring   mean k_o    proven-unsafe
    S_clear   clear            43.3%                -0.0996        0.0%
    S_clear   night            77.7%                +0.0281        1.1%
    S_mixed   clear            42.0%                -0.1188        2.0%
    S_mixed   night            19.6%                -0.2051        0.1%

The measured behaviour is exactly what the study predicts and what the driving tests say.
`S_clear` COLLAPSES at night: 43% to 78% non-restoring, with the mean gain flipping POSITIVE
-- anti-restoring on average across the box. `S_mixed` IMPROVES at night: 42% to 20%, gain
nearly doubling. In clear weather the two are equivalent. `S_clear`/night is 77.7%
non-restoring in reality and only 1.1% provable, because the bounds there are too wide to
certify what is plainly happening.

**What survives.** Each individual certificate is sound: a positive lower bound is a proof,
so those regions really do lack any restoring action, and the reachability result stands
(`S_mixed` holds 0.062 m where its defects begin at 0.30 m; 0 of 32 entered).

**What does not.** F32's claim that verification "inverts the safety ranking" rested on
comparing these counts and is WITHDRAWN. Ranked by measured behaviour, verification agrees
with the driving tests about which model is better.

**The methodological lesson.** A verifier reports what it can prove, not what is true. Any
metric built on counting successful proofs silently rewards models whose bounds are loose.
Cross-model and cross-condition comparisons must use a quantity that does not depend on
provability -- the measured response, or a bound-width-normalised score -- and certificates
should be used for what they are: sound evidence about a specific set, not a scoreboard.

## F34 -- the per-frame route works: SUSTAINED bias, not maximum deviation (F30 corrected)

Zach: "would a cheap approximation work like just integrating the steering error bounds?"
Yes, and it corrects F30.

`CLOSED_LOOP_TOLERANCE` = 0.0120 is defined as the steering error which, SUSTAINED for
T_CLOSED_LOOP_S = 1.85 s, carries the vehicle to the edge of its lane. F30 compared it
against the MAXIMUM steering deviation. That is dimensionally the wrong quantity: the maximum
is dominated by transients that reverse sign and integrate to nothing. The MEAN deviation is
the sustained component the threshold actually describes.

    persistent bias = mean over the lap of ( steer(disturbed) - steer(clear) )
    FAIL  iff  |persistent bias| > CLOSED_LOOP_TOLERANCE

    direction   model     condition   bias      x tol   verdict   closed loop
    westbound   S_clear   clear      +0.00000    0.00    PASS      PASS  0/10
    westbound   S_clear   fog        -0.00540    0.45    PASS      PASS  0/10
    westbound   S_clear   night      -0.07064    5.88    FAIL      FAIL 10/10
    westbound   S_clear   shadows    -0.01628    1.36    FAIL      FAIL 10/10
    westbound   S_mixed   clear      +0.00000    0.00    PASS      PASS  0/10
    westbound   S_mixed   fog        -0.00033    0.03    PASS      PASS  0/10
    westbound   S_mixed   night      -0.00250    0.21    PASS      PASS  0/10
    westbound   S_mixed   shadows    +0.00162    0.14    PASS      PASS  0/10
    eastbound   S_clear   night      -0.06016    5.01    FAIL      FAIL 10/10
    eastbound   S_clear   shadows    -0.01667    1.39    FAIL      FAIL 10/10
    eastbound   S_mixed   night      -0.00227    0.19    PASS      PASS  0/10
    eastbound   S_mixed   shadows    +0.00178    0.15    PASS      PASS  0/10

14/14, both directions, eastbound reproducing westbound independently. Every passing cell is
at or below 0.45x tolerance and every failing cell at or above 1.36x -- a 3x gap with the
threshold inside it, so this does not depend on where the threshold sits within that gap.

**Nothing is fitted.** The tolerance derives from lane width, vehicle width, wheelbase,
speed and a closed-loop time constant measured long before this criterion existed. The
statistic is an unweighted mean over every pose on the lap. There is no aggregation choice,
no envelope, no pose selection.

**It is PER-FRAME.** No vehicle dynamics are simulated and no trajectory is rolled out. The
seven retired criteria and the propagation work were all attempts to reach the trajectory
level; the answer was to use the right per-frame statistic instead.

**Why F30 got the opposite answer.** Max deviation does not even ORDER the cells correctly
(`S_mixed` deviates more under shadows than `S_clear` does, and passes while `S_clear` fails
10/10), so no threshold could rescue it. The mean does, by 3x.

**Two caveats before this is written up.** It is computed from RENDERED condition frames, so
it is a measurement; the verification form bounds the same mean over the declared interval
s in [0,1] with alpha-CROWN, which is a direct extension and not yet run. And it is
IN-SAMPLE -- ground truth was known. Three committed blind predictions have already failed
after looking strong in-sample (P-03 2/6, P-06 3/7, P-07 6/10), so a blind test is required
before any claim. Eastbound fog is the one missing cell.

**A bug worth recording.** The first run of this scored 8/14 because the nominal path was
read as `frames[:, 0, 0]` -- the CORNER of the offset/heading grid, -1.5 m off centre and
-6 deg of heading -- instead of its centre. Nominal-only captures have a 1x1 grid where the
two coincide, which is why only the full-grid captures were wrong.

## F35 -- bounding the sustained bias over the declared interval

F34 MEASURED the persistent bias at the rendered condition. This bounds it over every
intensity in the declared interval, x(s) = x_clear + s*(x_cond - x_clear) for s in [0,1],
which is the for-all claim scenario testing cannot make. Three things came out of it.

**A verdict-logic error, corrected.** The safety property is "safe at EVERY intensity", so
ANY violation falsifies it. The first version required the WHOLE bias interval to lie
outside the corridor before reporting FALSIFIED -- which asks whether the model is unsafe at
every intensity, a different and much weaker statement. It scored 6 of 10 cells INCONCLUSIVE.
With the correct rule the same bounds give 8/10.

**Interior peaks are real, and they matter for the coverage argument.** Sampling s directly:

    model     cond      worst |bias|   at s    endpoint
    S_mixed   night        0.33x tol    0.8      0.22x
    S_mixed   shadows      0.08x        0.6      0.06x
    S_mixed   fog          0.16x        0.6      0.03x
    S_clear   night        6.21x        1.0      6.21x
    S_clear   shadows      1.70x        1.0      1.70x
    S_clear   fog          0.57x        1.0      0.57x

`S_mixed` is worst at INTERMEDIATE intensity in all three conditions, not at the endpoint --
0.8 for night, 0.6 for shadows and fog. Scenario testing renders the full condition and
would miss the worst case, though here the peaks are far inside the corridor so nothing is
hidden. Measured over the whole interval the criterion is 6/6.

**The remaining misses are bound looseness, not defects.** At NSPLIT = 4 the bound on
`S_mixed`/night reads -0.0128 (1.07x tol) against a true worst of -0.0039 (0.33x) -- 3.3x
conservative, enough to falsify a model that is safe at every intensity. That is the
relaxation, and branch-and-bound is the fix; NSPLIT = 16 is running.

This is the difference between a sound certificate and a measurement. The measurement says
6/6. The certificate says 8/10 and will say more once the relaxation is tightened -- and
unlike the measurement it covers intensities never rendered.

## F36 -- STEP 4 ACHIEVED: sound certificate over the disturbance interval, 10/10

The study's contribution, from CLAUDE.md: "Apply formal verification to both, and get the
same answer without simulating." This is that result.

    for EVERY intensity s in [0,1], at EVERY pose on a full lap (intersection excluded):
        persistent bias = mean( steer(x(s)) - steer(x(0)) )
        SAFE iff |persistent bias| <= CLOSED_LOOP_TOLERANCE

alpha-CROWN with 16-way input-space branch and bound, both directions:

    dir    model     cond      bias bound (x tol)   verdict      closed loop
    west   S_clear   fog       [-0.75, +0.29]       CERTIFIED    PASS  0/10
    west   S_clear   night     [-6.96, +0.93]       FALSIFIED    FAIL 10/10
    west   S_clear   shadows   [-2.26, +0.64]       FALSIFIED    FAIL 10/10
    west   S_mixed   fog       [-0.25, +0.38]       CERTIFIED    PASS  0/10
    west   S_mixed   night     [-0.61, +0.26]       CERTIFIED    PASS  0/10
    west   S_mixed   shadows   [-0.29, +0.31]       CERTIFIED    PASS  0/10
    east   S_clear   night     [-5.99, +1.28]       FALSIFIED    FAIL 10/10
    east   S_clear   shadows   [-2.40, +0.65]       FALSIFIED    FAIL 10/10
    east   S_mixed   night     [-0.76, +0.31]       CERTIFIED    PASS  0/10
    east   S_mixed   shadows   [-0.25, +0.39]       CERTIFIED    PASS  0/10

10/10. Tightening branch and bound from 4 to 16 splits moved `S_mixed`/night from -1.07x to
-0.61x and certified it, confirming that miss was relaxation looseness rather than a defect,
exactly as direct sampling of the interval had predicted (true worst 0.33x).

**What is proven.** Sound bounds, not sampling. The claim quantifies over a continuum of
intensities, including the interior peaks where `S_mixed` is worst at s = 0.6-0.8 rather than
at full strength -- operating points no closed-loop run renders. Per-pose bounds are averaged,
which lets s differ BETWEEN poses, so the certificate also covers spatially varying
disturbance rather than one global intensity.

**No fitted parameters.** CLOSED_LOOP_TOLERANCE derives from lane width, vehicle width,
wheelbase, speed and a closed-loop time constant fixed long before this criterion existed.
The statistic is an unweighted mean over every pose. There is no threshold, envelope,
aggregation rule or pose selection to tune.

**Declared gaps.**
- Two cells missing: eastbound fog was never captured (the simulator died mid-run).
- IN-SAMPLE. Ground truth was known. Three committed blind predictions have failed after
  looking strong in-sample (P-03 2/6, P-06 3/7, P-07 6/10), so a blind test at untested
  operating points is required before this is claimed in print. It needs full-lap captures;
  195 m segments cannot be scored against full-lap driving results (measured: `S_clear`/fog
  flips verdict between the two scopes).
- Sound with respect to the affine family between the clear and rendered frames, which is
  exact in projection (1.2e-7) but is not a claim about images CARLA would render at
  intermediate intensities.

## F37 -- final table: 12/12 canonical, 2/4 blind

Eastbound fog completed the set (it had been saved under a filename the certifier did not
look for, which is why it read "capture missing" three times).

    dir    model     cond      bias bound (x tol)   verdict      closed loop
    west   S_clear   fog       [-0.75, +0.29]       CERTIFIED    PASS  0/10
    west   S_clear   night     [-6.96, +0.93]       FALSIFIED    FAIL 10/10
    west   S_clear   shadows   [-2.26, +0.64]       FALSIFIED    FAIL 10/10
    west   S_mixed   fog       [-0.25, +0.38]       CERTIFIED    PASS  0/10
    west   S_mixed   night     [-0.61, +0.26]       CERTIFIED    PASS  0/10
    west   S_mixed   shadows   [-0.29, +0.31]       CERTIFIED    PASS  0/10
    east   (same six cells, same verdicts)

12/12, both directions, sound bounds over every intensity in the declared interval, no
fitted parameters, per-frame with no vehicle dynamics simulated.

**And 2/4 on the blind cells (P-08b).** `S_mixed` at +22 sun is CERTIFIED at 0.31x and 0.41x
of tolerance and departs on all ten runs. The two results are not in tension: the canonical
conditions all fail through SUSTAINED drift, which a lap-wide mean detects, while +22 fails
through brief repeated excursions (0.2-0.9% of lap) that the same mean dilutes across ~1,590
clean poses.

**The defensible claim.** A sound per-frame certificate over a physically parameterised
disturbance interval reproduces closed-loop outcomes for failures that are sustained. It
does not detect localised ones, and a committed blind test showed that in the unsafe
direction. Both halves belong in the writeup; the second is what tells a reader where the
method's edge is.

## F38 -- windowing and a feedback-derived tolerance: 7/9, and +22 sits at 0.84-0.91

Zach asked whether there is a middle ground between the maximum (blind to persistence) and
the lap mean (blind to localisation), and whether the threshold could be retuned. Both
questions turned out to be answerable without new data.

**A windowed mean is the statistic the tolerance actually describes.**
CLOSED_LOOP_TOLERANCE is defined for an error SUSTAINED over T_CLOSED_LOOP_S = 1.85 s, which
at 8.94 m/s is 16.5 m -- a window, not a lap. Sweeping window length over the nine cells:

    window   poses  max PASS  min FAIL  ratio
      8.9m       5     10.71     12.81   1.20
     16.1m       9      6.35      7.27   1.15
     26.8m      15      3.98      4.36   1.10
     44.7m      25      2.70      2.77   1.03
     71.5m      40      2.30      2.11   0.92   <- ordering inverts
    357.6m     200      0.96      0.77   0.81
   2843.1m    1590      0.46      0.10   0.22   <- the lap mean

At 9-45 m windows the ordering is CORRECT for all nine cells, including the blind +22 cell
the lap mean certified. But every value sits 2.7-13x above a threshold of 1.0, so the fixed
tolerance falsifies everything. Ordering right, scale wrong.

**The scale error has a physical cause, and correcting it is a derivation not a fit.**
The tolerance assumes a steering deviation integrates into lateral motion with NO corrective
response. The policy corrects continuously, so the admissible bias is what its own restoring
gain can absorb: tolerance = |k_o| * CTE_BUDGET_M, which is POLICY-SPECIFIC. With k_o
measured from the (offset x heading) captures:

    S_clear   k_o 0.2556  ->  tol 0.1707   14.2x the open-loop value
    S_mixed   k_o 0.1550  ->  tol 0.1035    8.6x

That recovers the ~10x gap from measured quantities, with no parameter fitted to outcomes.

**Result: 7/9, and the two misses are marginal rather than gross.**

    model     cell      windowed / derived tol   verdict   drive
    S_clear   fog                        0.26     PASS     PASS
    S_clear   night                      1.61     FAIL     FAIL
    S_clear   shadows                    1.22     FAIL     FAIL
    S_clear   sun+22                     0.91     PASS     FAIL   <- miss
    S_mixed   fog                        0.51     PASS     PASS
    S_mixed   night                      0.67     PASS     PASS
    S_mixed   shadows                    0.44     PASS     PASS
    S_mixed   sun+45                     0.74     PASS     PASS
    S_mixed   sun+22                     0.84     PASS     FAIL   <- miss

Under the lap mean these cells were certified at 0.24x -- deeply, wrongly safe. Three
independent corrections (windowing, feedback-derived tolerance, per-policy gain) each moved
them toward the boundary without crossing it: 0.84 and 0.91.

**What that pattern suggests, stated as a hypothesis and not a result.** Every correction
that improves the other seven leaves +22 just under the line. That is more consistent with a
systematic factor of ~1.2 than with a wrong statistic -- but with only TWO failing cells of
this type, it cannot be distinguished from coincidence. Resolving it needs more localised
failures, which means more sun angles, split IN ADVANCE into a calibration set that fixes
the window and a held-out set not examined until scoring. P-08 was compromised precisely by
choosing operating points whose outcomes were already known.

**Rain under this technique.** The measured-endpoint approach needs a rendered endpoint,
which rain supplies, but rain is STOCHASTIC: two renders at one pose differ, so x_rain is not
a point. The extension is to capture N realisations and verify over the CONVEX HULL of
{clear, rain_1, ..., rain_N} -- an N-dimensional input set alpha-CROWN handles directly, and
a richer family than a single line. Sound over the sampled realisations, not over the
distribution. Unchanged and out of reach: rain lowers tire friction, which a
perception-to-steering verifier structurally cannot observe.

## F39 -- P-09 resolves F38's hypothesis: the ~1.2x factor was coincidence, and the statistic is wrong

F38 left a hypothesis: every correction moved the two `+22` misses toward the boundary
without crossing it (0.84, 0.91), which looked more like a systematic ~1.2x factor than a
wrong statistic -- but with two failing cells it could not be told from coincidence. P-09
added cells of that type, with the calibration/held-out split declared before any capture
(`results/predictions/P09_sun_angle_design.md`) and the held-out verdicts committed before
either was driven (`070a2b2`).

    cell   role          certificate   x tol (W/E)    driven        outcome
    +60    calibration   PASS          0.72 / 0.91    PASS  0/10    agree
    +30    calibration   PASS          0.73 / 0.89    FAIL 10/10    MISS
    +37    held out      PASS          0.73 / 0.93    FAIL  3/10    MISS
    +15    held out      PASS          0.68 / 0.87    PASS  0/10    agree

    held out 1/2, overall 2/4 -- the same score as P-08b, on the same failure mode

**It is not a scale factor.** All four cells sit in a 0.68-0.93 band while the driven
outcomes span 0/10 to 10/10. A single multiplicative correction cannot separate cells that
the statistic does not order.

**The window is not the missing parameter either.** Step 2 of the protocol permitted tuning
the window on the calibration cells. Swept from 5.4 m to the full lap, the PASSING cell's
statistic exceeds the FAILING cell's at EVERY length:

    window     poses   max PASS   min FAIL   ratio
      5.4 m        3    0.23730    0.15994    0.67
     16.1 m        9    0.09375    0.07553    0.81
     44.7 m       25    0.03236    0.03154    0.97
    143.1 m       80    0.01303    0.00884    0.68
   2843.1 m     1590    0.00235    0.00040    0.17

Never above 1.0. The ordering is inverted at every scale, so no threshold and no window
repairs it, and nothing was fitted.

**Why, located.** `+30` eastbound departs reproducibly at (x=-20, y=100..240), ~1990 m into
the lap. At that pose the windowed steering deviation reads 0.00151 and ranks 1064th of 1599
poses; for the passing `+60` it reads 0.00009, ranked 1569th. Both cells' lap maxima occur at
the SAME pose 578, unrelated to either outcome.

There is nothing to see on the nominal path. That is the whole explanation for why eight
criteria built from centreline steering have landed at chance on this mode: they are all
functions of a measurement that does not contain the failure.

**The candidate that remains.** A lane-keeping policy is stable because steering responds to
lateral offset with a restoring gain `k_o = d(steer)/d(offset)` of the correcting sign.
Steering can be exactly right at zero offset while the RESPONSE to being off-centre is flat
or inverted; drift then stops being corrected. This is invisible to any nominal-path
statistic by construction, and it fits the direction dependence (eastbound departs 29-43 ft,
westbound exceeds budget by 1-2 ft at the same angle) and the small `frac_over_budget`.
Under test by capturing the (offset x heading) grid at +30, +60 and clear over 1800-2200 m.

If it holds, the property to certify is the GAIN rather than the bias -- a bound on the
policy's stability rather than on its output, and a stronger claim than the one that failed.

**What is untouched.** The canonical twelve cells stand at 12/12 (F34-F37). Those conditions
fail in the sustained way the criterion is built for. This is a distinct failure type and the
honest statement, already written into the paper's limitations, is that the per-frame
sustained certificate does not detect it.

## F40 -- the failure IS reproducible from captured frames, but the deviation model is not calibrated

F39 established that the localised failure leaves no signature on the nominal path. The
obvious response is the one F30 already named as the only route left: stop scoring the
centreline and roll the vehicle state forward over the (offset x heading) grid.

Captured 9 offsets x 5 headings over 1800-2200 m eastbound at +30 (departs 10/10), +60
(clean 0/10) and clear, and integrated the deviation dynamics using ONLY captured frames:

    o'   = o + v dt psi
    psi' = psi + (v dt / L) MAX_STEER_RAD ( S_cond,i(o, psi) - S_clear,i(0, 0) )

**On the two sun cells it reproduces closed-loop driving, quantitatively.**

    cell   rollout max |o|   driven
    +60             0.243 m  PASS  0/10
    +30            11.387 m  FAIL 10/10, measured departure 8.8-13.2 m

No simulator in the loop. The predicted magnitude lands inside the measured range.

**And it localises the cause, which is upstream of the symptom.** Divergence begins near
y = 54..61, where `+30`'s restoring gain INVERTS sign (+0.0222, +0.0204) while clear and +60
stay correcting (-0.095, -0.100) -- local positive feedback, the policy steering further off
lane. Peak CTE occurs ~150 m downstream at y = 100..240. That is why every statistic aimed at
the departure site read zero: cause and symptom are in different places.

**But it is NOT a criterion, and the reason is measured, not suspected.** Run against the
canonical cells it scores 2/6, and the failures are not edge cases:

    model     cond      rollout max |o|   driven    
    S_clear   fog             17223 m     PASS  0/10   false FAIL
    S_mixed   fog                 5.6 m   PASS  0/10   false FAIL
    S_mixed   night               6.6 m   PASS  0/10   false FAIL
    S_mixed   shadows          7094 m     PASS  0/10   false FAIL

Two candidate excuses were tested and both fail:

- *Extrapolation past the grid.* The grid spans +-1.5 m and a departure reaches 13 m, so
  beyond the edge `interp` clamps and the dynamics are fictional. But `S_mixed` fog breaches
  the 0.668 m budget at 1.010 m -- INSIDE the grid, where every value is measured. The false
  alarm is real, not an artefact of leaving the domain.
- *Integration length.* Shortening the window to 45 poses (81 m) with the state reset at each
  window start still gives `S_clear` fog 23.1 m against a clean drive.

**What that means.** The model over-predicts drift by roughly 2x. It omits steering actuation
lag, the throttle/speed controller, and the difference between a kinematic bicycle and CARLA's
tyre model. A 2x error turns a real 0.5 m excursion into a modelled 1.0 m one, which crosses a
0.668 m budget -- so the verdicts are dominated by model error, not by the disturbance.

**Status: promising direction, not a result.** Making it a criterion requires validating the
deviation dynamics against measured CTE traces before any verdict is read off it, and a grid
wide enough to contain the recovery envelope (+-1.5 m is not). That is the "verify the loop"
programme F30 identified, and it is a piece of work, not an overnight adjustment.

**Unchanged.** The canonical twelve stand at 12/12 under the sustained per-frame certificate
(F34-F37). The localised mode remains undetected, which is what the paper's limitations say.

### F40 addendum -- the over-prediction is 36x, and its cause is the off-nominal surface

Calibrated the rollout against a MEASURED cross-track trace
(`results/traces/Smixed_fog_fog_westbound_rep00.csv`, 1600 steps of x, y, yaw, steer, cte_m).

    measured  |cte| max 0.155 m, mean 0.029 m
    modelled  |o|   max 5.609 m          -> over-prediction 36.3x, not the ~2x first estimated

The estimate of "roughly 2x" above was wrong and is corrected here.

**It is not the integrator, and it is not a physical modelling gap.** A stable loop driven by
bounded forcing settles near `excess / |k_o|` = 0.0063 / 0.154 = 0.04 m. The rollout should
have sat at four centimetres. That it runs to 5.6 m means the loop it is integrating is not
the stable one the pole analysis measured (mean rho 0.75).

**The cause is that the off-nominal surface is not accurate enough to integrate.** Evaluating
the network at the vehicle's MEASURED offset and comparing to the steering it actually
commanded:

    mean |error| 0.00490 normalised = 0.005987 rad     correlation +0.769
    disturbance driving term                0.006327 rad

The surface error is 0.95x the size of the signal being integrated. Gate A validated the
NOMINAL captures against driven steering (0.0137 over a full lap, threshold 0.05); the
off-nominal placements were never held to that standard, and this is the first measurement of
them. A per-frame verdict tolerates that error because it never accumulates. A rollout
integrates it, so noise of the same magnitude as the disturbance dominates within a few
seconds.

**Consequence.** The rollout route needs the off-nominal captures validated the way the
nominal ones were -- a gate-A equivalent at every grid point -- BEFORE any verdict is read
from it. Until then its agreement on +30 and +60 is not evidence: those cells simply have an
effect large enough to outrun the noise. That is the honest reading of tonight's result.

## F41 -- the off-nominal captures fail a gate-A equivalent, by 4-5x the signal

F40's addendum blamed the rollout's 36x over-prediction on the accuracy of the off-nominal
surface. This measures it directly, on three cells, using the driven traces (which record
x, y, yaw, steer and cte at every step) and including HEADING error, not just offset -- the
first pass evaluated at zero heading and some of its error was that omission.

Predicted steering at the vehicle's measured (offset, heading) vs what it actually commanded:

    cell                |offset| band     n     mean |err|     p95
    S_mixed  fog          0.00-0.15    1599       0.00469   0.01325
    S_clear  night        0.00-0.15      10       0.03441   0.08430
                          0.15-0.40       8       0.02925   0.07367
                          0.40-0.80      10       0.03417   0.07664
                          >1.50          37       0.38833   0.60782
    S_clear  shadows      0.00-0.15     501       0.02101   0.06173
                          0.15-0.40     122       0.02696   0.07734
                          0.40-0.80      10       0.04832   0.11843
                          >1.50         332       0.20916   0.32330

Including heading barely moved `S_mixed` fog (0.00490 -> 0.00469), so the discrepancy is the
surface, not the missing state.

**Against the two references that matter.** Gate A on the NOMINAL captures achieved 0.0137
against a 0.05 threshold. The disturbance driving term the rollout integrates is 0.0063 rad
= 0.0052 in normalised units.

    in-grid off-nominal error   0.021 - 0.048     (shadows bands have the sample size)
    nominal capture error       0.0137
    disturbance signal          0.0052

The off-nominal captures are 1.5-3.5x less faithful than the nominal ones, and their error is
**4-5x the disturbance effect** being integrated. Beyond the grid (>1.5 m) it reaches 0.21-0.39,
as expected where `interp` clamps and there are no measurements at all.

**Why this matters and why it went unnoticed.** A per-frame verdict compares one bound to one
threshold, so a surface error of 0.02 is harmless. A rollout integrates that error every
step, so within a few seconds it dominates whatever the disturbance did. The captures were
built for the per-frame use and are adequate for it; they are not adequate for the loop, and
nothing before tonight had tested them at off-nominal states.

**The likely cause, and the next experiment.** Off-nominal frames come from STATIC placement:
the vehicle is teleported to an offset and settled. A vehicle actually driving at that offset
is steering to correct, and carries suspension pitch and roll from that steering which the
static placement does not reproduce. Testing that means capturing frames from a vehicle
DRIVEN through a known offset -- a perturbed closed-loop run -- and comparing against the
static capture at the same pose. That is the gate the off-nominal grid has to pass before any
rollout verdict can be believed.

**Unchanged.** The canonical twelve stand at 12/12 under the sustained per-frame certificate.
This finding constrains the loop-verification route, which was never part of that claim.

## F42 -- static placement does not reproduce what the camera sees while driving

F41 named the suspect: off-nominal frames come from teleporting the vehicle to an offset and
settling it under physics, while a vehicle actually at that offset is steering to correct and
carries the resulting suspension state. This tests it against frames the car really met.

Logged every frame of six `S_clear`/night runs with `--log-frames` (748 frames with a
cross-track reading; night departs, so the vehicle transits the whole grid on its way out).
For each frame whose measured (offset, heading) lands within 0.25 m and 3 deg of a grid node,
compared the STATIC capture at that pose and node against the DRIVEN frame.

The grid is coarse relative to the effect -- `k_psi` is about -1.29 rad/rad, so 3 deg of
heading mismatch alone is ~0.055 of steering -- so the node prediction is corrected to the
driven state to first order with the local measured gains before comparing. That correction
removed only 14% of the discrepancy (0.0301 -> 0.0258), so quantisation is not the story.

    n = 198 matched frames

    image difference     0.0142 per pixel        night's own disturbance is 0.142
    steering difference  0.0258 mean, 0.0827 p95, 0.1442 max

    for reference   nominal gate A          0.0137
                    disturbance driving term 0.0052

    |offset| band      n    img err   steer diff
      0.00-0.15       86     0.0147      0.03048
      0.15-0.40       78     0.0135      0.02204
      0.40-0.80       34     0.0143      0.02281

**Two things follow.** The images genuinely differ: 0.0142 per pixel is 10% of the entire
night disturbance the study is trying to certify against. And the steering discrepancy,
0.0258, is 5x the disturbance effect a rollout integrates and about twice the nominal gate A
figure.

**It is flat across offset.** 0.030, 0.022, 0.023 across the three bands -- the discrepancy is
not something that appears off-nominal, it is present at the centreline too. So it is not
about lateral placement; it is about the difference between a settled, stationary vehicle and
a moving one.

**Read this with its caveat.** These frames come from DEPARTING runs, where the vehicle is
turning hard and dynamic effects are at their largest. The typical-driving discrepancy is
likely smaller, and gate A's 0.0137 on nominal captures is evidence that it is. What the
measurement establishes is the ceiling: static captures are not interchangeable with driven
frames at the precision a rollout needs.

**Consequence.** The per-frame certificate is unaffected -- it compares one bound to one
threshold and never accumulates this error, and its captures passed the gate built for that
use. The loop-verification route needs captures taken from a MOVING vehicle at a commanded
offset, not from a teleported one. That is a capture-rig change, and it is the first thing to
build if the loop route is pursued.

## F43 -- the eastbound fog cell was certified against a baseline from another session

Checking whether the committed 12/12 is reproducible turned up something else. Every cell
takes its two endpoints from two different files,

    clear      <- results/calibration/lap_{dir}_clear.npz
    condition  <- results/calibration/lap_{dir}_{cond}.npz

and those are separate CARLA sessions, recorded hours apart. The certificate interpolates
between them, `x(s) = x_clear + s (x_cond - x_clear)`, so the clear endpoint defines the
disturbance exactly as much as the condition endpoint does. Anything that drifted globally
between the two sessions sits inside `(x_cond - x_clear)` and gets bounded as if it were
weather.

**`lap_eastbound_fog.npz` is the one capture that recorded its own clear frames**, at
identical poses (max |dx| = |dy| = 0.0), which makes it the only cell where this can be
measured rather than argued.

    the two eastbound CLEAR captures, same poses, different sessions
      signed mean   +0.04899        <- equals the abs mean, so it is a uniform offset
      abs mean       0.04912
      std            0.02076
      present at 100% of poses, flat along the whole lap

A uniform brightening of ~0.049 per pixel, not noise and not misalignment. Against fog's own
disturbance of 0.0594 that is **83% of the signal**.

**It inverts the sign of the fog disturbance.** Cross-direction consistency shows which
captures are sound and which are not:

    cond        W |mag|   E |mag|  rel gap    W signed   E signed
    fog          0.0710    0.0421   40.7%     -0.0348    +0.0149   <- sign flip
    night        0.1418    0.1424    0.4%     -0.0614    -0.0607
    shadows      0.1305    0.1300    0.3%     -0.1288    -0.1284

Night and shadows reproduce across directions to 0.3-0.4% in both magnitude and signed mean.
Fog does not: the same preset reads as darkening westbound and BRIGHTENING eastbound, which
is not something fog can do. Re-paired against its own clear, eastbound fog lands on the
westbound value:

    eastbound fog vs its INTERNAL clear   |mag| 0.0594   signed -0.0341
    westbound fog                         |mag| 0.0710   signed -0.0348

Signed means agree to 2%, and the sign flip is gone.

**Effect on the certificate** (`scripts/baseline_pairing_probe.py`, eastbound fog, stride 8,
NSPLIT 16 -- identical arithmetic to the certifier):

    model     baseline    measured bias   x tol            bound         x tol     verdict
    S_clear   external      -0.00644      -0.54   [-0.00984,+0.00348] [-0.82,+0.29] CERTIFIED
    S_clear   internal      -0.00038      -0.03   [-0.00541,+0.00469] [-0.45,+0.39] CERTIFIED
    S_mixed   external      +0.00220      +0.18   [-0.00259,+0.00512] [-0.22,+0.43] CERTIFIED
    S_mixed   internal      +0.00077      +0.06   [-0.00206,+0.00306] [-0.17,+0.26] CERTIFIED

**Both verdicts are unchanged, and the corrected numbers are better.** The measured bias falls
17x for `S_clear` (-0.54x to -0.03x) and the bound tightens from -0.82x to -0.45x. -0.82x was
the closest any CERTIFIED cell sat to the corridor edge in the published table, so correcting
it widens the separation from the falsified cells rather than narrowing it: the worst
certified cell becomes westbound `S_clear` fog at -0.75x against a worst falsified -2.26x, a
genuine 3.0x gap where the paper had claimed 3x off a 2.76x ratio.

**Scope: this is one cell, and the other eleven have positive evidence.** Only eastbound fog
carries an internal baseline, so only it could be repaired directly. But the 0.3-0.4%
cross-direction agreement for night and shadows is exactly what a drifting baseline would
destroy, and westbound fog's signed mean matches the corrected eastbound value to 2%. The
contamination is isolated to the cell that was captured last, on its own, to fill the gap
F37 records ("saved under a filename the certifier did not look for").

**Fixed** in `certify_sustained_bound.py`: a condition capture that recorded its own clear
frames is now paired against those, and which baseline was used is printed and stored in
`sustained_bound.json` (`"baseline": "paired" | "foreign"`) rather than chosen silently.

**What this does NOT touch.** The verdict count is still 12/12 and every westbound number is
unchanged -- the published Table I is westbound and is unaffected. What changed is one
eastbound bound in Figure 5 and the "at most 0.82" claim in its caption.

**The rule for future captures.** Record the clear baseline in the same session and the same
file as the condition. It costs one extra condition slot per capture and it is the only thing
that makes the disturbance a controlled comparison.

## F44 -- there are two rendering regimes, and the disturbance is what survives both

F43 left one thing unresolved: WHY do two nominally identical clear captures differ by a
uniform +0.049? Two explanations had opposite consequences.

  a. the capture protocol contaminates one condition slot -- e.g. the CARLA next-tick trap,
     where the first condition renders under the weather the world had BEFORE `set_weather`.
     If so the internal clear in `lap_eastbound_fog.npz` (clear is its FIRST condition) is
     the WRONG one and F43's fix is backwards.
  b. the absolute level drifts between sessions while the within-session difference holds.
     If so the fix is right.

Three 40-pose westbound captures on a freshly launched simulator settle it.

    TODAY's clear against the ARCHIVED westbound clear
      clear captured FIRST (with fog)     signed +0.04810   abs 0.04836
      clear captured ALONE                signed +0.04814   abs 0.04840
      clear captured SECOND (after fog)   signed +0.04817   abs 0.04843

    TODAY's clear captures against EACH OTHER
      first-slot vs alone                 signed -0.00004   abs 0.00008
      second-slot vs alone                signed +0.00003   abs 0.00019
      first-slot vs second-slot           signed -0.00007   abs 0.00012

**Explanation (a) is dead.** Slot order changes the frames by 1e-4, which is 500x smaller
than the effect. The capture script handles the next-tick ordering correctly; whatever else
that trap has cost this project, it is not doing this.

**Explanation (b) is confirmed, and the offset is a session property.** All three of today's
captures sit +0.048 above the archive by the same amount, whether or not another condition
was present. Two regimes exist; everything captured inside one session agrees with itself.

**And the disturbance is preserved across the regimes.** This is what makes the study
survivable:

    fog disturbance computed WITHIN a file
      today, clear first                  signed -0.03219   abs 0.06150
      today, fog first                    signed -0.03215   abs 0.06150
      archive, westbound (cross-file)     signed -0.03480   abs 0.07100
      archive, eastbound re-paired (F43)  signed -0.03410   abs 0.05940

Four measurements of the same physical disturbance, from three sessions and two regimes,
agreeing to within 8%. The absolute level is what drifts; `x_cond - x_clear` is not.

**Consequences, in order of importance.**

1. **F43's fix is right, for the reason F43 gave.** Pair within the session and the regime
   cancels. The eleven cells that pair across files are sound whenever both files sit in the
   same regime, which is what the 0.3-0.4% cross-direction agreement for night and shadows
   already indicated, and what westbound fog's -0.0348 against today's -0.0322 confirms
   directly. Eastbound fog is the one cell that straddled the two.

2. **Do NOT re-capture the study on today's simulator to "fix" this.** It would move all
   twelve cells into the new regime while the closed-loop runs they are compared against
   were driven in the old one, and gate A -- captured steering against driven steering,
   0.0137 -- was measured in the old regime too. The regime is not known to be harmless to
   that check; it is only known to cancel in the disturbance. Re-capturing is a decision
   about the whole study's data, not a bug fix, and it needs the driving re-run with it.

3. **The cause is not identified.** The candidate is the render path: this session cannot
   open a window (Vulkan surface creation fails; only `-RenderOffScreen` starts), so today's
   frames are offscreen-rendered while the archive was captured windowed. That is a
   PLAUSIBLE cause and nothing here tests it -- it cannot be tested until windowed mode
   works again on this machine. Recorded as the leading suspect, not as the answer.

## F45 -- the tolerance horizon is a fitted parameter, and at its a-priori value the certificate is UNSOUND

Two independent expert reviewers, reviewing the arXiv paper blind and separately, converged on
the same objection and derived the same arithmetic. It reproduces exactly against this repo's
own `sustained_bound.json`, so it is recorded here rather than argued with.

`config.py` derives the tolerance as

    CLOSED_LOOP_TOLERANCE = (2 L B) / (v^2 T^2) / MAX_STEER_RAD

and sets `T_CLOSED_LOOP_S = 1.85` with the comment "[MEASURED, back-solved from the observed
cliff]". The observed cliff is the closed-loop departure threshold -- i.e. **T was fitted to
the same driving outcomes the certificate is then validated against.** The paper nonetheless
claims "no fitted parameter" in the abstract, in the methodology, and in the conclusion.

**Sweeping T against the twelve committed cells:**

    T (s)    tolerance    score    failures
    1.00      0.04111     10/12    west S_clear shadows UNSOUND CERT; east S_clear shadows UNSOUND CERT
    1.20      0.02855     11/12    west S_clear shadows UNSOUND CERT
    1.23      0.02717     11/12    west S_clear shadows UNSOUND CERT
    1.50      0.01827     12/12    --
    1.85      0.01201     12/12    --   <- the value in use
    2.10      0.00932     12/12    --
    2.13      0.00906     11/12    east S_mixed night false alarm
    2.50      0.00658      9/12    three false alarms

    admissible window: T in (1.231, 2.128) s

**The serious part is the failure MODE at T = 1.0.** That is not an arbitrary value -- it is
the one-second reaction horizon the paper itself introduces two sentences before back-solving
1.85, and it is where `STEER_CORRIDOR_RAD` already sits (0.0502 rad, 0.041 normalised). At
that value the criterion **certifies both shadows cells as safe, and both depart on 10/10
runs.** An unsound certificate on a model that reliably leaves its lane is the worst failure
this project can produce, and it is one parameter change away from the published result.

**What this does and does not undermine.**

- It does NOT show the criterion is wrong. The 3.0x separation gap is a ratio and is
  invariant to T; the ordering of the cells is correct at every T. What T does is place the
  threshold inside that gap, and T was chosen by looking at where the gap is.
- It DOES mean "no fitted parameter" is not defensible as written. One parameter was fitted,
  on the validation labels.
- The 12/12 is **not fragile to using an honest value.** T = 1.5 s -- a standard human-factors
  reaction time, obtainable without looking at our data -- scores 12/12 with the threshold
  comfortably inside the gap. So the repair costs nothing except the "no fitted parameter"
  sentence: adopt a literature T, report the admissible window as a sensitivity result, and
  the claim becomes defensible instead of circular.

**Recommended, not yet done** (this changes a published claim and is Zach's call):
1. Set `T_CLOSED_LOOP_S` from the human-factors literature, not from our own cliff.
2. Report the (1.231, 2.128) s window in the paper as a sensitivity analysis.
3. Delete "no fitted parameter" from the abstract, methodology and conclusion.

**A second, independent terminology objection from the same reviews, also correct.** A sound
over-approximation can CERTIFY; it cannot FALSIFY. When a bound escapes the corridor the
correct verdict is NOT CERTIFIED (unknown), not FALSIFIED. Under that reading the headline is
eight sound certificates, none contradicted by driving, plus four uninformative unknowns that
happen to coincide with failure. `certify_sustained_bound.py` emits the string `FALSIFIED`
and the paper's Table I and Fig. 5 use it throughout. Making the claim sound requires either
renaming the verdict, or producing a witness s* at which the sampled lap-mean deviation
actually exceeds tolerance -- which this repo can do cheaply, since it already samples the
family.

## F46 -- the family's interior IS behaviourally faithful, and the fog axis is not monotonic

Both blind reviewers raised the same objection independently: the study invented a
behavioural test for a disturbance model, used it to kill the analytic Koschmieder family
(faithful to images at road-ROI R^2 0.848, drove the policy **23.8x** harder than real
fog), and then never ran that test on the replacement. The interior of

    x_p(s) = x_p^clear + s (x_p^cond - x_p^clear)

is a pixel-space chord; only s = 0 and s = 1 are rendered. The paper's coverage claim
rests entirely on that chord meaning something.

**Run it.** Fog rendered at densities 17.5 / 35 / 52.5 against the canonical 70, 200 poses
over the full westbound lap, every capture carrying its own clear
(`scripts/interpolation_fidelity.py`). Each render is projected onto the chord to find the
`s` it corresponds to, then the policy is evaluated at both points.

    model     density   s*    pixel err   steer err   x tol   chord/render
    S_clear      17.5  0.149    0.01648    +0.00219    +0.18   (render bias ~0)
    S_clear      35.0  0.555    0.00622    +0.00266    +0.22        1.60x
    S_clear      52.5  0.996    0.01211    +0.00114    +0.09        1.10x
    S_mixed      17.5  0.149    0.01648    -0.00074    -0.06        0.45x
    S_mixed      35.0  0.555    0.00622    +0.00089    +0.07        1.64x
    S_mixed      52.5  0.996    0.01211    +0.00013    +0.01        1.06x

**The chord passes the test the analytic model failed.** Where the render has a
measurable effect the chord drives the policy 1.06-1.64x as hard, against Koschmieder's
23.8x. In absolute terms the error a verdict would inherit never exceeds **0.22x
tolerance**, against a worst certified margin of 0.76x and a least uncertified escape of
2.26x. So the interior is not a fiction, and the coverage claim survives -- with a stated
error bar rather than as an unquantified caveat. At d = 17.5 the ratio is meaningless
because the render's own bias is +0.00001; the absolute error, 0.18x tolerance, is the
honest statistic there and it is reported as such.

**But the physical axis is NOT monotonic, and that is the new information.** Fog's signed
effect on the road region, each against its own clear:

    density    17.5     35.0     52.5     70.0
    signed   +0.0115  -0.0133  -0.0464  -0.0342
    |mag|     0.0116   0.0310   0.0672   0.0607

It BRIGHTENS the road at low density and darkens it above, and both the signed effect and
the magnitude turn over between 52.5 and 70. So `s` is not a monotone reparameterisation
of density: it runs roughly linearly to d = 52.5 (s* = 0.15, 0.56, 1.00) and then
saturates, with d = 70 landing back inside the chord rather than beyond it. Two
consequences:

1. The certificate over s in [0,1] does **not** cover "all densities up to 70". It covers
   the chord between clear and the d = 70 render, and the worst real fog on this axis
   (d ~ 52.5) sits at s ~ 1 rather than beyond it. That is lucky rather than designed.
2. Any future family built by interpolating to a "maximum" condition should check
   monotonicity first. Ours holds only because the fold is small and lands inside.

**A control that fell out for free.** The four captures ran against one CARLA session and
their four independent `clear` captures agree to **3e-4 per pixel** (signed means +4.7e-5
to 0). F44's +0.048 regime offset is therefore a strictly BETWEEN-session effect, now
confirmed from the other side: within a session the capture rig is reproducible to 1e-4.

## F47 -- WITHDRAWN with the rain condition (2026-08-25)

This entry reported a held-out rain experiment. Rain was withdrawn from the study:
CARLA's rain rendering is temporally stochastic (two renders at one pose differ --
see the note under F36), so the deterministic two-endpoint family cannot represent
it, and a proper treatment needs a stochastic element in the disturbance family.
That is future work, and reporting a rain result computed on the deterministic
family would overclaim. The full entry and its artifacts are recoverable from git
history at this commit's parent.

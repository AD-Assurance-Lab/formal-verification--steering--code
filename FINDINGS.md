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

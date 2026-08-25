# The Study

## Claim

> Given two trained driving policies and no simulation, formal verification identifies
> which conditions each one is safe in. Closed-loop simulation then agrees.

The demo form of this claim is **blind**: two students are handed over as `A` and `B`
without their training history. Verification emits a per-condition verdict for each. The
verdicts are committed. Only then is closed-loop run. If verification recovered which model
is which, per condition, without simulating — that is the result.

## What is and is not novel

| | |
|---|---|
| **not novel** | training a network to drive in CARLA; behaviour cloning; DAgger; distillation |
| **not novel** | showing a clear-weather model fails in fog |
| **novel** | a physically-parameterized disturbance family that is *formally verifiable*, indexed by a quantity an ODD is written in |
| **novel** | verification predicting the closed-loop outcome per condition, in advance, exhaustively over an interval |

M1-M4 exist to produce the two students. They are a means. M5-M6 are the paper.

## The ledger

Pre-registered. Filled in as results arrive. `python -m study.ledger` checks it.

| condition | axis | `S_clear` closed-loop | `S_clear` verify | `S_mixed` closed-loop | `S_mixed` verify |
|---|---|---|---|---|---|
| clear | — | PASS | CERTIFIED | PASS | CERTIFIED |
| night | road illuminance, lux | FAIL | FALSIFIED | PASS | CERTIFIED |
| fog | MOR, m | FAIL | FALSIFIED | PASS | CERTIFIED |
| shadows | solar elevation, deg | FAIL | FALSIFIED | PASS | CERTIFIED |

**Rows 1-4 are the spine.** The verification column must agree with the closed-loop column
in every cell. Any disagreement is a bug until dispositioned.

### How a verification sweep collapses to one verdict

**Pre-registered 2026-08-11, before any verification cell was run; AMENDED 2026-08-12
(commit `34c9d30`, F17).** A sweep returns, per frame, the fraction of the declared axis
box resolved CERTIFIED / FALSIFIED / UNKNOWN. The rule that turns those into a ledger
verdict lives in `study.design.verify_verdict` — which is the executable pre-registration
and wins over this table if they ever disagree — and is deliberately asymmetric:

| verdict | condition |
|---|---|
| FALSIFIED | a violation region exists on >= 5% of the sampled frames |
| CERTIFIED | **every** sampled frame is fully certified |
| UNKNOWN | otherwise |

The original 12-frame **median** rule was amended after it produced two unsound
certificates (F17, P-02): a median over 12 frames cannot see a 38% violating tail on a
~1700-frame lap. The amendment makes CERTIFIED strictly harder to earn (60 frames, all
fully certified) and is recorded in `design.verify_verdict`'s docstring. This table
previously still showed the superseded median rule — the human-facing and executable
pre-registrations had silently diverged, which is exactly what
`conformance/test_traps.py::test_expectation_table_is_pinned` now guards against on the
expectation side.

`FALSIFIED` is an existence claim backed by soundness, so it needs no coverage threshold —
only evidence it is a property of the route rather than one frame. `CERTIFIED` is a
coverage claim, so "nothing was falsified" is explicitly *not* sufficient: an all-UNKNOWN
sweep also falsifies nothing, and reading that as certified is how the previous study
turned 11.5% UNKNOWN into a robustness finding.

**The `clear` verify cell is vacuous.** Its disturbance box has zero width, so the bound is
exact and CERTIFIED holds by construction. It is recorded with `vacuous: true` and excluded
from every certified-rate summary.

### What is compared, and what M5 still owes

Closed loop drives **one point** on each axis (the CARLA preset). Verification covers an
**interval**. Mapping the preset onto the axis — CARLA `fog_density=70` to a MOR in metres —
is M5 calibration and is **not done**. Until it is, the two instruments are not being
evaluated at the same axis location, and the ledger comparison rests on the weaker claim
that a policy falsified across the majority of an axis is the policy that fails the preset
drawn from it.

This does not weaken the black-box demo, which is the funding-facing result and needs no
calibration at all: given two unlabelled policies, verification alone separates them.

### Each student is sized to its own task -- architectures may differ

**Revised 2026-08-11 (Zach).** An earlier rule here forced identical architecture across
both arms. That was over-constrained, and the reasoning behind it did not survive contact
with what the study actually claims.

**The central claim is WITHIN-model:** for each policy, verification's verdict matches
closed loop's verdict. Each model is judged against its own closed-loop behaviour, so its
size is irrelevant to that comparison.

**Size confounds a DIFFERENT claim** -- "disturbance training improves certified
robustness" -- which is model-vs-model on certified rate. That is precisely what the
previous generation stumbled into: its wider student certified 20% on fog against the
narrow one's 72%, and its own methodology notes part of that gap was width rather than
robustness. The fix is not identical architecture. The fix is **not making that
comparison**, and reporting ReLU count and UNKNOWN rate alongside every certified rate so
bound-looseness is visible rather than hidden.

**And the deployment case settles it.** A policy arrives as a binary. Model size is not an
indicator of whether it drives in fog, and a tool that only works when two models happen
to share an architecture is not a tool. Size each model to its own task; that is the
realistic case and the one worth demonstrating.

**Consequence to keep visible, not engineer away:** a larger `S_mixed` will have looser
bounds and may return UNKNOWN where a smaller `S_clear` is decisive. That is a real
property of the delivered model. Report it.

**Deferred, not decided (2026-08-11).** Matching the two sizes *would* remove looseness as
a variable in the cross-model reading of the ledger, which is a real benefit. But it is
not free either: looseness pushes verdicts toward UNKNOWN in BOTH directions, since a bound
too wide to fit inside the corridor is usually also too wide to sit entirely outside it. So
padding `S_clear` with capacity it does not need makes it less decisive precisely where a
crisp FALSIFIED is wanted.

Neither choice has to be made now. **Primary run: size each student to its own task.** If
the cross-model reading then looks confounded by size, distil a matched-size `S_clear` as a
controlled follow-up and report both -- one extra distillation, no new data, no CARLA,
about 15 minutes. Do not block the end-to-end pipeline on this.

**snow is out of scope.** CARLA renders no snow. Say so in the paper.

**rain is out of scope (withdrawn 2026-08-25).** Its rendering is temporally
stochastic — two renders at one pose differ — so the deterministic two-endpoint family
cannot represent it (`docs/DISTURBANCE_MATH.md` has the appearance-model argument). A
proper treatment needs a stochastic element in the disturbance family; future work.

### Parameter axes (declared before training, per the design rule in CLAUDE.md)

| condition | parameter | range | trained at | verified over |
|---|---|---|---|---|
| night | road illuminance E | 10^4 → 10 lux | extremes only | full interval |
| fog | meteorological optical range | 2000 → 60 m | extremes only | full interval |
| shadows | solar elevation | 60° → 10° | extremes only | full interval |

Training at the extremes and verifying over the continuum is what leaves room for the
optional M7 finding (below).

## Milestones

Exit criteria are **measurements that pass**, not "code written".

| | milestone | exit criterion |
|---|---|---|
| **M0** | repo, conformance suite, ledger, axes declared | conformance green; `study.ledger` prints all-PENDING |
| **M1** | camera exposure fixed + clear teacher | clear road ROI at real-camera levels (see D1); pure-pursuit expert <= CTE budget both directions; BC teacher converges |
| **M1.5** | teacher DAgger | clear teacher <= 0.668 m CTE both directions over N reps |
| **M2** | mixed-condition collection + mixed teacher | mixed teacher drives every condition within CTE budget |
| **M3** | distill -> `S_clear`, `S_mixed` + student DAgger | both students <= CTE budget on clear; ReLU-only asserted; `S_clear` demonstrably fails >= 1 unseen condition |
| **M4** | closed-loop table | left half of the ledger filled, failure rates over >= 10 reps with Wilson intervals |
| **M5** | disturbance characterization | linearity probe run on all four conditions; >= 2 pass the fidelity gate (D3) |
| **M6** | verification, blind | right half filled, verdicts committed *before* their closed-loop counterparts |
| M7 | *optional* — stretch goals | see below. Nice if they land, none required for the paper |

## M7 — stretch goals

**Gated on M5 and M6 landing first.** These are genuinely interesting and none of them is
needed for the claim. The study has an established habit of expanding; do not start these
while the single-axis result is incomplete.

### S1. Interpolation gap (night vs dusk)

Trained at the extremes of an axis, does the model fail in the middle? Verify over the
continuum, predict a failing sub-interval, confirm inside and outside at >= 10 reps.
Weakness: "it fails at dusk" is a prediction a reviewer may call obvious.

### S2. Combined disturbances (Zach, 2026-08-11)

fog+night. Shadows are largely exclusive with the others -- they need direct sun,
which heavy cloud removes -- though **thin fog with sun is physically real** and fog
washing out shadow contrast is a genuine interaction worth one experiment. (This
axis-combination programme now lives in the multi-condition study.)

**Why this may be the better probe.** Train on single conditions only, verify over the
JOINT parameter box, and ask where the combination fails. Nobody's intuition is reliable
about fog-at-night, so a correct prediction there is a real prediction in a way "it fails
at dusk" is not. A joint certificate is also exactly the form an ODD is written in --
"visibility > X AND illuminance > Y" -- which is a better product statement than any
single axis.

**It stress-tests the paper's central technical claim.** The tractability argument is that
`theta` is low-dimensional so BaB costs `k^d` rather than `2^thousands`. At d = 1 that
claim is never actually tested. Combinations are the first honest test of it, and the
sampling-cost comparison gets far more favourable as d grows.

**Two things that are NOT free, and must be handled explicitly:**

1. **Composition is bilinear, not affine.** Fog then night gives
   `x'' = (g*t)*x0 + (g*A*(1-t) + c*H)`. The gain is a PRODUCT of the two conditions'
   parameters, so the composed map loses the exactly-affine property each has alone. BaB
   absorbs it -- on a cell where `t` is pinned narrow, `g*t` is affine in `g` with a
   residual shrinking quadratically -- but the cell count goes `k -> k^d`. Measure the
   growth; it is a result either way.

2. **The easy composition is physically wrong.** Naive fog-then-dim holds the airlight `A`
   fixed, but at night the airlight is not skylight -- it is HEADLIGHT BACKSCATTER,
   spatially concentrated in the near field. Real fog at night is a bright wall in front of
   the car, not dimmed daytime fog. So fog+night needs `A(lux)`, a modelling extension
   rather than a composition.

**What makes it cheap to attempt:** the D3 fidelity gate applies unchanged, and it answers
the interesting question directly -- does CARLA render the combination physically, or does
it just stack effects naively? Either answer is publishable, and the second is a concrete
statement about simulator fidelity that the single-axis results cannot make.

**On M1 vs M1.5, corrected 2026-08-11 after hitting it.** M1 was originally written with the
exit criterion "teacher <= 0.668 m CTE". That is not achievable with M1's file set:
behaviour cloning alone never drives a full lap, because errors compound off the expert's
state distribution. Measured here — the BC teacher reached val RMSE 0.0042, well inside the
closed-loop tolerance, and still departed the lane at step 1233 of ~1700. DAgger is the fix
and it is a separate file. Splitting the milestone rather than pretending the criterion was
met.

**M5 is the research risk, and it is front-loadable.** The linearity probe needs captured
frames and no GPU. Run it on all four conditions at the start of M5, before committing to
any of them, so the conditions that cannot be made verifiable are known early rather than
discovered late.

## The six decisions, resolved

**D1 — the clear baseline.** Fix the *camera*, not the weather preset. The previous study
ran `sensor.camera.rgb` with only `image_size` and `fov` set, leaving CARLA's default
**per-frame histogram auto-exposure** active — the same defect that disqualified the ACDC
dataset for photometry. Set `exposure_mode='manual'` with fixed `shutter_speed`/`iso`/
`fstop`, tuned so the clear road ROI lands at real-camera levels (target mu in [0.28, 0.34],
sigma within 1.3x of a real clear road).

**Keep the existing clear preset**, which is *not* `ClearNoon`: it is a custom flat,
shadowless preset (`cloudiness = 80`, `sun_altitude_angle = 90`) in
`carla_env.set_clear_weather`. Swapping it for `ClearNoon` (sun at 45 deg, so shadows)
made the clear teacher depart the lane at 33.54 ft CTE where it otherwise held 0.43 ft.
Keeping it avoids that and turns shadows into a deliberately studied condition instead of
a confound.

This *strengthens* the auto-exposure diagnosis: a flat overhead sun at cloudiness 80 is
diffuse light with no strong highlights, and it should not put a road surface at mu = 0.81.
A per-frame histogram tonemapper should. Fallback if manual exposure
cannot hit the target: a fixed monotone response curve in `imaging.py`, shared by the live
loop and the offline dataset so they cannot drift.

*Unverified.* That auto-exposure is on is confirmed; that fixing it moves mu to ~0.31 and
removes the night contrast inversion is M1's first measurement.

**D2 — conditions and order.** night -> fog -> shadows; rain and snow out of scope.
Risk-ordered for execution. The paper presents them symmetrically; there is no lead
condition.

**D3 — what "faithfully modelled" means.** A conjunction; all must pass. Precondition:
`goc()` alignment above threshold, *refusing to proceed* below it.

| | check | threshold |
|---|---|---|
| a | Delta-mu **sign** agreement, model vs rendered, road ROI | must agree |
| b | Delta-mu magnitude | within 0.25x of rendered |
| c | Delta-sigma ratio | in [0.7, 1.4] |
| d | (a)+(b)+(c) **per depth band**, 5 bands | >= 3 of 5 pass |
| e | behavioural gate | <= 1.5x, ranking preserved, >= 2 students |
| f | ROI R^2 on aligned pairs | >= 0.5 |

(a) is the direct falsifier for the previous study's fog failure, where the model moved the
road mean by 0.003 against the renderer's 0.248 and still passed a behaviour-only gate.
(d) is only possible with ground-truth depth, and pooled statistics previously hid a case
where near bands fit at R^2 = 0.91 with a physically impossible negative airlight while far
bands fit at R^2 = 0.18.

**D4 — depth.** A `sensor.camera.depth` at the *identical transform* as the RGB camera,
captured in the same tick. **Both sensors run a frame behind**; both must be matched on the
frame id `world.tick()` returns. Decode `(R + G*256 + B*256^2)/(256^3 - 1) * 1000` to metres.
With per-pixel depth and pose-matched pairs, Koschmieder has exactly two unknowns over ~10^5
pixels spanning a real depth range — identifiable, where a flat-road row-to-depth assumption
was not.

*The cheap falsification test:* fit `(beta, A)` independently at each severity. **A must be
constant across severities** (it is an illumination property, not a fog-density one) and
beta should scale monotonically with `fog_density`. If A drifts, CARLA fog is not
Koschmieder and the fog leg aborts to a reported negative result.

Depth is used to *construct the certified disturbance set*, never to run the policy. The
deployed network sees no depth.

**D5 — predict-then-confirm.** The primary form is the blind protocol at the top of this
document: verdicts per condition, committed before closed-loop. The finer interval-level
version (adaptive bisection on log-illuminance, localizing a failing sub-interval, then
confirming at >= 10 reps per point) is M7 and is optional.

Error directions are **not** symmetric. Certificate says UNSAFE, closed loop PASSES ->
conservatism; expected, quantify it. Certificate says SAFE, closed loop FAILS ->
**unsoundness, a bug**; stop and find it.

**D6 — conformance suite.** The nine checks that need no CARLA and no GPU, built before any
pipeline code, green in CI on every commit. CARLA-gated and GPU-gated checks land as marked
tests with their milestones. See `conformance/`.

## What would falsify the claim

Falsified if **any** of:

1. Verification's per-condition verdicts do not match closed-loop's, measured at >= 10 reps
   per point, on any attempted condition.
2. The UNKNOWN (bound-looseness) rate is high enough that verification returns no usable
   verdict — no answer is not a prediction.
3. Closed loop fails anywhere inside a certified-safe region. **This one is fatal**: it
   invalidates the tool, not the experiment. (1) and (2) are publishable negatives that
   still support the tooling.

## Honest limitations, stated up front

1. **Image formation is CARLA's.** The parameters are real; the rendering is not. The
   certificate is *indexed* by a real-world quantity. We do not claim CARLA's fog at 85 m
   MOR looks like real fog at 85 m MOR.
2. **Closed-loop is not independent of verification.** How the disturbance is defined
   changes how the simulation is run — manual vs auto exposure being the clearest case. The
   two instruments share a parameterization by design; they are independent in *mechanism*
   (bound propagation vs rollout), not in *setup*.
3. **Transfer to a real camera is unproven.** The route to closing it is the DENSE
   family's **Pixel Accurate Depth Benchmark** -- 17 measured fog-chamber visibility
   levels (20-100 m in 5 m steps), 12-bit RGB, and survey-scanner depth, with calibrated
   reflectance targets at known distances that make `(beta, A)` measurable rather than
   fitted. NOT *Seeing Through Fog*, which has ~3 visibility levels; the inherited notes
   conflated them. See `docs/DENSE_ACCESS.md`. Registration-gated, not technically
   blocked.
4. **Verification covers the parameterized family only.** It replaces exhaustive sampling
   *within* a disturbance family. It does not replace scenario sampling.
5. **The policy is small and the ODD is narrow** — one route, one speed, one vehicle.

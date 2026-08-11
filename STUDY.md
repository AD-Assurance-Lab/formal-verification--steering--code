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
| rain | rain rate, mm/h | FAIL | FALSIFIED | PASS | CERTIFIED |

**Rows 1-4 are the spine.** The verification column must agree with the closed-loop column
in every cell. Any disagreement is a bug until dispositioned.

**snow is out of scope.** CARLA renders no snow. Say so in the paper.

**rain is contingent** — see `docs/DISTURBANCE_MATH.md`. Its appearance model is
high-frequency and spatially stochastic, with no low-rank per-pixel affine form. Attempted
only if night, fog and shadows land.

### Parameter axes (declared before training, per the design rule in CLAUDE.md)

| condition | parameter | range | trained at | verified over |
|---|---|---|---|---|
| night | road illuminance E | 10^4 → 10 lux | extremes only | full interval |
| fog | meteorological optical range | 2000 → 60 m | extremes only | full interval |
| shadows | solar elevation | 60° → 10° | extremes only | full interval |
| rain | rain rate | 0 → 25 mm/h | extremes only | full interval |

Training at the extremes and verifying over the continuum is what leaves room for the
optional M7 finding (below).

## Milestones

Exit criteria are **measurements that pass**, not "code written".

| | milestone | exit criterion |
|---|---|---|
| **M0** | repo, conformance suite, ledger, axes declared | conformance green; `study.ledger` prints all-PENDING |
| **M1** | camera exposure fixed + clear teacher | clear road ROI at real-camera levels (see D1); teacher <= 0.668 m CTE both directions over N reps |
| **M2** | mixed-condition collection + mixed teacher | both experts drive every condition within CTE budget |
| **M3** | distill + DAgger -> `S_clear`, `S_mixed` | both students <= CTE budget on clear; ReLU-only asserted; `S_clear` demonstrably fails >= 1 unseen condition |
| **M4** | closed-loop table | left half of the ledger filled, failure rates over >= 10 reps with Wilson intervals |
| **M5** | disturbance characterization | linearity probe run on all four conditions; >= 2 pass the fidelity gate (D3) |
| **M6** | verification, blind | right half filled, verdicts committed *before* their closed-loop counterparts |
| M7 | *optional* — interpolation gap | trained at extremes, does the model fail in the middle? Nice if yes, not required |

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
sigma within 1.3x of a real clear road). Keep `ClearNoon` and the noon sun angle — this
avoids the shadow preset that broke the policy (0.43 -> 33.54 ft CTE) and turns shadows
into a deliberately studied condition instead of a confound. Fallback if manual exposure
cannot hit the target: a fixed monotone response curve in `imaging.py`, shared by the live
loop and the offline dataset so they cannot drift.

*Unverified.* That auto-exposure is on is confirmed; that fixing it moves mu to ~0.31 and
removes the night contrast inversion is M1's first measurement.

**D2 — conditions and order.** night -> fog -> shadows -> rain(contingent); snow out.
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
3. **Transfer to a real camera is unproven.** The route to closing it is a controlled
   facility: DENSE (Bijelic et al. 2020) has 17 measured fog-chamber visibility levels with
   12-bit RGB and lidar depth. Registration-gated, not technically blocked.
4. **Verification covers the parameterized family only.** It replaces exhaustive sampling
   *within* a disturbance family. It does not replace scenario sampling.
5. **The policy is small and the ODD is narrow** — one route, one speed, one vehicle.

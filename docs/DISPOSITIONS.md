# Dispositions

`CLAUDE.md`: *a result that contradicts a ledger cell is a bug until proven otherwise, and
may not be written up as a finding until a written disposition lists the candidate causes
that were ruled out.*

This file is that record. A disposition here does **not** silence the ledger. `study.ledger`
only stops flagging a cell when the cell's own JSON carries a `disposition` key, and that
key is added deliberately, by a person, after reading what follows.

---

## D-01 — `fog / S_mixed / closed_loop` returned FAIL where PASS was pre-registered

**Status: OPEN. Needs Zach's decision. The `disposition` key has NOT been added.**

Recorded 2026-08-11 22:10.

### The measurement

```
verdict FAIL   failures 1/20 = 5.0%   Wilson 95% [0.9%, 23.6%]
passing runs : max|CTE| median 1.07 ft, worst 2.12 ft   (budget 2.19 ft)
failing run  : rep 0 westbound, 2.61 ft, over-budget on 0.2% of frames, departed=False
```

### Candidate causes considered

| candidate | ruled out? | on what evidence |
|---|---|---|
| the model cannot drive fog | **yes** | 19/20 runs pass with median max-CTE 1.07 ft, less than half the budget. A capability gap does not look like this. |
| the preset-race bug (night ran at fog_density 70) | **yes** | `weather_params` constructs fresh `WeatherParameters` and reads no live state; the cell ran after that fix. |
| auto-exposure artefact | **yes** | fog uses the daylight exposure, manual, declared in `CONDITION_EXPOSURE`. |
| frame desync pairing image[t-1] with pose[t] | **yes** | `grab_frame` matches on the frame id `world.tick()` returns and raises `FrameDesync` rather than swallowing a timeout. No desync was raised. |
| cleanup destroying data | **yes** | that bug cost `ledger_mixed_clear`, not this cell; this one wrote a complete 20-rep record. |
| **stability-cliff non-determinism** | **NO — this is the leading explanation** | CARLA closed-loop pass/fail is measured non-deterministic near the cliff; a single run gives the wrong verdict roughly 1 in 8 times. A 2.61 ft excursion against a 2.19 ft budget, 0.2% of frames over, no departure, is a marginal event of exactly that kind. |
| **the verdict rule is too strict for a stochastic simulator** | **NO — genuinely unresolved** | The rule fails a cell when the Wilson interval excludes zero, so *any* single failure in 20 is a FAIL. Whether that is the right criterion is a design question, not a measurement. |

### What this comes down to

Either the criterion is too strict for a stochastic simulator, or the model has a real ~5%
fog failure rate. Both are defensible and they are different papers, so the choice is not
mine to make after seeing the number — which is the whole reason the expectation was
pre-registered.

**Not done deliberately:** the verdict rule has not been loosened, and `disposition` has not
been added to the cell. Relaxing a pre-registered criterion to accommodate the first result
that violates it is precisely the failure this ledger exists to prevent, and it is how the
previous study turned a contradiction into "the counter-intuitive finding".

### Options

1. **Keep the criterion.** Report `S_mixed` as failing fog at 5% [0.9%, 23.6%], and say so.
   Costs the clean four-for-four story; gains an honest one.
2. **Raise the repetition count.** 20 more reps tightens the interval and distinguishes a
   ~5% rate from a ~1% one. Roughly 30 min of CARLA. Does not change the rule, only the
   evidence. *This is the cheapest way to learn something real.*
3. **Amend the criterion to a rate threshold** (e.g. fail above 10%) — but amend it for
   **every** cell, committed as a deliberate change, and re-evaluate all cells under it.

Recommendation: option 2 first, since it is cheap and informative, then decide 1 vs 3 with
a tighter interval in hand.

---

## D-02 — `shadows / S_clear / verify` returned CERTIFIED where FALSIFIED was pre-registered

**Status: OPEN, and unusually well-positioned — the prediction is on the record before the
drive.**

Recorded 2026-08-11 22:36, while the sweep was still running.

Verification certifies most of the shadow axis for the clear-only student. The
pre-registered expectation is FALSIFIED, on the reasoning that `S_clear` never saw shadows.

**Why this contradiction is worth more than the others.** The `S_clear` closed-loop cells
were deliberately deferred (see `pipeline/checkpoints/.overnight_done/README_DEFERRED.txt`)
so verification could be committed first. So this is a genuine blind prediction:
verification says `S_clear` will **pass** shadows, and that is on the record before the car
drives. Confirmation would be a stronger result than agreement on a cell everyone expected,
because the prediction is surprising and could be wrong in public.

**Early structure in the sweep, per frame:** frames with near-zero clear steering certify at
100% in a single bound; the one curve frame so far (clear steer −0.0675) falsifies 72.2%.
That is physically coherent — dimming barely moves steering on a straight, but degrades the
lane-edge contrast a curve depends on — and it suggests the honest statement is
*conditionally* certified: safe on straights, not on curves.

**A known weakness in the first run, already fixed.** That first sweep used a shadow mask
pooled over 400 pose-matched pairs. Cast shadows are static in the world and therefore move
through the image as the ego drives, so pooling blurs them toward a smooth global dimming
and understates spatial structure. The mask is now measured **per frame** from that frame's
own pose-matched counterpart, which keeps the map affine in `s` and makes `s = 1` reproduce
the observed CARLA shadows frame exactly. Both runs are kept; the pooled one is retained as
a diagnostic, not as the cell.

---

## P-01 — prediction recorded BEFORE running the `S_mixed` verify cells

Recorded 2026-08-11 22:42, with `S_mixed` verification not yet started. Costs nothing to
be on the record, and an unrecorded expectation is not a prediction.

**I expect `night / S_mixed / verify` to come back FALSIFIED, contradicting the
pre-registered CERTIFIED — and I expect that to be a calibration artefact, not a real
disagreement.**

Reasoning: `night / S_mixed / closed_loop` already returned PASS at 0/20. The declared
night axis is `ambient in [0.02, 0.50]`, i.e. `g = 1/(1+ambient) in [0.667, 0.980]`, which
at the far field where the headlight field `L -> 0` scales the image to between 0.02x and
0.33x. Whether CARLA's `sun_altitude_angle = -25` preset is anywhere near that severe is
**unmeasured** — it is precisely the preset-to-axis mapping M5 owes. If the declared axis is
harsher than what CARLA renders, verification falsifies a policy that drives the preset
fine, and the two instruments disagree because they are being asked different questions.

Note the direction: FALSIFIED-but-passes is the **conservative** direction and does not
trip `unsound_cells`, which only fires on CERTIFIED-but-fails. Over-strict is survivable;
unsound is not.

The fix is not to widen the corridor or shrink the axis after the fact. It is to measure
where CARLA's night preset actually sits on the illuminance axis and evaluate verification
over an interval containing that point — the same alignment that shadows already has for
free from its pose-paired mask.

---

## D-03 — `clear / S_mixed / closed_loop` rerun of 2026-08-11 23:14 is CONTAMINATED, discard it

**Status: my error. The cell is being deleted and rerun, not reported.**

While that cell was driving on CARLA port 3000, I opened a **second client on the same
port** to run a photometric comparison. Both were in synchronous mode, so their
`world.tick()` calls interleaved, and the second client additionally set the weather and
teleported a vehicle into the running scene.

    rep 0 eastbound   1.15 ft  PASS
    rep 0 westbound   0.50 ft  PASS
    rep 1 eastbound   1.26 ft  PASS
    rep 1 westbound   0.50 ft  PASS
    rep 2 eastbound  20.69 ft  FAIL (departed)   <- my second client

A 20.69 ft departure after four runs at 0.50-1.26 ft is not a model failure. The timing
matches the intrusion exactly.

**Nothing errored.** The simulator served both clients, every frame looked plausible, and
the corrupted run is indistinguishable from a real result unless you know what else was
running. That is the same shape as the read-after-write and queue-desync traps in
`CLAUDE.md`, and I walked into it while being careful about CARLA as a *shared* resource
between projects — the collision was with my own run.

**Fix, so it cannot recur:** `pipeline/carla_lock.py` takes an exclusive per-port lock.
`closed_loop_ledger.py` and `fog_density_sweep.py` now acquire it and refuse to start if
another holder is alive, rather than queueing behind it.

**Consequence:** the cell's JSON and its completion marker are deleted and the cell reruns
on a quiet server. No other cell is affected — `fog`, `night` and `shadows` for `S_mixed`
all completed before phase 2 began, and the frozen fog sweep's captures finished at
23:13:45, before phase 2 started at 23:14:40.

---

## D-04 — the fog `k` disagreement is OPEN; three hypotheses tested and falsified

Route frames put the surface-illumination attenuation at `k ~ 0.72` at `fog_density=70`;
the static-pose sweep puts it at `~1.1-1.2`. These are not both reasonable: scanning `k` on
route frames, rmse has a sharp minimum at 0.70 and D3 (a),(b),(f) pass only for `k <= 0.8`.

**Tested and ruled out:**

| hypothesis | test | result |
|---|---|---|
| camera not warmed up, biasing the clear baseline dark | 20 warm-up ticks + end-of-sweep drift check | **no** — density 10 gave k 1.070 without, 1.098 with; drift 0.0053 |
| vehicle captured above ride height, corrupting depth-per-row | measured z: 0.2943 two ticks after teleport vs 0.0135 settled; settle then freeze physics | **no** — k unchanged (1.098, 1.125 at densities 10, 20) |
| sweep poses drift off-road, so the "road ROI" is not road | route path is straight at y ~ 30.1, yaw ~ 0.05 for the full 220 m | **no** — poses are on-road and aligned |
| scene/position dependence | fit route frames restricted to the sweep's own x-range | **no** — k is 0.732 / 0.720 / 0.712 near / mid / far |

**Leading untested hypothesis: motion blur.** The route frames were captured from a vehicle
moving at 20 mph; the sweep's vehicle is stationary. CARLA's RGB camera applies motion blur
by default. Untested because testing it needs CARLA, and CARLA is running ledger cells —
see D-03 for what happens when I ignore that.

**What is used meanwhile, and why it is not cherry-picking.** Verification uses the
**route-frame** calibration, because the frames a policy meets in closed loop are
moving-camera frames, and the model's job is to reproduce *those*. The route fit passes all
four computable D3 checks 8/8 (ROI R^2 +0.870); the sweep's `k` fails them on route frames.
`k` is nonetheless carried as a bounded interval spanning both fits, so a certificate stays
sound whichever fit is eventually vindicated.

### D-04 addendum — the frozen sweep's `k` is constant, which argues the sweep is at fault

Frozen-physics sweep, 8 poses per density:

| density | 10 | 30 | 50 | 70 | 90 | 100 |
|---|---|---|---|---|---|---|
| MOR (m) | 862 | 237 | 153 | 106 | 77 | 64 |
| k | 1.098 | 1.144 | 1.129 | 1.141 | 1.174 | 1.140 |
| A | 0.308 | 0.363 | 0.395 | 0.408 | 0.417 | 0.418 |

MOR falls monotonically and plausibly, and A rises as it should. But `k` sits at ~1.14
**independently of density**, and that is the tell: `k` is meant to be the attenuation of
sunlight reaching the road, so it must fall as fog thickens. A constant multiplicative
factor is not attenuation — it is a fixed offset between this capture's clear baseline and
its fog frames. `d_sun` is `nan` for the same reason: no fitted `k` is below 1.

So the disagreement is most likely a defect in the **static capture's clear baseline**,
not in the route frames, which is the opposite of what I assumed when I started chasing
warm-up and ride height. The route frames remain the primary calibration, and they are also
the right choice on principle: they are moving-camera frames, which is what a policy
actually meets in closed loop.

`k` stays bounded over [0.637, 1.330] regardless. Measured cost of that conservatism, at a
budget of only 16 bounds on one frame: 50% certified, 0% falsified, 50% UNKNOWN — loose but
not vacuous, and it tightens with the full budget. Resolving D-04 would buy back tightness,
which is the concrete reason to finish it rather than leave it.

---

## D-05 — `S_clear` fails its OWN training condition; the negative control is compromised

**Status: OPEN. Needs your call on whether to retrain the control.**

Recorded 2026-08-12 ~23:40, from a cell whose verification counterpart was committed first.

    clear / S_clear / closed_loop   FAIL   2/20   Wilson [0.03, 0.30]
      rep 8 eastbound  86.42 ft  DEPARTED
      rep 9 westbound   2.19 ft  marginal, exactly at budget
      passing runs: median 1.58 ft, worst 2.18 ft (budget 2.19)

`overnight.sh` anticipated this in writing before the run: *"The negative control has to be
a GOOD clear specialist. If S_clear is merely undertrained, 'S_clear fails fog' is
confounded — it must fail because it never saw fog, not because it drives badly."* It is
now confounded, and I am not going to pretend otherwise.

### But the night result survives it, and the margin is the reason

    night / S_clear   20/20 failures, EVERY run departed, 54-59% of frames over budget
    clear / S_clear    2/20 failures,  1 departure,        1.2% of frames over budget

These are not the same phenomenon at different strengths. On clear the policy completes 19
of 20 laps with a median max-CTE of 1.58 ft, comfortably inside budget; on night it never
completes a lap and spends the majority of every lap outside it. A policy that "drives
badly in general" does not produce that gap. So `S_clear` genuinely cannot drive night, and
verification said so before the drive.

What the confound *does* cost is the clean version of the claim. "S_clear fails only what
it never saw" is no longer supportable as stated; "S_clear fails night catastrophically and
clear only marginally" is, and it is the weaker sentence.

### Options

1. **Retrain / extend student-DAgger on `S_clear`** until clear is clean, then rerun the
   S_clear row. Costs a few hours of CARLA and re-runs four cells. Gives the clean control.
   Note the verify cells would need recommitting first to preserve the blind protocol.
2. **Report as measured**, with the margin argument above carrying the weight.
3. **Diagnose first.** Both marginal failures across every cell tonight are *westbound*, and
   cells now record the (step, x, y) of the worst excursion. One more clear cell would show
   whether there is a single recurring corner. Cheapest of the three, and it also settles
   D-01.

Recommendation: 3, then 1 if a corner is not the explanation.

### A related fix, not a silencing

`study.ledger` reported this as `certified safe, closed loop FAILED` — its most serious
alarm, reserved for verification calling something safe that was not. It fired on the
**vacuous** clear cell, which asserts nothing: a zero-width disturbance box makes CERTIFIED
mean only "the network agrees with itself at the nominal frame". The check now distinguishes
vacuous cells and says so explicitly rather than counting them as soundness violations. The
closed-loop contradiction is still reported, and still fails the ledger.

---

## P-02 — prediction from the corrected statistic, committed BEFORE the fog cell runs

Recorded 2026-08-12 ~23:55. `fog / S_clear / closed_loop` has **not** been run.

Measured on 300 pose-matched on-route frames, `S_clear` under fog exceeds the steering
corridor on **23.7%** of them. Every cell measured above 23% has failed closed loop; every
cell at or below 8% has passed. So:

**Prediction: `fog / S_clear / closed_loop` will FAIL, and not marginally — expect
departures, closer to the shadows cell (37%, 20/20 with 16 departures) than to the
marginal 1-in-20 cells.**

This is on the record before the drive. If it comes back PASS, the coverage statistic in
F17 is wrong and F17 should be withdrawn rather than patched.


---

## D-06 — CORRECTION: two of the three "marginal westbound" failures were also my contamination

Recorded 2026-08-12 00:09. **This withdraws part of what D-01 and D-05 claimed.**

The `clear / S_mixed` cell was rerun on a quiet server with the port lock held:

    clear / S_mixed / closed_loop   PASS   0/20
      all 20 runs passed, median max-CTE 0.72 ft, worst 1.49 ft
      westbound specifically: median 0.49 ft, worst 0.82 ft

The contaminated version of that cell reported 3/20 failures. I attributed rep 2 (20.69 ft,
departed) to my concurrent CARLA client and treated reps 4 and 9 (2.45 and 2.23 ft
westbound) as genuine marginal excursions — the beginning of a pattern. **They were not.**
On a quiet server the worst westbound run is 0.82 ft, less than half of what those
"marginal failures" recorded, so all three failures came from the intrusion.

**What I got wrong, specifically.** I wrote that the marginal-westbound pattern "now shows
up on clear, the condition S_mixed was trained on", and drew the inference that the issue
therefore could not be about disturbance robustness. That inference was built on
contaminated data. I had already identified the cell as contaminated and still mined it for
a secondary conclusion, which is the wrong instinct: a run corrupted at one point is not
trustworthy at any other point.

**What actually survives:**

- `fog / S_mixed` rep 0 westbound, 2.61 ft — clean cell, predates any contamination. D-01
  stands as originally written, on that single instance.
- `clear / S_clear` rep 9 westbound, 2.19 ft, exactly at budget — clean cell (it ran
  23:25-23:31, well clear of the 23:16-23:18 intrusion). D-05 stands.

So the marginal-westbound observation rests on **two** instances in different cells, not
three-plus, and it is correspondingly weaker evidence for a recurring corner. The (step,
x, y) instrumentation added tonight is still the right way to settle it.

`S_mixed` now passes clear, night and shadows cleanly and fails only fog, at 1/20.

---

## D-04 resolution (partial) — the static-capture harness does not reproduce the preset

Chasing the fog `k` disagreement to its root, at the SAME pose, same nominal preset:

| region | route frame (dataset) | my static capture | ratio |
|---|---|---|---|
| sky, rows 0–180 | **0.0021** | **0.2568** | 123x |
| road, rows 240–450 | 0.3135 | 0.2203 | 0.70 |
| hood, rows 450–480 | 0.2447 | 0.1343 | 0.55 |

The dataset's clear, night and shadows frames have a **black sky**; fog has a bright one.
That is not a defect — `CLEAR_BASELINE` sets `scattering_intensity = 0.0` and
`mie_scattering_scale = 0.0`, so with no atmospheric scattering the sky renders black, and
fog is bright precisely because the fog volume scatters. The dataset is behaving as
specified.

**It is my ad-hoc static harness that is wrong.** It renders a bright sky from the same
nominal preset, so it is not reproducing `CLEAR_BASELINE` — most likely because the world
retains scattering state from preceding runs and the harness does not establish it the way
`set_condition` does in the real pipeline.

**Ruled out along the way:** world staleness (a full Town04 reload gives an identical
0.2204), render settling (converges by ~10 ticks and is flat out to 320), dataset vintage
(the last `CLEAR_BASELINE` change is the commit that immediately precedes collection), and
motion blur as the primary term (route frames are blurrier — Laplacian variance 90 vs 199 —
but blur cannot move a regional mean by 42%).

**Why this matters, and how far.** The fog airlight `A` is driven mainly by the sky region,
so fitting against a harness whose sky is wrong by two orders of magnitude will bias `A`
and, through the A/k trade-off, bias `k`. That is the most likely root of D-04.

**What it does NOT implicate.** The closed-loop pipeline renders live through
`set_condition`, and `S_mixed` passes clear, night and shadows cleanly, which is not what a
gross train/render mismatch would produce. The ledger cells stand. What is in doubt is the
**static-capture calibration path**: `fog_density_sweep.py` and the MOR(density) curve.

**Consequence for the fog cells now running.** They use the route-frame calibration, which
is measured from dataset frames on both sides of the pair and is therefore unaffected by
the harness bug — and `k` is bounded over an interval that spans the harness's value
anyway, so the certificates stay sound. The sweep's MOR(density) curve should be treated as
unvalidated until the harness reproduces the preset.

**That proposed next step is already eliminated.** I was going to route the harness through
`set_condition`, but reading it, for a non-night condition it does exactly what the harness
already does — `world.set_weather(weather_params(name))` plus headlights. So the difference
is not the weather call. Do not spend time re-testing that.

**What is actually still unknown:** why the same constructed `CLEAR_BASELINE` renders a
black sky in the dataset frames and a bright one in a live static capture. Note the
Town04-reload test measured only the road ROI, so it does not rule out a sky difference
surviving a reload. The cheapest next probe is to capture one clear frame immediately after
a fresh reload and print the SKY mean, before anything else touches the world.

**Priority: low.** This blocks only the static-capture calibration path
(`fog_density_sweep.py` and its MOR(density) curve, both already marked unvalidated). It
does not touch the ledger cells, which render live and whose fog calibration comes from
route frames on both sides of each pair.

---

## P-02 RESOLVED — confirmed, emphatically

    predicted (before the drive): FAIL, with departures, closer to the shadows cell
    measured: FAIL 20/20, ALL 20 runs departed, median max-CTE 92.3 ft (range 90.1-98.7)

The verify cell for the same pair says CERTIFIED at 72.3%. So the pre-registered 12-frame
median protocol certified a policy that departs the road on every single run, and the dense
corridor-breach statistic (23.7%) predicted the failure before it happened.

This is the second unsound certificate of the night and the first one predicted in advance.
Together with `shadows / S_clear` it settles F17: the defect is the aggregation rule, not
the verifier and not the disturbance models.

**Immediate consequence.** Two of the four `S_clear` verify cells are unsound, and the
reason is systematic rather than incidental. Until `verify_verdict` is replaced, CERTIFIED
from this protocol carries no assurance. I have not rewritten it tonight: it is
pre-registered, and replacing it is the kind of change that has to be deliberate and
committed as an amendment, not slipped in at 01:00 by the process that just failed it.

---

## D-01 RESOLVED — it is one specific corner, not a too-strict verdict rule

Recorded 2026-08-12 02:43. 20 extra repetitions of `fog / S_mixed` (40 runs), written to a
`_diag_` name so it is not a ledger cell.

    3/40 failures, rate 7.5%, Wilson [0.03, 0.20]

    rep  4  westbound  3.09 ft  step 1683  x -365.8  y 11.6
    rep  9  westbound  2.91 ft  step 1684  x -365.8  y 11.7
    rep 12  westbound  2.23 ft  step 1683  x -365.9  y 11.9

**All three failures are at the same place**, within 0.3 m of each other and at the same
step of the lap (~1683 of ~1700, near the westbound finish). Every failure across every
clean cell tonight has been westbound; there has not been a single marginal eastbound
failure. Westbound is systematically harder in this cell too: median max-CTE 1.27 ft
against eastbound's 0.62 ft, worst 3.09 ft against 0.91 ft.

**This settles the question D-01 posed.** The two candidates were "the verdict rule is too
strict for a stochastic simulator" and "there is a specific westbound corner where the
controller is marginal". It is the second. Three independent failures landing inside a
0.3 m window is not what stability-cliff non-determinism looks like — that would scatter
along the route.

**So do not loosen the verdict rule.** It was reporting something real. Had it been
relaxed to accommodate the first 1-in-20 failure, this corner would have been hidden, and
that is precisely the retrofitting the pre-registration exists to prevent.

**What it means for the study.** `S_mixed` drives fog competently everywhere except one
location, where it clips a 2.19 ft budget by 0.04-0.90 ft without departing. That is a
narrow, characterised, reportable defect rather than a robustness failure, and it is a much
better sentence than either option D-01 originally offered.

**Follow-ups, cheapest first:**

1. Look at what is at `x ≈ -365.8, y ≈ 11.7` on Town04 — geometry, lane markings, a
   junction — and whether the expert's own trajectory is marginal there.
2. Check whether the *clear* cells' marginal failures land at the same spot. The one clean
   instance so far is `clear / S_clear` rep 9 westbound, and that cell predates the
   `max_cte_at` instrumentation, so it needs a rerun to say.
3. If it is a route artefact rather than a policy defect, say so explicitly in the paper
   rather than reporting a 7.5% fog failure rate that is really one corner.

### D-01 root cause — the corner is inside the western intersection

Probing Town04 along the westbound lane at the failure point:

    x        lane w   junction   curvature deg/m   lane id
    -355.0     3.50     False          0.000         -2
    -360.0     3.50     True           0.000         -2
    -365.8     3.50     True           0.000         -2   <-- all three failures
    -380.0     3.50     True           1.510         -1

The westbound lap ends by driving back into the western intersection, and all three
failures land inside it, at step ~1683 of ~1700.

**Why the policy drifts there, and why the number is partly an artefact of the metric.**
`route.py` builds the reference by tracing lane centreline with a *straightest-at-junction*
policy. Inside a junction there is no painted centreline, so the reference is a
**constructed** path, and the policy has no visual cue corresponding to it. The vehicle is
being scored against a line that is not on the road, in the one place the road stops
telling it where to go.

This is not the metric being broken — CTE is measured against a fixed route polyline, not a
live `get_waypoint` projection, so it is not the lane-snapping artefact `route.py` was
written to avoid. The deviation is real. But "the lane-keeping policy deviates where there
is no lane" is a different and much narrower claim than "the policy fails in fog 7.5% of
the time", and only the first is supported.

**Recommendation, and it changes a success criterion so it is Zach's call.** Either exclude
junction segments from the CTE metric, or end the lap before the intersection. Both are
defensible; doing neither means every cell carries a junction-driven failure rate that has
nothing to do with the disturbance under test. Note this affects **all** cells equally, so
it does not change the ordering of any result reported tonight — `S_clear` still fails
night, fog and shadows catastrophically with departures, which is nothing like a junction
excursion.

---

## D-05 UPDATE — the control is less compromised than I said; its failures are the junction too

Recorded 2026-08-12 03:07. `clear / S_clear` rerun, 20 reps, with location recording:

    4/20 failures, NONE departed
      rep 1 westbound  2.23 ft  step 1687  x -374.1  y 11.9
      rep 6 westbound  2.39 ft  step 1687  x -373.9  y 11.9
      rep 8 westbound  2.26 ft  step 1688  x -374.1  y 11.9
      rep 8 eastbound  3.73 ft  step 1693  x -370.5  y 29.0

Every one is inside the western intersection at the end of the lap (~step 1690 of ~1700).
The westbound three cluster within 0.2 m; the eastbound one is the same junction on its own
lane. **This corrects two things I said earlier:**

1. "Every marginal failure is westbound" — wrong, there is now an eastbound instance. The
   direction was incidental; the *junction* is the invariant.
2. D-05 said the negative control "genuinely fails its own training condition" and is
   therefore compromised. On this rerun its failures are **entirely** the junction artefact
   that affects every cell equally, with no departures at all. That is not a policy that
   drives badly on clear.

**What remains genuinely open for D-05:** the original cell's rep 8 eastbound departure at
86.42 ft. Nothing in this 20-rep rerun resembles it, so it is a rare event rather than the
control being broken, and its cause is unknown. One departure in 40 runs on the training
condition is still worth explaining before the control is called clean.

**Net effect on the study.** With junction excursions set aside, the picture sharpens
considerably:

    S_clear   clear    marginal junction excursions only, no departures
              night    20/20 FAIL, every run DEPARTED
              fog      20/20 FAIL, every run DEPARTED
              shadows  20/20 FAIL, 16/20 DEPARTED
    S_mixed   clear    PASS 0/20
              night    PASS 0/20
              shadows  PASS 0/20
              fog      marginal junction excursions only, no departures

That is a much cleaner statement of the study's spine than anything available six hours
ago: the clear-only student departs the road on every unseen condition, the mixed student
completes every lap, and the only blemish on either is a shared route artefact at an
intersection where the reference path is synthetic.

---

## D-05 RESOLVED — every clear failure, departures included, is the intersection

Recorded 2026-08-12 03:33, pooling **80 runs** of `clear / S_clear` across three cells.

    80 runs, 9 failures (11.2%), 2 departures (2.5%)

Both departures are eastbound at essentially the same magnitude — 86.42 ft and 86.17 ft,
each 1.2% of frames over budget — which is a reproducible mode, not noise. And the location
settles what it is:

    rep 3 eastbound  86.17 ft  DEPARTED  step 1705  x -371.0  y 3.8

Step 1705 is the end of the lap and x = -371.0 is **inside the western intersection**, the
same place as every marginal excursion. `y = 3.8` is far off both lanes (eastbound ~30,
westbound ~12), so the vehicle really did leave the road — but it left it in the one place
where `route.py` follows a *synthetic* centreline and there is no painted cue to follow.

So the departures are not a second failure mode. They are the junction artefact escalating
when the drift happens to run far enough to trip the departure test.

### I revised this twice; here is the honest arc

1. First reading: the control "genuinely fails its own training condition", so the S_clear
   arm is confounded. Based on 2/20 including one departure.
2. Second reading: the failures are "entirely the junction artefact, no departures", so the
   control is mostly clean. Based on a 20-rep rerun that happened to contain none — **too
   thin a sample to support a negative claim about a 2.5% event.** Same sample-size mistake
   as F17, in a different guise.
3. This reading, on 80 runs: the failures *are* all the junction, departures included, and
   the departure rate there is 2.5%.

The second reading reached roughly the right conclusion for a bad reason, which is not the
same as being right. Twenty runs cannot establish "no departures" at a 2.5% rate — the
chance of seeing none is about 60%.

### Why the control is nevertheless sound

    S_clear on clear     2.5% departures, ALL inside the intersection
    S_clear on night     100% departures, throughout the route
    S_clear on fog       100% departures, throughout the route
    S_clear on shadows    80% departures, throughout the route

A 40x separation, and the failures are in different places for different reasons. "S_clear
fails the conditions it never saw" is supportable. The caveat that belongs in the paper is
narrow and specific: *on clear it also departs 2.5% of the time, at an intersection where
the reference path is synthetic* — which is an argument for fixing the route or the metric,
not evidence that the control cannot drive.

---

## D-07 — CORRECTION: the intersection is NOT a route artefact. It is a real ODD boundary.

Recorded 2026-08-12 03:40. **This overturns the recommendation in D-01's root-cause note
and in the overnight report.**

Pure pursuit steers geometrically toward a point on the reference path and never looks at
an image, so it has no perception to lose. Driving it round both laps under clear weather:

    eastbound   outside junction  max 0.17 ft   over budget 0.00%
    westbound   outside junction  max 0.14 ft   over budget 0.00%
    westbound   INSIDE  junction  max 0.05 ft   over budget 0.00%

The expert tracks the reference through the intersection to within **0.05 ft**. The
reference path is therefore geometrically feasible and perfectly drivable, junction or not.

**So I was wrong.** I argued the excursions were an artefact of scoring against a synthetic
centreline where no painted line exists, and recommended excluding junction segments from
the metric or ending the lap earlier. Both would have hidden a real result. The path is
drivable; what the students lack there is the *visual cue*, not a feasible reference.

**What it actually is.** An end-to-end lane-keeping policy fails inside an intersection
because the lane markings it depends on are absent. That is a genuine limitation of the
policy class and a real boundary of the operational design domain — considerably more
interesting than a metric bug, and exactly the sort of thing this study exists to find.

**Revised recommendation.** Do **not** exclude junction segments. Report the intersection
behaviour as a finding: both students degrade where markings vanish, `S_clear` to the point
of departing 2.5% of the time on its own training condition. If the study wants a clean
lane-keeping claim it should say "outside intersections" explicitly, rather than quietly
deleting the region that breaks it.

**How this was caught.** Only by running the control. The junction explanation fit every
observation — same location, both directions, both students, every condition — and it was
wrong about the cause. Fitting all the data is not the same as being right.

---

## D-07 WITHDRAWN — the expert control never drove the junction; it establishes nothing

Recorded 2026-08-12 03:52. **I asserted D-07 on a broken control and must take it back.**

D-07 claimed pure pursuit tracks the reference through the intersection to within 0.05 ft,
and concluded the reference is drivable and the excursions are a real ODD boundary. Both
runs behind that claim were invalid:

1. **First run: the car never moved.** I omitted the warm-up `closed_loop_ledger` performs,
   so the vehicle sat at spawn for all 2200 steps. Its "max CTE 0.14 ft" was a parked car
   sitting exactly on the route. I read that as perfect tracking. The tell was there in the
   output — the closest approach to every student failure was 13–33 m, which is roughly the
   spawn-to-junction distance — and I did not check it before writing the conclusion.

2. **Second run, with the car actually driving: it still never reaches the junction.**
   Comparing by route index rather than world coordinate: the expert visits 1055/1522
   (eastbound) and 1068/1522 (westbound) route indices and **0 of the junction indices** in
   both directions. The lap terminates on loop closure (within 12 m of start) and the spawn
   sits just west of the intersection, so the expert lap ends before entering it.

**So the question D-07 claimed to answer is still open:** is the reference through the
junction trackable? Unknown. To find out, the control must not stop at loop closure — start
the expert mid-route, or extend past the closure point.

### What IS established, and it is not nothing

The CTE measurement is sound, which was worth checking given the failures all cluster at
lap end where `nearest_index` could wrap. Comparing each recorded max-CTE position against
the true distance to the reference polyline:

    departure   reported 86.17 ft   true distance 86.17 ft   exact
    marginals   reported 2.2-3.1 ft true distance 3.2-4.2 ft

The departure is exact, so the vehicle genuinely left the road by 86 ft — no index
wraparound. The marginal gap is the expected vertex-versus-segment difference at ~1 m route
spacing, not an error. **The failures are real deviations from a real reference.**

### The lesson, which is the same one twice tonight

D-05 and D-07 both went wrong the same way: I ran something, it produced a number in the
direction I expected, and I wrote the conclusion without checking that the experiment had
exercised what it claimed to. A parked car reports excellent tracking. Twenty runs report
no departures at a 2.5% rate. Neither is evidence, and both look like evidence.

---

## D-08 — expert control, third attempt: EASTBOUND answered, westbound still not

Recorded 2026-08-12 04:00. Starting the expert 120 route indices *before* the junction so
it must drive through, rather than at spawn where the lap ends first:

    eastbound   visited 183 idx, junction 14/14   max CTE IN JUNCTION  0.00 ft,   0% over budget
    westbound   visited 123 idx, junction  5/16   max CTE             159.68 ft, 100% over budget

**Eastbound is a real result.** The expert covers every junction index and tracks the
reference to 0.00 ft, against a 2.19 ft budget, having driven ~180 route points cleanly
(whole-drive max 0.12 ft). So the reference path through the intersection **is** trackable
eastbound. The student's eastbound failure at that same place (3.73 ft, and the 86 ft
departure) is therefore not caused by an infeasible reference.

**Westbound is not a result, it is a broken run.** 123 indices in 400 steps is far short of
the ~700 expected at 20 mph, only 5 of 16 junction indices were reached, and 159.68 ft is
not a tracking error, it is a vehicle somewhere else entirely. The start pose is computed
from `route[ji[0]-120]`, and route index order need not follow travel direction, so
westbound very likely started facing the wrong way or off-road. **I am not reporting the
159.68 ft as evidence of anything.**

### Where this leaves the question

For **eastbound**, D-07's withdrawn claim turns out to have been right for the wrong
reasons: the reference is drivable and the failure is the policy's, consistent with an ODD
boundary at intersections where markings vanish. For **westbound** — which is where most of
the marginal excursions occurred — it remains open.

That asymmetry matters and should not be smoothed over. Do not generalise the eastbound
result to westbound; fix the start-pose construction (use the route's own travel direction,
and verify the vehicle is on-road and moving before trusting the numbers) and rerun.

---

## D-09 — the junction coincides with the route's index SEAM; the two explanations are confounded

Recorded 2026-08-12 04:08. Found while trying to fix the westbound control, and it is more
useful than the control would have been.

    westbound junction route indices: 1506..1521  of 1522

The intersection occupies the **last 16 indices of the route**, so it sits exactly on the
seam where the closed-loop route wraps 1521 -> 0, which is also where the lap-termination
test fires. Every failure tonight — marginal and departure, both students, all conditions —
happened there.

**So two explanations are confounded, and no measurement tonight separates them:**

1. *Perception*: an intersection with no lane markings, where an end-to-end policy has no
   cue. (Supported eastbound by D-08: the expert tracks that region at 0.00 ft, so the
   reference is feasible and the failure is the policy's.)
2. *Representation*: the route's index seam, where `nearest_index` can wrap and pure
   pursuit's lookahead `route[(i + n_ahead) % n]` crosses the discontinuity.

They are at the same place, so "failures cluster at the junction" and "failures cluster at
the seam" are the same observation.

**What rules part of it out.** The CTE values themselves are sound: each recorded max-CTE
position was checked against true distance to the reference polyline and the 86 ft
departure matched exactly. So the *measurement* does not wrap. That does not clear
explanation 2 — a policy steered by a lookahead that crosses the seam can genuinely drive
off, and the CTE would then correctly report a real excursion.

**How to separate them, and it is cheap.** Rebuild the route with its seam moved to the
middle of a straight — e.g. rotate the index origin by half a lap — and rerun one cell. If
failures follow the *junction*, it is perception and the ODD-boundary reading is right. If
they follow the *seam*, it is representation and the excursions are an artefact of the
route encoding rather than anything about weather robustness. Nothing else in the pipeline
needs to change.

**Why I stopped here.** Three attempts at the expert control produced one valid answer
(eastbound) and two broken runs, and the fourth attempt drifted 6 m off-lane during warm-up
before it reached the junction. The seam finding makes the control less important than the
experiment above, which tests the actual question directly.

---

## D-09 RESOLVED — failures follow the junction, not the seam. It is a real ODD boundary.

Recorded 2026-08-12 04:10. `ROUTE_ROLL=761` moves the westbound junction from route indices
1506–1521 (on the seam) to 745–760 (mid-route), leaving geometry, spawn and lap termination
untouched. Rerunning `clear / S_clear`, 20 runs:

    2/20 failures
      rep 2 westbound  2.35 ft  x -373.9  y 11.9
      rep 6 eastbound  2.52 ft  x -368.1  y 29.3

    unrolled, for comparison: x -374.1, -373.9, -374.1 (westbound), -370.5 (eastbound)

**Failures land in the same physical place with the seam moved half a lap away.** So they
follow the intersection, not the route's index discontinuity. The representation
explanation is eliminated; the perception one stands.

Consistent with D-08's eastbound control, which showed the expert tracks that same region
at 0.00 ft — the reference is feasible, and it is the learned policies that degrade there.

**So the ODD-boundary reading is correct after all, and now it is supported.** An
end-to-end lane-keeping policy fails inside an intersection because the lane markings it
depends on are absent. `S_clear` departs 2.5% of the time on its own training condition for
this reason, and both students show marginal excursions there.

**Do not exclude junction segments from the metric.** That was my first instinct, and it
would have deleted a real finding. Report it: the ODD is "lane-marked road", and the study
has measured where that boundary lies.

**Note the route of this conclusion.** I reached it, withdrew it as unsupported, and
reached it again with evidence. The middle step was right: the first control was broken,
and a conclusion resting on a parked car deserved withdrawal even though it happened to
point the correct way. Being right by luck and being right are different, and only the
second is reportable.

---

## D-10 — fog `k` narrowed to the route-frame fit; why this is not tuning toward a verdict

Recorded 2026-08-12 11:20. **This changes a verification input, so the reasoning is on the
record before the cells are re-run.**

Fog was the only condition running at d = 2, because two calibrations disagreed on the
surface-illumination term `k` (route frames 0.72, static sweep ~1.14) and I bounded it over
both, [0.637, 1.255]. That was the right call while both measurements stood. It is no
longer, because one of them has an identified defect.

**Why the static sweep is excluded, not out-voted.** Its clear baseline renders a sky at
0.2575 where the dataset's is 0.0021 — a 100x difference, from a harness that does not
reproduce the preset (D-04, F18). Airlight is driven by the sky region, and `A` trades off
against `k` in the fit, so a sky wrong by two orders of magnitude biases `k` directly. The
route-frame fit uses dataset frames on **both** sides of every pair, so it is internally
consistent, and it is the one that passes the fidelity checks — D3 (a),(b),(c),(f) 8/8 at
ROI R^2 +0.870, with a sharp rmse minimum at k = 0.70 that degrades 3.5x by k = 1.20.

**This is not the thing I argued against.** Zach proposed tuning the disturbance model until
verification matched closed loop; I said no, because that fits the answer. This is
different: a measurement is being dropped for a cause identified independently of any
verdict, and the surviving value was chosen by image fidelity, not by which verdict it
produces. The distinction is that the criterion is pixels, not agreement.

**Measured effect, same frame, same student, same verifier:**

| | certified | falsified | UNKNOWN |
|---|---|---|---|
| k bounded [0.637, 1.255] | 56.2% | 0.0% | **43.8%** |
| k fixed 0.717 | 82.4% | **17.6%** | **0.0%** |

UNKNOWN collapses and the verifier resolves a violation it previously could not. On an
8-frame sample the cell goes FALSIFIED with median UNKNOWN 0.0%, and costs roughly 3x less
because many frames resolve in 11-17 bounds instead of exhausting 96.

**What is given up, and it should be said in the paper.** The interval was sound under
either calibration; a point estimate is only sound if the route-frame fit is right. The
honest framing is that fog certificates are conditional on a calibration measured from
dataset pairs and validated by D3 — not on an assumption-free bound. If D-04's root cause
is ever fixed and the static sweep agrees, the interval can come back and the certificates
strengthen.

---

## D-11 — the eastbound fog certificate used a clear baseline from a different session

Recorded 2026-08-15. **This changes a verification input, so the reasoning is on the record
before the cells are re-run.** It was found while checking whether the committed 12/12 is
reproducible, not by a ledger contradiction — the ledger cannot see it, because the affected
quantity is an input to the certificate rather than one of its verdicts.

### The defect

`certify_sustained_bound.py` builds the disturbance from two files:

    clear      <- lap_{dir}_clear.npz
    condition  <- lap_{dir}_{cond}.npz

The certificate interpolates between them, so the clear endpoint is half the definition of
the disturbance. Those two files are different CARLA sessions, hours apart, and nothing in
the pipeline required them to agree.

### The measurement

`lap_eastbound_fog.npz` is the only capture that recorded its own clear frames. Against the
clear capture the certifier actually used, at identical poses (max |dx| = |dy| = 0.0):

    signed mean +0.04899, abs mean 0.04912  ->  a uniform brightening, not noise
    83% of the fog disturbance it is supposed to be certifying against

### Candidate causes considered

| candidate | ruled out? | why |
|---|---|---|
| pose misalignment | **yes** | max |dx| = |dy| = 0.0; the two captures are pose-identical |
| random render noise | **yes** | signed mean equals abs mean, present at 100% of poses, flat along the lap — a DC offset, not noise |
| a real fog property | **yes** | it is measured between two CLEAR captures; no fog is involved on either side |
| coarse quantisation | **yes** | std is 0.021 against a 0.049 mean; the offset dominates its own spread |
| affects all conditions equally | **no, and this is the useful part** | night and shadows reproduce across directions to 0.3-0.4%; fog differs by 41% and FLIPS SIGN (-0.0348 W, +0.0149 E). Re-paired against its own clear, eastbound fog reads -0.0341 against westbound's -0.0348 |

### What it comes down to

The same fog preset cannot darken the road in one direction and brighten it in the other.
One capture is inconsistent with the rest and it is the one whose baseline came from a
different session — the cell F37 records as added late, "saved under a filename the
certifier did not look for".

### Effect on the verdicts, measured before deciding anything

    model     baseline    bound            x tol           verdict
    S_clear   foreign     [-0.00984,+0.00348] [-0.82,+0.29] CERTIFIED
    S_clear   paired      [-0.00541,+0.00469] [-0.45,+0.39] CERTIFIED
    S_mixed   foreign     [-0.00259,+0.00512] [-0.22,+0.43] CERTIFIED
    S_mixed   paired      [-0.00206,+0.00306] [-0.17,+0.26] CERTIFIED

**No verdict changes, and the study is not better off for it having been wrong.** The
corrected bound is tighter, so the correction widens the gap between certified and falsified
cells rather than closing it. Had it gone the other way this would be a retraction.

### The fix, and why it is not tuning

A condition capture that recorded its own clear frames is paired against those; otherwise
the dedicated clear capture is used, and which one was chosen is printed and stored in
`sustained_bound.json`. This is not a parameter chosen to move a verdict — it is a rule that
says a controlled comparison must vary one thing, and it is applied to every cell
identically, including the eleven where it changes nothing.

### What is NOT fixed

Ten of the remaining eleven cells still take their baseline from a different session, because
they have no internal one to use. The evidence they are sound is the 0.3-0.4% cross-direction
agreement above, which a drifting baseline would have destroyed — that is positive evidence,
not proof. **Future captures must record the clear baseline in the same file as the
condition.** Until they do, this failure mode is undetectable in any cell but eastbound fog.

---

## D-12 — the ledger's `verify` cells belong to a RETIRED instrument, and the headline is not in the ledger at all

Recorded 2026-08-15. This disposes of the two standing `verify` contradictions
(`night/S_mixed`, `fog/S_mixed`), which have sat red without a written cause while D-01 and
D-05 covered the two closed-loop ones.

### What the ledger is actually holding

Every non-vacuous `verify` cell carries `median_certified` / `median_falsified` /
`cell_budget` / `fog_k_interval` — the 12-frame-median, per-frame-**fraction** instrument.
None of them carries a sustained-bias bound. Checked all eight:

    clear   S_clear   CERTIFIED   vacuous by construction
    clear   S_mixed   CERTIFIED   vacuous by construction
    fog     S_clear   FALSIFIED   12-frame median
    fog     S_mixed   FALSIFIED   12-frame median   <- contradicts pre-registered CERTIFIED
    night   S_clear   FALSIFIED   12-frame median
    night   S_mixed   FALSIFIED   12-frame median   <- contradicts pre-registered CERTIFIED
    shadows S_clear   FALSIFIED   12-frame median
    shadows S_mixed   CERTIFIED   12-frame median

### Why they are red, and why that is correct

That instrument is retired. It counts the fraction of a disturbance axis it can prove safe,
which F33 established measures **provability rather than severity** — provability depends on
bound width, which depends on network size, and `S_mixed` is 3x the width of `S_clear`. Its
verdicts are therefore expected to be wrong in exactly the direction observed: it falsifies
the wider, safer model. Against ground truth it scores 4/8, and both cells the ledger flags
are cells where it disagrees with driving and the sustained instrument agrees with driving.

**The ledger is not malfunctioning here. It is correctly reporting that a superseded
instrument disagreed with the study's expectations.**

### The real gap

The instrument that produces the paper's result — the sustained-bias bound of F34-F37 —
**has no ledger cell type at all**. Its twelve results live in
`results/calibration/sustained_bound.json`, which `study.ledger` never reads. So the
executable smell test that `CLAUDE.md` says to run before interpreting any result does not
cover the headline claim. That is how F43's baseline defect survived: the ledger could not
have caught it, because it was never looking.

### What was deliberately NOT done

**The verify cells were not overwritten with the sustained verdicts.** Writing them now would
place a verification verdict in git AFTER the closed-loop run it is supposed to have
predicted, which is precisely what `python -m study.ledger --check-order` exists to detect.
The blind protocol is worth more than a green ledger.

### What should be done instead

Give the ledger a THIRD instrument column for the sustained certificate, populated going
forward, with the existing twelve entered as what they honestly are — in-sample, computed
after the driving, and marked as such. The blind record then stays intact and the smell test
starts covering the claim the paper actually makes.

### D-12 addendum (2026-08-25) — the era-1 `S_mixed` verify cells were never blind, and the ordering says so

`--check-order` flags `night/fog/shadows / S_mixed / verify` as committed AFTER their
closed-loop counterparts. That is historically accurate, not an artifact: on 2026-08-11
the S_clear closed-loop cells were deliberately deferred so their verification could be
committed first (D-02), but the S_mixed drives ran before the S_mixed verification
sweeps of the retired 12-frame-median instrument. Those verify cells were postdictions
of a retired instrument and were never claimed as predictions — the paper reports the
canonical certificate cells as in-sample throughout. The cells carry
`disposition: D-12`; the ordering flag stays visible as a dispositioned warning. The
blind record of this study is: the S_clear era-1 arm (D-02) and the committed
predictions P-03..P-09, each checkable in git.

The third-instrument column described above now exists: `study.design` registers
`sustained_bound.json` (in-sample, 12 cells), and `study.ledger` renders it against
the final campaign.

---

## D-13 -- WITHDRAWN with the rain condition (2026-08-25)

This section disposed of a rain ledger contradiction. Rain was withdrawn from the
study: CARLA's rain rendering is temporally stochastic, the deterministic
two-endpoint family cannot represent it, and it is future work (see
`study/design.py` OUT_OF_SCOPE and FINDINGS F47's withdrawal note). The number
D-13 is retired, not reused; the full text is in git history at this commit's
parent.

---

## D-14 — the era-1/final fog contradiction is the JUNCTION, and the lap-scope amendment is the divide

Recorded 2026-08-25, during the codebase audit that reconciled the ledger with the
paper. Two records coexisted without a written bridge: the canonical
`fog / S_clear / closed_loop` cell says FAIL 20/20 (2026-08-12, P-02), while the final
campaign (`fog___trunc_Sclear`, 2026-08-14) and the paper say PASS 0/10 — and the
pre-registered expectation for `fog / S_clear` is FAIL, which the final campaign
therefore contradicts.

### Candidate causes considered

| candidate | ruled out? | on what evidence |
|---|---|---|
| the students were retrained between the campaigns | **yes** | both cells record the same checkpoint (`S_clear_84x28`); no retrain commit exists between them |
| a fog-rendering fix changed the disturbance | **yes** | the era-1 cell postdates the constructed-preset fix; its runs drove fog_density 70 through the same `weather_params` path |
| a genuine fog capability change | **yes** | era-1 runs held the lane for 98.8% of frames (`frac_over_budget` mean 0.012) — a policy that cannot drive fog looks like night (67.9% of frames over, failing from step ~11) |
| **the western intersection** | **NO — this is the cause** | every era-1 fog failure has its max-CTE at steps 1695–1706, x ≈ −370..−379 — inside the junction at the end of the full lap, the exact location D-01/D-05/D-09 characterised. The same is true of the P-03 density cells (d25/d40/d55: all departures at steps 1703–1705). On the open road the same checkpoint at the same densities is clean: 0/60 departures across densities 25–100 (`fog___openfog_*`), max CTE 0.22–0.28 m |

### What happened, in order

1. Era-1 drove the FULL lap, whose last ~16 route indices sit inside the western
   intersection (D-09). In fog, the policy completes the open road cleanly and departs
   at the junction on every run — the ODD boundary (no lane markings) escalating under
   degraded contrast, not a fog-robustness failure.
2. The protocol was amended by deliberate direction (F28, quoted there: "it must be
   the full lap but no intersection"): the lap is scored 0–2861 m, ending before the
   junction, which is reported separately as a real ODD boundary (D-07/D-09
   established the reference through it is drivable eastbound and the failure is the
   policy's).
3. Under the amended protocol the final campaign measured the table the paper reports:
   `S_clear` PASS clear+fog, FAIL night+shadows 10/10; `S_mixed` PASS all four.

### What is corrected

The pre-registered expectation `fog / S_clear -> FAIL` (and `-> FALSIFIED` for the
certificate) is superseded by measurement, an expectation superseded by measurement: the design-time
expectation "the clear-only student fails every condition it never saw" turned out
wrong for fog specifically, for a measured physical reason — Koschmieder transmittance
barely moves at short range, so fog darkens the far field the crop discards rather
than the road the network sees (F27, STATE_OF_PLAY §1). The expectation is NOT edited;
the cells carry `disposition: D-14` and stay visibly flagged as dispositioned.

### What this does NOT license

The era-1 cells are not deleted or overwritten — they are the record of the
superseded protocol, and the junction finding they contain is real and reported.
`study.design.FINAL_CLOSED_LOOP` names the final-campaign cells, and `study.ledger`
now checks both eras and the sustained certificate side by side.

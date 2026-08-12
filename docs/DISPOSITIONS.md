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

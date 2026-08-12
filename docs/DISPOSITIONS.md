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

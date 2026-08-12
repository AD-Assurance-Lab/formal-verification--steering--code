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

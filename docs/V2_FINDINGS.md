# V2 — what the paper's "0.98 ft" student actually does: findings (RETRACTED — see header)

> **RETRACTION, 2026-09-06 09:05.** The central conclusion below is WRONG and its
> recommendation must not be acted on.
>
> V2 measured this checkpoint through `closed_loop_ledger.py` **before** that driver was
> given the R-SIM-4 rendered-frame check. That check costs six `world.tick()` calls, which
> `evaluate.py` had and the ledger did not, so the vehicle settled differently and the
> closed loop committed to a different discrete basin. V2's "1.42 ft in twelve of twelve
> laps" was that basin, not the student.
>
> Re-run on the corrected driver (`results/town06/lr_seed0_fixed/`, 12 laps):
>
> ```
>   0.97 ft x8   0.98 ft x1   1.34 ft x3      median 0.97
>   clears pass 3's 1.0958 ft margin: 9 of 12
>   evaluate.py, same night: 0.97 x3, 0.99, 1.34 x2  -- the SAME two modes
> ```
>
> **So the paper's "drives fog at 0.98 ft" is corroborated, not contradicted**, and
> E4-F1's "the first student in this study to clear pass 3's margin gate on fog" is also
> corroborated — it clears it in three quarters of laps. **Do not remove that number from
> `sec_results.tex`.**
>
> What survives from below: the cross-driver discrepancy was real and is now diagnosed and
> fixed (six ticks, and a missing R-SIM-4 check on the scored driver); and quoting an arm
> with its interval is still better practice than quoting one seed, because the two modes
> here are 0.97 and 1.34. But the reason is ordinary multimodality, not a failure to
> replicate.
>
> The document is kept unedited below so the wrong conclusion and its correction sit
> together.


**Run 2026-09-05, 23:08–23:29.** Pre-registration `docs/V2_PREREGISTRATION.md`, committed
before the first lap. 12 laps of `S_mixed_depth_d3lr3_s0` under fog through the scored
ledger driver, plus a 6-lap cross-driver check. Output `results/town06/lr_seed0/`.

```
  closed_loop_ledger.py   12 laps    1.42 ft x 12      median 1.42   0/12 clear the 1.095 ft margin
  evaluate.py (sweeps)     6 laps    0.97 x3, 0.99, 1.34 x2         3/6 clear it

  the paper (sec_results.tex:330) quotes 0.98 ft
```

## The short answer

**Under the study's own scored instrument the student drives fog at 1.42 ft, twelve times
out of twelve, and never clears pass 3's margin.** Under the sweep instrument it ranges
0.97–1.34 ft. Either way, **0.98 ft is at the favourable end of a distribution, not a
property of the student**, and the draft's sentence should not rest on it.

V2-P1 and V2-P3 held. V2-P2 held in an extreme form. V2-P4 held.

## V2-P1 — HELD. 0.98 ft is not the centre

Predicted the median of 12 laps would be above 0.98 ft. Measured **1.42 ft in every one of
12 laps** through the ledger, and a median of **0.98 ft** through the sweep driver — which
is the number the paper quotes, and which is that driver's *best* mode, not its only one.

## V2-P2 — HELD, extremely. The distribution is discrete

Predicted fewer than 8 distinct values in 12 laps. Measured **one**. Twelve laps landed on
1.42 ft to two decimal places.

This is a sharper version of E1b's discreteness result and it is worth noting for its own
sake: this checkpoint is not noisy on this route. It is *perfectly* repeatable through the
ledger. The shipped student's fog cell, by contrast, produced six distinct values across 24
laps (V1). **Multimodality is a property of the particular policy, not of the harness** —
which is further evidence the harness is not what makes cells void.

## V2-P3 — HELD, and this is the one the paper needs

Predicted fewer than half the laps clear the 1.095 ft margin. Measured **0 of 12** through
the ledger and **3 of 6** through the sweep driver.

The draft's Limitations calls this student one that "drives fog at 0.98 ft", and E4-F1
called it *"the first student in this study to clear pass 3's 1.095 ft margin gate on fog"*.
Through the instrument that writes the study's scored ledger, **it does not clear that gate
at all**, in twelve consecutive attempts. Through the instrument that produced the original
claim it clears it half the time.

**Neither reading supports quoting 0.98 ft as what the student does.**

## V2-P4 — HELD. Every lap is under budget

12/12 under the 2.19 ft budget through the ledger, 6/6 through the sweep driver. The student
is a good driver. The question was always headroom, and it does not have pass 3's.

## The open item: two committed drivers disagree, systematically

Same checkpoint, same GPU, same night, same condition:

```
  closed_loop_ledger.py    1.42 ft, twelve times
  evaluate.py              0.97-1.34 ft, six laps
```

Things that are **not** the explanation, each checked:

* **Not scoring scope.** Both exclude PPC-bridged steps. The ledger's trace is 1274 rows =
  1179 non-bridged + 95 bridged, and `evaluate.py`'s reported "steps 1179/1280" is exactly
  that non-bridged count. Both drive the same lap and score the same subset.
* **Not the route or the spawn.** Both call `env.teleport` then `env.warmup_to_speed` with
  pure-pursuit steering, on `SPAWNS['lap']`.
* **Not a bridged-span peak.** The ledger's peak sits at s = 206.7 m, far from either bridge
  span (618–707 m, 1548–1630 m).

One difference *was* found and it does not explain the CTE gap: the departure threshold is
`|cte| > 4.0` m in `evaluate.py` and `> 6.0` m in the ledger. That changes departure flags,
not peak CTE, and no lap here is near either.

**So the cause is a genuine trajectory difference and it is not yet identified.** That is
recorded as an open item rather than guessed at.

### Why it matters beyond this student

The two families of numbers in this study come from these two drivers:

```
  closed_loop_ledger.py   the scored ledger -- the paper's agreement figure, all eight cells
  evaluate.py             via compare_student_variants: E4, Q1, Q2's gate, Q4, and pass 3
```

If they disagree by ~0.4 ft on a student that is otherwise perfectly repeatable, then **a
sweep number and a ledger number are not interchangeable**, and comparisons that cross the
boundary need care. Q2's gate, for instance, is an `evaluate.py` measurement being compared
against pass 3's `evaluate.py` measurements — internally consistent, and the right
comparison. But the paper's "0.98 ft" (sweep family) sits in a Limitations paragraph
otherwise discussing ledger results.

**Nothing measured so far is invalidated by this.** Every comparison in Q1–Q4 was
driver-consistent within itself. What it means is that the discrepancy should be understood
before any future result mixes the two.

## Recommendation for the draft

Replace the single figure with the arm-level result, which is driver-consistent and
15 seeds deep:

> changing only the learning rate moves the fog median from 10.43 to 2.33 ft (n = 15 per
> arm, Hodges–Lehmann +5.96 ft, 95% CI [−0.02, +9.57], Mann–Whitney p = 0.055), and the fog
> distillation-error tail from 0.1024 to 0.0732 (p = 0.008).

and drop the claim that any student cleared the margin gate on fog, since the one student
that appeared to does not do so through the scored instrument.

## What was NOT done

Nothing written to either canonical ledger or either certificate. E4's, Q1's and Q2's cells
all stand as collected — V2 replaces no committed measurement. The cross-driver check is a
new artifact (`crossdriver_evaluate_fog.json`), not a re-scoring of an old one.

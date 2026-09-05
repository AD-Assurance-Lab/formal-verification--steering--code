# Q6 — why is a fixed objective on fixed data this noisy?: pre-registration

**Written 2026-09-05, before any Q6 distillation.** Queue item `docs/EXPERIMENT_QUEUE.md`
§Q6. Output `results/town06/variance/`. **No simulator at any point** — every endpoint here
is a KD error measured by `scripts/kd_error_by_condition.py` on cached teacher targets.

## The question

> With kernels pinned, seed fixed and data fixed, distillation is bit-exact. Across seeds
> the fog p99 has **CV 42.6%** and two objectives at the same seed correlate at r ≈ 0.
> Where does that dispersion come from, and can it be reduced?

## Why this is second in the queue and not last

It is not a result about the policy; it is a result about **the cost of every other
experiment in this lab**. The dispersion is why E4's 6x median shift landed at p = 0.247,
why Q1 needs 15 seeds per arm to confirm one knob, and why E2R-F5 put the sample size for a
20% effect at n ≈ 20–60. If Q6 finds a lever, every later experiment gets cheaper. If it
finds the dispersion is intrinsic, then that is the honest reason the study's training
comparisons are expensive, and it belongs in the write-up rather than being rediscovered
each time.

**Q6 runs before Q5** for exactly that reason, as the queue directs.

## What is already known and is NOT re-measured

* The seed alone never pinned a draw: three draws of "seed 0" gave fog p99 0.1027 / 0.1427
  / 0.1036 (E2-F6). `DISTILL_DETERMINISTIC=1` fixed that, and distillation is now bit-exact
  — re-confirmed today, twice, by SHA-256 against `S_mixed_taildet_a0p0_s0` and
  `S_mixed_depth_d3lr3_s0` (Q1 fold-in validation).
* The train/val split is **not** a variance source: `block_split(..., seed=0)` is hard-wired
  to seed 0 and does not read `DISTILL_SEED`.
* Augmentation is **not** a variance source at the study's recipe: `--augment` defaults to
  0.0, so `dataset._shift` never draws.

So the dispersion has to come from what `DISTILL_SEED` actually still controls: **weight
initialisation and minibatch order**, which today share one global RNG stream.

## Recipe — fixed before running

All Q6 arms use the **tuned** recipe, `lr=3e-4`, 168x56, channels (32,64,64), fc 128,
teacher `teacher_mixed_t06lap_dagger_r03`, base `mixed_t06lap`, the two DAgger dirs,
kernels pinned. That is the recipe everything downstream of Q1 uses, and measuring the
dispersion of a recipe the study is abandoning would answer the wrong question.

**Primary endpoint: fog `p99_abs_err`** from `kd_error_by_condition.py`
(`conditions.fog.p99_abs_err`). Secondary: clear p99, fog RMSE, and night p99. Dispersion
is reported as **SD and CV**, with bootstrap 95% intervals on the CV — a variance
comparison at n = 8 is itself noisy, and reporting a bare ratio of SDs would repeat the
mistake this experiment exists to characterise.

## The one code change, and how it is proved harmless

`DISTILL_SEED` currently seeds torch, numpy and python once, and both the student's
initialisation and the DataLoader's shuffling then draw from the same global torch stream.
Separating them needs two new **opt-in** environment variables:

* `DISTILL_INIT_SEED` — seeds the weight initialisation.
* `DISTILL_DATA_SEED` — seeds an explicit `torch.Generator` passed to the training
  DataLoader.
* `DISTILL_TRAIN_FRAC` — deterministically subsamples the training index for Q6b.

**The default path must remain bit-identical.** Passing a `generator=` to the DataLoader
changes the RNG stream even when it is seeded identically, because shuffling currently
consumes the same global stream the initialisation drew from. So the new path is taken
**only when the variables are explicitly set**; with them unset, not one line of the
existing code path changes.

**That is verified, not asserted.** After the change, seed 0 is re-distilled at both
`lr=1e-3` and `lr=3e-4` and compared by SHA-256 against `S_mixed_taildet_a0p0_s0` and
`S_mixed_depth_d3lr3_s0` — the two reference hashes recorded in the Q1 fold-in validation.
**If either differs, the change is reverted and Q6 does not run until it is bit-neutral.**
A pytest case pins this so it cannot regress silently.

---

## Q6a — initialisation or data order?

Three arms, n = 8 each, on the tuned recipe:

| arm | init seed | data seed | isolates |
|---|---|---|---|
| `init` | 0–7 | **fixed 0** | initialisation alone |
| `data` | **fixed 0** | 0–7 | minibatch order alone |
| `both` | 0–7 | 0–7 (tied) | the study's current notion of "a seed" |

The `both` arm is **free**: it is Q1's `lr3e4` arm, same recipe and same pinned kernels, at
n = 15. Only `init` and `data` need distilling — 16 runs, ~20 min of GPU.

**Q6a-P1.** Initialisation dominates: SD(`init`) is at least **2x** SD(`data`). Reason: the
loss surface here is small and heavily overparameterised relative to 27k frames, and E2-F6's
unpinned spread came from kernel non-determinism perturbing *gradients*, which is closer to
data order than to init — yet the spread across seeds is as large, suggesting the basin is
chosen early and by the draw.

**Q6a-P2.** The two roughly compose: SD(`both`)² is within a factor of 2 of
SD(`init`)² + SD(`data`)². A gross departure means the two interact, which would itself be
worth reporting.

**If Q6a-P1 holds, there is a cheap lever**: initialisation is the one thing a warm start
controls, and `distill.py` already has `--init-from`.

## Q6b — intrinsic to the 27k-frame pool, or estimation noise?

The queue asks whether variance shrinks with more DAgger data. **More data does not exist
without a new capture**, so the runnable form is the other direction: shrink the pool and
see whether the dispersion grows.

`DISTILL_TRAIN_FRAC` ∈ {0.25, 0.5, 1.0}, n = 8 seeds each (1.0 reuses Q6a's `both` arm).
16 new distillations, ~20 min.

**Q6b-P1.** CV of fog p99 **grows** as the pool shrinks, monotonically across the three
sizes. If it does, the dispersion is at least partly a sample-size effect and more DAgger
data would reduce it — a concrete, costed recommendation for the next capture.

**Q6b-P2.** The trend is **shallow**: CV at 0.25 is less than **2x** CV at 1.0. Reason:
E1 and E2 both found the draw dominating every lever tried, which reads more like an
intrinsic property of this objective than like an estimation error that would fall off
quickly. **If P1 fails — CV flat or falling as data shrinks — the dispersion is intrinsic
to the objective, more data will not fix it, and that is the answer.**

## Q6c — does combining seeds beat the median seed?

No new training. From the `both` arm's 15 students:

* **Output ensemble** of k ∈ {2, 4, 8} students, averaging predicted steering.
* **Weight average** of the same k, parameter-wise.

Both measured on the same fog p99 endpoint, over all disjoint subsets available at each k.

**Q6c-P1.** The output ensemble beats the **median** single seed on fog p99 at k = 4, and
beats the **best** single seed at k = 8. Averaging independent errors is the one thing that
reliably reduces a tail.

**Q6c-P2.** The weight average **fails**, and badly — worse than the worst single seed at
k = 2. Independently initialised networks are not linearly mode-connected without
permutation alignment, and nothing here aligns them. This prediction is recorded because
the queue lists "ensemble or weight average" as one option, and they are not one option.

**The caveat is declared now, before the numbers.** An output ensemble of k students is
**k times the ReLU count to certify**, and this study's whole thesis is that the bound
width is what constrains the architecture. E4-F2 measured depth costing 2.3–3.7x bound
width; a k = 4 ensemble is a much larger ask. **So a Q6c win is a result about the
distillation pipeline's noise floor, not a proposed shipping architecture**, unless the
bound on the averaged network is separately measured — which is out of Q6's scope and would
be its own queue item. Reporting an ensemble as a fix without that measurement would be
exactly the kind of claim this study exists to refuse.

## What counts as an answer

* **Q6a resolves the source** — init or data — and either way the next experiment can hold
  the dominant one fixed and halve its seed count. That is the outcome worth the most.
* **Q6b-P1 holds:** the next capture campaign has a measured reason to be larger, with a
  number attached.
* **Q6b-P1 fails:** the dispersion is intrinsic, n ≈ 20–60 for a 20% effect is simply the
  price of this objective, and it goes in the write-up as a measured property rather than
  as a repeatedly rediscovered inconvenience.
* **Q6c-P1 holds:** the pipeline has a cheap variance fix for *measurement* purposes — a
  stable reference point to compare arms against — even if it never ships.

## Bound by

`PROTOCOL.md`, standing rules 1, 3, 7 and 8. No CARLA, no promotion, no `.selected` pin,
nothing written to either ledger or either certificate. The code change is proved
bit-neutral against two committed reference hashes before any Q6 number is taken.

---

# AMENDMENT A-1 — the `both` arm is not free after all, and is run explicitly

**Recorded 2026-09-05, after the code change was proved bit-neutral and before any Q6
distillation.** No Q6 number existed when this was written.

## What was wrong

The pre-registration said the `both` arm — init and data seeds varying together, the
study's current notion of "a seed" — was **free**, being Q1's `lr3e4` arm at n = 15.

Tracing the two code paths after implementing them shows that is not sound:

* **Un-opted (Q1's arm):** `torch.manual_seed(s)`; the DataLoader is built but draws
  nothing at construction; `StudentNet` draws its weights from the global stream; every
  epoch then draws its permutation **from that same global stream**.
* **Opt-in with init = data = s:** `torch.manual_seed(s)`; a `torch.Generator` is seeded
  with `s`; `torch.manual_seed(s)` again immediately before construction, so **the weights
  are identical to the un-opted path**; but every epoch then draws its permutation **from
  the separate generator**.

So the two paths agree on initialisation and **disagree on minibatch order**. Using Q1's
seeds as the `both` reference would compare two arms on the opt-in path against a
reference on the un-opted one, and the difference between the paths is *exactly the
variable Q6 is decomposing*. That is the same shape of error as E4's amendment A-1 — one
variable named, two variables moved.

## The correction

`both` is **run explicitly**, on the opt-in path, `DISTILL_INIT_SEED = DISTILL_DATA_SEED = s`
for s in 0–7. Eight extra distillations, about 25 minutes, and all three Q6a arms then sit
on one code path with one variable moving between them.

For the same reason **Q6b's fraction arms also use the opt-in path with the seeds tied**,
so `TRAIN_FRAC = 1.0` *is* the `both` arm and the three pool sizes are directly comparable.

Q1's `lr3e4` arm is still reported alongside as the un-opted reference — and the
comparison between it and the tied `both` arm is now an incidental measurement of whether
the shuffling stream matters at all, which is worth having.

## What is unchanged

Predictions Q6a-P1, Q6a-P2, Q6b-P1, Q6b-P2, Q6c-P1 and Q6c-P2 stand exactly as written.
Q6c still needs no new training, but it now draws its ensemble members from the tied
`both` arm (n = 8) rather than from Q1 (n = 15), so its subset counts are smaller.

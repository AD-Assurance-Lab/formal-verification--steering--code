# Q6 — why is a fixed objective on fixed data this noisy?: findings

**Run 2026-09-05, 12:09–13:36 (sweep) and 13:37–13:52 (ensembles).** Pre-registration
`docs/Q6_PREREGISTRATION.md` with amendment **A-1** (the `both` arm is run, not reused),
both committed before any Q6 distillation. Drivers `scripts/q6_variance.sh` and
`scripts/q6_ensemble.py`, summariser `scripts/q6_summarise.py`, cells in
`results/town06/variance/`. **40/40 cells, no failures, no simulator at any point.**

All arms: tuned recipe (`lr=3e-4`), 168x56, (32,64,64)/128, kernels pinned, on the opt-in
seed path so exactly one variable moves between them.

```
fog KD p99 |err|   (steering tolerance 0.0120)
  arm     n   median      SD      CV    95% CI on CV
  init    8   0.0778  0.0181   22.3%   [12.8%, 26.9%]     init varies, data order fixed
  data    8   0.0786  0.0197   24.6%   [13.0%, 31.1%]     data order varies, init fixed
  both    8   0.0792  0.0221   28.1%   [14.6%, 36.1%]     both vary together
  f50     8   0.1420  0.0133    9.4%   [ 4.4%, 12.1%]     half the training pool
  f25     8   0.2198  0.0233   11.0%   [ 5.1%, 13.4%]     a quarter of it
```

## The short answer

**There is no cheap variance lever, and Q6 looked for it in all three places the queue
suggested.** Three of five predictions are falsified, and the falsifications are the
result: the dispersion is not attributable to initialisation, it is not an artifact of
having too little data, and it is not beaten by ensembling. It is a property of this
objective on this data, and the study's n ≈ 20–60 for a 20% effect is simply its price.

That is a negative, and it is the answer the queue asked for: *"If it finds the dispersion
is intrinsic, then that is the honest reason the study's training comparisons are
expensive, and it belongs in the write-up rather than being rediscovered each time."*

## Q6a-P1 — FALSIFIED. Initialisation does **not** dominate; the two are indistinguishable

Predicted: SD(`init`) at least **2x** SD(`data`). Measured **0.92x** — the wrong side of 1,
and the two variances are statistically indistinguishable:

```
  SD(init) 0.0181     SD(data) 0.0197     Levene p = 0.991
```

**Minibatch order contributes as much to the dispersion as weight initialisation does.**
That was not the expected answer and it removes the lever the prediction was reaching for:
`distill.py`'s `--init-from` warm start controls initialisation only, so it cannot address
half of a problem whose halves are equal.

What pinning each one actually buys, in SD of fog p99:

```
  pin the data order  ->  SD 0.0221 -> 0.0181     18% less
  pin the init        ->  SD 0.0221 -> 0.0197     11% less
```

**Neither is worth a code path.** An 18% SD reduction moves the required sample size by
about a third at best, against a design that needs n ≈ 20–60.

## Q6a-P2 — HELD, and slightly sub-additive

Predicted: SD(`both`)² within a factor of 2 of SD(`init`)² + SD(`data`)². Measured
**0.000491 vs 0.000718 — a factor of 0.68**, inside the declared band.

So the two sources roughly compose, with mild sub-additivity: varying both together
produces a little less variance than adding the two separate contributions, which means
they are not quite independent. Nothing here needs a mechanism beyond "the two draws
interact weakly", and at n = 8 that factor is not precisely estimated.

## Q6b-P1 — FALSIFIED, and the reason matters more than the verdict

Predicted: CV of fog p99 **grows** as the pool shrinks. Measured the opposite —
**28.1% → 9.4% → 11.0%** as the pool goes 1.00 → 0.50 → 0.25.

**But CV is the wrong statistic here, and the absolute numbers say something different and
more useful:**

```
  pool     median      SD        CV
  1.00     0.0792    0.0221    28.1%
  0.50     0.1420    0.0133     9.4%
  0.25     0.2198    0.0233    11.0%
```

**The SD is essentially flat — 0.013 to 0.023 across a 4x change in pool size — while the
median nearly triples.** The CV collapses because its *denominator* grows, not because the
spread shrinks. Removing three quarters of the training data makes every seed uniformly
much worse; it does not make them more alike in absolute terms.

**The honest reading: the absolute dispersion is independent of pool size over this range,
so it is intrinsic to the objective rather than estimation noise, and more DAgger data
should not be expected to reduce it.** That is exactly the branch the pre-registration
declared for a P1 failure — *"the dispersion is intrinsic to the objective, more data will
not fix it, and that is the answer"* — and it removes a costed recommendation from the next
capture campaign's justification. If the next campaign captures more data, it should be for
a reason other than reducing training variance.

**The caveat, stated rather than buried:** this measures the pool getting *smaller*. It is
an extrapolation to conclude that a *larger* pool would not help, and the honest form is
that nothing in the measured range shows the absolute spread responding to pool size at
all.

## Q6b-P2 — HELD, trivially and for the wrong reason

Predicted: CV at 0.25 less than 2x CV at 1.00. Measured **0.39x** — held, but only because
CV fell rather than rose. The prediction was written expecting a shallow *increase*; it
passed on a decrease. **Recorded as held per the letter, and it carries no evidential
weight**, since the mechanism it was probing did not occur.

## Q6c-P1 — FALSIFIED, and the practical consequence is clean

Predicted: the output ensemble beats the **median** single seed at k = 4 **and** the
**best** single seed at k = 8. The first clause held, the second did not:

```
  single seeds     median 0.0792    best 0.0469    worst 0.1088
  output   k=2     0.0720     -9.2% vs median   +53.5% vs best
  output   k=4     0.0644    -18.8% vs median   +37.2% vs best
  output   k=8     0.0616    -22.2% vs median   +31.4% vs best
```

The ensemble improves monotonically and saturates around −22%. **It never approaches the
best single seed — at k = 8 it is still 31% worse than simply having drawn seed 3.**

**So seed selection beats ensembling on this endpoint, and it is free.** That is a useful
result for the pipeline: the study already selects a seed, and Q6 says that is the more
effective of the two available tactics, not merely the cheaper one.

The declared caveat stands and now costs even more: an ensemble of k students is **k times
the ReLU count to certify**, against a −22% error gain that a seed draw beats outright.
There is no version of this worth the bound width.

## Q6c-P2 — HELD, by a factor of five

Predicted: the weight average fails, worse than the worst single seed at k = 2. Measured
**0.5434 against a worst single seed of 0.1088** — five times worse, and it does not
improve with k (0.5434 / 0.5618 / 0.5628).

Independently initialised networks are not linearly mode-connected without permutation
alignment, and nothing here aligns them. Averaging their weights produces a network that is
not a useful approximation of any of them. **This is why the queue's "an ensemble or weight
average" is two options and not one**, and it is now measured rather than argued.

## The incidental result: the minibatch stream alone moves the endpoint

Amendment A-1 was recorded on a code-path argument. It is now also a measurement. At tied
seeds the opt-in and un-opted paths produce **identical weights** and differ only in which
RNG feeds the shuffling:

```
  un-opted (Q1 lr3e4)   n=15   median 0.0732   SD 0.0167   CV 23.5%
  tied opt-in (both)    n= 8   median 0.0792   SD 0.0221   CV 28.1%
```

Comparable, as they should be — the two paths are the same experiment — and at seed 0
specifically the same initial weights gave 0.0627 un-opted against 0.1064 tied. **Pooling
Q1's arm into Q6a, as the pre-registration originally intended, would have added a
minibatch-stream difference to an experiment whose entire purpose is to decompose exactly
that.** The amendment was necessary.

## What this changes

1. **The dispersion is intrinsic.** It is not initialisation, not data order, not pool
   size, and not fixable by ensembling. `n ≈ 20–60 for a 20% effect` is a measured property
   of this objective and should be stated as one, in Limitations, instead of being
   re-derived by each experiment that trips over it.
2. **Q1's split verdict is explained.** Q1's fog KD p99 reached p = 0.0079 while its
   driving endpoint reached only p = 0.0553 on the same 15 students. Q6 says none of the
   controllable knobs would have narrowed that gap — the variance is in the training, and
   the closed loop only adds to it.
3. **Seed selection is the pipeline's best available tactic**, and it is what the study
   already does. That is a mild vindication of pass 3's design, whatever happens to its
   attribution.
4. **No recommendation for a larger capture on variance grounds.** Nothing in the measured
   range shows absolute spread responding to pool size.
5. **The queue's "CV 42.6%" does not match either arm measured here** — `lr3e4` is 23.5%
   over 15 seeds and `lr1e3` is 34.9%. The motivating figure is recipe-dependent, and the
   tuned recipe is less disperse as well as lower.

## What was NOT done

No CARLA, no driving, no promotion, no `.selected` pin, nothing written to either ledger or
either certificate. `DISTILL_INIT_SEED`, `DISTILL_DATA_SEED` and `DISTILL_TRAIN_FRAC` are
opt-in and were proved bit-neutral by SHA-256 against `S_mixed_taildet_a0p0_s0` and
`S_mixed_depth_d3lr3_s0` before any Q6 number was taken.

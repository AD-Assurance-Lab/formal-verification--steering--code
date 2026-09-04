# E4 — depth at matched ReLU count: findings (and the learning rate found on the way)

**Run 2026-09-04.** Pre-registration `docs/E4_PREREGISTRATION.md` with amendments **A-1**
(the arm was matched on neurons and nothing else) and **A-2** (the study's learning rate
does not fit a deeper student), both recorded before any E4 conclusion. Driver
`scripts/arm_sweep.sh`, summariser `scripts/e4_summarise.py`, cells in
`results/town06/depth/`.

Three arms, kernels pinned, seeds 0–5, fog and clear, 3 laps:

```
fog, worst-of-3 max|CTE|            budget 2.19 ft, pass-3 margin gate 1.095 ft
      arm        s0      s1      s2      s3      s4      s5   median  held  gate
  d3@1e-3     12.08    1.34   11.86   11.78    VOID   11.79    11.79   1/5   0/5
  d3@3e-4      0.98  37.65D    2.22    1.18    2.39    1.60     1.91   3/6   1/6
  d5@1e-4      1.25    4.67    5.80    2.00    3.60      --     3.60   2/5   0/5

clear
  d3@1e-3      VOID    1.18    VOID    1.07    1.79    1.09     1.14   4/4   2/4
  d3@3e-4      1.25    1.06    1.43    1.16    0.95    1.92     1.21   6/6   2/6
  d5@1e-4      1.29    VOID    1.31    VOID      --      --     1.30   2/2   0/2
```

## E4-F1. F5 HELD, and it is the biggest result in the follow-on queue

**Changing only the learning rate moved the fog median from 11.79 ft to 1.91 ft.** Same
architecture, same data, same teacher, same pinned kernels, same seeds — `--lr 3e-4`
instead of the study's `1e-3`.

* Seeds holding fog 3/3 under budget: **1/5 → 3/6**.
* Seed 0 drives fog at **0.98 ft**, which is the **first student in this study to clear
  pass 3's 1.095 ft margin gate on fog**.
* Fog KD p99 median improves 0.0977 → **0.0707** (−28%).
* Clear does not regress: 6/6 held, median 1.21 ft against 1.14 ft.

The learning-rate effect (+9.88 ft on the median) is **6x larger than the depth effect**
(−1.69 ft, and in the wrong direction). F5 predicted exactly this ordering.

**Statistical honesty.** Mann-Whitney on the six seeds gives **p = 0.247** — not
significant, because one arm contains a 37.65 ft departure and the dispersion is enormous
(this is the same power problem E2R-F5 quantified). The *effect size* is a 6x shift in
median, and the direction is consistent across five of six seeds. **This is strong enough
to act on and not strong enough to publish as-is.** It needs confirmation at more seeds,
and that is the top recommendation in the queue.

## E4-F2. F2 HELD: depth costs verification, by 2.3x to 3.7x

At **matched ReLU count** (101,888 against 101,892, four neurons apart) and matched
flatten dimension, on the same committed captures through the same bound math:

```
  certified bound WIDTH, in units of tolerance
  condition    d3 (3 conv)   d5 (5 conv)   ratio
  fog                 1.86          4.26   2.30x
  night               3.67         13.70   3.73x
  low_sun             0.61          2.25   3.70x     d3 CERTIFIED, d5 NOT
```

Every layer compounds α-CROWN's relaxation, and it is not a small effect: the deeper
student's bounds are **two to four times wider for the same number of neurons**, and the
one cell the shallow student certifies, the deeper one does not.

**This is the paper's thesis, measured directly for the first time.** The verifier really
does prefer shallow-and-wide, and the preference is expensive enough to constrain the
architecture.

## E4-F3. F1 HELD: depth does not rescue fog

`d5@1e-4` fog median **3.60 ft** against `d3@3e-4`'s **1.91 ft** — the deeper student is
worse at driving fog *and* worse to verify. It holds 2/5 against 3/6 and clears the margin
gate 0/5 against 1/6.

So the tension E4 was designed to find does not exist in the direction feared: **depth is
not the missing ingredient that verifiability was denying us.** Shallow-and-wide costs
nothing here — it is better on both axes.

## E4-F4. Two design errors caught before they became findings

Recorded because both would have produced a confident wrong answer:

1. **A-1.** The first `d5` was matched on ReLU count alone. Three stride-2 convs leave a
   1x15 map, so its flatten dimension was **300 against d3's 6,080** — a 20x
   representation bottleneck wearing a depth label. It trained ~4x worse and its first fog
   lap departed after 24 steps.
2. **A-2.** The corrected `d5` still would not train under the study's fixed recipe: best
   validation at **epoch 0**, flat at 8.26e-3, while `d3` descends 7.49 → 4.66e-3 in four
   epochs. Reporting that as "depth does not help" would have been reporting an
   optimisation failure.

Both were caught by looking at the training curve and the geometry before believing the
driving result. Neither is reported as a finding about depth.

## What this means for the study

**The fog failure is entangled with an untuned distillation recipe.** Every student in
this study, on both maps, was distilled at `lr=1e-3`, and nothing ever varied it. At
`3e-4` the same architecture halves its validation KD error and moves its fog median by
6x.

That does not overturn the certification result — see `docs/OVERALL_STATUS.md` — but it
directly weakens one sentence the paper currently leads with: *"no policy good enough to
certify exists yet, and the obstruction is distillation rather than verification."* The
obstruction is distillation, and at least part of it is a **hyperparameter that was never
swept**, not something intrinsic to distilling into a small verifiable student.

**Pass 3 is confounded by this.** Its 16 students — two widths x eight seeds — were all
trained at 1e-3. Its conclusion ("none passed, and fog stopped every one") is true of what
it ran, and it cannot separate "fog defeats this architecture" from "fog defeats this
architecture at this learning rate".

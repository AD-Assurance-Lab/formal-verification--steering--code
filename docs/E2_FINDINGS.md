# E2 — tail-sensitive distillation loss: findings

**Run 2026-09-04.** Pre-registration `docs/E2_PREREGISTRATION.md` (committed `e497002`)
with **amendment A-1** (committed `68ef8e6`) recorded before any scored lap. Driver
`scripts/e2_tail_loss.sh`, summariser `scripts/e2_summarise.py`, raw cells in
`results/town06/tail_loss/`.

3 alphas x 6 seeds, 168x56 w4 (the shipped architecture). 18 distillations, 18 KD
measurements, 108 laps.

```
KD p99 |err|, fog (steering tolerance 0.0120)
 alpha      s0      s1      s2      s3      s4      s5    median
   0.0  0.1036  0.0755  0.1265  0.0944  0.0835  0.0817    0.0890
   2.0  0.1331  0.0701  0.1619  0.1247  0.1112  0.0932    0.1180
   8.0  0.0882  0.0587  0.0590  0.0887  0.1314  0.0864    0.0873

closed loop, worst-of-3 max|CTE|, fog (budget 2.19 ft)
 alpha       s0       s1       s2       s3       s4       s5   held
   0.0     11.51     2.18   14.48D     1.39     1.66    16.08    3/6
   2.0     11.46     2.32    11.78     9.65    11.07     2.78    0/6
   8.0      7.24     2.16    11.53     1.95     2.41     8.20    2/6

closed loop, clear
   0.0      0.86     1.70     1.00     1.89     1.88     1.31    6/6
   2.0      1.51     1.77     0.77     1.17     0.86     1.15    6/6
   8.0      VOID     1.08     VOID     VOID     2.24     1.42    2/3
```

## E2-F1. C1 FALSIFIED: the loss did not reduce the fog error tail

| arm | fog p99 median | change | Mann-Whitney |
|---|---|---|---|
| alpha 2.0 | 0.1180 | **+32.6% (worse)** | p = 0.310 |
| alpha 8.0 | 0.0873 | −1.9% | p = 0.699 |

Neither is significant, and the direction is **not monotonic in alpha** — 2.0 worse, 8.0
unchanged. A real dose-response would not do that. The tail loss did not do the thing it
was changed to do.

## E2-F2. C2 held, in the strongest form: no arm improved closed-loop fog

Seeds holding fog 3/3 under budget: **baseline 3, alpha 2.0 zero, alpha 8.0 two.** The
best treated arm is *worse* than the baseline. I predicted a gain of at most +1; the
observed gain is −1.

## E2-F3. C3 FALSIFIED: there was no bulk/tail trade-off to observe

I predicted alpha 8.0 would buy tail accuracy by giving up bulk accuracy on clear. Clear
p99 was worse at 8.0 in only **2 of 6** seeds, and its median actually *improved*
(0.0620 against 0.0687). Nothing was traded, because nothing much happened.

The one real signal in the clear arm is instability: **alpha 8.0 produced 3 VOID cells of
6** on clear, against none in the other two arms. Heavy tail weighting appears to push
students toward the marginal, multimodal regime E1b characterised — which is a cost with
no matching benefit.

## E2-F4. C4 held: the seed still dominates

Largest within-alpha spread across seeds **14.69 ft**, against a between-alpha median
difference of **5.53 ft**. Consistent with E1: the draw is the strong lever.

## E2-F5. The finding that matters: this design could not have detected a useful effect

Baseline fog p99 across six seeds has **CV 19.9%** (mean 0.0942, sd 0.0187). Simulating the
6-vs-6 Mann-Whitney at that dispersion:

```
   a 10% shift is detected  10% of the time
   a 20% shift is detected  31%
   a 30% shift is detected  59%
   a 40% shift is detected  83%
   a 50% shift is detected  96%
```

**E2 as specified could only have seen an improvement of roughly 40% or more.** It found
none — but "no effect detected" here does not mean "no effect". A 20% improvement in the
fog error tail would be well worth having and this experiment would have missed it 69% of
the time. Reaching 80% power for a 20% shift needs **n ≈ 20 seeds per arm**, not 6.

**The tail-loss hypothesis is therefore not refuted. It is untested at usable power**, and
saying otherwise would be the same mistake as the single draws in T06-F48.

## E2-F6. And the reason the noise was that large is fixable — measured, then fixed

Amendment A-1 was triggered by re-distilling the baseline objective at the *same seed*
and getting a different model. Three independent draws of "seed 0", same data, same
objective:

```
   fog p99 |err|   0.1027   0.1427   0.1036     spread 1.39x
```

That is as large as the spread across six *different* seeds. `distill.py` seeded python,
numpy and torch — and its comment claimed "every existing result reproduces exactly" — but
cuDNN autotunes its algorithms and several backward kernels reduce non-deterministically,
so the same seed lands in a different basin.

**`DISTILL_DETERMINISTIC=1` fixes it.** With `cudnn.deterministic`, `benchmark=False`,
`use_deterministic_algorithms(True)` and `CUBLAS_WORKSPACE_CONFIG=:4096:8`, two runs at
seed 0 produced **bit-identical weights** (verified tensor by tensor) and identical
val MSE 2.080e-03. Off by default, so no committed checkpoint is implicitly re-defined.

This is the useful output of E2. It converts the seed from a label into an actual control
variable, which:

* makes a *paired* design valid again, recovering most of the power lost above;
* removes the confound that made A-1 necessary;
* means a re-run of any experiment here is a re-run, not a new draw.

## What to do next

1. **Re-run E2 with `DISTILL_DETERMINISTIC=1` and a paired design.** With the seed as a
   real control, the same-seed comparison measures alpha alone. This is the cheapest way
   to actually answer E2, and it should be done before adding seeds.
2. If the noise is not fully removed by pinning, **n ≈ 20 seeds per arm** is the price of
   a 20% effect. Budget it or do not ask the question.
3. E6 (curvature-weighted loss) should adopt the same discipline from the start. So should
   any comparison of two training configurations anywhere in this lab — the confound is
   not specific to the tail loss.

## What this does not touch

Passes 1–3, the certificates and E1 are unaffected: none of them compared two training
configurations against each other, which is the design this confound breaks. E1's
conclusion that the draw dominates is *strengthened* — part of what it measured as
"seed variance" is now identified as unpinned-kernel variance, and is removable.

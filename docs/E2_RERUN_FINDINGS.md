# E2 re-run (kernels pinned, paired): findings

**Run 2026-09-04.** Pre-registration amendment A-2 in `docs/E2_PREREGISTRATION.md`,
committed `7d22308` before the first distillation. Raw cells
`results/town06/tail_loss_det/`; summarise with
`E2_DIR=results/town06/tail_loss_det python3 scripts/e2_summarise.py`.

Same declared set as the first run — alphas 0.0 / 2.0 / 8.0, seeds 0–5, 168x56 w4, fog and
clear, 3 laps — with `DISTILL_DETERMINISTIC=1` so the seed is a control variable.

```
KD p99 |err|, fog                                   closed loop, fog, worst-of-3
 alpha    s0     s1     s2     s3     s4     s5      alpha  held
   0.0 .1773  .0914  .0656  .1040  .0564  .1116        0.0   1/5
   2.0 .1253  .1052  .1235  .0898  .1192  .1167        2.0   2/5
   8.0 .1421  .5589  .0692  .0746  .1170  .1340        8.0   1/6
```

## E2R-F1. D1 FALSIFIED — and the reason is the useful part

D1 predicted the paired design would separate arms the unpaired one could not. It did the
opposite: **Wilcoxon p = 0.562 for both alphas**, against Mann-Whitney p = 0.240 and 0.310
in the unpinned run. Pairing made the test *weaker*.

**Why.** Pairing only helps when the seed is a shared block effect across arms. It is not:

```
  corr(baseline, alpha 2.0) across the SAME seed:  r = +0.115  (p = 0.828)
  corr(baseline, alpha 8.0) across the SAME seed:  r = -0.015  (p = 0.977)
```

**Pinning the kernels makes a run reproducible; it does not make the seed a useful control
for comparing two training objectives.** The seed fixes the initialisation, and the
trajectories diverge immediately once the loss differs, landing in unrelated basins. Two
students sharing a seed but not an objective are no more alike than two students sharing
neither.

This is a stronger and more general statement than E2-F6, and it applies to every
comparison of training configurations in this lab, not just to this loss.

## E2R-F2. D4 falsified as stated, but the model distribution did NOT change

D4 was the guard: if the pinned baseline landed outside the unpinned run's range, pinning
had changed the model rather than just its reproducibility.

```
  unpinned baseline fog p99  median 0.0890   CV 19.9%   range 0.0755-0.1265
  pinned   baseline fog p99  median 0.0977   CV 42.6%   range 0.0564-0.1773
  Mann-Whitney between them: p = 0.937
```

**3 of 6 pinned seeds fall outside the unpinned range, so D4 fails as written — but the
two distributions are statistically indistinguishable.** The literal test was simply too
strict for n = 6 drawn from a distribution this wide. The correct reading is that pinning
did not change what the pipeline produces; it changed only whether a given run can be
repeated. D4 did its job: it forced this check rather than letting the assumption ride.

## E2R-F3. C1 still falsified: the tail loss does not reduce the fog error tail

Fog p99 median rose in both arms — **+20.7%** at alpha 2.0 (p = 0.240) and **+28.5%** at
alpha 8.0 (p = 0.310), with 2 of 6 seeds improving in each. Directionally the same as the
unpinned run, and no more significant.

Alpha 8.0 also produced an outright training failure at seed 1: fog p99 **0.5589**, clear
p99 0.5564, and a drive that departed the road at 35.40 ft. Heavy tail weighting can
destabilise the fit entirely.

## E2R-F4. C2 held; the closed loop did not move

Seeds holding fog 3/3: baseline **1**, alpha 2.0 **2**, alpha 8.0 **1**. The +1 at alpha
2.0 is inside the prediction and far inside the noise — this is a 2-vs-1 count on five
measured cells.

C3 falsified again (clear p99 worse at 8.0 in only 3 of 6). C4 held again: within-arm
spread 33.42 ft against a between-arm median difference of 9.34 ft.

## E2R-F5. The verdict on E2, and the cost of ever answering it

Two independent runs — one unpinned, one pinned and paired — agree: **no measurable
benefit from tail-weighted distillation, at either alpha.** But the honest statement is
still about power, and it is now worse than the first run suggested. At the pinned
baseline's dispersion (CV 42.6%):

```
  seeds per arm to detect a 20% improvement in fog p99:
     n= 6 -> power 10%      n=20 -> power 28%      n=40 -> power 52%
     n=10 -> power 15%      n=30 -> power 41%      n=60 -> power 71%

  what the n=6 design CAN see:
     20% shift -> 9%    40% -> 28%    60% -> 53%    80% -> 78%
```

**Comparing distillation objectives on this pipeline, by this endpoint, is not feasible at
any practical seed count.** Sixty students per arm still misses a 20% effect three times in
ten. E2 is therefore **closed as unanswerable by this route**, not as answered.

**What would make it answerable** is a lower-variance endpoint, not more seeds. Candidates,
in order of promise:

1. **Certified bound width** — deterministic given a checkpoint, no renderer and no
   optimiser noise in the measurement itself. This is why E4's decisive prediction is
   about certification rather than driving.
2. **Ensembling the endpoint over many checkpoints per arm** rather than treating each
   student as a sample — i.e. asking about the arm's mean behaviour with the seed averaged
   out, which needs the same n but a different question.
3. **Reducing the pipeline's intrinsic training variance**, which is the real disease. CV
   42.6% on a fixed objective and fixed data is extreme, and nothing in this study has yet
   asked why.

Item 3 is the highest-value open question this experiment has produced, and it is upstream
of every remaining experiment in the queue.

## What this does not touch

Nothing here bears on passes 1–3, the certificates, or E1. Those do not compare two
training configurations, which is the design this variance breaks.

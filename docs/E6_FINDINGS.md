# E6 — label balancing: findings

**Run 2026-09-04.** Pre-registration `docs/E6_PREREGISTRATION.md` with amendment **A-1**
(run the arms at the tuned learning rate), recorded before any E6 distillation. Driver
`scripts/arm_sweep.sh`, summariser `scripts/e6_summarise.py`, cells in
`results/town06/balancing/`. All arms `lr 3e-4`, kernels pinned, seeds 0–5, 3 laps.

```
fog, worst-of-3 max|CTE|              budget 2.19 ft, margin gate 1.095 ft
  arm      s0       s1      s2      s3      s4      s5   median  held  gate
  raw    0.98   37.65D    2.22    1.18    2.39    1.60     1.91   3/6   1/6
  bal    1.81     1.27    1.22    2.04    1.97    VOID     1.81   5/5   0/5
 curv    VOID     1.59    2.25    1.53    1.29    VOID     1.56   3/4   0/4

clear
  raw    1.25     1.06    1.43    1.16    0.95    1.92     1.21   6/6   2/6
  bal    1.69     0.72    1.01    0.93    VOID    0.88     0.93   5/5   4/5
 curv    VOID     1.59    1.05    0.98    1.28      --     1.17   4/4   2/4
```

## E6-F1. G1 held on the median — and the median is the wrong statistic here

`bal`'s fog median is **1.81 ft against raw's 1.91**, a 5% improvement, and `curv`'s is
**1.56 ft**, 18% better. Neither clears the 25% bar G1 set, and neither is significant
(Mann-Whitney p = 0.792 and 0.762).

**But every `bal` seed held fog: 5/5, against raw's 3/6.** Raw's median is flattered by a
distribution containing a **37.65 ft departure**; `bal` produced no failure at all, and its
worst seed was 2.04 ft. The same is true of `curv` (3/4, worst 2.25 ft).

This is exactly the distinction E1-F3 drew: **best achievable student and reliability of a
draw are different questions, and for a safety argument the second is the relevant one.**
Judged on the median, balancing does nothing. Judged on whether a random draw produces a
usable policy, it removes the failures.

With 5 or 6 seeds per arm, 5/5 against 3/6 is Fisher p ≈ 0.18 — suggestive, not
established.

## E6-F2. G3 FALSIFIED, and with it the repo's stated reason for rejecting balancing

I predicted `bal` would degrade clear, following the refutation in
`config.TOWN06_STUDENTS`: *"on a route that genuinely IS 84% straight, downsampling
straight frames trains the student for a distribution it will not meet."*

**Clear got better.** `bal`'s clear median is **0.93 ft against raw's 1.21**, and it holds
the 1.095 ft margin gate on **4 of 5** seeds against raw's **2 of 6**. The arm that was
supposed to lose straight-line accuracy is the best straight-line arm measured.

The refutation's *argument* is plausible and its *prediction* is wrong. It was made on the
superseded six-section route, before the seed sweep existed, and it has never been tested
on the current route until now. `--balance` should stop being described as refuted.

## E6-F3. G5 held, decisively — this is a second-order lever

```
  learning rate 1e-3 -> 3e-4   fog median  11.79 -> 1.91 ft   (9.88 ft)
  raw -> bal   at 3e-4         fog median   1.91 -> 1.81 ft   (0.10 ft)
  raw -> curv  at 3e-4         fog median   1.91 -> 1.56 ft   (0.35 ft)
```

The learning rate moved the fog median **28x further than the best balancing arm did**.
Balancing's contribution is real but small, and it shows up in variance rather than in
central tendency.

Running E6 against the old `lr=1e-3` baseline, as originally written, would have compared
these small effects against a badly misconfigured control and could easily have credited
balancing with a fraction of the learning rate's effect. Amendment A-1 was worth making.

## E6-F4. Four VOID cells, consistent with E1b

`bal s5` fog, `curv s0` and `curv s5` fog, `bal s4` and `curv s0` clear. Same signature as
E1b: marginal policies selecting among discrete closed-loop modes. Excluded, not averaged.

## What to do with this

**`--balance` is worth keeping on**, not because it improves the typical student but
because in this sample it eliminated the catastrophic ones, and it improved clear while
doing so. That is a cheap, already-implemented change to a flag that no driver currently
passes.

**It does not change the study's conclusion**, and it should not be presented as the fix
for fog. The learning rate is the first-order effect and balancing is a refinement on top
of it. Both need confirmation at more seeds before either is published.

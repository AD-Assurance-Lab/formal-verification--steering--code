# E2 — tail-sensitive distillation loss: pre-registration

**Written 2026-09-04, before any E2 distillation or lap.** Driver
`scripts/e2_tail_loss.sh`. Follows `docs/NEXT_EXPERIMENTS.md` E2 and
`docs/E1_FINDINGS.md`, which redirected the remaining work at distillation VARIANCE
rather than architecture.

## The question

> Does a loss that penalises the error tail recover fog, where MSE does not?

The premise re-measured on the shipped architecture (168x56, w4, seed 0), today:

```
condition   KD RMSE   p99 |err|      tolerance delta_tol = 0.0120
clear        0.0174     0.0695
fog          0.0292     0.1027       <- p99 is 8.6x tolerance
night        0.0291     0.1048
low_sun      0.0217     0.0675
```

Fog's **mean** error is no worse than night's, which passes. Fog's **tail** is 8.6x the
steering tolerance. `distill.py` trained with plain `mse_loss`, which fits the bulk and is
blind to exactly that. This is a documented KD failure mode, not a guess — average-case
accuracy can hold while tail behaviour changes.

## The change

`pipeline/distill.py`, behind `DISTILL_TAIL_ALPHA`, **default 0.0 which is bit-identical
to the existing objective** so no committed student needs re-deriving:

```python
err = (student(x) - y).abs()
loss = (err.pow(2) * (1.0 + TAIL_ALPHA * err.detach())).mean()
```

`err.detach()` in the weight is deliberate: it re-weights each sample by how badly it is
currently fitted, without adding a gradient term that would chase the cube of the error.

## Declared set — fixed before running

| axis | values |
|---|---|
| `DISTILL_TAIL_ALPHA` | **0.0 (baseline), 2.0, 8.0** |
| architecture | 168x56, w4 = (32,64,64)/fc128 — the shipped configuration |
| seeds | 0, 1, 2, 3, 4, 5 |
| conditions driven | fog (the question), clear (the regression guard) |
| laps | 3 |
| teacher | `teacher_mixed_t06lap_dagger_r03` |

The **baseline arm is already measured**: `S_mixed_t06lap_168x56_w4_s0..s5` were distilled
under the plain-MSE path and E1 drove their fog and clear. Only alpha 2.0 and 8.0 need new
checkpoints, so this costs 12 distillations and 72 laps.

## Endpoints, and why not the obvious one

**Primary: fog p99 |err|, paired by seed** — Wilcoxon signed-rank over 6 matched pairs per
alpha. This is continuous, computed without CARLA, and directly measures the thing the
loss was changed to move.

**Secondary: fog closed-loop worst-of-3 CTE**, 6 vs 6, Mann-Whitney; plus the count of
seeds holding fog 3/3 under 2.19 ft.

The count of seeds holding is the statistic E1 recommended, and it is reported — but it is
**underpowered on its own and I am saying so in advance**: 6 seeds moving from 2/6 to 4/6
is Fisher p ≈ 0.57. It cannot carry a conclusion. That is why the primary endpoint is the
continuous KD tail measure.

## Predictions

**C1 — the loss does what it says.** Fog p99 |err| falls at both alphas, improving in at
least 5 of 6 matched seeds at alpha 2.0. If this fails the implementation is wrong, not
the hypothesis.

**C2 — and it does NOT buy proportionate closed-loop fog.** The number of seeds holding
fog 3/3 rises by at most 1 over the baseline's 2. This is the real prediction and the
interesting one. E1b showed the closed-loop outcome is selection among a few discrete
modes, dominated by the draw; a smaller error tail should shift which mode is chosen only
weakly. **If C2 is wrong — if the tail loss clearly recovers fog — that answers the
study's open question and outranks everything else queued.**

**C3 — alpha 8.0 trades away the bulk.** Clear p99 |err| is worse at 8.0 than at 0.0 in a
majority of seeds. Upweighting the tail has to come from somewhere.

**C4 — the seed still dominates.** Within any single alpha, the spread of fog CTE across
seeds exceeds the difference between alpha medians. E1 measured 26.6x within a
resolution; nothing here is expected to be that large.

## Bound by

Restart before every lap (A-4/R-SIM-1); exit 3 aborts rather than scoring the model for an
unmeasured lap; no promotion and no `.selected` pin; output confined to
`results/town06/tail_loss/`; a cell whose 3 laps disagree by >25% is VOID and is not
averaged (standing rule 3, and E1b showed exactly what those cells are).

Report what happened, including where it contradicts C1–C4.

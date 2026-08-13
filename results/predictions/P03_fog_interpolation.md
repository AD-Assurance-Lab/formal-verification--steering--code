# P-03 — committed BEFORE driving fog densities 25, 40, 55

Recorded 2026-08-12 22:45. Closed loop has **only ever driven fog density 70**. Densities
25, 40 and 55 have never been simulated by either policy.

Verified mean signed steering bias, pose-local fields, westbound, threshold |bias| <= 0.0015:

| density | S_clear | verdict | S_mixed | verdict |
|---|---|---|---|---|
| 25 | [-0.00613, -0.00489] | FALSIFIED | [+0.00886, +0.00925] | **FALSIFIED** |
| 40 | [+0.00306, +0.00399] | FALSIFIED | [+0.00712, +0.00817] | **FALSIFIED** |
| 55 | [-0.00096, -0.00006] | certified | [+0.00801, +0.00884] | **FALSIFIED** |
| 70 | [+0.00555, +0.00621] | FALSIFIED | [-0.00035, +0.00013] | certified |

## The prediction

**`S_mixed` should FAIL closed loop at fog densities 25, 40 and 55, while passing at 70.**
Its verified bias is 15-40x larger at the thin and intermediate densities than at the dense
fog it was trained on and has been tested in.

**`S_clear` should FAIL at 25, 40 and 70.** Its density-55 cell is certified and is the one
cell I expect to be wrong -- it fails at both 40 and 70, so passing at 55 would be
surprising. Recorded as a prediction anyway rather than quietly excluded.

## Why this is the experiment worth running

`S_mixed` was trained on clear and on dense fog. Thin fog is the **interpolation gap between
its two training points**, and nothing in the closed-loop protocol samples it: the ledger
drives one preset per condition. If the prediction holds, verification found a real
non-monotonic weakness that closed-loop testing at a single operating point cannot find by
construction -- which is the strongest available argument for the tool.

## What each outcome means

* **`S_mixed` fails at 25/40/55, passes at 70** -- prediction confirmed. Verification
  located a failure mode simulation had never sampled.
* **`S_mixed` passes everywhere** -- the signed-bias criterion is too conservative in the
  mid-axis, and the 0.0015 threshold does not transfer out of sample. A real limitation,
  and the honest end of the interpolation claim.
* **`S_mixed` fails at 70 too** -- the density-70 certification was luck, and the whole
  6-cell table needs re-reading.

All three are results. The threshold was calibrated on the six cells at the preset
conditions, so these densities are a genuine out-of-sample test of it.

---

# RESULT — 2026-08-13 00:05. P-03 is REFUTED.

| density | model | predicted | actual | match |
|---|---|---|---|---|
| 25 | S_clear | FALSIFIED | FAIL 20/20, 20 departed | yes |
| 25 | S_mixed | FALSIFIED | **PASS 0/20** | no |
| 40 | S_clear | FALSIFIED | FAIL 20/20, 20 departed | yes |
| 40 | S_mixed | FALSIFIED | **PASS 0/20** | no |
| 55 | S_clear | **certified** | **FAIL 20/20, 20 departed** | no — **UNSOUND** |
| 55 | S_mixed | FALSIFIED | **PASS 0/20** | no |

**Out-of-sample agreement: 2/6.**

## What is refuted

**The interpolation hypothesis.** `S_mixed` was predicted to degrade in the gap between its
two training points. It drove 60 laps across three unseen fog densities without a single
failure. Verification's 15-40x larger bias at those densities corresponded to nothing.

**The threshold does not generalise.** It scored 5/6 on the six preset-condition cells and
2/6 here. Those six are the cells it was calibrated on, so the 5/6 was never evidence of
predictive power -- it was a fit, and this is what the fit is worth off its calibration set.
I said at the time that adopting a threshold tuned on six points needed out-of-sample
validation before it could be believed. This is that validation, and it failed.

**One cell is unsound.** `S_clear` at density 55 was CERTIFIED and departs the road on all
20 runs. That is verification declaring safe a policy that crashes every time -- the one
failure mode that discredits the tool rather than the experiment. It was flagged in advance
as the cell most likely to be wrong, which makes it an honest prediction rather than a
discovery, but it is still an unsound certificate.

## What survives

* `S_clear` fails at every fog density and verification caught it at 25 and 40. The
  falsification direction transfers; the certification direction does not.
* The two mechanisms found today are independent of the threshold and stand on their own
  measurements: signed bias discriminates where magnitude does not (30-70x separation), and
  disturbance fields must be pose-local to within ~2 m (0.97x signed response at 1.79 m,
  degrading to 2.3x by 14 m).

## What this means for the study

The honest statement is that **verification does not yet predict closed-loop outcomes on
conditions it was not tuned for.** It is directionally right about the bad policy and
systematically over-conservative about the good one, except for one cell where it was
confidently and dangerously wrong.

The next lever is not another threshold. A scalar bias summary discards when and where the
error occurs, and a policy departs the road because of a bias sustained through a specific
stretch of road, not because of a lap-average. The trajectory machinery built earlier
(`certify_trajectory.py`) already verifies per-frame along the driven path; the missing
piece is a criterion over the *sequence* rather than its mean.

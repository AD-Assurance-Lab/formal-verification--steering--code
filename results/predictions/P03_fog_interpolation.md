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

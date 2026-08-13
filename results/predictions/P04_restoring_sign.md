# P-04 — restoring-sign criterion, committed BEFORE testing out of sample

Recorded 2026-08-13 01:05.

## The criterion (no tuned parameter)

Place the vehicle at lateral offset `o` and read the policy's steering `s`. Recovery
requires `sign(s) = -sign(o)`. FALSIFIED iff any offset in the reachable tube (|o| <= 2 m)
has a non-restoring response.

On the eight preset-condition cells it agrees with closed loop **8/8**, including the two
that every previous criterion got wrong. But the sign test was formulated after seeing those
eight, so it is a fit until tested elsewhere -- which is exactly what happened to P-03's
threshold (5/6 in sample, 2/6 out).

## The prediction

Fog densities 25, 40 and 55 already have closed-loop ground truth from Stage 5:
`S_clear` FAIL 20/20 at all three, `S_mixed` PASS 0/20 at all three. The criterion has never
been evaluated at these densities.

**Predicted: `S_clear` shows non-restoring offsets at 25, 40 and 55 -> FALSIFIED.
`S_mixed` shows none -> certified. Expected 6/6.**

Concretely, `S_clear` should fail on the NEGATIVE side (its trapdoor was at -2.0 m in
clear/fog/shadows and reached -1.0 m under night), and the count of non-restoring offsets
should not shrink as fog thickens.

## What each outcome means

* **6/6** -- the criterion generalises. Verification predicts closed-loop failure on
  conditions it was not built from, which is the study's central claim.
* **`S_clear` certified anywhere** -- unsound, and the criterion is no better than the
  thresholds it replaced.
* **`S_mixed` falsified anywhere** -- over-conservative off the calibration set, the same
  failure mode as P-03, and the sign test is not the answer either.

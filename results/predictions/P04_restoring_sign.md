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

---

# RESULT — 2026-08-13 01:10. P-04 CONFIRMED, 6/6.

| density | model | non-restoring offsets | verdict | actual | match |
|---|---|---|---|---|---|
| 25 | S_clear | -2.0 | FALSIFIED | FAIL 20/20 | yes |
| 25 | S_mixed | none | certified | PASS 0/20 | yes |
| 40 | S_clear | -2.0 | FALSIFIED | FAIL 20/20 | yes |
| 40 | S_mixed | none | certified | PASS 0/20 | yes |
| 55 | S_clear | -2.0 | FALSIFIED | FAIL 20/20 | yes |
| 55 | S_mixed | none | certified | PASS 0/20 | yes |

**Out-of-sample 6/6. Combined with the eight preset-condition cells, 14/14.**

The predicted detail held too: `S_clear` fails on the negative side, at the same -2.0 m
trapdoor, and the violation does not disappear as fog thickens.

## Why this criterion works where five others failed

Every earlier attempt measured error on the NOMINAL path -- per-frame magnitude, signed
mean bias, sustained same-signed runs. F21 established that cannot work here: the frames
that cause a departure are off-centre views that occur nowhere on the nominal path, so at
fog 25-55 the true biases reverse sign every 8-16 frames while the vehicle departs on every
run.

This asks a STABILITY question instead of an accuracy one. Recovery from lateral offset `o`
requires steer of the opposite sign; either the policy provides it across the reachable tube
or it does not. `S_mixed` restores monotonically across +/-2 m in every condition and at
every fog density. `S_clear` restores near the centre and reverses at -2.0 m -- a one-way
trapdoor -- and under night loses restoring authority from -1.0 m outward, which is where it
fails worst.

## What is NOT yet established

* These are POINT evaluations at 8 poses x 9 offsets, not alpha-CROWN bounds over the
  offset intervals. The criterion is a strong empirical predictor; it is not yet a proof.
  Bounding it is the obvious next step and the machinery already exists.
* The tube is +/-2 m on a straight. Curves, and offsets beyond 2 m, are unprobed.
* Eight poses on one route in one town.

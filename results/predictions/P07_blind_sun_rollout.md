# P-07  Blind test of the validated-surrogate rollout

Committed 2026-08-13 17:07, BEFORE any closed-loop run at these sun altitudes. None of
+37, +26, +11, +5 or -15 degrees has ever been driven. This is the test the 8/8 in F27
needs, because that table was computed with ground truth already known, and both previous
blind predictions (P-03 at 2/6, P-06 at 3/7) failed after looking strong in-sample.

## Method, frozen

Rollout on the measured (offset x heading) surrogate, sampled at the control rate
(1.79 m = v * FIXED_DT), started from the lane centre, over the first 195 m of the route.
FAIL if peak |o| exceeds the pre-registered 0.668 m CTE budget. No fitted parameter, no
aggregation, no threshold.

## Predictions

    sun altitude        +37     +26     +11      +5     -15
    S_clear peak |o|  0.878   0.998   0.484   0.288   5.521
    S_clear verdict    FAIL    FAIL    PASS    PASS    FAIL
    S_mixed peak |o|  0.091   5.307   0.089   0.065   0.161
    S_mixed verdict    PASS    FAIL    PASS    PASS    PASS

Two of these are deliberately exposed rather than hedged:

- **`S_clear` PASS at +11 and +5.** The vehicle FAILS westbound at +15 (5/5) and PASSES
  westbound at +8 (0/5), so +11 sits inside a known transition and could fall either way.
- **`S_mixed` FAIL at +26**, peak 5.307 m. `S_mixed` passes every condition in the study,
  so this predicts a failure of the good model at an untested operating point. If the
  vehicle passes +26, this is a false alarm on the model the method should certify.

## Scope: WESTBOUND ONLY

Every capture is westbound, because eastbound captures were validated and rejected (F26:
captured steer reproduces driven steer to 0.208 against 0.025 westbound). These predictions
are therefore about the westbound direction and must be scored against westbound runs. The
closed-loop cell verdict combines both directions and will read FAIL if either fails, so
scoring the cell verdict directly would be scoring a prediction that was never made.

## What each outcome would mean

- **Agreement on both exposed cells** -- the rollout predicts closed-loop outcomes at
  operating points it has never seen, and the 8/8 is not an artefact of hindsight.
- **`S_clear` wrong at +11 or +5** -- the method resolves the coarse contrast but not the
  transition, which bounds its claimed resolution rather than refuting it.
- **`S_mixed` wrong at +26** -- a false alarm on a safe model. Less dangerous than the
  reverse, but it means the method over-predicts somewhere and the margin is not trustworthy.
- **Any missed failure** -- the unsafe direction, and the most serious outcome.

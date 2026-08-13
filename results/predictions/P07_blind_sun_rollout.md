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

---

## OUTCOME (2026-08-13 17:55)

    model     sun  predicted  onset(m)  in-scope(0-195m)  whole route
    S_clear   +37    FAIL        -        PASS 0/5  NO      PASS 0/5
    S_clear   +26    FAIL      2120       PASS 0/5  NO      FAIL 5/5
    S_clear   +11    PASS        -        PASS 0/5  yes     PASS 0/5
    S_clear    +5    PASS      2286       PASS 0/5  yes     FAIL 5/5
    S_clear   -15    FAIL         3       FAIL 5/5  yes     FAIL 5/5
    S_mixed   +37    PASS        -        PASS 0/5  yes     PASS 0/5
    S_mixed   +26    FAIL        90       FAIL 5/5  yes     FAIL 5/5
    S_mixed   +11    PASS        -        PASS 0/5  yes     PASS 0/5
    S_mixed    +5    PASS      2717       PASS 0/5  yes     FAIL 4/5
    S_mixed   -15    PASS        -        PASS 0/5  yes     PASS 0/5

    in-scope 8/10      whole route 6/10

Both in-scope errors are FALSE ALARMS. No failure inside the examined region was missed.

**The exposed call landed.** `S_mixed` at +26 was predicted to FAIL with a 5.3 m peak -- a
departure of the model that passes every condition in the study, at an untested operating
point. It departs 5/5 with onset at 90 m, inside the captured region.

**Honest accounting of the two scorings.** The committed Method section declared "over the
first 195 m of the route", so the scope was pre-registered; but the Predictions section gave
bare PASS/FAIL verdicts, and the decision to score in-scope was taken AFTER seeing the
results. Both numbers are therefore reported and the weaker one is not hidden. Future
predictions must state the scope in the verdict itself, not only in the method.

**What the whole-route misses actually are.** At +5 and +26 the vehicle departs at 2120-2717
m; the capture ended at 195 m. That is a coverage limit, not a missed failure -- the method
never examined the road where the vehicle left the lane. It is cheap to remove, and P-08
tests exactly that.

**What this does NOT establish.** A rollout follows one trajectory from one initial state and
carries no soundness guarantee. It can miss a failure that a set-based method would catch,
and today's result does not show otherwise -- it shows only that it missed nothing within the
region it examined. Soundness requires bounding a set of initial states, which is the
computation that blew up four times (F27).

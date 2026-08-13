# P-06  Blind prediction: where does `S_clear` lose the lane as the sun sets?

Committed 2026-08-13 12:37, BEFORE any closed-loop run at an intermediate sun altitude.
The only altitudes with existing ground truth are +90 (clear), +15 (shadows) and -25
(night). Every other altitude below is unmeasured.

## The criterion being tested (frozen, no free parameters)

Measure, per pose, the policy's linearized closed loop from the (offset x heading) capture:

    psi' = psi + (v/L) tan(steer * MAX_STEER) dt,   o' = o + v psi dt
    steer ~ k_o * o + k_psi * psi + b

    FAIL if   |lambda(A)| >= 1        (loop not stable)
         or   |b| > |k_o| * 0.668 m   (bias exceeds control authority over the lane budget)

`|lambda| < 1` is the definition of closed-loop stability; 0.668 m is the CTE budget fixed
from lane and vehicle geometry long before this criterion existed. Aggregation is the
pose MEAN, frozen in advance -- worst-pose and run-length variants exist and score
differently, and choosing among them by score is what this prediction is meant to avoid.

## Predictions

`S_clear`  PASS at +75, +60, +45, +30, +22, +15, +8
           FAIL at  +3,   0,   -5,  -10,  -25
           transition between +8 and +3 degrees

`S_mixed`  PASS at every altitude from +75 to -25

Measured margins (authority minus bias, metres of steering command):

    sun    +75    +60    +45    +30    +22    +15     +8     +3      0     -5    -10    -25
    Sclr +.144  +.150  +.145  +.101  +.096  +.095  +.106  -.026  -.067  -.065  -.065  -.065
    Smix +.069  +.066  +.055  +.050  +.030  +.059  +.071  +.031  +.051  +.087  +.087  +.087

The mechanism is a collapse of `k_o` (control authority) as the sun drops: `S_clear` falls
from -0.216 at +8 to -0.089 at +3 to -0.042 below the horizon, a 5x loss. `S_mixed` holds
-0.10 to -0.15 throughout, which is why it is predicted safe everywhere.

## Known-wrong cell, declared in advance

`S_clear` at +15 (the shadows preset) is predicted PASS and the closed loop FAILS it 10/10.
That disagreement is already known and is NOT counted as a blind test. It is stated here so
the prediction is not read as cleaner than it is: the criterion has one standing miss.

## What each outcome would mean

- **Transition observed between +8 and +3** -- the criterion predicts closed-loop failure
  at operating points it was never fitted to. This is the result the study needs.
- **Transition at a different altitude** -- the mechanism (authority collapse) is right but
  the threshold is mis-scaled; informative, and quantitatively falsifiable.
- **No transition, `S_clear` passes below the horizon** -- the criterion is measuring
  something that does not govern closed-loop behaviour, like the five before it.
- **`S_mixed` fails anywhere** -- the criterion misses a failure it predicted safe, which is
  the unsafe direction and the more serious error.

## Protocol

Closed loop runs truncated (open road, intersection out of scope), 5 reps per direction,
scored on `passed` (max CTE <= budget AND not departed). Preset follows the sun exactly as
the capture did: `clear` at or above +3, `night` below, so exposure and headlights match.

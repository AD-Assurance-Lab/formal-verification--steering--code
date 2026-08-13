# P-05  Where does `S_clear` break in fog?

Registered 2026-08-13 07:0x, BEFORE densities 70 / 85 / 100 were run.
Densities 25 and 40 had completed (both PASS 0/10); 55 was mid-run and its reps are
excluded from the fit below.

## Why this is worth registering

Zach predicted `S_clear` should survive fog at every density, reasoning that the input
crop and downsampling already discard the far field that fog degrades. The mechanism
checks out -- fog's disturbance magnitude on the road ROI is 0.059 against night's 0.151
-- but "weaker" is not "absent", and the peak CTE is climbing with density:

    density 25   peak |CTE| 0.98 ft   0.0% of lap over budget
    density 40   peak |CTE| 1.35 ft   0.0% of lap over budget
    budget                    2.19 ft

## Prediction

Peak CTE is linear in density over the measured range at 0.0247 ft/density. Extrapolating
to the 2.19 ft budget:

    departure onset at density ~74

    density  70   PASS, but peak CTE 2.0-2.2 ft -- marginal, may take a rep or two over
    density  85   FAIL
    density 100   FAIL

## What each outcome would mean

- **As predicted** -- `S_clear` is fog-robust only up to a threshold. Zach's mechanism is
  right about *why* fog is mild, wrong that it is unbounded.
- **PASS at all densities** -- the crop genuinely removes fog's leverage entirely; the
  linear trend saturates. Zach's prediction holds as stated.
- **FAIL earlier than 70** -- the trend is superlinear; the extrapolation is unsound and
  the margin at 40 was already thinner than it looked.

## Honest limitation

This is an empirical extrapolation from two points, NOT a formal-verification prediction.
It is registered to keep the reasoning falsifiable, not as evidence for step 4. The
verification-side prediction of the same threshold needs offset frames captured per fog
density, which is queued behind the current CARLA work.

---

## OUTCOME: REFUTED (2026-08-13 07:34). Zach's prediction was right, mine was wrong.

    density   peak |CTE|   over budget   departs
        25       0.98 ft        0.0%       0/10
        40       1.35 ft        0.0%       0/10
        55       1.44 ft        0.0%       0/10
        70       1.50 ft        0.0%       0/10
        85       1.55 ft        0.0%       0/10
       100       1.55 ft        0.0%       0/10          budget 2.19 ft

Predicted departure onset at density ~74. Actual: no departure at ANY density, 0/60 runs.

The error was assuming the trend stays linear. It saturates: 1.44, 1.50, 1.55, 1.55 --
the increments are 0.06, 0.05, 0.00 ft. My fit used the only two points (25, 40) that lay
on the steep part of a curve that had already begun to flatten.

**Why it saturates, physically.** Koschmieder transmittance is t = exp(-ln20 * d / MOR).
The crop the network sees spans road at short range, where d is small, so t stays near 1
even as MOR collapses; raising density mostly darkens the far field and the sky, which the
crop excludes. The road-ROI disturbance magnitude therefore approaches an asymptote rather
than growing without bound. This is Zach's mechanism, and the sweep confirms it holds at
every density rather than up to a threshold: `S_clear` is genuinely fog-robust on this
route, not marginally so.

**Consequence for the study.** Fog cannot serve as an unseen-condition failure for
`S_clear`. The clear-vs-mixed contrast rests on night (10/10 departures, 58.7% of lap out
of lane) and, pending its truncated runs, shadows.

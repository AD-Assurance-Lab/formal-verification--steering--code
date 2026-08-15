# P-09 verdicts, committed BEFORE the held-out cells are driven

Split fixed in `P09_sun_angle_design.md` before any capture. Criterion is F38's,
unchanged: windowed mean of the steering deviation against the feedback-derived
tolerance `|k_o| * CTE_BUDGET_M`, window `T_CLOSED_LOOP_S * TARGET_SPEED_MS`.

## Step 2 -- calibration, examined; no adjustment made

    cell   dir         windowed   x tol   certificate   DRIVEN
    +60    westbound    0.07493    0.72   PASS          PASS  0/10
    +60    eastbound    0.09375    0.91   PASS          PASS  0/10
    +30    westbound    0.07553    0.73   PASS          FAIL  5/5, 3.3-4.1 ft
    +30    eastbound    0.09239    0.89   PASS          FAIL  5/5, departed, 29-43 ft

`+60` agrees. `+30` is certified and departs on every run -- a third cell of the
localised type, after `S_clear` +22 and `S_mixed` +22.

**The window was swept and NOT adjusted, because no window works.** Step 2 allows
tuning the window on these cells. Sweeping it from 5.4 m to the full lap:

    window     poses   max PASS   min FAIL   ratio   separates?
      5.4 m        3    0.23730    0.15994    0.67   no
      8.9 m        5    0.16868    0.11051    0.66   no
     16.1 m        9    0.09375    0.07553    0.81   no
     26.8 m       15    0.05582    0.04679    0.84   no
     44.7 m       25    0.03236    0.03154    0.97   no
     71.5 m       40    0.02618    0.01874    0.72   no
    143.1 m       80    0.01303    0.00884    0.68   no
    357.6 m      200    0.00710    0.00459    0.65   no
    715.3 m      400    0.00482    0.00411    0.85   no
   1430.5 m      800    0.00410    0.00218    0.53   no
   2843.1 m     1590    0.00235    0.00040    0.17   no

At EVERY window length the passing cell's statistic is LARGER than the failing
cell's. The ordering is inverted at every scale, so no threshold and no window
separates them. This is the third outcome named in the design document: the
statistic is wrong for this failure mode, not merely mis-scaled. Tuning the window
to fit would be fitting to two points against a monotone-wrong ordering, so the
criterion is left exactly as F38 defined it.

## Step 3 -- HELD-OUT verdicts, committed before driving

    cell   dir         windowed   x tol   VERDICT
    +37    westbound    0.07591    0.73   PASS (certified)
    +37    eastbound    0.09621    0.93   PASS (certified)
    +15    westbound    0.07047    0.68   PASS (certified)
    +15    eastbound    0.09039    0.87   PASS (certified)

**Prediction: both held-out cells drive PASS 0/10.**

Stated plainly, this prediction is not expected to hold. Every one of the four
sun-angle cells lands in the same narrow 0.68-0.93 band regardless of outcome, and
+30 already sits inside that band while departing 10/10. The certificate is not
discriminating between these cells at all. Driving +37 and +15 measures how often
that band is wrong, which is the point of committing it.

## Scoring rule, fixed now

- Both held-out cells PASS in driving -> 2/2. The criterion survives here despite
  +30, and +30 is the outlier.
- Either departs -> that cell is a miss, and combined with +30 the conclusion is
  that the windowed statistic does not detect the localised failure mode at all.

Each driven cell is also labelled by `frac_over_budget`: sustained > 5%, localised
< 5%. `+30` measured 1.80-5.31% eastbound and 0.31-0.38% westbound.

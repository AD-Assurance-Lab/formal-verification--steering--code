# P-09 result: 2/4, and the reason is now located

Verdicts committed in `070a2b2` before either held-out cell was driven.
Design and split fixed in `P09_sun_angle_design.md` before any capture.

## Score

    cell   role          certificate      x tol        driven            outcome
    +60    calibration   PASS             0.72 / 0.91  PASS  0/10        agree
    +30    calibration   PASS             0.73 / 0.89  FAIL 10/10        MISS
    +37    held out      PASS             0.73 / 0.93  FAIL  3/10        MISS
    +15    held out      PASS             0.68 / 0.87  PASS  0/10        agree

    held out 1/2, overall 2/4

Ratios are westbound / eastbound. Every one of the four cells lands in the same
0.68-0.93 band and every one certifies PASS, while the driven outcomes range from
0/10 to 10/10. The certificate is not discriminating between these cells at all,
which is what the committed prediction said would happen.

This repeats P-08b exactly: 2/4, on the same failure mode, after a criterion
change that was supposed to fix it.

    P-03  14/14 in-sample -> 2/6 blind
    P-06   7/8  in-sample -> 3/7 blind
    P-07   8/8  in-sample -> 6/10 blind
    P-08b 10/10 in-sample -> 2/4 blind
    P-09   (no in-sample fit) -> 2/4 blind

## The window is not the missing parameter

Step 2 permitted tuning the window on the calibration cells. Swept from 5.4 m to
the full lap, the PASSING cell's statistic exceeds the FAILING cell's at every
single length (ratios 0.53-0.97, never above 1). The ordering is inverted at every
scale. No threshold, and no window, separates them. Nothing was fitted.

## Where the certificate is looking, and where the vehicle leaves

`+30` eastbound departs reproducibly at (x=-20, y=100..240), about 1990 m into the
lap. At that pose the windowed steering deviation is:

    cell   signed windowed dev @ departure site   rank among 1599 poses   lap max
    +60                              +0.00009            1569th           0.09375
    +30                              +0.00151            1064th           0.09239

Both cells' lap maxima occur at the SAME pose 578, which is nowhere near either
outcome. The statistic is dominated by a location irrelevant to both cells, and at
the location that actually matters it reads essentially zero.

**So the failure is not a steering bias on the centreline.** A nominal-path
statistic cannot see it, however it is windowed or scaled, because there is nothing
to see on the nominal path. That is why every reweighting of the same measurement
has landed at chance on this mode.

## The mechanism this points to, stated as a hypothesis under test

A lane-keeping policy is stable because steering responds to lateral offset with a
restoring gain `k_o = d(steer)/d(offset)` of the correcting sign. Steering can be
exactly right at zero offset while the RESPONSE to being off-centre is flat or
inverted. Then any drift the vehicle already has stops being corrected and grows.

That failure is invisible to every statistic computed on the nominal path, by
construction, and it would explain:

- why the departure site shows no nominal deviation,
- why the effect is direction-dependent (eastbound departs, westbound merely
  exceeds budget by 1-2 ft at the same sun angle),
- why it appears at intermediate sun elevations, where shadows fall ACROSS the
  lane rather than along it,
- and why `frac_over_budget` is small: the vehicle is fine until it is not.

Being tested now by capturing the (offset x heading) grid at +30, +60 and clear
over 1800-2200 m eastbound and measuring `k_o` per pose. If `+30` loses restoring
authority where `+60` keeps it, the criterion to certify is the GAIN, not the bias,
and that is a different and stronger property: it bounds the policy's stability
rather than its output.

## What this does not change

The canonical twelve cells stand at 12/12. Those conditions fail in the sustained
way the criterion is built for -- `S_clear` is out of lane for 58.7% of the lap
under night. This localised mode is a distinct failure type, already named as a
limitation in the write-up, and the honest statement is that the per-frame
sustained certificate does not detect it.

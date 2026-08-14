# Blind-test protocol for the sustained-bias certificate (P-08)

F36 agrees 10/10 with closed-loop testing, but IN-SAMPLE: the driving results existed when
the certificate was computed. Three predictions have already been committed before testing
in this study and all three failed while their in-sample scores looked strong:

    P-03  in-sample 14/14   blind 2/6
    P-06  in-sample  7/8    blind 3/7
    P-07  in-sample  8/8    blind 6/10

That record is the reason this protocol exists. Nothing about F36 should be claimed in print
until it survives the same treatment.

## Operating points

The sun-altitude axis, which the certificate has never been applied to. `clear`, `shadows`
and `night` are `sun_altitude_angle` = +90, +15 and -25 of one continuous parameter, so
intermediate altitudes are genuine unseen operating points on a declared physical axis.

    +45   between clear and shadows, untested by the certificate
    +22   between clear and shadows
     +8   where S_clear passes westbound but fails eastbound (direction-split)
     +3   where both models FAIL in driving, S_clear 5/5 and S_mixed 4/5
     -5   below the horizon, where both models PASS

+3 and -5 are the interesting pair: adjacent on the axis, opposite outcomes. A criterion that
gets both is doing something real.

## Order of operations, and why each step is fixed

1. **Capture full-lap, both directions, at each altitude.** 0-2861 m, intersection excluded,
   control-rate spacing, settled vehicle placement. NOMINAL PATH ONLY (offset 0, heading 0):
   the sustained-bias criterion needs no state grid, so this is 3,200 frames and a few
   minutes rather than 72,000 frames and two hours.
   NOT 195 m segments: measured, `S_clear`/fog flips verdict between the 195 m and full-lap
   scopes (-0.0143 against -0.0054), which is what invalidated P-07's scoring.
2. **Run the certificate and COMMIT the verdicts to git** -- before any closed-loop run at
   that altitude. `python -m study.ledger --check-order` verifies the ordering against git
   history, so the claim is checkable by a third party rather than asserted.
3. **Then drive it.** Truncated open road, 5 repetitions per direction, PASS iff max |CTE|
   <= 0.668 m and no departure.
4. **Score without reinterpretation.** The committed verdict stands as written. P-07 was
   re-scored "in scope" after the fact, which was not defensible; the honest number there is
   6/10 and that is what is recorded.

## What each outcome means

- **Passes at all five** -- the certificate predicts closed-loop outcomes at operating points
  it never saw, on a declared physical axis. That is the claim the paper can make.
- **Fails only at +8** -- the direction-split altitude. Would bound the claim to
  direction-symmetric conditions rather than refute it.
- **Fails at +3 or -5** -- these are adjacent with opposite outcomes, so missing them means
  the criterion cannot resolve the transition, which is where an ODD boundary actually sits.
- **Any missed FAILURE** -- the unsafe direction and the most serious result: a certificate
  that certifies a model the vehicle cannot drive.

## Cost

Ten altitude-direction captures at a few minutes each, plus ten closed-loop cells at ~5 min:
roughly 2-3 h in total, not the 20 h first estimated. The earlier figure assumed the
offset-by-heading grid, which this criterion does not use. Captures are independent and
resumable.

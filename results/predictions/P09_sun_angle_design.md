# P-09  Sun-angle study: calibration and held-out split, fixed in advance

F38 reached 7/9 with a windowed statistic and a feedback-derived tolerance, and the two
misses (`S_clear` and `S_mixed` at +22) sit at 0.91 and 0.84 of that tolerance -- just under
the line. With only two failing cells of the localised type, a systematic ~1.2x factor
cannot be distinguished from coincidence. This study adds cells of that type.

**The split is declared here, before any capture, and is not revised.** P-08 was compromised
by choosing operating points whose closed-loop outcomes were already known; the fix is not to
be more careful about which ones, but to fix the roles in advance.

## Cells

`S_mixed` has never been driven at +60, +37, +30 or +15. Those four are the new data.
`S_clear` is already driven at every angle in the sweep, so it contributes no new cells.

    CALIBRATION (may be examined; may be used to fix the window and threshold)
        S_mixed  +60
        S_mixed  +30

    HELD OUT (not examined until verdicts are committed and driving is done)
        S_mixed  +37
        S_mixed  +15

Two and two. Small, and reported as small.

## Protocol

1. Capture all four, full lap, both directions, nominal path, settled placement.
2. Compute the windowed statistic against the feedback-derived tolerance on the CALIBRATION
   cells only. Adjust window length there if warranted, and record what was adjusted.
3. Freeze. Compute verdicts for the HELD-OUT cells and commit them to git.
4. Drive all four. Score without reinterpretation.

## What each outcome means

- **Held-out cells both correct** -- the windowed + derived-tolerance criterion generalises,
  and the +22 misses were the two-point artefact they look like.
- **Held-out cells fail in the same direction (~0.8-0.9x, certified but departs)** -- that is
  a systematic factor, not coincidence, and the tolerance derivation is missing a term. That
  is a diagnosable result rather than a dead end.
- **Held-out cells fail in both directions** -- the statistic is wrong, not just its scale.

## Classification, recorded because it is the mechanism under test

Each driven cell is also labelled SUSTAINED or LOCALISED by `frac_over_budget`:

    sustained   > 5% of the lap over budget   (S_clear night 58.7%, shadows 13.5%)
    localised   < 5%                          (S_mixed +22, 0.2-0.9%)

The hypothesis under test is that the criterion handles sustained failures and
under-reports localised ones by a roughly constant factor.

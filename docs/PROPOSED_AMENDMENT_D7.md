# PROPOSED amendment to carla-determinism D-7 — NOT APPLIED

**Status: draft for Zach. Nothing in the `carla-determinism` package has been changed.**
Amending D-7 is lab-wide and touches studies whose numbers are already published, so it
follows the package's section 4 procedure or it does not happen.

---

## 1. The rule as frozen

> **D-7. Bit-exact closed-loop replay is NOT achievable, and no configuration reaches it.**
> [...] The floor is ~30 pixels of 307,200 differing by at most 13 levels, and a longer
> settle does not converge it away, so it is generated per frame rather than inherited.
> **Therefore every closed-loop number remains a RATE over at least 10 repetitions with a
> confidence interval.** D-1..D-6 shrink the noise; they do not remove it, and no future
> version of this file may claim they do without a measurement showing a frozen scene
> rendering bit-identically across reps.

## 2. What is NOT disputed

The measurement. A frozen scene does not render bit-identically, and D-1..D-6 do not make
it. Nothing here claims otherwise, and the closing sentence of D-7 stands untouched: no
version of that file may claim bit-identity without a measurement showing it.

What is disputed is the word **therefore** — the inference from "frames are not
bit-identical" to "every closed-loop number needs at least ten repetitions". Those are
different claims about different quantities. D-7 measured *frame* identity; the floor
exists to protect *verdict* stability.

## 3. The contradicting measurement

Lap-level verdict reproducibility, computed from the committed Town04 redo ledger cells
(`results/town04_v2/ledger/*closed_loop.json`), on the corrected harness -- deterministic
control on, `-notexturestreaming`, preflight green, a clean server and a fresh vehicle per
lap, one process per lap:

    cell                            lap verdicts        agree?
    clear__S_clear_84x28_v2         PASS PASS PASS      yes
    clear__S_mixed_84x28_w3_v2      PASS PASS PASS      yes
    fog__S_clear_84x28_v2           PASS PASS PASS      yes
    fog__S_mixed_84x28_w3_v2        PASS PASS PASS      yes
    night__S_clear_84x28_v2         FAIL FAIL FAIL      yes
    night__S_mixed_84x28_w3_v2      PASS PASS PASS      yes
    low sun__S_clear_84x28_v2       FAIL FAIL FAIL      yes
    low sun__S_mixed_84x28_w3_v2    PASS PASS PASS      yes

    lap-pair verdict disagreement: 0 of 24 pairs (0.0%)

Recomputable by anyone from committed artifacts; the script is in
`docs/TOWN04_REDO_FINDINGS.md` under T04-R12. This is at the LAP level, which is the unit
A-4 defines, and it includes three cells that failed unanimously -- agreement is not an
artifact of every cell being easy.

## 4. The limit of that measurement, stated plainly

**No Town04 cell sits near the cliff, so this does not measure verdict stability near the
cliff.** Distance from the 0.668 m budget, worst lap per cell:

    night__S_mixed        +36.1%   lap-to-lap spread 0.612 ft  (28% of budget)
    fog__S_clear          +38.2%   spread 0.252 ft
    low sun__S_mixed      +62.7%   spread 0.358 ft
    clear__S_clear        +73.5%   spread 0.054 ft
    clear__S_mixed        +81.5%   spread 0.107 ft
    fog__S_mixed          +81.6%   spread 0.138 ft
    low sun__S_clear    -1341.6%   spread 1.353 ft
    night__S_clear      -1789.7%   spread 14.124 ft

The tightest margin is +36.1% and the largest spread among passing cells is 28% of budget.
Those numbers are close enough to each other that a cell with materially less margin could
plausibly flip between laps. Ten repetitions would not fix that -- it would characterise a
coin flip more precisely, and the coin flip is the finding.

## 5. Proposed replacement for the final sentence of D-7

> **Therefore a closed-loop verdict is reported over at least three repetitions, under a
> fully enforced harness, WITH ITS MARGIN.** The repetitions are a reproducibility check,
> not a sample for estimating a rate: measured at the lap level on the corrected harness,
> verdict disagreement was 0 of 24 lap-pairs across eight cells, three of which failed
> unanimously. **If the repetitions disagree, that is a defect to be diagnosed and the
> cell is VOID, not a rate to be estimated** -- running more repetitions converts an
> identified defect into a plausible-looking failure rate and loses it.
>
> "Fully enforced" is not optional and is not a default: D-1..D-6 green on each fresh
> server, a clean server restart and a fresh vehicle before EVERY repetition, one process
> per repetition, one client per port. **Where the harness is not fully enforced, the ten
> repetition floor stands**, because a larger sample drawn through a harness known to be
> wrong measures the harness and still has the shape of a result.
>
> **A verdict whose margin is within the observed repetition-to-repetition spread is not
> settled by three repetitions.** It is a finding in its own right and is reported as one.
>
> D-1..D-6 shrink the noise; they do not remove it, and no future version of this file may
> claim they do without a measurement showing a frozen scene rendering bit-identically
> across reps.

## 6. What it costs, and who it touches

- **Already-published numbers stand as collected.** AEB and multi-condition collected under
  the ten-repetition reading; nothing is recomputed or withdrawn. Both repos carry the lap
  protocol as pending in `CARLA_DETERMINISM_PENDING.md`.
- **The lock must be regenerated in the same commit** as the rule change (section 4), and
  the amendment named in section 4's list, which currently reads "Amendments so far: none".
- `preflight.py:128` prints the ten-repetition floor at every restart and must change with
  the rule, or the harness will keep contradicting it out loud.

## 7. What would falsify this proposal

A cell whose three laps disagree under a fully enforced harness, where the cause is traced
to renderer noise rather than to a harness defect. That is the case D-7's floor was
protecting against, and this study has not produced one. Town06's 24 laps have not been
driven yet and are the next opportunity to.

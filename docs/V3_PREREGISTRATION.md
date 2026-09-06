# V3 — does the closed-loop ledger reproduce on current hardware?: pre-registration

## A disclosed deviation, first

**This was written at 22:45, four minutes AFTER V3 started driving, and after 1 of its 8
cells had completed.** Every other item in this programme was pre-registered before its
first scored lap; this one was not, and backdating it would be worse than saying so.

What is and is not compromised:

* **PROTOCOL R1 is satisfied.** V3's certificate — byte-identical to the canonical one —
  was committed at 22:41, before the driver was launched. The prediction preceded the
  drive, which is what R1 requires and what makes the comparison blind.
* **The completed cell is `clear/S_clear_t06lap_168x56_w2_s0`, which is VACUOUS** by
  construction (clear is the endpoint the disturbance family interpolates from, so the box
  has zero width). It carries no information about any certificate verdict, so it cannot
  have informed the predictions below.
* **The other seven cells had not run.** The predictions below are made before their
  results exist.

Recorded as a deviation rather than repaired, because the fix for a late pre-registration
is disclosure, not a better timestamp.

## The question

> Both committed ledger passes were driven **before** the RTX 5090 migration. Does the
> closed loop reproduce on current hardware?

```
  pass 1 driven               2026-09-03  00:27 - 00:53
  pass 2 driven               2026-09-03  12:49 - 13:14
  migration to the RTX 5090   2026-09-03  22:56
```

`docs/MIGRATION_2026-09-03.md` verified the **certificate** (offline; all six verdicts and
pose counts) and the **oracle** (bit-identical CSVs, photometry 0.003% off reference). It
states plainly that *"Nothing in the study was re-run for the paper"*. **No closed-loop cell
has ever been driven on this GPU** until V1, two hours ago.

So the paper's "all eight verdicts reproduced by an independent second pass" is a
**within-hardware** reproduction. That is not an error and was never concealed — it simply
has not been tested across the hardware change, and it is testable in under an hour.

## Why it might not reproduce

E1b established the mechanism: the renderer injects ~30 differing pixels per frame, the
policy amplifies them at one or two decision points, and the trajectory commits to one of a
few **discrete basins**. A different GPU changes that input. Photometry agreeing to 0.003%
is an aggregate check and does not imply bit-exact rendering, and D-7 already states that
bit-exact closed-loop replay is unreachable.

V1 gave the first evidence: the canonical VOID fog cell exceeded budget on 1 of 3 laps on
the old hardware and **0 of 24** on this one.

## Design

The canonical pair, four conditions, three laps, through the committed driver — the same
protocol as pass 1 and pass 2 — into `results/town06/hw_recheck/`, compared against a
byte-identical copy of the committed certificate. Both committed ledgers are untouched.

## Predictions — written before the seven remaining cells

**V3-P1 — at least seven of the eight verdicts reproduce.** Reason: pass 2 reproduced all
eight within-hardware, most cells are far from the corridor boundary (the clear-only student
reaches 21, 7.8 and 6.3 m from its lane centre — not marginal), and E1b found non-VOID cells
varying by only 1–3% across laps.

**V3-P2 — the fog/S_mixed cell does NOT reproduce as VOID.** V1 already drove it 24 times on
this hardware with 0 over budget. Predicted **PASS**. This is the cell the whole question
turns on.

**V3-P3 — agreement is still 4/5 or better** on scored cells. If P2 holds, the fog cell
stops being excluded as VOID and becomes a scored cell, which can only change the
denominator — so the agreement figure may move, and which way is exactly what is worth
knowing before the paper is reviewed.

**V3-P4 — no cell that drove FAIL now drives PASS.** The three failing `S_clear_t06` cells
are 3–10x outside budget; a hardware change that flipped one of those would mean something
far larger than basin selection.

## What counts as an answer

* **P1 and P2 hold:** the study reproduces across hardware except at one marginal cell, the
  VOID is explained as a hardware-conditioned basin outcome, and the paper gains a
  reproducibility result it does not currently have.
* **P1 fails:** the closed-loop half of this study is hardware-conditioned in a way that
  matters, and that is a finding about the paper's central evidence. Report immediately and
  before anything else in the queue.
* **P4 fails:** stop and investigate; it would mean the hardware changes more than the basin.

## Bound by

`PROTOCOL.md` R1/R4, `CLAUDE.md` R-SIM-1..6, standing rules 1 (deviation disclosed above),
3, 7, 8. Exploratory tag; nothing written to `results/town06/ledger`, `ledger_pass2`, or
either committed certificate.

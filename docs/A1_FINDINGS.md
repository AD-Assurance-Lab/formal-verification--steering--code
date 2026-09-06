# A1 — the best policy this pipeline knows how to build: findings

**Run 2026-09-05 23:29 – 2026-09-06 00:12.** Pre-registration `docs/A1_PREREGISTRATION.md`,
committed before the first lap, with the candidate-selection rule declared and its resolved
answer (seed 2) recorded in advance. Subject `S_mixed_bal_bal_s2` — `lr=3e-4` **and**
`--balance`, the two levers Q1 and Q4 identified. Nothing was distilled; Q4's arm already
existed. Output `results/town06/best/`.

```
pass 3's gate (evaluate.py, MARGIN_FRAC=0.5, margin 1.0958 ft)
  clear    3/3   1.02 ft        night    3/3   0.74 ft
  fog      3/3   1.08 ft        low_sun  0/3   2.12 ft        ->  9/12, gate NOT passed

the scored ledger (closed_loop_ledger.py, budget 2.19 ft), certificate committed first
  cond      drive   worst   laps                    certificate
  clear     PASS     0.79   0.74, 0.74, 0.79        (baseline, vacuous)
  fog       PASS     1.34   1.34, 1.29, 1.34        NOT_CERTIFIED  (+2.11x tol)
  low_sun   PASS     1.30   1.30, 1.27, 1.24        CERTIFIED      (+0.29x tol)
  night     PASS     0.85   0.84, 0.85, 0.85        NOT_CERTIFIED  (+3.38x tol)

  agreement 1/3      R1 satisfied against commit timestamps
```

## The short answer

**Under the study's scored instrument, the best policy this pipeline can currently build
passes all four Town06 cells — and the verifier refuses two of them.**

That is a reframing of the paper's Limitations paragraph, which currently says the binding
constraint "is currently distillation rather than verification". On this student, on the
ledger's own criterion, **distillation has caught up. What is left is the bound.**

## A1-P1 — HELD on the gate, but the gate is not the ledger's criterion

Predicted the pass-3 gate is not passed. It is not: **9/12**, stopped by low_sun at 2.12 ft
against a 1.0958 ft margin.

But the two criteria differ and both statements need saying together:

* **Pass 3's gate** demands every lap inside **50% of budget**. A1 fails it on one condition.
* **The ledger** demands every lap inside **budget**. A1 passes it on all four, worst lap
  1.34 ft = **61% of budget**.

So "no student has passed pass 3's gate" remains true, and "the best student now passes
every scored ledger cell" is also true, and they are not in tension.

## A1-P2 — FALSIFIED. Fog is no longer the stopping condition

This is the result that matters most for the draft.

Predicted fog would still stop it. **Fog held 3/3 at 1.08 ft, inside pass 3's margin — the
first student in this study to do so.** The condition that stopped it was **low sun**.

```
  pass 3, sixteen students        fog stopped every one
  Q2, five tuned candidates       fog failed the margin for 4 of 4 gated
  A1, tuned AND balanced          fog 3/3 inside the margin; low sun stops it
```

Balancing did not merely improve fog — **it moved the failure to a different condition.**
Q4 measured balancing removing fog failures rather than shifting the median, and A1 is what
that looks like at the gate.

The paper's "fog stopped every one" framing describes pass 3 accurately and should stay
attached to pass 3. It is no longer a general statement about this pipeline.

## A1-P3 — HELD. The certificate refuses fog

Predicted the bound stays outside the corridor on fog even if driving holds. Measured
**+2.11x tolerance, `NOT_CERTIFIED`**, while the student drives fog 3/3 at 61% of budget.

## A1-P4 — HELD. Driving holds all four under budget

0.79, 1.34, 1.30, 0.85 ft. Comfortable, on every condition.

## The soundness question, which was live and is answered

Before the drives, the certificate and the gate disagreed **in both directions at once**:
the bound refused fog (which the gate had just cleared) and certified low sun (which had
just stopped the gate at 2.12 ft). If low sun had then driven FAIL, that would have been a
**false certificate** — the soundness violation this study has never observed and which Q3's
pre-registration said would stop the queue.

**It did not happen.** Low sun drove **PASS 3/3 at 1.30 ft**, and the `CERTIFIED` cell is
the one cell of three that agrees with driving.

**No cell has ever been `CERTIFIED` while driving failed, in any experiment in this
programme.** Q3, V3 and A1 all tested it on different students; all three agree.

## The driver discrepancy is not a constant offset

V2 found the ledger reading ~0.4 ft **higher** than `evaluate.py` on one checkpoint. A1
shows it is not a bias that can be corrected for:

```
  cell      gate (evaluate.py)   ledger        difference
  fog             1.08 ft         1.34 ft       ledger +0.26
  low_sun         2.12 ft         1.30 ft       ledger -0.82
```

**On low sun the ledger reads 0.82 ft LOWER, and that flips the conclusion for that cell**
— gate-failing at 2.12 ft, comfortably passing at 1.30 ft. So the open item V2 recorded is
larger than "one driver runs hot": the two drivers disagree per-cell, in both directions, by
amounts that change verdicts. Any comparison that crosses the two families is unsafe until
this is understood, and that includes reading A1's gate result next to A1's ledger result.

**What is safe:** A1's gate against pass 3's gate (both `evaluate.py`), and A1's ledger
against the canonical ledger (both `closed_loop_ledger.py`). Both comparisons above are made
that way.

## Agreement, and what it means

**1/3**, the same as Q3's tuned student. The single agreeing cell is the `CERTIFIED` one.
Both `NOT_CERTIFIED` cells drive cleanly, so both disagreements are **incompleteness** —
the bound refusing safe policies, never the reverse.

Across the three blind tests run in this programme on non-shipped students, the pattern is
consistent: **as the policy gets better, agreement falls and every disagreement is the
verifier being conservative.**

```
  pass 1, shipped students (old hardware)   4/5
  V3, shipped students (current hardware)   4/6
  Q3, tuned student                         1/3
  A1, tuned + balanced student              1/3
```

## What this changes for the paper

1. **"Fog stopped every one" belongs to pass 3, not to the pipeline.** With the recipe tuned
   and balanced, fog is held 3/3 inside pass 3's own margin and low sun becomes the
   stopper.
2. **The Limitations sentence should be rewritten.** "The binding constraint is currently
   distillation rather than verification" is no longer supported for the best student
   available: it passes every scored ledger cell, and two of three are refused by the bound.
   The constraint has moved to the bound's looseness.
3. **Soundness now has three independent confirmations** on students the certificate was
   computed blind against.

## What was NOT done

`PROMOTE=0` and the private pin `S_mixed_best_gate` throughout; neither shipped `.selected`
moved. Nothing written to `results/town06/ledger`, `ledger_pass2`, or either committed
certificate. Nothing was distilled for A1.

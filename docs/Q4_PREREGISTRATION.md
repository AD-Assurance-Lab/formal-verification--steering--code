# Q4 — confirming label balancing: pre-registration

**Written 2026-09-05, before any Q4 distillation or lap.** Queue item
`docs/EXPERIMENT_QUEUE.md` §Q4. Driver `scripts/arm_sweep.sh`, output
`results/town06/balancing/` (extends E6's directory; E6's seeds 0–5 are the existing half).

## The question

> E6 measured `--balance` holding fog **5/5** against raw's **3/6**, and *improving* clear
> (0.93 vs 1.21 ft) — falsifying the repo's own stated reason for rejecting it. At 5 of 6
> seeds that is Fisher **p ≈ 0.18**. Does it survive twelve seeds?

## Why it matters, and why it is fifth rather than first

`--balance` is a **cheap default**: a flag already in `distill.py`, no new machinery, no
cost at inference or verification. If E6 holds, it should simply be on. But E6-F3 measured
it as a **second-order lever** — the learning rate moved the fog median by 9.88 ft and
balancing by 0.10 ft — so it cannot be allowed to delay Q1, Q2 or Q3.

The interesting claim is not about the median at all. It is E6-F1: **balancing did not move
the typical student, it removed the failures.** Raw's median is flattered by a distribution
containing a 37.65 ft departure; `bal` produced none. That is a claim about the *tail* of
the seed distribution, and a tail claim at n = 6 is exactly the kind this study keeps
watching die under a sweep.

## Declared design

Two arms, seeds 0–11 (n = 12), fog and clear, 3 laps, kernels pinned, `lr=3e-4` on both:

| arm | flags | isolates |
|---|---|---|
| `bal` | `--lr 3e-4 --balance` | straight-frame balancing |
| `curv` | `--lr 3e-4`, `DISTILL_CURV_BETA=4.0` | curvature-weighted loss, the alternative |

Seeds 0–5 exist from E6 in `results/town06/balancing/`; seeds 6–11 are new. **The fold-in
is validated the same way Q1's was** — seed 0 of each arm is re-distilled under the Q4 arm
definition and compared by SHA-256 against E6's checkpoint. If a hash differs, that arm
runs 0–11 fresh.

**The control is Q1's `lr3e4` arm** (raw, `lr=3e-4`, same architecture, same pinned
kernels), which Q1 takes to n = 15. Q4 therefore compares 12 vs 12 vs 15 without driving a
single control lap of its own.

## Declared analysis

**Primary endpoint — and it is the failure count, not the median.** Seeds holding fog 3/3
under the 2.19 ft budget, per arm, against the raw control. Fisher exact, two-sided,
alpha = 0.05. E6-F1 is explicit that the median is the wrong statistic for this effect, and
pre-registering the median as primary would test a claim nobody is making.

**Secondary.** Fog median and its Hodges–Lehmann shift vs control; clear median and holding
count (the control direction — E6 found clear *improving*, which is what made it a
falsification); fog KD p99 median; VOID counts per arm.

**VOID cells** excluded, never averaged, never re-driven. E6 saw **four** VOID cells across
these two arms, which is high, and **VOID rate is a declared secondary endpoint**: an arm
that is more often unmeasurable is worse, and E6's own note that they match E1b's
multimodal signature does not make them free.

## Predictions — written before any Q4 run

**Q4-P1 — the failure-removal effect survives.** `bal` holds fog 3/3 in at least **10 of
12** seeds, against the raw control's rate at n = 15. Reason: 5/5 at E6 with zero
departures, and the mechanism is specific and plausible — 83.8% of Town06 needs
|steer| ≤ 0.01 and two sections are 100.0%, so an unbalanced student learns to emit ~0 with
an offset that the straight sections integrate into a departure.

**Q4-P2 — it reaches significance.** Fisher p < 0.05 against the control. Weaker than P1:
if the control's own rate rises at n = 15 (Q1 may show `lr3e4` holding fog more often than
E4's 3/6 suggested), the contrast shrinks and this fails while P1 holds.

**Q4-P3 — clear does not regress**, and more specifically `bal`'s clear median stays at or
below the control's. This is E6-F2's falsification of the repo's stated objection, and
Q4 is where it either replicates or does not.

**Q4-P4 — `curv` does not beat `bal`** on the primary endpoint. E6 found the curvature
weighting the weaker of the two and it costs a hyperparameter the balancing flag does not.

## What counts as an answer

* **P1 and P3 hold:** `--balance` becomes the default, the repo's stated reason for
  rejecting it is retracted in the code comment as well as in the findings, and every later
  distillation in this lab gets it for free.
* **P1 fails:** E6 is the **fifth** single-sweep claim in this study to die at more seeds,
  and that pattern is itself the finding — it is what Q6 is chartered to explain, and Q4's
  result should be read next to Q6's.
* **P2 fails while P1 holds:** report the rate and the interval; a cheap flag with a
  consistent direction and a wide interval is still worth turning on, and the write-up says
  exactly that rather than claiming significance.

## Bound by

`PROTOCOL.md`, `CLAUDE.md` R-SIM-1..6, standing rules 1, 3, 7, 8. No promotion, no
`.selected` pin, nothing written to either ledger or either certificate.

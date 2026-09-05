# Q3 — a blind certificate-then-drive on a tuned student: pre-registration

**Written 2026-09-05, before any Q3 certification or lap.** Queue item
`docs/EXPERIMENT_QUEUE.md` §Q3. Output `results/town06/tuned/`.

## The question

> Q2 asks whether a tuned student **drives**. The paper's claim is that a certificate
> **predicts** driving. Does it, on a policy that is actually good?

## Why this is the one that matters

Every agreement number this study reports was measured on students that mostly **fail**.
A predictor that says "unsafe" about policies that are unsafe is doing less work than the
write-up implies, and the interesting direction — a certificate that refuses a policy which
then drives fine — is **incompleteness**, which the study currently asserts rather than
measures. E7-F3 is the warning shot: a student driving fog at **0.98 ft** is still
`not certified`.

So Q3 is where the method's incompleteness gets a number, on the study's own road, under
the study's own blind protocol.

## Order — and it is checkable, not merely promised

1. Certify to a **new** path, `results/town06/tuned/certificate_tuned.json`.
2. **Commit that certificate** (PROTOCOL R1) before a single scored lap.
3. Drive.
4. `python -m study.ledger --check-order` must pass, and R1 is verified against commit
   timestamps exactly as `73415e5` was for the canonical certificate.

The canonical certificate does not move. `certify_town06.py` refuses to overwrite it, and
`TOWN06_STUDENTS_OVERRIDE` refuses to write the canonical path at all — Q3 relies on both,
and does not rely on remembering.

## Subject

The **single best candidate from Q2**, chosen by the rule declared here before Q2 reports:
the candidate with the most gate laps under 1.095 ft, ties broken by lowest fog worst-of-3,
then by lowest seed. If Q2 produces no candidate that holds fog 3/3, Q3 runs on the
candidate with the lowest fog worst-of-3 regardless, and the write-up says so — a
certificate on a mediocre policy is still a blind test, it is just a weaker one.

Four conditions: `clear`, `fog`, `night`, `low_sun`. Three laps each, 12 scored laps.

## Declared analysis

**Primary endpoint.** The 2x2 agreement table between certificate verdict
(`CERTIFIED` / `NOT_CERTIFIED`) and driving outcome (held 3/3 under budget / not), across
the four cells, reported **cell by cell with the margin** — a pass at 1% of budget and a
pass at 60% are different results (standing rule 3).

**Secondary.** For every `NOT_CERTIFIED` cell, whether it is *falsified* (a witness exists)
or *undecided* (bound outside the corridor, no witness). This is the same three-way reading
Q8 exists to firm up, and Q3 is where it gets exercised on a good policy.

**VOID cells** are excluded from the agreement table and reported separately, never
averaged and never re-driven with more laps.

## Predictions — written before certifying

**Q3-P1 — the certificate is conservative, not wrong.** No cell is `CERTIFIED` while
driving fails. This is the soundness direction, and a violation would be the most serious
possible finding in this study — it would contradict §4.1, the paper's strongest result.
**If Q3-P1 fails, everything else in this queue stops until it is understood.**

**Q3-P2 — at least one cell is `NOT_CERTIFIED` while driving holds 3/3 comfortably.**
Incompleteness is real and E7-F3 already saw it. This is the *expected* outcome and it is
a contribution, not an embarrassment: it is the measured price of a sound method.

**Q3-P3 — fog is the cell where P2 bites.** Fog is where every disagreement in this study
has localised.

**Q3-P4 — agreement is worse than pass 1's 4-of-5.** A better policy sits closer to the
corridor boundary, so the bound has less room to be trivially right. If agreement is
*better* than 4-of-5, that is a genuinely good result for the method and is reported as
such — but it is not what is predicted.

## What counts as an answer

* **P1 holds, P2 holds:** the method is sound and measurably incomplete on a good policy.
  That is a publishable, honest characterisation and it is what the Limitations section
  currently lacks.
* **P1 holds, P2 fails** — every cell that drives is also certified: the strongest possible
  result for the method, and it needs its own scrutiny before it is believed, because it is
  better than the study has any reason to expect.
* **P1 fails:** stop the queue.

## Bound by

`PROTOCOL.md` R1/R2/R4, `CLAUDE.md` R-SIM-1..6, standing rules 1, 3, 7, 8. Nothing written
to `results/town06/ledger`, `ledger_pass2`, either committed certificate, or any `.selected`
pin. Needs a fresh CARLA server before every lap and the condition verified from a frame
(R-SIM-4) on every run.

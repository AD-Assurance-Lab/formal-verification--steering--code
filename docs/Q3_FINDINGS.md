# Q3 — a blind certificate-then-drive on a tuned student: findings

**Certified 2026-09-05 15:05, committed 15:06 (`c5c10fe3`), driven 15:31–15:41.**
Pre-registration `docs/Q3_PREREGISTRATION.md`, committed (`d09ee72`) before Q2 reported and
long before this certificate existed. Artifacts in `results/town06/q3_tuned/`, written under
`TOWN06_LEDGER_TAG=q3_tuned` so nothing touches pass 1's ledger, pass 2's, or either
published certificate.

**Subject:** `S_mixed_lr_lr3e4_s7` — Q2's best candidate at 9/12, selected by the rule Q3
declared before Q2 ran.

```
cell      drive   worst ft  % budget   bound hi (x tol)  certificate
clear     PASS     0.52       23.6%          --          (baseline, vacuous)
fog       PASS     1.19       54.4%       +4.081         NOT_CERTIFIED
night     PASS     1.47       67.0%       +1.656         NOT_CERTIFIED
low_sun   PASS     0.45       20.7%       +0.240         CERTIFIED

  agreement on scored cells: 1/3        (pass 1's shipped students: 4/5)
  R1 verified against commit timestamps: certificate 1788635174, every cell 1788637295
```

## The short answer

**The certificate is sound and it is expensively incomplete.** All four Q3 predictions held.

The tuned student **drives every condition, 3/3 laps, worst case 1.47 ft against a 2.19 ft
budget** — and the verifier refuses two of its three scored cells. This is the first time in
this study a certificate has been tested against a policy that is actually good, and the
answer is that the method's conservatism, which the write-up asserts, is real and large.

## Q3-P1 — HELD. Soundness is intact, and this was the one that could have stopped the queue

Predicted: no cell is `CERTIFIED` while driving fails. **No cell was.** `low_sun` is
`CERTIFIED` and drove 3/3 at 20.7% of budget; `clear` is vacuous and drove at 23.6%.

The pre-registration said a violation here *"would be the most serious possible finding in
this study — it would contradict §4.1, the paper's strongest result"*, and that the queue
would stop. It did not happen. **§4.1 stands.**

## Q3-P2 — HELD. Incompleteness is real, and now it has a number

Predicted: at least one `NOT_CERTIFIED` cell drives 3/3 comfortably. **Two did.**

```
  fog     NOT_CERTIFIED, bound +4.08x tolerance   ->  drove 3/3, worst 1.19 ft (54% of budget)
  night   NOT_CERTIFIED, bound +1.66x tolerance   ->  drove 3/3, worst 1.47 ft (67% of budget)
```

Neither is marginal driving. Both are comfortable passes on a policy the verifier will not
certify. That is the measured price of a sound method on this family, and it is what the
Limitations section has been asserting without evidence.

**This is a contribution, not an embarrassment**, and the pre-registration said so before
the numbers existed: a sound method that refuses safe policies is doing its job badly but
honestly, and the size of the refusal is a fact about CROWN on this architecture.

## Q3-P3 — HELD. Fog is where it bites hardest

Fog carries the widest bound of the three, **+4.08x tolerance**, and drives at 54% of
budget. Every disagreement in this study has localised to fog and this one does too.

## Q3-P4 — HELD. Agreement is worse on a better policy

Predicted: agreement worse than pass 1's 4-of-5. Measured **1/3 (33%)** against **4/5 (80%)**.

The pre-registration gave the reason in advance: *"a better policy sits closer to the
corridor boundary, so the bound has less room to be trivially right."* Pass 1's agreement
was carried substantially by `S_clear_t06` — a policy so bad that refusing it was easy. Take
the easy cells away and the agreement rate falls by half.

**This is the sentence the paper's agreement figure needs next to it.** An agreement rate
measured on policies that mostly fail is not evidence that the method predicts driving; it
is partly evidence that both the method and the road agree a bad policy is bad.

## The result that was not predicted: the better driver is harder to certify

Comparing the tuned student against the shipped one, on the **same captures, same bound
math, same stride and nsplit, same ReLU count (101,888)**:

```
  cell      shipped S_mixed      tuned S_tuned      driving (tuned)
  fog          +1.240             +4.081  (3.3x wider)   PASS 3/3, 1.19 ft
  night        +2.836             +1.656  (1.7x tighter) PASS 3/3, 1.47 ft
  low_sun      +0.299             +0.240                 PASS 3/3, 0.45 ft
```

**The tuned student's fog bound is 3.3x wider than the shipped student's, while it drives
fog better.** The shipped student's fog cell is VOID in pass 1 (1 of 3 laps failed); the
tuned student holds fog 3/3.

So on the one condition this whole study turns on, **bound width and driving quality move in
opposite directions between these two policies.** That is not a contradiction — a sound
upper bound is allowed to be loose, and looseness is a property of the weights, not of the
driving — but it is a direct measurement of how little the bound width says about the
policy's actual behaviour on this family, and it belongs next to E4-F2's result that
architecture drives bound width.

**It also weakens any temptation to use bound width as a model-selection signal.** Choosing
the narrower-bounded of these two students would have chosen the one that goes VOID in fog.

## What is NOT claimed

* **This is one student.** Q3 is n = 1 policy across 3 scored cells, and the dispersion Q6
  measured applies to the driving side of it as much as anywhere else. The agreement figure
  1/3 is not an estimate of a rate.
* **No expectation was pre-registered for this student**, and the comparison tool now says
  so explicitly rather than scoring it against the shipped students' table. The applicable
  predictions are Q3-P1..P4 above, which were committed before the certificate existed.
* **Nothing here revises the deployment test.** Pass 1's 4-of-5, both ledgers and both
  certificates are untouched; the canonical comparison still prints exactly what it did.

## A defect found by running this, and fixed

`study.town06_design.expected()` is keyed on the student in every branch but the vacuous
one, so `S_tuned` — a name the table has never heard of — **fell through to the clear-only
student's row** and was scored against it. The comparison printed three `CONTRADICTS` that
meant only "there is no row for me".

Under standing rule 2 a contradiction is a BUG until a written disposition rules out the
candidate causes, so a defaulted expectation does not merely print a wrong word: **it
manufactures an investigation with no subject.** `expected()` now refuses for an unknown
student, and returns "not pre-registered" under an exploratory tag. Pinned by tests; the
canonical comparison verified unchanged.

## Harness notes, recorded because they cost time

* The first two attempts at these drives used a hand-rolled
  `closed_loop_ledger.py --reps 3` loop and **aborted at the first in-run restart** with
  `terminate called ... TimeoutException`, core dumped, twice. That path is documented in
  the script itself as not working — *"releasing every reference the caller held was not
  sufficient"* — and a **process boundary per run** is the only correct version. The
  committed shell driver exists for exactly this. Standing rule 8, learned again.
* The 602 MB core dumps those aborts left in `/var/crash` were what the session kept
  reporting as low memory; actual free memory was ~50 GB throughout.
* Three cells were **re-driven** because they recorded `git_dirty=True` — an uncommitted
  edit and a tracked restart log modified by the failed attempts. Neither is in the driving
  path and the certificate never moved, so the measurements were sound, but pass 1's cells
  all record `dirty=False` and "attributable to an exact tree" is what the provenance block
  exists to provide. All four cells now share one clean sha.

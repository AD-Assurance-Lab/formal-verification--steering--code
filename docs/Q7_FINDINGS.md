# Q7 — the cross-road fog comparison at matched INPUT SIZE: findings

**Run 2026-09-06, 00:40–02:00.** Pre-registration `docs/Q7_PREREGISTRATION.md`, committed
before any capture. New capture set `results/town06/captures_84x28/`, student
`S_q7_84x28_s0`, certificate `results/town06/q7_84x28/certificate_84x28.json`. The committed
168x56 captures and the canonical certificate are untouched.

```
FOG certified bound width, in units of tolerance

  road     student                        ReLU     input     WIDTH    verdict
  Town04   S_clear   (published)          5,152    84x28      0.79    CERTIFIED
  Town04   S_mixed   (published)         15,456    84x28      0.23    CERTIFIED
  Town06   S_q7      (Q7, this run)      20,608    84x28      8.62    not certified   <-- new
  Town06   S_mixed   (19,104, E7)        19,104   168x56      4.15    not certified
  Town06   S_mixed   (101,888, tuned)   101,888   168x56      1.86    not certified
  Town06   S_mixed   (shipped)          101,888   168x56      1.69    not certified

  WIDTH is hi - lo, the convention E7 and the paper use. Q7's cell is
  [-1.480, +7.139], so its width is 8.619 and its upper edge is 7.14.
```

## The short answer

**The cross-road comparison survives at matched input size, and by a wide margin.** All
three predictions held.

E7 refuted the *capacity* reading of the fog asymmetry but could not address input size: its
Town06 students were all 168x56 while Town04's are 84x28, so the published comparison still
confounded **road** with **projection**. Q7 removes that confound by capturing Town06 at
84x28 and certifying a student there.

At the **same 84x28 input**, Town06's fog bound is **8.62x tolerance wide** against
Town04's **0.23x and 0.79x** — **11x to 37x wider**, and on the wrong side of the corridor
where both Town04 cells certify comfortably.

## Q7-P1 — HELD. The small-input student's bound is worse

Predicted the 84x28 Town06 student's fog bound would be worse than the 168x56 one's.
Measured **8.62x against 1.86x** at the tuned recipe — 4.6x worse — and worse than E7's
19,104-ReLU 168x56 student (4.15x) at a *larger* neuron count (20,608).

This extends E7's ladder in the direction it predicted: shrinking the representation, by
capacity or by projection, makes Town06's fog bound monotonically worse.

## Q7-P2 — HELD. The A-3 capture gate passes

```
  mean |capture - driven|   0.0150   over 1055 poses   threshold 0.05
  for reference: Town06 committed 0.0261, Town04 0.0065
```

**Better than the committed Town06 gate.** This was the precondition: a bound computed on
frames that do not reproduce the driving rig proves nothing about the system, and the gate
is what makes the new capture set usable at all.

The capture set was also compared against what it parallels before being believed (standing
rule 8):

```
  168x56 committed   frames (1,1060,1,1,3, 56,168)   1060 poses   2111.0 m   98.2 MB
   84x28 Q7          frames (1,1060,1,1,3, 28, 84)   1060 poses   2111.0 m   25.1 MB
```

Same pose count, same scored span to 0.1 m, correct projection, and a size ratio of 0.256
against the expected 0.25 for quarter resolution. This is the check Town04's redo failed
at 1.8 MB against a published 1.7 GB.

## Q7-P3 — HELD. This is the result Q7 was run for

Predicted the arterial's fog bound stays worse than the highway's at matched input size. It
does, by 11–37x.

**And the comparison is conservative in the right direction.** Q7's student is *larger* than
Town04's (20,608 vs 15,456 ReLU) — and E7 established that for Town06, smaller networks
certify fog *worse*. So matching Town04's capacity exactly would have made Town06's bound
worse still, not better. The gap measured here is a lower bound on the gap at fully matched
capacity and projection.

**A units note, because I got it wrong first.** E7 and the paper report bound **width**
(hi − lo). This document first quoted Q7's **upper edge** (7.14) in a column labelled
width, which compared an edge against widths. Corrected throughout to 8.62.

## What this closes

The sceptical reading of the published cross-road result was: *Town06's fog cells fail
because its networks are bigger and CROWN loosens with size, so the comparison measures
architecture rather than the ODD.* That objection now fails on both axes:

* **capacity** — E7, by shrinking Town06's students to Town04's size class (the bound got
  worse, not better);
* **input size** — Q7, by capturing Town06 at Town04's projection (the bound got worse
  again).

Fog on Town06 is harder to certify **at every capacity and every projection measured**.

## Caveats, stated plainly

1. **The recipes are not identical.** Q7's student uses the tuned-and-balanced recipe
   (`lr=3e-4 --balance`) that Q1 and Q4 established; Town04's students are from the
   published era at the original recipe. A perfectly matched comparison would re-distil
   Town04 at the tuned recipe. Everything measured since Q1 says the tuned recipe produces
   *better* students, so this also errs toward understating the gap.
2. **One seed.** Q7 certifies a single 84x28 student. E7 was explicit that it was
   exploratory and not pre-registered; Q7 *was* pre-registered, but n = 1 on the new
   projection.
3. **The 84x28 student was not driven under the ledger**, only under `evaluate.py` for the
   gate's driven trace (clear, 1.80 ft, PASS). Q7 is a certification result, not a driving
   one.

## What was NOT done

No canonical artifact touched. The committed captures, the canonical certificate and both
ledgers all stand. The new capture set lives in its own directory, and both certifier
guards added for this run — a non-canonical capture set may not write the canonical
certificate, and a non-default projection may not be applied to the committed frames — were
exercised and both fire.

# V2 — what the paper's "0.98 ft" student actually does: pre-registration

**Written 2026-09-05, before any V2 lap.** Output `results/town06/lr_seed0/` under
`TOWN06_LEDGER_TAG=lr_seed0`.

## The question

> `sec_results.tex:330` of the arXiv draft says changing only the learning rate "produced a
> student that drives fog at 0.98 ft". What does that checkpoint actually do over enough
> laps to say?

## Why this is worth a run of its own

It is a number **in the paper today**, and it has already failed to replicate once:

```
  E4  2026-09-04   0.98 ft
  Q1  2026-09-05   0.98 ft
  Q2  2026-09-05   1.34 ft   -- and the cell went VOID (laps disagreed by >25%)
```

Three drives of a byte-identical checkpoint, two agreeing and one not. That is not enough
to quote a single figure, and it is not enough to retract one either. **The paper needs a
range, and nobody has measured the distribution.**

This is the fifth single-draw number in this study to wobble under re-measurement, so the
useful output is not a corrected point estimate but a characterised spread.

## Design

12 laps of `S_mixed_depth_d3lr3_s0` under **fog**, one process and one fresh server per
lap, on the corrected harness. Same checkpoint, condition, route and budget as the
measurements above.

**Endpoints, declared:** the full distribution of worst-lap max|CTE|; the count of distinct
values at 0.01 ft resolution and clusters at a 1 ft gap (E1b's discreteness signature); the
fraction of laps at or under the **1.095 ft pass-3 margin** and at or under the **2.19 ft
budget**, each with a Wilson 95% interval; and where on the route the worst excursion falls.

## Predictions — written before any V2 lap

**V2-P1 — 0.98 ft is at or near the favourable end, not the centre.** The median of 12 laps
is **above** 0.98 ft. Reason: three prior drives gave 0.98, 0.98, 1.34, and every
single-draw claim in this study that has been swept has moved toward the middle.

**V2-P2 — the distribution is discrete**, in E1b's sense: 12 laps land on fewer than 8
distinct values at 0.01 ft resolution.

**V2-P3 — fewer than half the laps clear the 1.095 ft margin.** If this holds, the claim
"the first student in this study to clear pass 3's margin gate on fog" is a statement about
a draw and not about the student, and the paper should say so.

**V2-P4 — every lap stays under the 2.19 ft budget.** This student is a good driver; the
question is headroom, not safety. A lap over budget would make it a second VOID-shaped cell
and is reported separately.

## What counts as an answer

* **P1 and P3 hold:** the draft's sentence gets a range and loses its dependence on one
  lucky lap. That is the deliverable.
* **P1 fails** — 0.98 ft is the median — the number stands as written and only the VOID in
  Q2 needs explaining.
* **P4 fails:** the student is not the clean example the paper uses it as, and that matters
  more than the point estimate.

## Bound by

`PROTOCOL.md` R4, `CLAUDE.md` R-SIM-1..6, standing rules 1, 3, 8. Exploratory tag only;
nothing written to either canonical ledger or either certificate. **No cell here replaces
any committed measurement** — E4's, Q1's and Q2's cells all stand as collected.

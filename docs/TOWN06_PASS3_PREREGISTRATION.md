# Town06 pass 3 — the wider mixed student, and selecting for margin

**Committed before any distillation, sweep or drive. Not edited afterwards.** A prediction
here that turns out wrong is the result and is reported as one.

Read `PROTOCOL.md` A-5 and findings T06-F53 / T06-F55 first.

---

## Why pass 3 exists

Two things pass 2 established, and one thing the record turned out not to establish.

**1. The mixed student is genuinely marginal under fog.** `fog/S_mixed_t06` went VOID in
both passes, under both scopes, at **two unrelated locations** — arc 55.3 m in pass 1, arc
1058.6 m in pass 2. Across both passes plus T06-F50's six diagnostic runs: **3 of 12 laps
over budget.** T06-F50's "a decision boundary at one location" is falsified; the instability
is distributed, and the honest reading is that the policy sits on its CTE budget under fog.

**2. It was selected to sit there.** `scripts/select_mixed_student_seed.sh` stops at the
**first** seed that meets its criterion, and that criterion is "every lap under budget".
`w4_s3` cleared fog at **1.78 ft against a 2.19 ft budget — 19% margin — on the fourth
draw**, seeds 0–2 having failed their first screening lap. A rule that stops at the first
passing draw cannot select for headroom, because it stops at the first student that has
none.

**3. The evidence that a wider student would not help is one coin toss (T06-F55).** The
row of numbers in `config.TOWN06_STUDENTS` and T06-F48 —

    168x28 w4  fog 6.85 ft     168x56 w4  fog 11.15 ft     168x56 w6  fog 11.64 ft

— is one distillation per cell. Six hours after the w6 checkpoint was written, this repo
committed `389f192` on a measurement where re-drawing **one unchanged configuration** swung
1.16 → 8.68 ft. That swing is 7.5 ft; the w4-vs-w6 difference is 0.49 ft. w4 has five seed
variants on disk and ships its fourth draw; **w6 has zero.** The widths were never compared.

---

## What pass 3 changes, and what it does not

**Changes — exactly two, both declared here:**

1. A **wider mixed student** is swept: `w6 = (48, 96, 96) / fc 192` — 152,832 ReLUs,
   exactly **3.0× the clear student's 50,944**, matching published Town04's ratio
   (clear 5,152 → mixed 15,456). The shipped w4 is 101,888, i.e. 2.0×.
2. The **selection criterion requires margin**, not merely a pass, and is applied
   **identically to both widths**.

**Does not change:** the teacher, the training pools, the route, the conditions, the
exposure function, `T_CLOSED_LOOP_S`, the tolerance formula, the capture protocol, the
certifier, stride 8 / nsplit 16, or any constant in PROTOCOL §3. `PROTOCOL.lock` is
untouched. Passes 1 and 2 stand in the record (R4).

**Pass 3 is not blind**, for the same reason pass 2 was not: passes 1 and 2 are known. R1
still holds literally — every certificate is committed before every scored lap — but this is
model building with prior knowledge and is never to be reported as a blind test.

---

## The pre-registered selection criterion

Fixed before the first draw, per `389f192`'s own rule that the criterion is fixed before the
sweep starts and the sweep **stops at the first seed that meets it, not the best one.**

```
SCREEN  1 lap  x 4 conditions   every lap <= 100% of budget   (2.19 ft)   — cheap filter
GATE    3 laps x 4 conditions   every lap <=  50% of budget   (1.096 ft)  — the criterion
```

50% is chosen because it is the midpoint of the budget and because it is far enough above
the D-7 render residual to be a real margin: T06-F53 measured that residual moving a fog lap
by 0.7 m, and half the 0.668 m budget is 0.334 m. It is **not** tuned to any student's
observed value.

**The shipped `w4_s3` would fail this criterion**, on two conditions: fog 1.78 ft and low
sun 1.26 ft, both above 1.096 ft. That is the point of raising it, and it is stated here so
the criterion cannot later be said to have been chosen to admit a favoured model.

Seeds are drawn in the same fixed order for both widths, from the same list, with the same
screen-then-gate protocol and the same teacher and pools.

---

## Predictions

### P1. w6 is NOT ruled out by the existing evidence

Already established by T06-F55; restated because the run tests it. If w6 fails, it fails on
a sweep rather than on one draw.

### P2. Fog is the binding condition at both widths

Fog is where every draw has failed and where the VOID cells are. Predicted: at both w4 and
w6, the condition that rejects the most seeds is fog, and the last condition to meet the 50%
criterion is fog.

### P3. The main question, and both answers are reported

**Does any seed at either width hold all four conditions at 50% of budget over three laps?**

* **If w6 finds one and w4 does not** — width was the lever, T06-F48's conclusion is wrong
  in substance as well as in method, and the mixed student ships at 3.0×.
* **If both find one** — width was not the lever; the *criterion* was. The finding is that
  Town06's mixed student was marginal because it was selected to be, and the cheap fix is
  the gate, not the architecture.
* **If neither finds one** — fog is neither a capacity problem nor a seed problem at this
  input size and pool. That is a real result and it is reported as one: the mixed student is
  fog-limited, and the study says so rather than shipping another 19%-margin student.

I decline to predict which. T06-F55 shows the only prior evidence cannot separate the
widths, and inventing a prediction where the evidence is absent is the error that finding
documents.

### P4. Verification cost rises and bounds stay usable

w6 is **152,832 ReLUs** against w4's 101,888 — **1.5×**, and exactly 3.0× the clear
student's 50,944, which is the Town04 ratio this experiment exists to restore. (An earlier
estimate in conversation said ~229k; that was wrong and is corrected here rather than
quietly.) Commit `07c7a6c` records "verification is cost, not looseness: bounds stay tight
at 3x the network". Predicted: certification time rises roughly with ReLU count — the
pass-2 capped certificate took ~15 min for both students — and the w6 bounds are **not**
materially looser relative to tolerance than w4's. If they are, that is a finding about the
criterion's scalability and is reported.

---

## Stages, and what each is allowed to see

All of stages 1–3 are model building on the training side of PROTOCOL §5, exactly as the
teacher gate, the competence gate and the existing seed sweep are: no canonical cell is
scored, nothing reaches a ledger, no certificate exists yet.

| # | stage | notes |
|---|---|---|
| 1 | Sweep w6 seeds: distil → screen → gate | same teacher, same pools, same seed order |
| 2 | Re-sweep w4 seeds under the same criterion | `w4_s0..s3` already distilled; only drives are new |
| 3 | Student DAgger on the pinned student of each width | closes the residual below |
| 4 | Capture → A-3 capture gate → certify **both** widths, blind | |
| 5 | **Commit the certificates** | R1; `check_order_town06.py` enforces it |
| 6 | Scored ledger, `TOWN06_PASS=3`, 3 laps per cell, traces on | writes `ledger_pass3/` |
| 7 | Score both scopes, compare, dispose | `score_scopes.py`, `compare_town06.py --scope` |

**The residual stage 3 closes.** The seed sweep distils on the student-DAgger pool
(`--dagger-dirs "dagger_mixed_t06lap,dagger_student_S_mixed_t06_t06lap"`), so the pinned
student *is* trained on on-policy data — but on states collected by **earlier** students in
the `r01..r05` lineage, never its own. Stage 3 collects from the pinned student's own
trajectories and re-gates. It is applied to both widths or neither.

---

## What would make pass 3 invalid

* Changing the 50% criterion after seeing any sweep result. It is fixed here.
* Sweeping more seeds for one width than the other, or in a different order.
* Running stage 3 for one width only.
* Any scored ledger cell before its certificate is committed (R1 blocks this in code).
* Reporting a stage-1/2/3 gate number as a study result. They are training telemetry.

## What pass 3 cannot settle

* It does not restore blindness; passes 1 and 2 are known.
* It does not address the `night/S_mixed` DISAGREE, which is disposed in T06-F54 and is a
  property of the certified statistic rather than of the model.
* It does not test a different input size, a different route, or a different pool.
* If fog remains binding, it does not distinguish "not enough data" from "the chord family
  cannot represent fog" — T06-F48's data diagnosis stays open either way.

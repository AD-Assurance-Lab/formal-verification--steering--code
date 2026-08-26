# PROTOCOL — Town06 deployment test (V1)

**This file wins over every other file in this repository.** Where a script, a comment,
a docstring or a conversation disagrees with it, this file is right and the other thing
is a bug. It is hash-locked (see *Locking*) and is amended only by the recorded
procedure at the bottom, never silently and never to accommodate a result.

---

## 1. What this experiment is

The Town04 study established a certification criterion. It did so with the closed-loop
outcomes **already known**: `T_CLOSED_LOOP_S = 1.85` was back-solved from the measured
stability cliff, and at its a-priori value of 1.0 s the same criterion issues *unsound
certificates* on two cells that leave the road on every run (F45). That study is
therefore a **discovery test**. Its 12/12 measures whether a criterion of this shape
exists and is sensitive; it does not measure prediction, and the paper says so.

This experiment is the **deployment test**. The criterion is now frozen. New models are
trained on a new map, the certificate is computed and **committed to version control
before the vehicle is driven**, and only then is the vehicle driven. The question is a
different one:

> Given a criterion fixed in advance, does the certificate predict closed-loop outcomes
> on models and a route it was never tuned on?

A deployment test that is quietly re-tuned is worth less than no test at all, because it
produces a prediction claim that is not one. Everything below exists to make re-tuning
impossible to do by accident and obvious if done on purpose.

---

## 2. The ordering rule

**R1.** For every cell, the certificate verdict is committed to git **before** the
closed-loop run for that cell begins. `scripts/check_order_town06.py` verifies this
against commit timestamps and fails the study if violated.

**R2.** The tool that computes held-out verdicts has no truth table and cannot print an
agreement column. A held-out cell must not be scored by the tool that predicts it.

**R3.** No closed-loop result for any Town06 canonical cell may be read, summarised or
plotted before R1 is satisfied for that cell. Training telemetry is not a closed-loop
result (see §5), but a scored ledger run is.

**R4.** If a certificate is recomputed after its closed-loop run, the recomputation is a
new cell with a new name. The original stands in the record.

---

## 3. Frozen constants

These carry over from Town04 **unchanged and unexamined**. Changing any of them
invalidates the experiment.

| Constant | Value | Why frozen |
|---|---|---|
| `T_CLOSED_LOOP_S` | `1.85` s | The one calibrated parameter. Re-fitting it on Town06 reproduces the Town04 problem and destroys the test. |
| Tolerance formula | `δ_tol = 2·L·CTE_budget / (v²·T²) / MAX_STEER` | A formula, not a number. It **must** be recomputed from Town06's measured geometry; that is not re-fitting. |
| `T_HORIZON_S` | `1.0` s | a-priori reaction horizon |
| Disturbance family | `x(s) = x_clear + s(x_cond − x_clear)`, `s ∈ [0,1]` | |
| Verification poses | 200 per direction, every 8th control-rate pose | |
| BaB sub-intervals | 16 | |
| Statistic | sustained (route-mean) bias, not peak | |
| Conditions | clear, fog, night, low sun, at the Town04 parameter values | |
| Exposure function | `CONDITION_EXPOSURE`, unchanged | |
| Speed | 20 mph / 8.9408 m/s | |
| Vehicle | `vehicle.tesla.model3` | |
| Control rate | 5 Hz (`FIXED_DT = 0.2`) | |
| Min reps | 10 per cell, Wilson intervals | |

**What is allowed to differ, and only this:** the map, the route, the trained models,
and any quantity *derived by formula* from measured Town06 geometry (lane width →
CTE budget → `δ_tol`). Town06's lane width measures 3.500 m, identical to Town04, so
`δ_tol` is in fact numerically unchanged. That is a fact about the map, not a choice.

---

## 4. Declared differences from Town04

Recorded now, before any result, so they are not discovered later and argued about.

1. **The route is straighter.** Town06's best-matching window is 74–79 % straight
   (R > 500 m) against Town04's 51–56 %. Mean curvature matches well (0.0030 / 0.0034
   vs 0.00306) but the distribution is more bimodal: longer straights, tighter curves
   (min radius 22–27 m vs 45–63 m). This is the closest match Town06's outer loop
   offers under the constraints in §6.
2. **Consequence, stated in advance:** a straighter route is easier to hold. It is
   therefore *possible* that every cell passes and every cell certifies. **If that
   happens, this experiment measures sensitivity only and not specificity**, exactly as
   the withdrawn rain condition did, and it must be reported that way rather than as a
   clean 12/12. It does not become a stronger result by being reported as one.
3. **Lane count** is 4–5 per direction against Town04's 4.
4. **Speed limit** is unavailable: Town06's outer loop carries no OpenDRIVE type-274
   landmarks, so the posted limit could not be used as a selection criterion.
5. **Street lighting matches.** Both routes are 100 % within 30 m of a street light
   (Town06 median 14–15 m, Town04 12–13 m), so the night condition is lit in both.

---

## 5. The training-leakage boundary

Training requires driving, so "certify before driving" cannot mean "never drive". The
boundary is:

- **Permitted before certification:** behaviour cloning, DAgger, and distillation runs,
  including the mixed model's runs under rendered fog / night / low sun. These are
  training, and their telemetry is never scored, plotted, or used to choose anything.
- **Forbidden before certification:** any scored ledger cell — the ≥10-repetition
  failure-rate measurement that produces a PASS/FAIL verdict.

**The leak that remains, stated honestly:** the mixed student's training does expose its
behaviour under the disturbance conditions. The clear-only student's does not — it never
sees anything but clear weather — so the cells that carry the informative failures
(`S_clear` under night and low sun) are genuinely blind. Where the leak bites is that
nobody may look at mixed-model training telemetry and use it to adjust anything. R3
covers this; the honest statement is that the clear-only cells are the strong evidence
and the mixed cells are the weaker.

---

## 6. Route selection

Selected on **map geometry alone**, before any Town06 model existed, by
`scripts/build_town06_routes.py`. Inputs permitted: curvature profile, scored length,
lane-width constancy, junction character, lane count, street-light proximity. Inputs
forbidden: anything a policy does on the route.

Chosen: Town06 outer highway loop, 2861 m window, both carriageways of the same physical
road. Cached under `pipeline/data/routes_town06/` with `route_meta.json` recording the
full selection record.

---

## 7. Pre-registered expectations

Written before any Town06 certificate or drive exists. Per standing rule 2, a result
contradicting these is a **bug until a written disposition rules out the candidate
causes** — it is not a finding until then.

| Student | clear | fog | night | low sun |
|---|---|---|---|---|
| `S_clear` | PASS / CERTIFIED | PASS / CERTIFIED | FAIL / NOT CERTIFIED | FAIL / NOT CERTIFIED |
| `S_mixed` | PASS / CERTIFIED | PASS / CERTIFIED | PASS / CERTIFIED | PASS / CERTIFIED |

`fog / S_clear` is PASS following Town04 disposition D-14 (the clear-only student is
genuinely fog-robust on open road). The `clear` verify cells are **vacuous** by
construction (zero-width box) and are excluded from every agreement count, as in Town04.

**Pre-committed reporting rule:** the outcome is published whatever it is. A result of
6/12 is the result. This clause exists because the four criteria that failed
out-of-sample in this lab (14/14 → 2/6, 7/8 → 3/7, 8/8 → 6/10, 10/10 → 2/4) were only
informative because they were reported.

---

## 8. Locking

The frozen section is hash-locked. `scripts/check_protocol_lock.py` recomputes the
SHA-256 of §3 and compares it to `PROTOCOL.lock`. Every entry point that writes a
Town06 result calls it and refuses to run on a mismatch.

## 9. Amendment procedure

1. Stop. Do not edit and continue.
2. Write the amendment as a new numbered section below, stating what changed, **why**,
   and what it invalidates.
3. Regenerate `PROTOCOL.lock`.
4. Commit the amendment and the lock together, alone, with `PROTOCOL AMENDMENT` in the
   subject line.
5. An amendment made after the corresponding result exists **invalidates that result**
   and says so in its own text.

### Amendments

*(none)*

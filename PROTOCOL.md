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

## 4a. What the certificate assumes but does not verify

The bound is on `Δ_p(s) = δ_p(s) − δ_p(0)`: the change the disturbance induces,
measured against the model's **own** clear-weather output. It never asks whether
`δ_p(0)` is any good.

Taken to its limit, a network that ignores its input and emits a constant steering
angle has `Δ_p(s) ≡ 0` and certifies perfectly under every condition, while driving
straight off the road. **The certificate cannot distinguish robustness from
indifference.** Clear-weather competence is a precondition for the certificate meaning
anything, not something the certificate establishes.

This is not hypothetical here. Distillation is exactly where it can arise: a student
without the capacity to fit its teacher's task can be uniformly wrong in a way that is
*stable* across `s`, and stability is what this criterion rewards. The teacher driving
the condition is no guarantee that its student does.

The published study half-encodes this already, in that the clear cell is driven while
its certificate is recorded as vacuous (`Δ_p ≡ 0` by construction), but the assumption
is never named. Here it is a gate:
`scripts/check_student_competence.py` drives each student over every section in clear
weather and records the result, and `certify_town06.py` REFUSES to run without that
record, or with a student that failed it.

The check is clear weather only. Clear is the `s = 0` anchor of the disturbance family,
not one of the disturbance conditions, so it reveals nothing about fog, night or low sun
and does not weaken R3.

**Residual limitation, unchanged:** competence in clear plus a bounded sustained
deviation still does not exclude a disturbance that degrades the policy in a
*zero-mean* way. That is the same failure the paper already reports as catching
failures that last and missing failures that flicker.

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

#### A-1. Explore phase 2: the blind ordering rule R1 is SUSPENDED

**Date:** 2026-08-27. **Requested by:** Zach, after the first Town06 deployment test.

**What changed.** R1 -- certificate committed before the corresponding closed-loop run --
is suspended for the work that follows this amendment. Closed-loop simulation may be run
freely, in any order, on any model, including before or without certifying it.

**Why.** The first Town06 deployment test returned 5/6 agreement, and its three
contradictions are all model-building failures rather than verification failures. The
clearest is night: the mixed student was TRAINED on night and fails it 9/12, while its
teacher passes all 24 teacher-gate cells. The certificate AGREED with that failure, so
verification did its job -- but the criterion is designed to bound the effect of a
DISTURBANCE on a competent policy, and it is not designed to detect a policy that was
built wrong. Testing a criterion for disturbance sensitivity against a model that cannot
drive measures the wrong thing. The blind constraint exists to stop verdicts being tuned
to known outcomes; while the object under study is the TRAINING PIPELINE rather than the
criterion, it costs iteration speed and protects nothing.

**What it invalidates.** Nothing already recorded. The Town06 deployment test
(certificate e0a461f, result T06-F16) was completed under R1 in full and stands as a
blind result. This amendment applies only to work done after it.

**What it does NOT relax.** Standing rule 3 still holds: every closed-loop number is a
rate over at least 10 repetitions, never a single run. Section 3's frozen constants are
untouched -- the criterion, the tolerance, the stride and the BaB split are unchanged, so
a later blind test remains comparable to this one and to the published Town04 study.

**Re-entry condition.** R1 resumes when a mixed student drives every condition, and any
future blind claim must be produced under a fresh certificate committed before its drives.
NO result produced while this amendment is in force may be presented as a blind
prediction, in the paper or anywhere else. Results from this phase are exploratory by
construction and must be labelled as such.

#### A-2. The harness was wrong; all Town06 driven data is recollected from step 0

**Date:** 2026-08-28. **Requested by:** Zach, after T06-F22.

**What changed.** Every Town06 artifact that was produced by DRIVING is discarded and
recollected: base datasets, DAgger datasets, both teachers, both students, the oracle
validation and the lap captures. Nothing that was driven under the old harness is reused.

**Why.** Two defects in the simulator harness, measured open loop with the feedback cut
(T06-F22, and the `carla-determinism` package's RULES.md D-1..D-11):

1. `vehicle.apply_control()` is fire-and-forget and races `world.tick()`. Synchronous
   mode synchronises the tick, not the command queue feeding it. Three repetitions of
   one identical scripted command sequence finished 60 m apart.
2. UE4 streams texture mips asynchronously, so mip residency depends on load timing
   rather than on world state. `-notexturestreaming` cut the steering noise the renderer
   injects by 168x.

The second is what forces recollection rather than merely re-evaluation. Training frames
captured with texture streaming on carry mip variation that a corrected evaluation never
shows, which is a train/test distribution shift in the images themselves. The first means
the trajectories those frames were sampled along are not the trajectories the corrected
harness produces.

**What is NOT affected, and why it survives.** The route and its six sections were chosen
on map geometry alone, before any Town06 model existed and without driving anything
(section 6); fingerprint `706db50636cbd6c9` is unchanged and the pipeline's route guard
still enforces it. **Section 3's frozen constants are untouched** — the criterion, the
tolerance, the stride and the BaB split are unchanged, so `PROTOCOL.lock` is still valid
and a Town06 result stays comparable to the published Town04 study. What changed is the
instrument, not the measurement being made.

**What it invalidates.** Every Town06 closed-loop number and every Town06 checkpoint
produced before this date, including T06-F14's student-DAgger comparison and the
competence-gate results that motivated the capacity question in `TOWN06_STATUS.md`. That
capacity question is **re-opened, not answered**: it was asked of students trained on data
this amendment discards, so it must be re-asked of the rebuilt ones rather than carried
over.

**What it does NOT relax.** Standing rule 3 still holds and is now measured rather than
assumed: bit-exact closed-loop replay is unreachable (D-7), so every closed-loop number
remains a rate over at least 10 repetitions. A-1's suspension of R1 is unchanged and its
re-entry condition is unchanged.

**Re-derivation required before the rebuild is trusted.** The low-sun angle for Town06
(5 degrees, T06-F20) was chosen from rendered brightness measured on lap captures taken
under the old harness. It must be re-measured under the corrected one before the mixed
policy is collected; if it moves, the condition definition moves with it and this
amendment gains a clause.

**Re-derivation RESULT, 2026-08-28: 5 degrees HOLDS; no clause needed.** Measured under
the corrected harness at all six section spawns (`scripts/verify_conditions_render.py
--sections all`), on the network's own input:

| | Town06, corrected harness | Town04 published | verdict |
|---|---|---|---|
| low sun, mean brightness | 0.1204 | 0.1117 | 7.8% away; T06-F20 accepted 9% |
| night − low sun gap | 0.0921 | 0.0958 | axis stays ordered |
| low sun, per-section CV | 2.65% | — | was 3.29% under the old harness |

All four conditions also still classify as themselves under
`condition_signature.identify()`, with margin on every discriminator: night's sigma
0.1422 against a 0.100 threshold and 0.065 for the rest; fog's p01 0.1614 against 0.120
and at most 0.044 for the rest; clear's mean 0.2983 against 0.250 with low sun at 0.1204.
That check matters because `evaluate.py` RAISES on a condition mismatch, so a threshold
crossing would have aborted every run of the affected condition part-way through the
unattended rebuild rather than at its start.


#### A-3. The capture gate is a precondition of certification

**Date:** 2026-08-30. **Requested by:** Zach.

**What changed.** Section 4a names one precondition the certificate assumes but does not
verify -- clear-weather competence -- and enforces it in code. There is a second, and the
paper states it as though it were already enforced:

> Before any certificate is computed we require captured steering to match the steering
> the vehicle actually commanded at the same locations. [...] This check is cheap and it
> is not optional.

**It was not enforced anywhere.** No script computed it, on either map, and neither
rebuild ran it. The number quoted in the paper (0.0137 over 1,600 poses) comes from the
published era. It is now `scripts/capture_driven_gate.py`, it must pass before a
certificate is computed, and `scripts/audit_repo.py` fails when a certificate exists with
no gate artifact beside it.

**Why it is a precondition and not a diagnostic.** The bound is computed offline on
captured frames; the claim is about a driving vehicle. If the capture rig and the driving
rig differ -- ride height, pitch, field of view -- the bound is sound and describes a
camera that is not on the car. That is not hypothetical: a ride-height error made one
direction's captures disagree at 0.202 while the other passed at 0.016, purely because
its opening stretch happens to be flat. No verdict, interval or agreement rate can reveal
it, because every one of them is computed downstream of the frames.

**What it invalidates.** Section 9.5 says an amendment made after the corresponding result
exists invalidates that result. Applied honestly:

  * The certificate **superseded** on 2026-08-30 (`results/town06/_superseded_20260830_1731/`)
    was computed with no gate artifact and does **not** satisfy this amendment. It is
    already withdrawn and replaced; this records why it could not simply be reinstated.
  * The **current** Town06 certificate does satisfy it. The rebuild ran
    captures -> gate -> certificate -> commit -> drives, so the gate preceded
    certification rather than following it: worst mean |capture - driven| **0.0261**
    against the 0.05 threshold, 12/12 cells
    (`results/town06/captures/capture_gate.json`).
  * Town04 (discovery test) likewise: worst **0.0065**, gated by
    `scripts/certify_town04.sh` before its certifier runs.

So no current result is invalidated. That is a fact about the rebuild, not a convenience
-- had the amendment been adopted a day earlier it would have withdrawn the then-current
Town06 certificate, and the correct response would have been to rebuild, which is what
happened anyway.

**What it does NOT change.** No frozen constant in section 3, so `PROTOCOL.lock` is
unchanged. R1, R2 and R3 are untouched. The gate is deterministic given fixed artifacts
and has nothing to tune, so it cannot launder a verdict.


#### A-4. The LAP is the repetition, and three laps is the standard

**Date:** 2026-08-31. **Requested by:** Zach.

**What changed.** Section 3 treated SECTIONS as repetitions -- "6 sections x 2 reps = 12
runs per cell, over the >= 10 floor". A section is a distinct stretch of road, so twelve
runs were never twelve trials of one experiment; they were six different roads sampled
twice. A failure rate over them pooled unlike units, and it read misleadingly: two cells
reported 2/12 = 17% when in fact the SAME section failed in BOTH passes -- a 100% failure
of every attempt, diluted by five sections that were never in question.

A **lap** is one traversal of all the unique scored road. Town04's lap is eastbound +
westbound. Town06's is the loop. **The lap is the repetition, and the lap is what passes
or fails: a lap fails if any scored span departs.** Per-span outcomes are still reported,
because that is where the diagnostic value is.

**Three laps, not ten.** Standing rule 3's ">= 10 repetitions" was measured on the BROKEN
harness, where "CARLA pass/fail varies run-to-run near the cliff" and single runs were
wrong about one time in eight. That premise no longer holds. Measured on the corrected
harness, with a clean server restart and a fresh vehicle for every run:

    rep0 vs rep1 verdict disagreement: 0 of 48 section-pairs (0.0%)

Three laps is therefore a REPRODUCIBILITY CHECK, not a sample for estimating a rate. Its
purpose is to catch a bug, not to measure a probability.

**Conditional on the harness, and the condition is not optional.** Three laps is
defensible only while every one of these holds: a clean server restart before every run; a
fresh vehicle and camera per run; one process per run; the determinism preflight green on
each fresh server (D-1..D-6); one client per port; and the capture gate (A-3) passed
before certification. If one of them is not being enforced, the answer is to enforce it --
**not to compensate with more laps.** A larger sample taken through a harness known to be
wrong measures the harness, and it has the shape of a result, which is worse than having
no number at all.

**Margin is reported with every verdict.** A cell that passes with every span far below
budget and a cell that passes at 1% of budget are different results, and a pass/fail bit
does not distinguish them. **A cell with no margin is a finding in its own right** --
`clear/S_clear_t06` came within 1.0% of the budget in the condition that is supposed to be
its competence precondition -- and adding laps would only characterise a coin flip more
precisely rather than change that conclusion.

**If the three laps disagree, that is a BUG until proven otherwise, and more laps are
never the response.** Under an enforced harness the laps agree -- measured, 0 of 48
section-pairs disagreed. Disagreement therefore means the setup is wrong, and the correct
action is to find what is wrong and fix it. Running ten laps instead would convert an
identified defect into a plausible-looking failure rate and lose it: the number would be
reported, believed, and wrong. **A cell whose laps disagree is void, not uncertain**, and
it stays void until the cause is found and written down (standing rule 2).

**Corrected the same day it was written.** The first version of this amendment said
additional laps could serve as "a diagnostic for an identified instability" and that
relaxing the harness "returns the count to ten". Zach rejected both: there is no fallback
to ten. Recorded rather than silently edited, because an amendment that quietly changes
what it required is the failure this procedure exists to prevent.

**What it invalidates.** Every ledger cell scored as "runs" rather than laps is
re-aggregated at lap granularity. No drive is re-run: the underlying per-run artifacts are
unchanged and already carry a fresh server and vehicle each. Cells written before the
process-per-run change do not satisfy this amendment and are superseded.

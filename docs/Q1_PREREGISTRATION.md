# Q1 — the learning-rate effect at n=15: pre-registration

**Written 2026-09-05, before any Q1 distillation or lap.** Driver `scripts/arm_sweep.sh`,
output `results/town06/lr_confirm/`. Queue item `docs/EXPERIMENT_QUEUE.md` §Q1.

## The question

> Does changing only the distillation learning rate from `1e-3` to `3e-4` improve fog
> driving on the shipped architecture, at enough seeds to publish?

## Why this is the blocker

E4-F1 measured the fog median moving **11.79 → 1.91 ft** from the learning rate alone —
same architecture, same data, same teacher, same pinned kernels, same seeds — with seeds
holding fog 3/3 going 1/5 → 3/6 and one seed driving fog at **0.98 ft**, the first student
in this study to clear pass 3's own 1.095 ft margin gate on fog.

At six seeds that is **Mann-Whitney p = 0.247**. It is a 6x shift in median with the
direction consistent in five of six seeds, and it is not significant, because one arm
contains a 37.65 ft departure and the dispersion is enormous (E2R-F5 quantified the same
power problem).

Two things in the write-up depend on the answer:

1. **Pass 3's attribution.** All 16 pass-3 students were distilled at `lr=1e-3`, which no
   experiment in this study ever varied. If the effect is real, pass 3 cannot attribute
   the fog failure to the architecture, and `docs/OVERALL_STATUS.md` §3.3 already records
   that as confounded.
2. **A Limitations sentence.** "The obstruction is distillation rather than verification"
   is either considerably sharper or considerably weaker depending on this result.

**Nothing else in the study should be published until this resolves.** That is why Q1 runs
first.

## Declared design — fixed before running

| arm | stack | channels / fc | lr | ReLU |
|---|---|---|---|---|
| `lr1e3` | 3 conv (5x5 s2, 5x5 s2, 3x3 s2) | (32,64,64) / 128 | **1e-3** | 101,888 |
| `lr3e4` | identical | (32,64,64) / 128 | **3e-4** | 101,888 |

Architecture, teacher (`teacher_mixed_t06lap_dagger_r03`), base (`mixed_t06lap`), DAgger
dirs, input size 168x56, epochs, patience and data are **identical between arms**. The
learning rate is the only variable that moves.

* **Seeds 0–14, n = 15 per arm.** Seeds 6–14 are new; seeds 0–5 are folded in (below).
* **Conditions fog and clear.** Clear is the control — a recipe that fixes fog by breaking
  clear is not a fix.
* **3 laps per cell**, kernels pinned (`DISTILL_DETERMINISTIC=1`), so the comparison is
  paired by seed and free of the run-to-run noise E2-F6 measured at the size of the effect.
* Restart before every lap; `exit 3` aborts rather than scoring; no promotion, no
  `.selected` pin.

**Two arms only.** A third arm at `lr=1e-4` was considered and declined: the blocking
question is whether `3e-4` beats the shipped `1e-3`, and a dose-response curve is not
needed to answer it. `d3@1e-4` reached val KD-MSE 1.229e-3 against `3e-4`'s 1.183e-3 at
seed 0 (E4 A-2 grid), so the optimum is already bracketed.

### The fold-in, and how it is validated before it is used

Seeds 0–5 already exist for both arms and the queue says to fold them in rather than
re-drive them:

* `lr3e4` seeds 0–5 = `S_mixed_depth_d3lr3_s*` in `results/town06/depth/`.
* `lr1e3` seeds 0–5 = `S_mixed_tail_a0p0_s*` in `results/town06/tail_loss_det/`. E2's
  alpha 0.0 arm: `DISTILL_TAIL_ALPHA=0` leaves the objective **bit-identical** to the
  default and no `--lr` was passed, so it is the shipped recipe at the default `1e-3`.

**That claim is checked, not asserted.** Before any fold-in number is used, seed 0 of each
arm is re-distilled under the Q1 arm definition and compared **bit-exactly** (SHA-256 of
the state dict) against the existing checkpoint. Distillation is bit-exact under pinned
kernels, so this is decisive: if the hashes match, the existing seeds were trained by the
identical recipe and are poolable. **If either hash differs, that arm's seeds 0–5 are
discarded and the arm runs seeds 0–14 fresh.** Recorded either way in the findings.

## Declared analysis — fixed before running

**Primary endpoint.** Per seed, the **worst-of-3 max|CTE| in fog**, in feet. Budget
2.19 ft; pass-3 margin gate 1.095 ft.

**Primary test.** Two-sided Mann-Whitney U on the 15 vs 15 fog endpoints, alpha = 0.05.
Reported with the **Hodges-Lehmann median shift and its 95% interval** — E2R-F5 says the
power here is moderate at best, so the effect size and interval are the result and the
p-value is an accompaniment, not the headline.

**Secondary endpoints**, all declared now:

1. Seeds holding fog 3/3 under the 2.19 ft budget, per arm — Fisher exact.
2. Seeds clearing the 1.095 ft pass-3 margin gate on fog, per arm — Fisher exact.
3. Fog KD p99 median per arm (no simulator; measured by `kd_error_by_condition.py`).
4. Clear worst-of-3 max|CTE| median per arm — the control.

**Sensitivity analysis.** The primary test is repeated on **seeds 6–14 only** (n = 9 vs 9),
which are entirely new and collected under one harness in one sweep. If the pooled and
new-seeds-only results disagree in direction or in significance, the new-seeds-only result
is the one reported, and the disagreement is itself a finding about the fold-in.

**VOID cells.** A cell whose 3 laps disagree by more than 25% is VOID (standing rule 3): it
is **excluded, never averaged, and never replaced by more laps**. VOID counts are reported
per arm. E4 saw 1/6 VOID in `lr1e3` fog and 2/6 in `lr1e3` clear against 0/6 in `lr3e4`, so
**a materially different VOID rate between arms is a declared secondary outcome in its own
right** — an arm that is unmeasurable more often is worse, and burying that in an exclusion
would hide it.

## Predictions — written before any Q1 run

**Q1-F1 — the effect survives.** `lr3e4`'s fog median over 15 seeds is at least **3x lower**
than `lr1e3`'s. Reason: the direction held in five of six seeds at E4, and the mechanism
(a 43% lower validation KD error on the same architecture) is measured, not inferred.

**Q1-F2 — it reaches significance.** Mann-Whitney p < 0.05 on 15 vs 15. This is the weakest
of the predictions: E2R-F5's dispersion estimate puts power near the boundary, and a single
large departure in either arm can carry the test. **If F2 fails while F1 holds, the reported
answer is the effect size and interval, and the queue's other items are unaffected** — the
Limitations sentence then says the recipe is implicated but not confirmed.

**Q1-F3 — more seeds hold fog.** `lr3e4` has at least **twice** as many seeds holding fog
3/3 under budget as `lr1e3`, and at least **3 of 15** clear the 1.095 ft margin gate. This
is what gates Q2 — Q2 needs candidates, and a recipe producing none makes Q2 unrunnable.

**Q1-F4 — clear does not regress.** `lr3e4`'s clear median is within 25% of `lr1e3`'s. A
fog fix that costs clear is not a fix, and E4 saw 6/6 clear held at `3e-4`.

**Q1-F5 — the seed still dominates.** Within-arm fog spread exceeds the between-arm
difference in medians, as in E1 (26.6x), E2 (14.69 vs 5.53 ft) and E4. **If F5 fails —
if the arms separate cleanly with little overlap — that is a bigger result than F1**, and
it would say the dispersion Q6 is chartered to explain is largely a learning-rate artifact.

## What counts as an answer

* **F1 and F2 hold:** the recipe is confirmed as the dominant lever, pass 3's attribution
  is formally retracted rather than merely flagged, and Q2/Q3 run on tuned students.
* **F1 holds, F2 fails:** report the interval; the Limitations sentence softens rather than
  reverses; the queue proceeds unchanged.
* **F1 fails** — the effect does not survive more seeds — is the **fourth** single-draw
  claim in this study to die under a sweep, it exonerates pass 3, and it is reported
  immediately and separately rather than folded into a summary.

## Bound by

`PROTOCOL.md`, `CLAUDE.md` R-SIM-1..6, and standing rules 1, 3, 7 and 8. Committed before
the first scored lap; ordering checkable with `python -m study.ledger --check-order`.
Nothing here writes to `results/town06/ledger`, `ledger_pass2`, either certificate, or any
`.selected` pin.

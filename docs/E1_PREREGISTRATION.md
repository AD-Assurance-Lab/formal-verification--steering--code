# E1 — input-resolution ablation on fog: pre-registration

**Written 2026-09-03, before the sweep, on the new desktop.** Template and rationale:
`docs/TOWN06_PASS3_PREREGISTRATION.md`, which is what made pass 3 interpretable.
Driver: `scripts/e1_resolution_ablation.sh`. Nothing here gates the paper — the frozen
scope is `docs/PAPER_HANDOFF.md`.

## The question

> Does fog robustness decrease monotonically with student input resolution, and does
> straight-line accuracy move the other way?

Motivation is `docs/NEXT_EXPERIMENTS.md` E1. The three numbers the repo currently carries
are **one draw each** (T06-F48), which is exactly the flaw that made the w6 width
refutation worthless (T06-F55) and that `389f192` demonstrated by swinging an unchanged
configuration from 1.16 to 8.68 ft.

## Declared set — fixed before running

| axis | values |
|---|---|
| input size | 84x28, 168x28, 168x56, 252x84 |
| ReLU count (32,64,64 / fc128) | 20,608 / 42,816 / 101,888 / 242,816 |
| seeds | 0, 1, 2, 3, 4, 5 |
| conditions | fog (the question), clear (the straights) |
| laps per cell | 3 (standing rule 3) |
| width | w4 = (32,64,64) / fc 128, **held fixed** to isolate resolution |
| teacher | `teacher_mixed_t06lap_dagger_r03` (drives Town06 fog at 0.37–0.40 ft, T06-F29) |
| budget | 2.19 ft |

168x56 reuses the already-distilled pass-3 w4 seeds, so the middle point of the ablation
IS the measured study point rather than a re-draw of it.

## What I have already seen, before writing these predictions

Honesty about ordering matters more than a clean story. Two cells were run as smoke tests
to prove the path worked on the new machine, and I saw both:

* `84x28 s0`, distilled: val KD-RMSE 0.0372.
* `84x28 s0`, **fog, 1 lap: 6.37 ft** — 291% of budget, FAIL, 1181/1280 steps.

So the lowest-resolution point is already known not to be trivially fog-robust at seed 0.
The predictions below are written with that knowledge and say so.

## Predictions

**P1 — the monotone-resolution hypothesis is FALSE as stated.** Best-of-6-seeds fog
max|CTE| will *not* be ordered 84x28 < 168x28 < 168x56 < 252x84. Specifically I predict
84x28's best-of-6 fog will exceed 2.19 ft, so the Town04 disposition D-14 result
("84x28 is fog-robust") will **not** transfer to Town06's route.

Reason: D-14 was measured on Town04's highway ODD against a different teacher and a
different route. The one Town06 cell I have seen at that size is 6.37 ft.

**P2 — fog is lost at every resolution.** No (resolution, seed) cell will hold fog 3/3
under 2.19 ft. This follows pass 3: 16 students over two widths and eight seeds, none
passed, and fog stopped every one. If P2 is wrong — if some resolution recovers fog —
that is the most interesting outcome available here and it directly answers the study's
open question.

**P3 — the straights get worse as resolution drops.** Clear-condition max|CTE| at 84x28
will be worse than at 168x56, consistent with T06-F11 (at 84 px the whole 0.668 m CTE
budget spans 1.79 px of image shift at 20 m lookahead).

**P4 — seed spread will be large enough to have made any single draw uninterpretable.**
Within at least one resolution, the best and worst seed's fog max|CTE| will differ by
more than 2x. This is the claim that retroactively justifies re-measuring T06-F48, and it
is falsifiable: if spread is small, single draws were fine and the repo's caution was
overheld.

## What counts as an answer

* Best- and worst-of-6 fog max|CTE| per resolution, with all 6 seeds reported, never just
  the best. Clear-condition max|CTE| beside it.
* A monotone trend in fog across all four sizes, in either direction, is a real finding.
* **If fog improves at low resolution while clear degrades**, the trade-off is real, and
  the honest conclusion is that no resolution satisfies both on this ODD — itself a clean
  publishable statement about the ODD rather than about the model.
* **A cell whose 3 laps disagree is VOID, not uncertain** (standing rule 3), and stays
  void until the cause is found. It is not evidence of a failure rate and will not be
  averaged into one.

## Rules this run is bound by

1. Restart before every lap — `compare_student_variants.py` does it and checks the exit
   status (A-4 / R-SIM-1).
2. An unmeasured lap is not a failing lap: driver exit 3 aborts the whole sweep rather
   than scoring the model for a harness failure.
3. No `.selected` pin is written and no checkpoint is promoted, so the models the
   committed Town06 results resolve through cannot move.
4. Everything lands under `results/town06/res_ablation/`; pass 1, pass 2 and both
   certificates are untouched.
5. Report what happened, including where it contradicts P1–P4.

## Caveat recorded in advance

A new input size needs **its own captures** before it can be *certified* — the capture rig
projects to the model input at capture time. This sweep is closed-loop driving only, which
`evaluate.py` supports directly via `--in-w/--in-h`. No certificate is claimed for any new
resolution, and none will be until a recapture exists.

# E4 — depth at matched ReLU count: pre-registration

**Written 2026-09-04, before any E4 distillation or lap.** Driver `scripts/arm_sweep.sh`.

## The question

> Is the student's 3-conv-layer stack the limitation, rather than its width?

Pass 3 varied width across 16 students and eliminated it. **Depth has never been varied in
this study, on either map** — `StudentNet` has been `conv 5x5 s2 -> 5x5 s2 -> 3x3 s2`
throughout. The teacher has five conv layers and drives Town06 fog at 0.37–0.40 ft.

## The tension that makes this worth running

The verifier prefers shallow-and-wide: each layer compounds α-CROWN's relaxation
looseness, so a deeper student should certify *worse* at the same neuron count. **If fog
needs depth, then verifiability constrained the architecture in a way that caused the
failure** — a considerably more interesting result than "the model was too small", and
directly on the paper's thesis.

That is why this experiment reports **certified bound width alongside the driving result**,
not just pass/fail.

## Declared set — fixed before running

| arm | conv stack | channels / fc | ReLU |
|---|---|---|---|
| `d3` | 5x5 s2, 5x5 s2, 3x3 s2 | (32,64,64) / 128 | **101,888** |
| `d5` | 5x5 s2, 5x5 s2, 3x3 s2, 3x3 s1, 3x3 s1 | (32,64,48,24,20) / 128 | **101,892** |

Matched to **4 neurons (0.004%)**. 56 px of input height is too short for five stride-2
layers, so the two added layers are stride 1 — which is also what the PilotNet teacher
does. Seeds 0–5, fog and clear, 3 laps, **kernels pinned** so the comparison is paired.

`d3` is the shared baseline already being driven as E2's alpha 0.0 deterministic arm — the
same checkpoints, conditions and lap protocol — so only `d5` needs new runs.

**Certification uses the committed 168x56 captures.** Depth does not change the input size,
so no recapture is needed and both arms are certifiable against the same frames.

## Predictions

**F1 — depth does not rescue fog.** `d5`'s best-of-6 fog max|CTE| will not beat `d3`'s by
more than 25%, and the number of seeds holding fog 3/3 will not increase by more than 1.
Reason: E1 and E2 both measured the draw dominating every architectural lever tried so far,
and pass 3 eliminated width across 16 students.

**F2 — depth costs verification, measurably.** At matched ReLU count, `d5`'s certified
bound will be **wider** than `d3`'s on the same condition and captures, in at least 2 of
the 3 conditions. This is the prediction the paper's thesis rests on and it is the reason
to run E4 even if F1 holds.

**F3 — clear is unaffected.** Best-of-6 clear max|CTE| differs by less than 25% between
arms. Neither stack should struggle on clear; both hold it comfortably today.

**F4 — the seed still dominates.** Within-arm seed spread in fog exceeds the between-arm
difference in medians, as in E1 (26.6x) and E2 (14.69 ft vs 5.53 ft).

## What counts as an answer

* F1 false — depth *does* rescue fog — is the single most important outcome available in
  the remaining queue, and it would mean the architecture was constrained by the verifier
  into the failure. Report it immediately and do not fold it into a summary.
* F1 true and F2 true: depth is not the missing ingredient, and it would have cost
  verification anyway. That closes the architecture line cleanly.
* F2 false — a deeper net certifying no worse — is a useful negative about α-CROWN on this
  family, and worth reporting on its own.

## Bound by

Restart before every lap; exit 3 aborts rather than scoring the model; no promotion, no
`.selected` pin; output under `results/town06/depth/`; certification writes with `--out` to
that directory and never to the committed certificate; VOID cells (>25% lap disagreement)
excluded, not averaged.

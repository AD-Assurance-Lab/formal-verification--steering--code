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

---

# AMENDMENT A-1 — the depth-5 arm was a bottleneck experiment, not a depth experiment

**Recorded 2026-09-04, after one seed and before any E4 conclusion.** One `d5` checkpoint
had been distilled and one fog cell driven; both are discarded and the arm is redefined.

## What went wrong

The declared `d5` stack was `5x5 s2, 5x5 s2, 3x3 s2, 3x3 s1, 3x3 s1` with channels
`(32,64,48,24,20)` — matched to `d3` on **ReLU count** (101,892 against 101,888, 4 neurons
apart). It was not matched on anything else, and the third stride-2 layer leaves a final
feature map of **1x15**:

```
  d3  (32,64,64)        101,888 ReLU   final map 5x19   flatten 6,080
  d5  (32,64,48,24,20)  101,892 ReLU   final map 1x15   flatten   300     <- 20x smaller
```

The student's fully-connected head therefore saw **300 features instead of 6,080**. It
trained about four times worse (val KD RMSE 0.0909 against ~0.03; fog p99 0.5566 against
0.1773) and its first fog lap departed after 24 steps.

**That is a representation-size result wearing a depth label.** Reporting it as "depth does
not help" would have been wrong in exactly the way this study keeps catching elsewhere —
one variable named, two variables moved.

## The corrected arm

Only the first two convolutions are strided, so the map stays large:

```
  d5  (32,32,24,24,36)  strides 2,2,1,1,1   101,892 ReLU  final map 5x33  flatten 5,940
```

Matched to `d3` on **ReLU count to 0.004%** and on **flatten dimension to 2.3%**. Depth is
now the variable that moves; width, neuron count and representation size are held.

## Predictions

F1–F4 are unchanged and were not written with any knowledge of the corrected arm's
behaviour — no corrected-arm student had been distilled when this amendment was recorded.

The discarded arm is not reported as a finding. It is one seed of a configuration that was
never the intended comparison, and its only value is this amendment.

---

# AMENDMENT A-2 — the study's learning rate does not fit a deeper student

**Recorded 2026-09-04, after the corrected `d5` arm's first seed and before any E4
conclusion.** The corrected arm still failed, and for a different reason.

## What was measured

The corrected `d5` (matched on ReLU count AND flatten dimension) did not train at all under
the study's fixed recipe: best validation at **epoch 0**, val KD-MSE flat at 8.26e-3, while
`d3` descends 7.49 → 6.26 → 5.25 → 4.66e-3 over its first four epochs.

That is an optimisation failure, not an architectural result. `distill.py` has used
`lr=1e-3` for every student in this study, and it is tuned to the 3-conv stack. Sweeping a
declared grid at seed 0, selecting on **validation KD-MSE** (never on fog or on any driving
outcome):

```
                 lr 1e-3     lr 3e-4     lr 1e-4
  d3 (3 conv)   2.080e-3    1.183e-3    1.229e-3     <- best at 3e-4
  d5 (5 conv)   8.259e-3    2.121e-3    1.619e-3     <- best at 1e-4, and does not train at 1e-3
```

**Two things follow, and the second is more important than E4.**

1. `d5` trains fine at 1e-4 and reaches **1.619e-3**, better than `d3` at the study's own
   learning rate. Comparing depth at a single shared learning rate would have measured the
   learning rate.
2. **`d3` at 3e-4 reaches 1.183e-3 against 2.080e-3 at the shipped 1e-3 — a 43% lower
   validation KD error on the shipped architecture.** Every student in this study, on both
   maps, was distilled at 1e-3. That is a property of the recipe, not of the architecture,
   and nothing in the study has ever varied it.

## Revised design

Three arms, learning rate selected per arm from the declared grid by validation KD-MSE:

| arm | stack | lr | what it isolates |
|---|---|---|---|
| `d3@1e-3` | 3 conv (32,64,64) | 1e-3 | the shipped recipe (already measured as E2's alpha 0.0 arm) |
| `d3@3e-4` | 3 conv (32,64,64) | 3e-4 | **the recipe alone** — same architecture |
| `d5@1e-4` | 5 conv (32,32,24,24,36) | 1e-4 | **depth**, each arm at its own best recipe |

Seeds 0–5, fog and clear, 3 laps, kernels pinned.

## Added prediction

**F5 — the learning rate matters more than the depth.** `d3@3e-4` will beat `d3@1e-3` on
fog by more than `d5@1e-4` beats `d3@3e-4`. If F5 holds, the study's fog failure is
entangled with an untuned distillation recipe, and "the obstruction is distillation rather
than verification" becomes considerably more pointed than the paper currently states.

F1–F4 are unchanged. No driving result from either new arm existed when this was recorded.

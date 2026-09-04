# E6 — label balancing, re-tested by a method the refutation does not cover

**Written 2026-09-04, before any E6 distillation or lap.** Driver `scripts/arm_sweep.sh`.

## The question

> Does the steering-label imbalance matter, when addressed by a method whose own
> refutation does not cover it?

`distill.py --balance` exists, is **off by default, and no driver anywhere passes it** — so
every certified Town06 student trained on the raw label distribution, on a route where
**83.8% of frames need |steer| <= 0.01**. The E2E literature treats this as a standard
failure mode.

The refutation in `config.TOWN06_STUDENTS` (`c1e5dfd`) predates the seed sweep by a week,
was measured on the **superseded six-section route**, and refutes only *downsampling*. Its
argument — "on a route that genuinely IS 84% straight, downsampling straight frames trains
the student for a distribution it will not meet" — is sound, and **does not apply to loss
weighting**, which leaves the input distribution untouched and changes only each frame's
gradient contribution.

## Declared set — fixed before running

| arm | method | knob |
|---|---|---|
| `raw` | plain MSE on the raw distribution | (the shared baseline) |
| `bal` | downsample straight frames — **the refuted arm, re-tested honestly** | `--balance` |
| `curv` | curvature-weighted loss — the arm the refutation does not cover | `DISTILL_CURV_BETA=4.0` |

`curv` scales each frame's squared error by `1 + 4.0 * |steer| / mean|steer|`, with the
scale fixed over the whole training set so an all-straight batch cannot rescale the
objective. 168x56 w4, seeds 0–5, fog and clear, 3 laps, **kernels pinned** so the
comparison is paired. `raw` is E2's alpha 0.0 deterministic arm — same checkpoints, same
protocol — so only `bal` and `curv` need new runs.

## Predictions

**G1 — `bal` does not improve fog.** Its refutation's argument is sound and I expect it to
hold: best-of-6 fog will not beat `raw` by more than 25%. Re-testing it is about honesty,
not expectation — it was refuted on a route that no longer exists.

**G2 — `curv` does not improve fog either, but by less of a margin than `bal`.** I expect
reweighting to be the better of the two interventions and still not enough. Concretely:
`curv`'s best-of-6 fog will be no worse than `bal`'s.

**G3 — `bal` degrades clear.** Downsampling straight frames trains for a distribution the
route does not present, and clear is where straight-line accuracy shows. `bal`'s best-of-6
clear will be worse than `raw`'s.

**G4 — the seed still dominates**, as in E1, E2 and (predicted) E4.

## Why run it if I expect all three to fail

Because `--balance` sits in the codebase unused and unmeasured on the current route, and
"we never tried it" is not a finding. E1 has already shown twice that this repo's
single-draw dismissals do not survive a sweep. If `curv` *does* move fog, it is the first
intervention in the study that has, and it directly answers the open question.

## Bound by

The same rules as E4: restart before every lap, exit 3 aborts, no promotion, no
`.selected` pin, output under `results/town06/balancing/`, VOID cells excluded rather than
averaged.

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

---

# AMENDMENT A-1 — run the arms at the tuned learning rate, not the shipped one

**Recorded 2026-09-04, before any E6 distillation.** Follows `docs/E4_FINDINGS.md`.

E4 measured that `lr=3e-4` moves this architecture's fog median from 11.79 ft to 1.91 ft
and its validation KD error from 2.080e-3 to 1.183e-3, changing nothing else. The shipped
`lr=1e-3` is not the recipe anyone should use going forward.

Running E6 against a `1e-3` baseline would therefore answer "does balancing rescue a
recipe we already know is misconfigured" — a question nobody needs. All three arms move to
**`--lr 3e-4`**, and the `raw` baseline becomes **E4's `d3lr3` arm**, which is already
measured at six seeds under identical conditions, kernels and lap protocol.

| arm | method | lr |
|---|---|---|
| `raw` | plain MSE (E4's `d3lr3`, already measured) | 3e-4 |
| `bal` | `--balance` downsampling — the refuted arm | 3e-4 |
| `curv` | `DISTILL_CURV_BETA=4.0` reweighting | 3e-4 |

**Predictions G1–G4 are unchanged in substance**, and are now read against the tuned
baseline: `raw` fog median 1.91 ft, 3/6 seeds holding, clear 6/6.

One prediction is added.

**G5 — balancing matters less on the better recipe, not more.** Whatever gap `bal` or
`curv` shows against `raw` will be smaller than the 9.88 ft the learning rate moved. If
that is wrong — if a label-weighting change outperforms the learning-rate change — then the
imbalance is a first-order problem after all and the study's framing needs revisiting.

# Archive — retired approaches, kept as evidence

Nothing here is needed to reproduce the result. It is kept because the paper makes
**negative** claims, and a negative claim whose code has been deleted cannot be checked.
If you are trying to run the study, you want the top-level `scripts/` and can ignore this
directory entirely.

Each file below is retired for a *measured* reason, not a stylistic one. The finding that
retired it is named so you can read the evidence rather than take this on trust.

> **These files are not maintained.** Several hardcode absolute paths from the original
> machine and will not run unmodified. They are here to be read.

## Trajectory-level propagation — the two days that solved the wrong problem

`certify_invariant.py`, `certify_maximal_invariant.py`, `certify_lap_invariant.py`,
`certify_grid_tube.py`, `certify_interval.py`, `certify_closed_loop.py`,
`certify_trajectory.py`

Interval tubes, zonotope tubes, box grids and inductive invariants, all built to bound the
vehicle state rather than the steering output. Every one of them diverged: F-log entries
record *"three propagation schemes were built and all three blew up"* and *"four bounding
formulations were built and all four blew up"*. `certify_trajectory.py` reached 4/8 and was
never sound.

The reason none of it was necessary is the paper's actual finding: the answer was the right
**per-frame statistic**, not set-based propagation through the dynamics. See
`docs/STATE_OF_PLAY.md` §4.

## Seven retired pointwise criteria

`equilibrium_offset.py`, `equilibrium_helpers.py`, `predict_frac_out.py`,
`predict_frac_out_dense.py`, `measure_cte_gain.py`, `certify_restoring.py`,
`measure_restoring_gain.py`, `certify_shadow_tube.py`, `fit_fields.py`,
`fit_operating_point.py`

Analytic-model bias, measured-field bias, error accumulation, restoring sign, restoring sign
over a bounded tube, equilibrium offset. All scored well in-sample and failed out-of-sample.
F22 tested the last of them directly against ground truth at 263 locations and got
**r = -0.053, with flagged locations cleaner than unflagged ones**.

`fit_operating_point.py` still produces the fog calibration `certify_cell.py` looks for; it
is archived rather than deleted for that reason.

## The retired verification instrument

`certify_fog.py`, `certify_night.py`, `certify_sustained.py`, `certify_vulnerability.py`

`certify_fog`/`certify_night` implement the 12-frame-median, per-frame-**fraction** rule that
wrote the `verify` cells still present in `results/ledger/`. It is retired because it measures
**provability rather than severity** — provability depends on bound width, which depends on
network width, so it falsifies the wider, safer model. See disposition **D-12**, which also
explains why those ledger cells are deliberately left red rather than overwritten.

`certify_sustained.py` is the F34 predecessor of the delivered instrument: it *measured* the
sustained bias at the rendered condition. `certify_sustained_bound.py` *bounds* it over the
whole interval and supersedes it.

`certify_vulnerability.py`: the proof it computes stands, but F32's claim that verification
inverts the safety ranking is **withdrawn** (F33).

## Localized sun-elevation failures — moved out, not abandoned

`p09_windowed_stat.py`, `p09_window_sweep.py`, `p09_departure_locality.py`,
`grid_rollout.py`, `driven_rollout.py`, `capture_driven_offsets.py`, `static_vs_driven.py`,
`validate_offnominal_grid.py`, `driven_campaign.sh`

The expansion beyond the canonical conditions. It is characterized but not closed, and it now
lives as a standalone write-up in the lab roadmap repository:

> `lab--future-plans--docs/localized-sun-elevation-failures.md`

Read that first — it says what was tested, what failed, and what the next experiment is.
`p09_window_sweep.py` is the exhaustive window sweep behind the paper's claim that no window
length separates the cells, which is the one result here the paper depends on.

> ⚠️ **`driven_rollout.py` has a known unfixed bug.** Two different cells returned identical
> peak (1.875 m) and residual (0.05469) to three decimals, which is impossible for two
> different captures. Do not trust it for verdicts until that is found.

## Other

`linearity_probe.py`, `box_vs_rank1.py` — archived as a pair: the probe measured the wrong
thing and `box_vs_rank1.py` is the replacement measurement.

`capture_offset_frames.py` — superseded by `capture_offset_yaw.py` once F23 established that
heading is a state, not a nuisance: captures with the vehicle aligned to the path measure the
spring and not the damper, and the resulting loop is an undamped oscillator that must diverge.

`adversarial_frames.py` — selection of frames by rendered behaviour, which `study/design.py`
forbids as a pre-registration violation.

`expert_junction_control.py` — the third attempt at the expert control, which settled that the
intersection is a real ODD boundary rather than a route artifact (D-07 withdrawn, D-09
resolved). It is why the route is truncated at 2861 m.

## docs/

`RESULT_SUMMARY.md` — **stale and wrong.** Claims "formal verification predicts closed-loop
outcome 14/14". That criterion was subsequently refuted out-of-sample at 2/6. Kept only so the
arc is visible; `docs/STATE_OF_PLAY.md` supersedes it entirely.

`CARLA_PLAN.md`, `OVERNIGHT_2026-08-11.md`, `SESSION_HANDOFF_2026-08-15.md` — session
planning and handover notes, superseded by `docs/STATE_OF_PLAY.md`.

# Overnight run, 2026-08-11 → 12

Written for Zach to read first thing. Detail lives in `FINDINGS.md` (F14–F16) and
`docs/DISPOSITIONS.md` (D-01 … D-04). Run `python -m study.ledger` for live state.

## The short version

M4 closed loop and M6 verification both advanced, but **the night's most important results
are negative**, and they land on the disturbance models rather than on the policies. Two of
the three disturbance models do not reproduce what CARLA renders. One is repaired and
measured; one is diagnosed and not yet repaired.

**Nothing in the ledger has been silenced.** `python -m study.ledger` still exits nonzero.

## What needs your decision

**1. D-01 — does a 1-in-20 marginal excursion fail a cell?** This is now more pressing than
when I first raised it, because the same pattern appeared on **clear**, the condition
`S_mixed` was trained on:

| cell | failing run | max CTE | budget | departed |
|---|---|---|---|---|
| fog / S_mixed | rep 0 westbound | 2.61 ft | 2.19 | no |
| clear / S_clear | rep 9 westbound | 2.19 ft | 2.19 | no |

**Corrected 00:09 (D-06).** I originally listed two further instances from
`clear / S_mixed`. That cell was contaminated by my own concurrent CARLA client; rerun
clean it is **PASS 0/20** with a worst westbound run of 0.82 ft. I had already flagged the
cell as contaminated and still drew a secondary conclusion from it, which was wrong — a run
corrupted at one point is not trustworthy at another. The pattern rests on two instances in
different cells, not three, and is weaker evidence for a recurring corner than I said. Either the verdict rule (any failure in 20 → FAIL) is too strict for a
stochastic simulator, or there is a specific westbound corner where the controller is
marginal. Cells now record the (step, x, y) of the worst excursion so the next run can tell
those apart — that was an instrumentation gap.

Options and costs are in D-01. My recommendation is unchanged: add repetitions first, since
it is cheap and discriminates, then decide.

**2. The night axis needs amending, and that is a pre-registration change.** Measured, the
CARLA night preset sits at `ambient = 0.553` against a declared axis of `0.02–0.50`. The
axis **does not contain the point closed loop drives**. I did not amend it — changing a
pre-registered axis after seeing results is your call, not mine. The committed night cells
stand as "falsified over the declared axis", which is true but is not a statement about
CARLA's night.

## What was found

**F14 — plain Koschmieder does not describe CARLA's fog, and we nearly certified against
it.** Road ROI: CARLA darkens by −0.031, the model brightens by +0.015. Opposite signs,
ROI R² −0.030. Full-frame rmse looked fine (0.053) only because sky dominates. This is the
train/verify family mismatch `CLAUDE.md` names as an unruled-out cause of the previous
study's inverted fog result. Adding the omitted physics — fog also attenuates the sunlight
reaching the road — takes all four computable D3 checks from 0/8 to 8/8 (ROI R² +0.870),
and moves the operating point from MOR 250 m to **61 m**.

**D4 is closed for fog.** Airlight measured at ~[0.47, 0.44, 0.43], not the assumed 0.78.

**F15 — CARLA condition frames are pose-paired** (median 0.039 m / 0.03°), unlike ACDC. That
is what made all of the above measurable, and it calibrates shadows for free: `s = 1`
reproduces the observed shadows frame exactly, so the closed-loop operating point sits at a
known place on the axis.

**F16 — the night model gets the mean right and the structure wrong** (D3 a,b 10/10 pass;
c,f 0/10 fail), and its retroreflection term fits *negative*, which is what a scene with no
headlights looks like. The mirror image of fog's failure.

## What I got wrong, and how it was caught

- **I corrupted a ledger cell** by opening a second synchronous CARLA client on port 3000
  while a cell was driving. Rep 2 went to 20.69 ft between neighbours at 0.50–1.26 ft.
  Nothing errored. The cell is retired to `results/diagnostic/` and rerun;
  `pipeline/carla_lock.py` now makes it impossible. (D-03)
- **Three wrong hypotheses** for the fog `k` disagreement — camera warm-up, ride height,
  off-road poses — each tested and falsified rather than assumed. The ride-height defect was
  real (0.29 m above settled) and worth fixing, but was not the cause. (D-04)
- **Every fog bound before tonight rested on an unmeasured assertion**: the rank-1 chord
  assumes the true curve barely bows off it. `DISTURBANCE_MATH.md` asserts this; no code
  checked. It is now measured per cell.

## Open

**D-04 — fog `k`.** Route frames say 0.72, the static sweep says ~1.14 *independently of
density*. A real attenuation must fall as fog thickens, so the constant points at the
sweep's clear baseline, not at the route frames. Leading untested hypothesis: the route
camera moves at 20 mph and the sweep's is static, and CARLA applies motion blur by default.
Meanwhile `k` is carried as a bounded interval spanning both fits — sound either way, at a
measured cost in tightness. Resolving it buys that tightness back.

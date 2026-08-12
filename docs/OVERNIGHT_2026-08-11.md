# Overnight run, 2026-08-11 → 12

Written for Zach to read first thing. Detail lives in `FINDINGS.md` (F14–F17) and
`docs/DISPOSITIONS.md` (D-01 … D-06, P-01, P-02). Run `python -m study.ledger` for live
state.

## The short version

Two things happened, and they point opposite ways.

**The study's central claim was demonstrated.** `night / S_clear`: verification committed
FALSIFIED to git *before* the drive, closed loop then failed 20/20 with every run departing.
`--check-order` confirms the ordering from git history. That is step 4 of `CLAUDE.md`, as a
prediction.

**And the M6 protocol I pre-registered is broken.** It produced **two unsound certificates**
— `shadows / S_clear` and `fog / S_clear` both CERTIFIED, both then failing closed loop
20/20 with departures (median max-CTE 21.3 ft and 92.3 ft). Certifying a policy that leaves
the road on every run is the one failure mode that invalidates the tool rather than the
experiment.

The cause is diagnosed and it is narrow: **not** the verifier (α-CROWN bounds are sound for
the frames given), **not** the disturbance models (shadows reconstructs CARLA at ROI
R² +0.996). It is the aggregation rule — 12 frames and a median, against ~1700 frames per
lap, where 37.8% of on-route frames breach the corridor. Measured densely the same corridor
separates every cell correctly (≥23.7% fails, ≤8% passes), so the *premise* holds and only
my summary statistic was wrong. F17 predicted the second unsound certificate before it
happened, and P-02 named the cell and the outcome.

**So: do not report any CERTIFIED verdict from tonight's protocol.** FALSIFIED survives —
it is an existence claim, and sparse sampling can only miss violations, never invent them.

Separately, two of the three disturbance models do not reproduce what CARLA renders; one is
repaired and measured, one is diagnosed.

**Nothing in the ledger has been silenced.** `python -m study.ledger` still exits nonzero.

## The study's spine, with the junction artefact set aside

Every marginal failure in every cell — and both departures — traces to one place: the
western intersection at the end of the lap. Confirmed across both students, both
directions and two conditions, at ~step 1690 of ~1700.

**Cause unresolved — see D-07, which I asserted and then withdrew.** I claimed an expert
control had shown the reference is drivable there. It had not: the first run's vehicle never
moved, and the second never reaches the junction because the lap ends at loop closure. So
whether the reference through the intersection is trackable is still open, and the choice
between "report it as an ODD boundary" and "exclude it as a metric artefact" cannot be made
yet.

**What is established:** the failures are real. Each recorded max-CTE position was checked
against the true distance to the reference polyline — the 86 ft departure matches exactly,
so the vehicle genuinely left the road, and there is no `nearest_index` wraparound at lap
end. Setting the junction aside only to show the conditioning effect:

| | clear | night | fog | shadows |
|---|---|---|---|---|
| **S_clear** | junction only, no departures | **20/20 FAIL, all departed** | **20/20 FAIL, all departed** | **20/20 FAIL, 16 departed** |
| **S_mixed** | **PASS 0/20** | **PASS 0/20** | junction only, no departures | **PASS 0/20** |

The clear-only student departs the road on every condition it never saw. The mixed student
completes every lap. The only blemish on either is a shared route artefact. That is the
result the study was built to produce, and verification predicted the night column before
the car drove.

## The completed ledger, 16/16 active cells

| condition | S_clear closed loop | S_clear verify | S_mixed closed loop | S_mixed verify |
|---|---|---|---|---|
| clear | FAIL 2/20 ⚠ | CERTIFIED (vacuous) | PASS 0/20 | CERTIFIED (vacuous) |
| night | FAIL 20/20 | **FALSIFIED** ✓blind | PASS 0/20 | FALSIFIED ⚠ |
| fog | FAIL 20/20 | CERTIFIED ⚠**unsound** | FAIL 1/20 ⚠ | CERTIFIED ⚠**unsound** |
| shadows | FAIL 20/20 | CERTIFIED ⚠**unsound** | PASS 0/20 | CERTIFIED |

Three cells are **CERTIFIED with a failing closed loop** — `fog/S_clear`, `shadows/S_clear`
and `fog/S_mixed`. All three come from the same defect (F17), and `fog/S_mixed` is the
mildest: closed loop failed there at 1/20 on a single marginal excursion, which is the D-01
question rather than a departure.

Ordering: `--check-order` flags only `night/S_mixed` and `shadows/S_mixed`, both known —
their closed-loop cells ran in the original overnight script before I inverted the order.
Every `S_clear` cell is properly blind.

## What needs your decision

**1. D-01 is RESOLVED — no decision needed.** I ran the diagnostic I had recommended (20
extra repetitions, 40 runs) and it answered the question:

    3/40 failures, all westbound, ALL AT THE SAME PLACE
      step 1683  x -365.8  y 11.6
      step 1684  x -365.8  y 11.7
      step 1683  x -365.9  y 11.9

Within 0.3 m of each other, near the westbound finish. That is one specific corner, not
stability-cliff non-determinism, which would scatter along the route. **The verdict rule
was reporting something real and should not be loosened** — relaxing it after the first
1-in-20 would have hidden this. `S_mixed` drives fog competently except at that one spot,
where it clips the 2.19 ft budget without departing. Follow-ups are in D-01.

**2. `verify_verdict` and `VERIFY_FRAMES` need replacing.** This is the fix for F17 and it
is a pre-registration change, so it is yours to make. The statistic should be a COVERAGE
over the route — the fraction of frames whose bound stays in the corridor, over a frame
sample justified against the ~1700 frames in a lap — with CERTIFIED requiring that fraction
near 1. I deliberately did not rewrite it at 01:00: the process that just failed a
pre-registered rule should not quietly replace it.

**3. The night axis needs amending, and that is a pre-registration change.** Measured, the
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
- **I mined a cell I had already declared contaminated** for a secondary conclusion, and
  built an argument on it. A run corrupted at one point is not trustworthy at another.
  (D-06)
- **My M6 aggregation rule produced an unsound certificate.** `shadows/S_clear` certified,
  then failed closed loop 20/20 with 16 departures. Not the verifier and not the
  disturbance model (shadows reconstructs CARLA at ROI R² +0.996) — 12 frames and a median,
  against ~1700 frames per lap, where 37.8% of on-route frames breach the corridor. (F17)
- **Every fog bound before tonight rested on an unmeasured assertion**: the rank-1 chord
  assumes the true curve barely bows off it. `DISTURBANCE_MATH.md` asserts this; no code
  checked. It is now measured per cell.

## The result the study exists for

`night / S_clear`: verification committed **FALSIFIED** to git *before* the drive;
closed loop then failed **20/20, every run departing**, 54–59% of frames outside budget.
`python -m study.ledger --check-order` confirms the ordering from git history and does not
flag this cell. That is step 4 of `CLAUDE.md` demonstrated as a prediction.

And F17 shows the surrogate is sound in principle: measured densely, the fraction of
on-route frames breaching the steering corridor separates the cells cleanly — ≥23.7% fails
closed loop, ≤8% passes. The machinery works; the sampling in my aggregation rule did not.

## Open

**D-04 — fog `k`.** Route frames say 0.72, the static sweep says ~1.14 *independently of
density*. A real attenuation must fall as fog thickens, so the constant points at the
sweep's clear baseline, not at the route frames. Leading untested hypothesis: the route
camera moves at 20 mph and the sweep's is static, and CARLA applies motion blur by default.
Meanwhile `k` is carried as a bounded interval spanning both fits — sound either way, at a
measured cost in tightness. Resolving it buys that tightness back.

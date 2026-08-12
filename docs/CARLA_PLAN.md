# CARLA experiment plan

Written 2026-08-12 after exhausting the work that needed no simulator. Ordered so that each
stage answers a question the previous stage raised, and so an interruption at any point
still leaves a defensible result.

Total CARLA time ≈ **6 h**. Nothing here needs supervision; all of it is scripted.

---

## Where we are, in one paragraph

Verification now separates the two policies **at the conditions CARLA actually renders**:
night 10/10 falsified for `S_clear` against 10/10 certified for `S_mixed`, shadows likewise,
fog more weakly (4/10 vs 1/10). That came from measuring each disturbance field rather than
assuming its analytic form (F19). Two things remain unproven, and both need the simulator:
the **domain gap** (verification reads dataset frames, closed loop drives live renders, and
they differ enough to move steering on 40% of frames — F18), and the **interpolation claim**
(verification flags intermediate severities that closed loop has never driven — F20).

---

## Stage 1 — Log frames on every closed-loop lap (≈ 0 h extra) **[replaces recollection]**

**Revised 2026-08-12 after Zach asked why recollection was needed. It is not.** The earlier
plan opened with a 2.5 h dataset recollection to close the domain gap (F18: dataset road ROI
0.3135 against a live 0.2205, enough to move steering past tolerance on 40% of frames).
That was written before `certify_trajectory.py` existed and I failed to revisit it.

Verification only has to read the **same domain** closed loop drives. Logging frames during
the closed-loop laps achieves that by construction, at no extra simulator cost:

    closed_loop_ledger.py --condition <cond> --reps 10 --log-frames results/traj

Run it for clear and for each condition. The clear laps supply the frames verification
consumes; the condition laps supply the pose-matched counterparts the disturbance fields are
fitted from.

**What recollection would have bought, and why we are declining it.** The students were
*trained* on old-domain frames, so they are deployed slightly out of distribution.
Recollecting would fix that — but it also means retraining both students and discarding all
eight closed-loop cells. The models demonstrably absorb the shift (`S_mixed` passes clear,
night and shadows at 0/20 in the live domain), so this is a nice-to-have, not a correctness
requirement. Revisit only if a result turns on it.

**Exit criterion.** Every condition has ≥ 1 logged lap per direction, pose-matchable to the
clear laps within 0.15 m.

---

## Stage 2 — Re-fit the measured fields IN THE LIVE DOMAIN (≈ 0 h CARLA, 30 min CPU)

The night illumination field, fog affine field and shadow masks are currently fitted from
*dataset* pairs. Verification will consume *live* frames, so the fields must map
live-clear → live-disturbed or the domain gap simply moves from the frames into the fields.

    pose-match Stage 1's clear laps against each condition lap
    re-fit: night gain G, fog affine (a,b), shadow masks S

**Exit criterion**, both checks, per condition:

  * held-out road-ROI image R² ≥ 0.8
  * **behavioural ratio within 2x** — each student's response to the modelled disturbance
    must match its response to the real one. This is the check F19 showed is missing from
    D3, where the analytic fog model passed on images (R² 0.848) while being 23.8x wrong
    behaviourally for `S_mixed`.

---

## Stage 3 — Fog density sweep, for the axis (≈ 1 h)

**Why.** The measured fields above are each pinned to one operating point. To verify an
*interval* rather than a point — which is the whole claim — we need the field as a function
of severity.

    scripts/fog_density_sweep.py --poses 12
    densities 0,10,...,100 at fixed poses, physics frozen

Two known traps, both already fixed in the script and both worth re-checking: the camera
must be warmed up, and the vehicle must be settled and frozen (it sat 0.29 m above ride
height, which biases depth-per-row and therefore the fit).

**Exit criterion.** MOR falls monotonically with density, and `k` falls with it too. If `k`
comes back constant again, the static harness is still not reproducing the preset (D-04) and
the sweep is not usable — say so rather than fitting it.

**Deliverable.** MOR(density) and the field interpolated across the axis, so verification
covers the continuum with measured rather than assumed physics.

---

## Stage 4 — Trajectory-logged closed loop, the clean prediction (≈ 1.5 h)

This is the headline experiment and the one that removes both remaining caveats at once.

    1. closed_loop_ledger.py --condition clear --reps 1 --log-frames results/traj
    2. certify_trajectory.py --traj results/traj/clear_<dir>_rep00 --condition <cond>
    3. COMMIT the verdict to git
    4. closed_loop_ledger.py --condition <cond> --reps 10
    5. compare

Step 2 verifies the **frames the car actually drove**, in the **live-render domain**, and
never sees the disturbed run. So step 4 tests a genuine prediction, on the real trajectory,
with no sampling gap and no domain gap. Run for fog, night and shadows, both students.

**Exit criterion.** `--check-order` confirms every verify cell precedes its closed-loop
counterpart, and the ledger's own soundness check finds no CERTIFIED-then-failed cell.

---

## Stage 5 — The interpolation experiment (≈ 2 h) **[the novel result]**

**The prediction, on the record before driving (F20).** `S_mixed`'s over-corridor rate rises
monotonically with fog thickness — 5% at MOR 2000 m, 10% at 500, 20% at 250, 50% at 140,
55% at 90. Closed loop has only ever driven MOR ≈ 61–106 m, where the model passes 19/20.
Verification says it degrades in between; simulation has never looked.

    for each intermediate density from Stage 3's MOR(density) curve:
        closed_loop_ledger.py --student S_mixed --condition fog_<density> --reps 10

Sample the axis at roughly MOR 500, 250, 140 and 90 m.

**What each outcome means.** If failure rate rises with fog thickness as predicted, that is
verification telling us something closed loop did not know — the strongest possible argument
for the tool, because exhaustive simulation of a continuum is exactly what it replaces. If
the model passes everywhere, the corridor is too conservative on the mid-axis and that is a
real, publishable limitation. **Both outcomes are results**; only silence is not.

---

## Stage 6 — Junction behaviour, to settle the ODD boundary (≈ 1 h)

Every marginal excursion in the study, and both departures, sit inside the western
intersection where lane markings vanish (D-09, confirmed by rotating the route's index seam
so the artefact could not be a representation effect). Two runs settle how to report it:

    a. the expert (pure pursuit) driven THROUGH the junction, starting mid-route so the lap
       does not end first -- eastbound already shows it tracks to 0.00 ft, westbound has
       never been measured because the start pose was wrong
    b. S_mixed on clear with the route truncated before the intersection

**Exit criterion.** If the expert tracks it cleanly and truncation removes the failures, the
ODD is "lane-marked road" and the boundary is a finding, not a defect.

---

## Stage 7 — Confirm the F18 root cause (≈ 15 min)

Restart CARLA at a different `-quality-level`, capture one clear frame at a known pose, and
compare the sky mean against the dataset's 0.0021 and the current 0.2575. This needs the
server stopped, which is why it never ran. Cheap, and it either confirms the hypothesis or
sends it back.

---

## Order and rationale

| stage | hours | blocking? |
|---|---|---|
| 1. log frames on closed-loop laps | 0 extra | folded into the laps we drive anyway |
| 2. re-fit fields in the live domain | 0.5 CPU | yes — Stage 4 depends on it |
| 3. fog density sweep | 1.0 | needed for Stage 5 |
| 4. trajectory-logged prediction | 1.5 | **the headline** |
| 5. interpolation | 2.0 | **the novel result** |
| 6. junction | 1.0 | reporting decision |
| 7. quality-level check | 0.25 | tidies F18 |

Total ≈ **6 h**, down from 9–11 h: dropping the recollection also drops the retraining risk
that came with it.

Stage 4 is the one to protect if time is short: it is the cleanest form of the study's
central claim. Stage 5 is the one most likely to produce something no closed-loop study
could produce on its own.

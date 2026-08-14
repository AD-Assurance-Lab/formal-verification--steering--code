# State of play

`FINDINGS.md` has 33 entries accumulated over three days, several of which are superseded,
withdrawn or corrected by later ones. Reading it cold gives a misleading picture. This file
is the single place that says what is currently believed, what is dead, and what is open.
It is updated in place; findings are the running log, this is the current position.

Last updated 2026-08-14.

---

## 1. What is solid

### Closed-loop ground truth (complete)

Full open-road lap, 0-2861 m, intersection excluded. Five repetitions in each direction, ten
runs per cell. PASS requires max |CTE| <= 0.668 m AND no departure. Every cell reproduced on
a freshly restarted simulator.

    condition   S_clear        S_mixed
    clear       PASS  0/10     PASS 0/10
    fog         PASS  0/10     PASS 0/10
    night       FAIL 10/10     PASS 0/10
    shadows     FAIL 10/10     PASS 0/10

Every cell is unanimous within each direction. Nothing here is marginal or noisy.

### Two model findings that stand on their own

- `S_clear` is fog-robust at EVERY density tested, 0/60 departures from 25 to 100.
  Koschmieder transmittance barely moves at short range, so raising density darkens the far
  field the crop discards rather than the road the network sees.
- `S_mixed` passes at all three sun altitudes it was TRAINED on (+90, +15, -25) and FAILS
  between them (+8, +3, 0 degrees), worst at 0 where the sun sits on the horizon. Training
  on discrete condition presets does not cover the continuum joining them.

### Measured infrastructure corrections

Each of these invalidated earlier work and each is measured, not assumed:

- **Vehicle placement.** The lap climbs 11 m. Freezing physics at spawn ride height put the
  camera metres below the road on the climbs. Settling the vehicle on the surface per pose
  takes eastbound validation from 0.202 to 0.014 and gives 0.0137 mean error across all
  1600 poses.
- **Steering gain.** The configured MAX_STEER_RAD (70 deg) over-steers by 22 percent. Fitted
  from driven traces it is 57.6 deg, agreeing to 0.5 percent between directions.
- **Heading is a state.** Captures with the vehicle aligned to the path measure the spring
  and not the damper; the loop is then an undamped oscillator that must diverge (F23).
- **Sample at the control rate.** 1.79 m = v * FIXED_DT. The same analysis on 4-5 m spacing
  scores 2/8 because it holds stale steering commands across control steps.
- **Validate the surrogate first.** Captured steering must match driven steering before
  anything is computed on it. This check rejected the eastbound captures and would have
  caught both bugs above on day one had it been run earlier.

---

## 2. What is dead, with evidence

- **Seven pointwise criteria** (F14-F22): analytic-model bias, measured-field bias, error
  accumulation, restoring sign, restoring sign over a bounded tube, equilibrium offset. All
  scored well in-sample and failed out-of-sample. F22 tested the last directly against
  ground truth at 263 locations and got r = -0.053, with flagged locations CLEANER than
  unflagged ones.
- **Per-frame verification against a steering threshold** (F30). This is the intuitive
  formulation -- bound the steering under the disturbance, compare to a lane-keeping
  threshold -- and it cannot work here, for a reason no threshold choice repairs:

      condition   S_clear max |dsteer|   S_mixed max |dsteer|
      fog             0.1114 PASS            0.0903 PASS
      night           0.4124 FAIL            0.0757 PASS
      shadows         0.2275 FAIL            0.2494 PASS

  `S_mixed` deviates MORE under shadows than `S_clear` does, and passes while `S_clear`
  fails 10/10. The ordering is wrong, so no threshold separates them. The cause is physical:
  a large deviation that reverses sign integrates to nothing while a small persistent one
  walks the vehicle out of the lane, and a per-frame bound cannot see persistence.
- **Counting proven-unsafe regions as a safety metric** (F33). It measures provability, not
  severity, and provability depends on bound width, which depends on network size. Measured
  directly, `S_clear` goes 43 to 78 percent non-restoring at night with its mean gain
  flipping positive, while `S_mixed` goes 42 to 20 percent -- which agrees with the driving
  tests. F32's claim that verification inverts the safety ranking is WITHDRAWN.
- **SDP-CROWN for this problem.** Its advantage is L2 geometry in high dimensions. Our input
  set is one to three scalars, where alpha-CROWN plus input-space branch and bound converges
  to the network's genuine output variation (0.0165 -> 0.0116 measured). There is no
  looseness left for it to remove. An L2 pixel ball large enough to contain a night image
  also contains physically impossible images and is vacuous.

---

## 3. What is currently believed, and how strongly

- **The certificates are sound.** A positive lower bound over a state box proves no restoring
  action exists anywhere in it. `S_mixed` has such regions; reproduced by an independent
  capture, and controlled -- the same frames give clean restoring bounds for `S_clear`.
  Confidence high.
- **Those regions are unreachable in nominal driving.** `S_mixed` holds 0.062 m of
  cross-track error where its defect regions begin at 0.30 m; 0 of 32 entered. So the
  defects are real, proven, and never visited -- which is why the driving tests see nothing.
  Confidence high, on the passing cells. The failing cells could not be tested this way
  because a departing vehicle leaves the route.
- **Verification and testing answer different questions**, and the bridge is reachability: a
  closed-loop failure is a defect region the trajectory intersects; latent risk is the ones
  it misses. Coherent and supported, but demonstrated on one side only. Confidence moderate.
- **The best pass/fail instrument is 4/8.** Bicycle-model propagation on the corrected
  captures: `S_clear` 4/4, `S_mixed` 0/4. It is a POINT rollout over 1600 open-loop steps and
  is not sound; small drift carries it into `S_mixed`'s defect regions, which the real
  vehicle never reaches. The disagreement is the instrument's fragility meeting a real defect.

---

## 4. The open problem, stated precisely

The sound instrument answers a different question than closed-loop testing. The instrument
that answers the same question is not sound.

Closing that gap needs the steering bound propagated through the vehicle dynamics AS A SET
rather than as a point, so that the policy's feedback -- and therefore the cancellation that
keeps the real vehicle in its lane -- is inside the abstraction instead of being discarded.
Interval and zonotope tubes both diverged; the invariant formulation is the right shape but
the invariant set is roughly 0.05 m x 0.5 deg, smaller than the boxes used to search for it.
That is a resolution problem, not a soundness or tightness one, and it is pure compute.

Three blind predictions have been committed to git before testing and all three failed
(P-03 2/6, P-06 3/7, P-07 6/10) while in-sample scores at the time were 14/14, 7/8 and 8/8.
That gap is the strongest evidence in this study that in-sample agreement means nothing here.

---

## 5. Data on disk

Seven of eight full-lap captures at control-rate spacing with corrected placement:
westbound clear/night/shadows/fog, eastbound clear/night/shadows. **Eastbound fog is missing**
-- the simulator died mid-capture after ~16 h uptime, past the leak window in CLAUDE.md.

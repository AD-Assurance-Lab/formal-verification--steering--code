# State of play

`FINDINGS.md` has 33 entries accumulated over three days, several of which are superseded,
withdrawn or corrected by later ones. Reading it cold gives a misleading picture. This file
is the single place that says what is currently believed, what is dead, and what is open.
It is updated in place; findings are the running log, this is the current position.

Last updated 2026-08-14 16:20.


---

## 0. HEADLINE: step 4 is achieved in-sample (F34-F36)

    for EVERY intensity s in [0,1], at EVERY pose on a full lap (intersection excluded):
        persistent bias = mean( steer(x(s)) - steer(x(0)) )
        SAFE iff |persistent bias| <= CLOSED_LOOP_TOLERANCE

alpha-CROWN with 16-way input-space branch and bound. Sound bounds, not sampling.

    dir    model     cond      bias bound (x tol)   verdict      closed loop
    west   S_clear   fog       [-0.75, +0.29]       CERTIFIED    PASS  0/10
    west   S_clear   night     [-6.96, +0.93]       FALSIFIED    FAIL 10/10
    west   S_clear   shadows   [-2.26, +0.64]       FALSIFIED    FAIL 10/10
    west   S_mixed   fog       [-0.25, +0.38]       CERTIFIED    PASS  0/10
    west   S_mixed   night     [-0.61, +0.26]       CERTIFIED    PASS  0/10
    west   S_mixed   shadows   [-0.29, +0.31]       CERTIFIED    PASS  0/10
    east   S_clear   night     [-5.99, +1.28]       FALSIFIED    FAIL 10/10
    east   S_clear   shadows   [-2.40, +0.65]       FALSIFIED    FAIL 10/10
    east   S_mixed   night     [-0.76, +0.31]       CERTIFIED    PASS  0/10
    east   S_mixed   shadows   [-0.25, +0.39]       CERTIFIED    PASS  0/10

**10/10.** No fitted parameters: the tolerance derives from lane width, vehicle width,
wheelbase, speed and a closed-loop time constant fixed long before the criterion existed,
and the statistic is an unweighted mean over every pose. Per-frame -- no vehicle dynamics
simulated, no trajectory rolled out.

**Why it works where F30 failed.** CLOSED_LOOP_TOLERANCE is a SUSTAINED-error threshold.
F30 compared it against MAXIMUM deviation, which is dimensionally the wrong quantity: the
maximum is dominated by transients that reverse sign and integrate to nothing, and it does
not even ORDER the cells correctly (`S_mixed` deviates more under shadows than `S_clear`
does, and passes while `S_clear` fails 10/10). The MEAN is the persistent component the
threshold describes, and it separates by 3x.

**Bound convergence checked**, so the verdict is not sitting on a knife edge:

    splits    4        8       16       32
    x tol   -1.06    -0.70    -0.61    -0.59      (measured worst -0.33)

**Two gates remain.** The result is IN-SAMPLE, and this study's record is that in-sample
scores mean nothing here (P-03 14/14 -> 2/6; P-06 7/8 -> 3/7; P-07 8/8 -> 6/10). The blind
protocol is fixed in `scripts/blind_protocol.md` and needs ~20 h of simulator time. And
eastbound fog was never captured, so two cells are missing.

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
- **SUPERSEDED by section 0.** The bicycle-model point propagation scored 4/8 and is no
  longer the best instrument; it was never sound, and the sustained-bias certificate answers
  the same question with sound bounds at 10/10. Retained only as the record of why
  trajectory-level propagation was attempted.

---

## 4. The open problem -- RESOLVED, and what replaced it

The gap was: the sound instrument answered a different question than closed-loop testing,
while the instrument that answered the same question was not sound.

It did NOT need set-based propagation through the vehicle dynamics. Interval tubes, zonotope
tubes, box grids and inductive invariants were all built and all failed, and none of that
was necessary -- the answer was to use the right PER-FRAME statistic. The trajectory-level
machinery was two days of solving the wrong problem.

What remains open is the blind test, not the method.

Three blind predictions have been committed to git before testing and all three failed
(P-03 2/6, P-06 3/7, P-07 6/10) while in-sample scores at the time were 14/14, 7/8 and 8/8.
That gap is the strongest evidence in this study that in-sample agreement means nothing here.

---

## 5. Data on disk

Seven of eight full-lap captures at control-rate spacing with corrected placement:
westbound clear/night/shadows/fog, eastbound clear/night/shadows. **Eastbound fog is missing**
-- the simulator died mid-capture after ~16 h uptime, past the leak window in CLAUDE.md.

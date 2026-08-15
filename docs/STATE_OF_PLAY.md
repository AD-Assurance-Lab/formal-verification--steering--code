# State of play

`FINDINGS.md` has 33 entries accumulated over three days, several of which are superseded,
withdrawn or corrected by later ones. Reading it cold gives a misleading picture. This file
is the single place that says what is currently believed, what is dead, and what is open.
It is updated in place; findings are the running log, this is the current position.

Last updated 2026-08-15 00:00.


---

## 0. HEADLINE: a certificate that works on ONE CLASS of failure (F34-F37)

**Read section 0b before quoting anything here.** The 10/10 below is real and
the bounds are sound, but a committed blind test refuted the criterion at an
unseen operating point, in the unsafe direction. The correct scope is
"agrees where failures are SUSTAINED", not "predicts closed-loop outcomes".

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

---

## 0b. THE BLIND TEST REFUTED IT (P-08b, 2/4, unsafe direction)

    blind cell               certificate            driving       result
    S_mixed +45 westbound    CERTIFIED [-0.37,+0.16]  PASS  0/10   correct
    S_mixed +45 eastbound    CERTIFIED [-0.19,+0.23]  PASS  0/10   correct
    S_mixed +22 westbound    CERTIFIED [-0.27,+0.31]  FAIL 10/10   REFUTED
    S_mixed +22 eastbound    CERTIFIED [-0.15,+0.41]  FAIL 10/10   REFUTED

`S_mixed` at +22 departs on EVERY one of ten runs, both directions, max |CTE| 2.38-5.11 ft
against a 2.19 ft budget -- while the certificate placed it at 0.31x and 0.41x of tolerance.
Not marginal. A model declared safe leaves its lane, reliably.

**Mechanism, from the data.** `frac_over_budget` is 0.2-0.9%: brief excursions of a few
metres on a 2.86 km lap. The criterion averages the steering bias over the WHOLE lap, so a
large deviation lasting ten metres is diluted by ~1,590 clean poses.

This is F30 mirrored. The MAXIMUM cannot see persistence, so it falsifies everything. The
MEAN cannot see LOCALISATION, so it certifies a model that departs briefly but repeatedly.
Neither statistic spans both failure modes, and choosing between them by in-sample score is
how this study reached a criterion that scored 10/10 and then failed the first unseen cell.

**Why the canonical 10/10 survives but means less.** All four canonical conditions fail
through SUSTAINED drift, which a lap-wide mean detects. `S_clear` at night drifts
continuously; `S_mixed` at +22 does not. The certificate discriminates the first kind and is
blind to the second.

**THE MOST ROBUST FINDING IN THIS PROJECT.** Four criteria, four times:

    P-03  in-sample 14/14  ->  blind 2/6
    P-06  in-sample  7/8   ->  blind 3/7
    P-07  in-sample  8/8   ->  blind 6/10
    P-08b in-sample 10/10  ->  blind 2/4

Every criterion produced here scored well in-sample and failed out-of-sample. That pattern
is more durable than any individual criterion and belongs in the writeup ahead of them.

---

---

## 0c. P-09 SETTLED IT: the localised mode needs a different instrument (F39, F40)

P-08b left one live hypothesis: that the misses were a systematic ~1.2x scale error rather
than a wrong statistic. P-09 tested it with the split declared before capture and the
held-out verdicts committed before driving (`070a2b2`).

    cell   role          certificate   x tol (W/E)    driven        outcome
    +60    calibration   PASS          0.72 / 0.91    PASS  0/10    agree
    +30    calibration   PASS          0.73 / 0.89    FAIL 10/10    MISS
    +37    held out      PASS          0.73 / 0.93    FAIL  3/10    MISS
    +15    held out      PASS          0.68 / 0.87    PASS  0/10    agree

    2/4 -- the same score as P-08b, on the same mode

**Not a scale factor.** All four cells sit in a 0.68-0.93 band while driving spans 0/10 to
10/10. Swept from 5.4 m to the full lap, the PASSING cell's statistic exceeds the FAILING
cell's at every window length. No threshold and no window orders them; nothing was fitted.

**Why: the nominal path does not contain the failure.** At the pose where +30 reproducibly
departs, the windowed deviation ranks 1064th of 1599 poses, and both cells' lap maxima sit
at the same unrelated pose 578. Every criterion built from centreline steering is a function
of a measurement in which this failure is absent -- which is the whole explanation for eight
criteria landing at chance on it.

**The mechanism is visible off-nominal, and the direction is right.** Rolling the deviation
dynamics over the measured (offset x heading) grid reproduces both sun cells from captured
frames alone: +30 diverges to 11.4 m (measured departure 8.8-13.2 m), +60 stays at 0.24 m.
It also locates the cause 150 m UPSTREAM of the symptom: the restoring gain inverts sign at
y = 54..56 for +30 while clear and +60 keep correcting.

**But the rollout is not yet a criterion (F40).** Against the canonical cells it scores 2/6
with four false FAILs, and both available excuses are ruled out by measurement: `S_mixed` fog
breaches the budget at 1.010 m while INSIDE the +-1.5 m grid, and an 81 m window does not
help. The deviation model over-predicts drift by ~2x, so its verdicts are dominated by model
error rather than by the disturbance.

**Consequence for the write-up.** The paper claims the sustained certificate (12/12) and
reports the localised mode as a MEASURED negative result: the obvious repair does not work at
any window length, and the failure leaves no nominal-path signature. That is a bound on where
the certificate applies, stated from evidence.


**Follow-on (F40-F42), recorded so the loop route is not restarted blind.** Rolling the
vehicle state over the measured (offset x heading) grid reproduces the two sun cells
quantitatively (+30 diverges to 11.4 m against a measured 8.8-13.2 m departure; +60 stays at
0.24 m) and locates the cause 150 m upstream of the symptom. It is NOT a criterion: 2/6 on the
canonical cells, and the reason is measured rather than argued --

    off-nominal surface error, in grid   0.021 - 0.048     (F41)
    static vs driven frame, gain-corr.   0.0258            (F42, n=198)
    nominal capture error (gate A)       0.0137
    disturbance term a rollout integrates 0.0052

The captures are 5x too coarse for integration and were never built for it. A per-frame
verdict never accumulates that error, which is why the certificate above is unaffected. The
loop route needs frames captured from a MOVING vehicle held at a commanded offset; that is a
capture-rig change and the first thing to build if it is pursued.


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
- **MAXIMUM steering deviation as the statistic** (F30). Note carefully what is dead here:
  the MAX, not per-frame verification itself. Bounding the steering under the disturbance and
  comparing it to a lane-keeping threshold is exactly what section 0 does and it WORKS -- with
  the mean. The maximum fails for a reason no threshold choice repairs:

      condition   S_clear max |dsteer|   S_mixed max |dsteer|
      fog             0.1114 PASS            0.0903 PASS
      night           0.4124 FAIL            0.0757 PASS
      shadows         0.2275 FAIL            0.2494 PASS

  `S_mixed` deviates MORE under shadows than `S_clear` does, and passes while `S_clear`
  fails 10/10. The ordering is wrong, so no threshold separates them. The cause is physical:
  a large deviation that reverses sign integrates to nothing while a small persistent one
  walks the vehicle out of the lane. The error was DIMENSIONAL -- CLOSED_LOOP_TOLERANCE is a
  sustained-error threshold and was being compared against a peak. The mean is the persistent
  component it describes, and it separates the same cells by 3x (section 0).
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

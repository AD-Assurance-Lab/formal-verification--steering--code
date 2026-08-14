# P-08 / P-08b  Sustained-bias certificate at five sun altitudes

Verdicts computed and committed BEFORE the closed-loop runs that test the blind subset.

## Method (frozen, no fitted parameters)

    for EVERY intensity s in [0,1] between the sun-90 baseline and the altitude in question,
    at EVERY pose on a full lap (0-2861 m, intersection excluded):
        persistent bias = mean( steer(x(s)) - steer(x(0)) )
        SAFE iff |persistent bias| <= CLOSED_LOOP_TOLERANCE = 0.0120

alpha-CROWN, 16-way input-space branch and bound, both directions.

## Predictions

    dir    model     sun   bias bound (x tol)   VERDICT
    west   S_clear   +45   [-0.74, +0.44]       CERTIFIED
    west   S_clear   +22   [-0.91, +1.04]       FALSIFIED   (knife-edge, 4% over)
    west   S_clear    +8   [-0.78, +0.21]       CERTIFIED
    west   S_clear    +3   [-6.78, +0.05]       FALSIFIED
    west   S_clear    -5   [-7.03, +0.97]       FALSIFIED
    west   S_mixed   +45   [-0.37, +0.16]       CERTIFIED   <-- BLIND
    west   S_mixed   +22   [-0.27, +0.31]       CERTIFIED   <-- BLIND
    west   S_mixed    +3   [-0.22, +0.59]       CERTIFIED
    east   S_clear   +45   [-0.48, +0.54]       CERTIFIED
    east   S_clear   +22   [-0.57, +1.25]       FALSIFIED
    east   S_clear    +8   [-0.78, +0.40]       CERTIFIED
    east   S_clear    +3   [-5.94, +0.14]       FALSIFIED
    east   S_clear    -5   [-6.24, +1.28]       FALSIFIED
    east   S_mixed   +45   [-0.19, +0.23]       CERTIFIED   <-- BLIND
    east   S_mixed   +22   [-0.15, +0.41]       CERTIFIED   <-- BLIND

Full set in `results/calibration/P08_predictions.json`.

## Honest scope: P-08 is OUT-OF-SAMPLE, only P-08b is BLIND

Closed-loop results already existed at all five altitudes for `S_clear`, and at +8, +3 and
-5 for `S_mixed`, from the sun sweep. Those outcomes were known when the altitudes were
chosen, so P-08 is reported as out-of-sample and nothing stronger. There is no evidence of
contamination -- the criterion has no free parameters and the 16-way split was fixed by a
convergence study on `S_mixed`/night -- but that is precisely the assurance a blind test
replaces.

Audited against the ledger, exactly four cells have NO driving data:

    P-08b BLIND CELLS:  S_mixed at +45 and +22, both directions.

All four are CERTIFIED, and none marginally: the tightest margin is 0.41x tolerance. A
departure in any of them falsifies the certificate outright rather than by a boundary
quibble.

## What makes these testable

At +22 the same certificate FALSIFIES `S_clear` (+1.04x west, +1.25x east) and CERTIFIES
`S_mixed` (+0.31x, +0.41x) on identical road and lighting. `S_clear` at +22 is already known
to fail 10/10. So the prediction is not merely "S_mixed passes" but "S_mixed holds the lane
exactly where S_clear does not", which is a discrimination, not a base rate.

## Outcomes and what each would mean

- **All four PASS** -- the certificate predicts closed-loop outcomes at operating points it
  has never seen. That supports putting verification inside the development loop rather than
  after it.
- **Any FAIL** -- a certified model departs. That is the unsafe direction and refutes the
  certificate as it stands; it would be reported as such, without rescoring.

Three prior blind predictions in this study failed after strong in-sample scores
(P-03 14/14 -> 2/6, P-06 7/8 -> 3/7, P-07 8/8 -> 6/10). That record is why this is worth
running even at four cells.

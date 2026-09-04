# E1b — is the bimodality real, and does the client process matter? (subsumes E5)

**Written 2026-09-04, before the runs.** Follows `docs/E1_FINDINGS.md` E1-F6. Driver:
`scripts/e1b_bimodal_probe.sh`. This also answers E5 in `docs/NEXT_EXPERIMENTS.md`, which
asked whether the screen/gate fog discrepancy is systematic or sampling.

## What prompted it

Six of E1's 48 cells were VOID under standing rule 3. They are not noisy — they are
**bimodal**. In four of six, two laps are bit-identical and the third lands elsewhere:

```
 252x84  s1 fog    22.58 / 2.49 / 22.58    two laps DEPARTED at step 304, one completed
 252x84  s5 fog     3.84 / 10.32 / 3.84
 168x56  s5 fog     2.40 / 1.66 / 1.66
 168x28  s3 fog     1.26 / 1.76 / 1.26
```

Three of the six span the 2.19 ft budget, so this flips verdicts. Every one of these runs
had the determinism preflight green, `deterministic_control` true, no lock problems, and
full step counts — so it is not R-SIM-6 and not a degraded server.

E5's original evidence points the same way: under fog the gate's laps were worse than the
screen's lap for the same checkpoint, four times, never reversed. The screen is
`--reps 1`, the gate `--reps 3`. If something about repeated laps in one process changes
the measurement, that touches every gated result in this study.

## The probe

`252x84 s1 fog` is the cleanest case: the two outcomes are far apart (22.58 vs 2.49 ft),
one departs and one completes, and the departure reproduces to the exact step.

| arm | invocation | laps |
|---|---|---|
| A | one process, `--reps 12` | 12 |
| B | twelve processes, `--reps 1` each | 12 |

`compare_student_variants.py` restarts CARLA before **every** lap in both arms (A-4), so
the only difference between them is whether the *client* process persists across laps.
That isolates exactly what E5 asked about.

24 laps, about 35 minutes.

## Predictions

**B1 — the distribution is bimodal, not continuous.** The 24 outcomes will fall into two
clusters, one near 2.5 ft (completes) and one near 22.6 ft (departs near step 304), with
nothing in between. Falsified by a spread of intermediate values.

**B2 — lap index does not predict the outcome.** Within arm A, the position of a lap in
the sequence will not correlate with which branch it takes. This is the direct test of
E5's "systematic" hypothesis, and I predict it is **sampling**, not drift: the corrected
harness restarts the server before every lap, which is the mechanism drift would need.

**B3 — arm A and arm B agree.** The departure fraction will not differ meaningfully
between one long process and twelve fresh ones. If it does, the client process carries
state across laps and every multi-rep number in this study needs re-examination.

**B4 — the split is not 50/50.** I expect a stable, reproducible branch probability that
is not a coin flip; E1 saw 2 of 3 departures, so I predict the departure fraction lands
above 0.5. This is the weakest prediction and the least important.

## What counts as an answer

* If B1–B3 hold: the VOID cells are marginal policies sitting on a genuine bifurcation
  that residual D-7 render noise resolves. The cells stay VOID, standing rule 3 stands,
  and the disposition is written. E5 is answered as *sampling*, and the screen simply
  gets one draw.
* If B2 or B3 fails: that is a harness finding, it outranks everything else queued, and
  no gated number in this study should be quoted until it is understood.
* **This does not become a failure rate.** Standing rule 3 is explicit that a cell whose
  laps disagree is void, not uncertain, and that more laps would convert an identified
  defect into a plausible rate and lose it. The purpose here is to characterise the
  mechanism, not to publish `p(depart)` as a result.

## Bound by

Restart before every lap (A-4/R-SIM-1, enforced by the driver); an unmeasured lap aborts
rather than scoring the model (exit 3); no promotion and no `.selected` pin; output
confined to `results/town06/bimodal/`.

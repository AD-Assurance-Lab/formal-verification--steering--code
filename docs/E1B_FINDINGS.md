# E1b — the bimodality is real, multimodal, and not caused by the harness (answers E5)

**Run 2026-09-04.** Pre-registration `docs/E1B_PREREGISTRATION.md`, committed at `d5e90c0`
before the runs. Driver `scripts/e1b_bimodal_probe.sh`, summariser
`scripts/e1b_summarise.py`, raw laps in `results/town06/bimodal/`.

Cell probed: `S_mixed_res_252x84_s1`, fog, 252x84 — the cleanest of E1's six VOID cells.
24 laps in two arms. CARLA restarted before **every** lap in both (A-4), so the arms
differ only in whether the *client process* persists.

```
arm A, one process, 12 laps
   7.54  7.51  22.58  22.58  1.45  1.77  3.40  22.96  7.51  7.51  22.58  22.58
   departed 5/12

arm B, twelve processes, 1 lap each
  22.58  23.43  7.51  23.43  22.96  22.58  22.96  2.13  7.51  23.43  22.58  7.51
   departed 8/12
```

## E1b-F1. B1 FALSIFIED: it is MULTImodal, not bimodal — and strikingly discrete

Four clusters at a 1 ft gap threshold, not two:

```
  n= 3    1.45 ..  2.13 ft     completes
  n= 1    3.40 ..  3.40 ft     completes
  n= 7    7.51 ..  7.54 ft     completes
  n=13   22.58 .. 23.43 ft     DEPARTS, always near step 304
```

The sharper observation is that **24 laps land on only 9 distinct values**, and seven of
them agree to within 0.03 ft (7.51–7.54). This is not a continuum with noise on it. The
closed loop has a small set of discrete outcomes and each lap falls into one of them.

That is consistent with the D-7 floor: the renderer injects a tiny perturbation
(~30 differing pixels per frame), the policy amplifies it at one or two decision points,
and the trajectory then commits to one of a handful of basins and rides it out. It is
also why the earlier 3-lap cells looked "bimodal" — with three laps you usually see two
of the four modes.

## E1b-F2. B2 held: lap index does not drive it

Within arm A, corr(lap index, departed) = **+0.269** on 12 laps, departures 2/6 in the
first half against 3/6 in the second, and consecutive laps share a branch 6 of 11 times
against ~5.5 expected by chance. No trend, and none of this is distinguishable from
sampling at this n.

The visually striking pairing in the raw sequence (`7.54 7.51`, `22.58 22.58`,
`7.51 7.51`, `22.58 22.58`) is what a 4-mode distribution looks like in 12 draws. It is
not persistence.

## E1b-F3. B3 held: the client process does not matter

Arm A departed 5/12, arm B 8/12 — **Fisher exact p = 0.414**. On the CTE values
themselves, Mann–Whitney **p = 0.087**. Neither is significant, and the eye-catching gap
between the medians (7.53 vs 22.58 ft) is an artifact of a multimodal distribution whose
median sits on a cluster boundary and jumps between clusters on small changes.

**No evidence that a persisting client process changes the measurement.** Every multi-rep
number in this study stands.

## E1b-F4. E5 is answered: the screen/gate discrepancy is order statistics, not a fault

E5 asked why, under fog, the gate's laps were worse than the screen's lap for the same
checkpoint — four times, never reversed — and warned that if systematic it "would touch
every gated result in the study".

The screen reports the worst of **1** lap; the gate reports the worst of **3**. Drawing
independently from the 24 laps measured here:

```
  P(gate worst-of-3  >  screen worst-of-1) = 0.645
  P(equal)                                 = 0.185
  P(gate  <  screen)                       = 0.171
```

So the gate is expected to look worse, and **P(all four observations in the same
direction) = 0.17** — unremarkable. Combined with E1b-F3 finding no process effect, the
discrepancy needs no harness fault to explain it.

**Caveat, stated plainly:** this pool comes from ONE deliberately pathological checkpoint,
and E5's four observations were four different students. The order-statistics argument is
therefore an existence proof that sampling suffices, not a measurement of those specific
cells. What *is* directly measured is E1b-F3: the arms do not differ.

**B4** (departure fraction above 0.5) is not resolvable at this n — 13/24 combined. It was
the weakest prediction and nothing rests on it.

## Disposition for E1's VOID cells

Standing rule 3 requires a written cause before a VOID cell stops being void. The cause is
now named and evidenced:

> A marginal policy on this route has a small number of discrete closed-loop outcomes.
> Residual D-7 render nondeterminism selects between them. The selection is not driven by
> lap index, not by the client process, and not by server degradation (preflight green,
> `deterministic_control` true, full step counts on every completing lap).

**The cells stay VOID.** This explains them; it does not rehabilitate them. A cell that
lands on four different outcomes has no single verdict to report, and averaging its laps
would publish a failure rate for a defect that is now identified — precisely what standing
rule 3 forbids.

What this *does* change is how a marginal cell should be read: **a 3-lap cell near the
budget is one draw from a multimodal distribution, not a measurement with error bars.**
Cells with large margin are unaffected — every non-VOID cell in E1 varied by 1–3% across
its laps, which is the ordinary D-7 floor.

## Consequence for the study

E1's headline stands and is strengthened. The seed dominates (26.6x), resolution is a weak
lever (1.29x), and now the residual within-cell variation is understood as discrete mode
selection rather than measurement error. Nothing here reopens pass 1, pass 2 or pass 3:
their cells are not near this regime, and E1b-F3 rules out the one mechanism that would
have touched them all.

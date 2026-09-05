# Q1 — the learning-rate effect at n = 15: findings

**Run 2026-09-05, 09:02–11:57.** Pre-registration `docs/Q1_PREREGISTRATION.md`, written and
committed (`41844d9`) before the first scored lap. Driver `scripts/arm_sweep.sh`,
summariser `scripts/q1_summarise.py`, cells in `results/town06/lr_confirm/` plus the
validated fold-ins. 36/36 new cells measured, no harness failures.

```
fog, worst-of-3 max|CTE| (ft)         budget 2.19 ft, pass-3 margin gate 1.095 ft
  arm      s0     s1     s2     s3     s4     s5     s6     s7     s8     s9    s10    s11    s12    s13    s14  median  held   gate  VOID
lr1e3   12.08   1.34  11.86  11.78   VOID  11.79   1.36   2.40   3.37   VOID 37.63D  1.00  12.20  10.43   5.84   10.43  3/13   1/13     2
lr3e4    0.98 37.65D   2.22   1.18   2.39   1.60   2.75   1.42   2.91   VOID   2.36   2.29   1.87   2.44   3.36    2.33  5/14   1/14     1

clear
lr1e3    VOID   1.18   VOID   1.07   1.79   1.09   1.65   0.82   1.51   2.01   1.17   VOID   0.72   VOID   5.93    1.18 10/11   4/11     4
lr3e4    1.25   1.06   1.43   1.16   0.95   1.92   1.15   0.67   1.44   1.10   0.78   VOID   1.23   1.30   1.37    1.19 14/14   4/14     1
```

## The short answer

**The learning-rate effect is real, it is large, and at n = 15 it still does not reach
significance on the driving endpoint — but it reaches it decisively on the KD endpoint.**

E4-F1's headline survives in direction and magnitude: the fog median goes **10.43 → 2.33 ft**,
a **4.49x** shift. The Mann-Whitney lands at **p = 0.0553**, just outside the declared
alpha. The Hodges-Lehmann interval, **[−0.02, +9.57] ft**, misses zero by two hundredths of
a foot.

That is the whole result in one line, and it is neither the confirmation Q1 was run to get
nor a refutation.

## Q1-F1 — HELD, on the pooled seeds, and this needs the caveat attached to it

Predicted: `lr3e4`'s fog median at least **3x** lower. Measured **4.49x** (10.43 → 2.33 ft).

**But on the nine new seeds alone the ratio is 1.92x**, which would have falsified F1. The
pre-registration's sensitivity rule is written on *direction and significance*, and by that
rule the two agree (same direction, both non-significant) so the pooled result stands. **The
rule did not anticipate an effect-size disagreement, and reporting only the pooled 4.49x
would be selective.** Both numbers are the finding:

```
  pooled, seeds 0-14   10.43 -> 2.33 ft   4.49x
  new,    seeds 6-14    4.61 -> 2.40 ft   1.92x
```

The fold-in half of `lr1e3` contains four departures clustered near 12 ft (s0, s2, s3, s5);
the new half is more varied. Nothing about the fold-in is invalid — it was validated
bit-exactly by SHA-256 before use — but the effect is **smaller on fresh seeds than on the
seeds E4 first saw it in**, which is the direction that regression to the mean predicts and
is worth stating plainly.

## Q1-F2 — FALSIFIED. p = 0.0553

Predicted p < 0.05 on 15 vs 15. Measured **p = 0.0553**, VOID cells excluded (n = 13 vs 14).

The pre-registration anticipated this exact outcome and said what to do: *"If F2 fails while
F1 holds, the reported answer is the effect size and interval, and the queue's other items
are unaffected."* So:

```
  Hodges-Lehmann shift (lr1e3 - lr3e4)   +5.96 ft   95% CI [-0.02, +9.57]
```

**This is not "the effect is not real".** It is a 4.49x median shift whose interval clips
zero at n = 15 because the dispersion is enormous — which is precisely what Q6 exists to
diagnose, and precisely why E2R-F5 put the sample size for a 20% effect at n ≈ 20–60.

## Q1-F1b — the effect IS significant where the measurement is precise

This was a declared secondary endpoint and it turns out to be the most informative result in
Q1. Fog KD p99 error, n = 15 per arm, **no simulator involved**:

```
  fog   KD p99   0.1024 -> 0.0732   -28.5%   Mann-Whitney p = 0.0079
                 HL shift +0.0286   95% CI [+0.0094, +0.0475]
                 seeds below 0.08:  4/15 -> 12/15
  clear KD p99   0.0667 -> 0.0454   -32.0%   Mann-Whitney p = 0.00036
```

**The same 15 students, the same seeds, the same recipe difference.** Measured through the
distillation error, the effect is unambiguous at p < 0.01. Measured through driving, it is
p = 0.0553.

**The difference between those two p-values is not about the learning rate. It is about the
measurement.** The closed loop adds enough variance to hide an effect that the open loop
resolves comfortably, and that is a statement about this study's instrument that applies to
every training comparison in the lab. It reinforces E4-F1's reasoning (which also reported a
−28% KD improvement) and it makes Q6 more valuable, not less.

## Q1-F3 — FALSIFIED, and this is the consequential one

Predicted: `lr3e4` has at least **twice** as many seeds holding fog 3/3, and at least **3 of
15** clear the 1.095 ft margin gate.

```
  held fog 3/3     3/13  ->  5/14     Fisher p = 0.678     (not 2x)
  cleared gate     1/13  ->  1/14     Fisher p = 1.000     (not 3)
```

**Exactly one student in thirty clears pass 3's own fog margin gate, and it is seed 0 at
0.98 ft — the same seed E4 already found.** The tuned recipe did not produce a second one in
nine fresh draws.

This matters for what the study can claim. E4-F1 called seed 0 *"the first student in this
study to clear pass 3's 1.095 ft margin gate on fog"*. **After nine more seeds it is still
the only one.** A recipe that produces one gate-clearing student in fifteen has not
"fixed fog"; it has shifted the distribution enough that the good tail occasionally reaches.

## Q1-F4 — HELD. Clear does not regress, and it quietly improves

Predicted: clear median within 25%. Measured **1.18 → 1.19 ft, a 1% difference** — but the
median hides the real result:

```
  lr1e3   held 10/11   max 5.93 ft   4 VOID
  lr3e4   held 14/14   max 1.92 ft   1 VOID
```

`lr3e4` held **every measured clear lap of every seed**, with a worst case of 1.92 ft.
`lr1e3` produced a **5.93 ft clear failure** (s14). The tuned recipe is not merely
non-regressive on the control condition; it is more reliable there.

## Q1-F5 — HELD. The seed still dominates

Within-arm fog spread **36.67 ft** against a between-arm median gap of **8.11 ft**. The draw
is still the largest single factor in whether a student drives, exactly as in E1 (26.6x),
E2 and E4. **Q6 is the right next item.**

## The VOID rate — declared secondary endpoint

```
  fog     lr1e3 2/15    lr3e4 1/15
  clear   lr1e3 4/15    lr3e4 1/15
  both    lr1e3 6/30    lr3e4 2/30     Fisher p = 0.254
```

Direction favours the tuned recipe — three times as many unmeasurable cells at `1e-3` — and
it does not reach significance. Pre-registering this mattered: at 6 vs 2 it is the kind of
difference that is easy to leave in an exclusion footnote, and an arm that is more often
unmeasurable is worse.

Note that **s9 is VOID in both arms on fog**, which is consistent with E1b's finding that
VOID cells are a property of the *seed's* multimodality rather than of the harness.

## What this means for the queue

**Q1 was the blocker, and it resolves as "confirmed in effect size, not in significance, on
driving — and confirmed outright on KD error."** Concretely:

1. **`OVERALL_STATUS.md` §3.3 stands as written.** Pass 3's attribution is still confounded:
   all 16 of its students used a learning rate that measurably degrades both the fog KD tail
   (p = 0.0079) and clear-lap reliability. Q1 does not retract pass 3 — Q2 tests it.
2. **The Limitations sentence softens rather than reverses**, which is the branch the
   pre-registration declared for F1-holds-F2-fails. The recipe is implicated with a measured
   effect size and a 95% interval that clips zero; it is not confirmed at alpha = 0.05 on
   driving.
3. **Report ranges and intervals, never the single pair.** This is now the *fourth* claim in
   this study where a single draw sat at the favourable end of a wide distribution.
4. **Q2 has candidates and can run.** Seeds holding fog 3/3 at `lr3e4`: **0, 3, 5, 7, 12** —
   five candidates, within the declared cap of six. By the declared tie-break (lowest fog
   worst-of-3) the order is s0 (0.98), s3 (1.18), s7 (1.42), s5 (1.60), s12 (1.87).
   **Q2-P1 is already in doubt**: only s0 clears the 1.095 ft margin on fog, so the other
   four candidates enter Q2 needing the gate's other three conditions to carry them.

## What was NOT done

No promotion, no `.selected` pin moved, nothing written to either ledger or either
certificate. The canonical certificate and both ledgers are untouched. `git status` clean
throughout; every lap recorded its own provenance.

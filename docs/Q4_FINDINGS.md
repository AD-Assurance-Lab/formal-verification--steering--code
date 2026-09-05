# Q4 — confirming label balancing at twelve seeds: findings

**Run 2026-09-05, 16:19–18:18.** Pre-registration `docs/Q4_PREREGISTRATION.md`, committed
(`d09ee72`) before the first scored lap. Driver `scripts/arm_sweep.sh`, summariser
`scripts/q4_summarise.py`, cells in `results/town06/balancing/`. **48/48 cells, no
failures.** Seeds 0–5 folded in from E6 after both arms were validated **bit-exactly** by
SHA-256 against `S_mixed_bal_bal_s0` and `S_mixed_bal_curv_s0`.

Control: Q1's `lr3e4` arm at n = 15 — same architecture, same learning rate, same pinned
kernels, raw labels. Q4 drove no control laps of its own.

```
fog, worst-of-3 max|CTE| (ft)                    budget 2.19 ft
  arm     s0     s1     s2    s3    s4    s5    s6    s7    s8    s9   s10   s11  median  held  VOID
  raw   0.98  37.65D  2.22  1.18  2.39  1.60  2.75  1.42  2.91  VOID  2.36  2.29    2.33  5/14    1   (+s12-14)
  bal   1.81   1.27   1.22  2.04  1.97  VOID  2.49  1.23  1.46  1.26  1.69  1.68    1.68 10/11    1
 curv   VOID   1.59   2.25  1.53  1.29  VOID  1.60  2.53  1.55  2.72  2.98  2.07    1.83  6/10    2

clear
  raw   1.25   1.06   1.43  1.16  0.95  1.92  1.15  0.67  1.44  1.10  0.78  VOID    1.19 14/14    1   (+s12-14)
  bal   1.69   0.72   1.01  0.93  VOID  0.88  0.53  VOID  1.29  0.81  1.23  1.00    0.97 10/10    2
 curv   VOID   1.59   1.05  0.98  1.28  VOID  0.61  2.00  VOID  0.96  VOID  VOID    1.05  7/7     5
```

## The short answer

**E6 replicates. `--balance` should be on by default.** All four predictions held, and the
primary endpoint is significant:

```
  seeds holding fog 3/3 under budget
    bal   10 of 12   (11 measured, 1 VOID)   vs raw 5/14   Fisher p = 0.0119
    curv   6 of 12   (10 measured, 2 VOID)   vs raw 5/14   Fisher p = 0.4081
```

This is the first training-side lever in this study to reach significance on a **driving**
endpoint. Q1's learning rate reached p = 0.0079 on KD error and only p = 0.0553 on driving;
balancing reaches **p = 0.0119 on driving itself**.

## Q4-P1 and Q4-P2 — both HELD, and the reason the primary endpoint was the failure count

Predicted: `bal` holds fog 3/3 in at least 10 of 12 seeds (**10 held**), and Fisher
p < 0.05 against the control (**p = 0.0119**).

The pre-registration was explicit that the median is the wrong statistic here, and the
measurement vindicates that choice:

```
  fog median      bal 1.68 ft  vs raw 2.33 ft    HL +0.61 [-0.05, +1.13]   MW p = 0.0667
  fog failures    bal 1 of 11  vs raw 9 of 14                              Fisher p = 0.0119
```

**The median moves a little and does not reach significance; the failure count moves a lot
and does.** That is E6-F1's claim — *balancing does not move the typical student, it removes
the failures* — reproduced at twice the seeds with the sign and the significance intact. Had
Q4 pre-registered the median as primary, it would have reported a null result on a real
effect.

## Q4-P3 — HELD. Clear does not regress; it improves

Predicted: `bal`'s clear median at or below the control's. Measured **0.97 ft against
1.19 ft**, and `bal` held **10 of 10** measured clear cells with a worst case of 1.69 ft.

This is E6-F2 replicating, and it matters beyond the number. The repo's stated reason for
rejecting balancing was that downsampling straight frames would train the student for a
distribution it will not meet on a route that genuinely is 84% straight. **Measured twice
now, at 6 seeds and at 12, clear gets better rather than worse.** That argument should stop
being made in `config.TOWN06_STUDENTS`; it is refuted, not merely unsupported.

## Q4-P4 — HELD. The curvature weighting is the weaker lever, and it is unmeasurable more often

Predicted: `curv` does not beat `bal` on the primary endpoint. Measured **6/10 against
10/11**, Fisher p = 0.41 against the control — indistinguishable from raw.

`curv` also has the **worst VOID rate in the study so far**, and VOID rate was a declared
secondary endpoint precisely so it could not be left in a footnote:

```
  VOID cells (of 24 driven per arm; raw is of 30)
    raw    fog 1   clear 1   total 2
    bal    fog 1   clear 2   total 3
    curv   fog 2   clear 5   total 7
```

**Seven of twenty-four `curv` cells could not be measured at all**, five of them in *clear* —
the condition every other arm holds comfortably. An arm whose laps disagree that often is
worse, not merely noisier: under standing rule 3 each of those cells is void until the cause
is found, so `curv` costs more to evaluate and yields less. Nothing here recommends it.

## The KD endpoint disagrees with the driving endpoint, and that is worth stating

```
  fog KD p99 median     raw 0.0732     bal 0.0658     curv 0.0544
```

**`curv` has the best distillation error of the three arms and the worst driving record.**
It reduces the fog KD tail by 26% against raw — more than `bal`'s 10% — and holds fog in
6 of 12 seeds against `bal`'s 10.

This is the sharpest example yet of something the study has seen repeatedly: **the open-loop
error and the closed-loop outcome are not interchangeable.** Q1 found the KD endpoint far
more sensitive (p = 0.008 vs p = 0.055) and it was tempting to treat KD error as the cheap
proxy for driving. Q4 shows the proxy can point the wrong way. A cheaper endpoint that
disagrees with the expensive one on which arm to ship is not a proxy at all.

## What this changes

1. **`--balance` becomes the default for new distillations in this study.** Cheap, already
   implemented, no cost at inference or verification, significant on driving, and it
   improves the control condition.
2. **The repo's stated objection to balancing is retracted**, in the code comment as well as
   in the findings. It has now been contradicted by measurement twice.
3. **The curvature-weighted loss is dropped.** It is the weaker lever on driving, it is
   unmeasurable three times as often, and its advantage on KD error is exactly the kind of
   signal Q4 has just shown to be untrustworthy on its own.
4. **KD error is not a substitute for driving in arm selection.** Use it to screen, never to
   decide.

## A note on provenance, recorded rather than hidden

Q4's new cells (seeds 6–11) record `git_dirty=True`; E6's folded-in cells (0–5) record
`False`. The **only** modified tracked file during the run was
`results/town06/balancing/sweep.log` — the driver's own append-only log, which
`arm_sweep.sh` writes to by design.

E6's cells recorded clean only by accident: its `balancing/` directory did not exist yet, so
its `sweep.log` was untracked at the time and was committed afterwards. **Any re-run of an
existing sweep directory dirties the tree**, so unlike Q3's case, re-driving would not fix
this. The delta is 22 lines in a log file, nothing in the driving path, and the git SHA is
recorded on every lap, so each cell is still attributable. It is a wart in `arm_sweep.sh`
worth fixing — the log belongs somewhere untracked — and it is fixed separately from this
experiment's results.

## What was NOT done

No promotion, no `.selected` pin moved, nothing written to either ledger or either
certificate. The control arm was reused from Q1 rather than re-driven, so no control lap in
this comparison was collected knowing what it would be compared against.

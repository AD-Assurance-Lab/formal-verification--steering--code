# V1 — a disposition for the canonical VOID fog cell: findings

**Run 2026-09-05, 22:14–22:39.** Pre-registration `docs/V1_PREREGISTRATION.md`, committed
before the first lap. 24 laps of `S_mixed_t06lap_168x56_w4_s3` under fog, one process and
one fresh server per lap, in `results/town06/void_fog/`. The committed ledger is untouched.

```
  V1, 24 laps          worst-lap max|CTE|, budget 2.19 ft
    1.19 ft  x14        min 1.19   median 1.19   max 1.66
    1.20 ft  x 1        over budget:  0 / 24
    1.21 ft  x 5        departed:     0 / 24
    1.32 ft  x 2        distinct values at 0.01 ft: 6
    1.47 ft  x 1        one cluster at a 1 ft gap threshold
    1.66 ft  x 1

  peak location    s = 50.8 m  (14 laps)    s = 1964-1966 m  (9)    s = 1722 m (1)

  canonical cell   1.33, 5.25, 1.47 ft   -> VOID (laps disagree)
```

## The short answer

**The cell's excursion has a location, the distribution is tightly discrete, and the lap
that voided the cell did not recur in 24 independent laps.** Two predictions held, two
failed, and the two that failed are the informative ones.

**But the cause is not what V1 was designed to look for.** The canonical cell was driven on
**different hardware**, and that is the finding.

## The hardware timeline, which is the actual result

```
  pass 1 ledger driven          2026-09-03  00:27 - 00:53
  pass 2 ledger driven          2026-09-03  12:49 - 13:14
  migration to the RTX 5090     2026-09-03  22:56          <- 10 h after pass 2
  V1                            2026-09-05  22:14
```

**Both committed ledger passes predate the GPU.** `docs/MIGRATION_2026-09-03.md` says so
plainly — *"Nothing in the study was re-run for the paper"* — and what it verified was the
**certificate** (an offline computation, all six verdicts and pose counts reproduced) and
the **oracle** (bit-identical CSVs, photometry 0.003% off). **The closed-loop ledger was
never re-driven.**

So the paper's *"all eight verdicts reproduced by an independent second pass"* is a
**within-hardware** reproduction. That is not wrong, and it was not hidden — it simply has
not been tested across the hardware change, and V1 is the first closed-loop cell ever driven
on the current GPU.

This matters because E1b established the mechanism: the renderer injects ~30 differing
pixels per frame, the policy amplifies it at one or two decision points, and the trajectory
commits to one of a handful of discrete basins. **A different GPU changes exactly that
input.** Photometry agreeing to 0.003% does not make rendering bit-exact, and D-7 already
says bit-exact closed-loop replay is unreachable.

## V1-P1 — HELD. The distribution is discrete, and more sharply than predicted

Predicted fewer than 15 distinct values in at most 5 clusters. Measured **6 distinct
values**, with **14 of 24 laps landing on exactly 1.19 ft**, and a single cluster at the
1 ft gap threshold. This is E1b's signature reproduced on the canonical checkpoint: the
closed loop has a small set of discrete outcomes, not a continuum with noise on it.

## V1-P2 — HELD. No lap departed

0 of 24 departed the road, and the worst lap reached 1.66 ft of a 2.19 ft budget. The cell
is a corridor-margin question, not a safety one, on this hardware.

## V1-P3 — FALSIFIED. The over-budget fraction is zero, not 10–50%

Predicted 10–50% of laps over budget, since one of the canonical three was. Measured
**0 of 24**.

```
  over-budget rate  0/24   Wilson 95% upper bound  13.8%
```

The canonical cell exceeded budget on 1 of 3 laps. On current hardware the same checkpoint,
condition and route exceeds it on 0 of 24, bounding the rate below 13.8%. Those two are not
comfortably reconcilable as draws from one distribution.

## V1-P4 — PARTIALLY FALSIFIED, and this is the decisive one

Predicted the three canonical laps fall inside V1's clusters. **Two do; one does not.**

```
  canonical 1.33 ft  -> inside V1's range (V1 has 1.32)
  canonical 1.47 ft  -> inside V1's range (V1 has 1.47 exactly)
  canonical 5.25 ft  -> 3.2x V1's worst lap. Not sampled in 24 tries.
```

The pre-registration said a P4 failure "is a harness question, not a policy question, and it
takes priority over the disposition." So the harness was checked, and **the 5.25 ft lap's
own provenance is clean**:

```
  restart_granularity  per_run          independent_runs  True
  deterministic_control True            lock_problems     []      (frozen rules intact)
  git_dirty            False            server flags      -RenderOffScreen -quality-level=Epic
                                                          -notexturestreaming
```

It was collected correctly. It is not a harness violation, not a dependent chain, and not a
degraded server. **What differs is the machine.**

## The excursion has a location, and it is the same one every time

All three canonical laps and 14 of V1's 24 peak at the same place:

```
  canonical rep 1 (5.25 ft)   step 26, onset step 22   s = 55.3 m
  canonical rep 2 (1.47 ft)   step 23                  s = 50.8 m
  V1, 14 of 24 laps           step 24                  s = 50.8 m
```

That is inside the route's **first curve**, s = 0–66.6 m at 2.81 deg/vertex — the
second-sharpest of seven curved spans on a lap that is 83% straight. The student takes over
from pure-pursuit at step 0 and meets it immediately, with no straight section to settle on.
`closed_loop_ledger.py` already documents a first-run-after-spawn asymmetry at a fixed
position; this is that, localised.

**The cause standing rule 3 asks for is therefore: a single identified corner, met
immediately after the control handover, where the policy under fog selects among a small set
of discrete basins.** That is more specific than E1b's general finding and it is measured on
the cell in question.

## What this does and does not license

**It does NOT clear the cell.** PROTOCOL R4 requires the committed ledger to stand, and
standing rule 3 forbids the move this evidence might tempt: *"more laps would turn an
identified defect into a plausible failure rate and lose it."* The canonical cell remains
VOID and V1 wrote nothing to it.

**What it licenses is a much better sentence than "VOID":**

> The cell's disagreement is a discrete multimodal outcome at one identified corner, met
> immediately after the control handover. The excursion that voided it was collected on
> different hardware and did not recur in 24 independent laps on current hardware
> (0/24 over budget, Wilson 95% upper bound 13.8%).

**And it raises a larger question than the cell.** If closed-loop basin selection is
hardware-conditioned, then every closed-loop number in the study is conditioned on a GPU the
lab no longer has, while every certificate number is not. V3 tests that directly: the full
eight-cell ledger, re-driven on current hardware, compared against the same committed
certificate.

## What was NOT done

Nothing written to `results/town06/ledger` or `ledger_pass2`; both verified untouched. No
certificate recomputed — V1's scope carries a byte-identical copy of the canonical one so
R1's guard had a committed artifact. No promotion, no `.selected` pin.

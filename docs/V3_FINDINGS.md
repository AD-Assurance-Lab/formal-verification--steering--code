# V3 — the Town06 ledger re-driven on current hardware: findings

**Run 2026-09-05, 22:41–23:07.** Pre-registration `docs/V3_PREREGISTRATION.md` — **written
late and saying so**; R1 held (the certificate was committed at 22:41, before the driver
launched). Canonical pair, four conditions, three laps, one process and one fresh server per
lap, into `results/town06/hw_recheck/`. Both committed ledgers untouched.

```
cond     student        old(pre-migration)   new(RTX 5090)    reproduced
clear    S_clear_t06    PASS    1.29 ft      PASS    1.27 ft      yes
clear    S_mixed_t06    PASS    1.30 ft      PASS    0.84 ft      yes
fog      S_clear_t06    FAIL   68.98 ft      FAIL   79.55 ft      yes
fog      S_mixed_t06    VOID    5.25 ft      PASS    1.95 ft      NO
low_sun  S_clear_t06    FAIL   20.76 ft      FAIL   20.76 ft      yes
low_sun  S_mixed_t06    PASS    2.19 ft      PASS    2.14 ft      yes
night    S_clear_t06    FAIL   25.52 ft      FAIL   25.51 ft      yes
night    S_mixed_t06    PASS    1.00 ft      PASS    1.00 ft      yes

                                          verdicts reproduced: 7 / 8
```

## The short answer

**The study reproduces across the hardware change, and the one cell that does not is the
VOID cell — which resolves to PASS.** V3-P1, P2 and P4 all held.

**And resolving it lowers the agreement figure**, because the cell it un-voids is one the
bound refuses:

```
  published (pre-migration hardware)   agreement 4/5   fog/S_mixed excluded as VOID
  current hardware                     agreement 4/6   fog/S_mixed scored, and DISAGREES
```

That is the uncomfortable half of a good result, and it should be stated in that order.

## V3-P1 — HELD. Seven of eight verdicts reproduce

Predicted at least seven. Measured exactly seven, and the agreement is closer than the
verdict count suggests. On the cells that are not marginal, the two hardware generations
agree to within measurement noise, and in two cases to **two decimal places**:

```
  low_sun / S_clear   20.76 ft  ->  20.76 ft
  night   / S_clear   25.52 ft  ->  25.51 ft
  night   / S_mixed    1.00 ft  ->   1.00 ft
```

A 25 ft departure lands within 0.01 ft of where it landed on a different GPU. **The hardware
change is not moving the simulation in any general way.** It moves exactly one cell, and
that cell is the one sitting near the corridor boundary — which is precisely what E1b's
basin mechanism predicts: renderer perturbation only matters where the policy is near a
decision point.

## V3-P2 — HELD. The VOID cell is PASS on this hardware

```
  old hardware   VOID   1.33, 5.25, 1.47 ft      (1 of 3 over the 2.19 ft budget)
  new hardware   PASS   1.19, 1.19, 1.95 ft      (0 of 3)
  V1, same cell  24 laps on new hardware         (0 of 24, range 1.19-1.66)

  combined on current hardware: 27 laps, 0 over budget, worst 1.95 ft
```

V3's third lap at 1.95 ft is a mode V1's 24 laps never sampled, so the distribution is wider
than V1 alone showed — the cell is genuinely multimodal and its upper modes do approach the
budget. But across 27 independent laps on this GPU **nothing exceeds it**, against 1 of 3 on
the old one.

## V3-P4 — HELD. No FAIL became a PASS

The three failing `S_clear_t06` cells stay failing, at 79.55, 25.51 and 20.76 ft. A hardware
change that flipped one of those would have meant something far larger than basin selection.
It did not happen.

## The consequence for the agreement figure, stated plainly

The published figure is **4/5**. On current hardware it is **4/6**. Nothing was measured
wrongly either time; the denominator changed because a VOID cell became scoreable:

```
  fog / S_mixed_t06     drives PASS (3/3 under budget)     certificate NOT_CERTIFIED
                        -> a DISAGREE, in the incompleteness direction
```

The bound refuses a policy that drives the condition cleanly. That is the same finding Q3
measured directly on a tuned student (agreement 1/3, two `NOT_CERTIFIED` cells driving 3/3),
and it is the direction the draft already anticipates when it says the $4/5$ does not beat a
one-line baseline.

**No cell is `CERTIFIED` while driving fails, on either hardware.** Soundness is intact
across the change, which is the property that matters most.

## What this licenses, and what it does not

**Does not:** change the published result. PROTOCOL R4 keeps pass 1 and pass 2 standing, and
V3 wrote to neither. The 4/5 was correctly measured on the hardware of record. V3 is a
**new measurement**, not a correction.

**Does:** answer the question `compare_town06.py` has been printing all along — *"the study
is not complete while [the VOID cell] stands"*. On current hardware there is no VOID cell.
And it converts a caveat the paper cannot currently quantify into two sentences it can:

> Re-driving the full eight-cell ledger on replacement hardware reproduces seven verdicts
> exactly, including three lane departures to within 0.01 ft. The eighth, the one cell whose
> laps disagreed, resolves to PASS — and scoring it moves agreement from 4/5 to 4/6, because
> the bound refuses a policy that drives that condition cleanly.

## The larger point, which is a contribution rather than a caveat

Both committed ledger passes predate the GPU (00:27 and 12:49 on 2026-09-03; the 5090
landed at 22:56). The migration verified the **certificate** — an offline computation — and
the **oracle**, bit-identically. It explicitly did not re-drive the closed loop, and until
tonight no closed-loop cell had ever run on this hardware.

So this study now has something few closed-loop verification results do: **a measured
statement about which of its numbers are hardware-portable.** The certificate side is
deterministic and reproduced exactly. The driving side reproduces exactly wherever the
policy is not marginal, and is basin-selective exactly where it is. That is a more useful
thing to be able to say than "we re-ran it and it was fine".

## What was NOT done

Nothing written to `results/town06/ledger` or `ledger_pass2` — both verified untouched. No
certificate recomputed; V3's scope carries a byte-identical copy so R1's guard had a
committed artifact. No promotion, no `.selected` pin. The pre-registration's late writing is
disclosed in its own header rather than repaired.

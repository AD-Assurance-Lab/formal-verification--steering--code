# E1 — input-resolution ablation on fog: findings

**Run 2026-09-03/04 on the new desktop.** Pre-registration: `docs/E1_PREREGISTRATION.md`,
committed at `3d1fc7a` before the first scored lap. Driver:
`scripts/e1_resolution_ablation.sh`. Raw cells: `results/town06/res_ablation/`.
Summarise with `scripts/e1_summarise.py`.

48 cells: 4 input sizes x 6 distillation seeds x {fog, clear} x 3 laps. Width held at
w4 = (32,64,64)/fc128 throughout, so resolution is the only axis that moves. 168x56
reuses the pass-3 seeds, so the ablation's middle point IS the study's measured point.

## Results

```
fog, worst-of-3 laps per cell (budget 2.19 ft)
   input      s0        s1        s2        s3        s4        s5     best   worst  held
   84x28    6.37    28.86D      5.88      1.22      1.63     10.75     1.22   28.86   2/6
  168x28    2.41     13.03      1.47      VOID     30.48D    20.14D    1.47   30.48   1/5
  168x56    1.56     41.54D      8.75     1.67      2.33      VOID     1.56   41.54   2/5
  252x84    3.21      VOID       1.88     2.09      1.57      VOID     1.57    3.21   3/4

clear
   84x28    1.28      1.77      4.03      1.27      1.04      VOID     1.04    4.03   4/5
  168x28    1.51      1.93      1.97      1.31      3.01      6.86     1.31    6.86   4/6
  168x56    1.49    41.54D      1.22      0.79      VOID      0.85     0.79   41.54   4/5
  252x84    1.21      1.12      0.88      1.24      0.84      1.10     0.84    1.24   6/6
```

`D` = the car departed the road. `held` = cells holding all 3 laps under budget.

---

## E1-F1. P1 is FALSIFIED: best-of-seeds fog IS ordered by resolution — and it barely matters

Best-of-6 fog rises monotonically with input size: **1.22, 1.47, 1.56, 1.57 ft** for
84x28, 168x28, 168x56, 252x84. I predicted this ordering would not appear. It did.

**But the effect is trivial next to the noise it sits in.** Across a 9x range of input
pixels the best-achievable fog CTE moves 29% (0.35 ft), while *within* a single
resolution the seed changes it by up to **26.6x**. The three larger sizes are separated by
0.09 and 0.01 ft — far below the lap-to-lap spread of many individual cells. The
monotone ordering is carried almost entirely by 84x28 being the best of the four.

Reporting "fog robustness decreases with resolution" from these numbers would be true of
the statistic and misleading about the system.

## E1-F2. The T06-F48 resolution trend does not survive a seed sweep

The repo carried three single draws: 84x28 fog-robust (Town04 D-14), 168x28 fog **6.85
ft**, 168x56 fog **11.15 ft** — a strong, clean-looking trend, and the main reason E1 was
ranked highest expected value.

Measured over six seeds, those two numbers are unremarkable members of their own
distributions: 168x28 spans 1.47–30.48 ft and 168x56 spans 1.56–41.54 ft. Best-of-6 at
those sizes is **1.47** and **1.56 ft**, not 6.85 and 11.15.

**The apparent trend was an artifact of single draws**, exactly as the pre-registration
suspected and exactly the failure mode that voided the w6 width refutation (T06-F55) and
the balancing refutation. This is now the third time in this study that a conclusion drawn
from one draw has not survived a sweep.

## E1-F3. The two honest summaries of this data point in OPPOSITE directions

* **Best achievable student** favours LOW resolution: 1.22 ft at 84x28.
* **Reliability of a draw** favours HIGH resolution: cells holding fog 3/3 under budget
  go 2/6, 1/5, 2/5, **3/4** as resolution rises; and on clear, 252x84 holds **6/6** with
  every seed between 0.84 and 1.24 ft, the only resolution with no failure and no VOID.

84x28 produces both the single best fog student and a 28.86 ft departure. 252x84 produces
no outstanding student and almost no bad one.

So "does fog robustness decrease with input resolution?" has no single answer: it depends
whether you are asking what a good draw can achieve or what a random draw will give you.
For a safety argument the second question is the relevant one, and it favours the larger
input — the opposite of E1's motivating hypothesis.

## E1-F4. P2 is FALSIFIED: fog IS held, at every resolution — and pass 3 still stands

**8 of the 20 measured fog cells hold all three laps under the 2.19 ft budget**, at all
four input sizes. I predicted none would. The claim that distillation simply cannot
produce a fog-robust student at this architecture is wrong.

**This does not contradict pass 3.** Pass 3's gate was `MARGIN_FRAC=0.5` — every lap under
**1.095 ft** — across all four conditions. The best fog cell measured here is **1.22 ft**,
above that gate, and these cells were driven on fog and clear only. Pass 3's finding
("none of 16 students passed, and fog stopped every one") is consistent with everything
here. The gate stands and was not relaxed.

What changes is the interpretation: fog robustness is not absent, it is **unreliable**.
The teacher holds Town06 fog at 0.37–0.40 ft; a good student draw reaches 1.22 ft; most
draws are far worse.

## E1-F5. P3 holds: the straights do get worse at low resolution

Best-of-seeds clear: **1.04 ft at 84x28** against **0.79 ft at 168x56** and **0.84 ft at
252x84**. 252x84 is the only size with no clear-condition cell over 4 ft at all; the other
three each have at least one (84x28 s2/s5, 168x28 s5, 168x56 s1). Consistent with T06-F11 (at 84 px the entire 0.668 m CTE budget spans 1.79 px of image shift at 20 m
lookahead).

Combined with E1-F1, the trade-off E1 was designed to look for is **real but weak in one
direction and strong in the other**: dropping resolution buys ~0.35 ft of best-case fog
and costs ~0.25 ft of best-case straight-line accuracy plus a large loss of reliability.

## E1-F6. Six VOID cells, and they are BIMODAL rather than noisy

Standing rule 3: a cell whose laps disagree is VOID, not uncertain, and stays void until
the cause is written down. Six of 48 cells (12.5%) disagree by more than 25%:

```
  84x28  s5 clear   4.62 / 5.85 / 2.06     full-length, no departure
 168x28  s3 fog     1.26 / 1.76 / 1.26     full-length, no departure
 168x56  s4 clear   0.77 / 3.91 / 3.71     full-length, no departure
 168x56  s5 fog     2.40 / 1.66 / 1.66     full-length, no departure
 252x84  s1 fog    22.58 / 2.49 / 22.58    two laps DEPARTED at step 304, one completed
 252x84  s5 fog     3.84 / 10.32 / 3.84    full-length, no departure
```

**In four of the six, two laps are bit-identical and the third lands elsewhere.** That is
not measurement noise — it is the closed loop selecting between two outcomes. 252x84 s1
is the clearest case: two laps depart at exactly step 304 with exactly 22.58 ft, the third
completes the lap at 2.49 ft.

Candidate cause, NOT yet ruled in: residual D-7 render nondeterminism (~30 differing
pixels per frame) deciding which side of a bifurcation a marginal policy falls on. The
determinism preflight was green on every one of these runs, `deterministic_control` is
true, no lock problems, and step counts are full — so this is not R-SIM-6 and not a
misconfigured server.

**Three of the six span the 2.19 ft budget**, so the bimodality is verdict-flipping, not
cosmetic. These cells stay VOID. They are not averaged into a rate, because doing so
would convert an identified, reproducible bifurcation into a plausible-looking failure
percentage and lose it.

This is the sharpest available follow-up and it subsumes E5: drive one bimodal cell
(252x84 s1 fog is the cleanest) for 10+ reps and characterise the split.

---

## What this means for the study's open question

The question was *"why does knowledge distillation lose fog robustness that the teacher
demonstrably has, and what recovers it?"*

E1 says the premise needs adjusting. Distillation does **not** reliably lose fog
robustness — 8 of 20 measured cells hold it. It loses it **on most draws**, and the
variance between draws (up to 26.6x) is an order of magnitude larger than anything
resolution buys (1.29x). Architecture is a weak lever here; **the draw is the strong one**.

That redirects the remaining experiments. E4 (depth) and further resolution work are
measuring a small effect through a large noise source and would need many seeds per point
to say anything. **E2 (tail-sensitive loss) and E6 (curvature-weighted loss) are the right
next moves**, because they target the variance itself rather than the architecture — and
both should now be judged on *how many seeds* clear the bar, not on the best seed.

# Q2 — the pass-3 gate at the tuned recipe: findings

**Run 2026-09-05, 13:40–14:48.** Pre-registration `docs/Q2_PREREGISTRATION.md`, committed
(`d09ee72`) before the first scored lap and before Q1 reported, so the candidate-selection
rule was fixed in advance. Driver `scripts/select_student_seed.sh` — pass 3's own gate,
unchanged, `MARGIN_FRAC=0.5`. Summariser `scripts/q2_summarise.py`, cells in
`results/town06/tuned_gate/`.

Candidates: the five seeds Q1 showed holding fog 3/3 under budget, in the declared
ascending-seed order — **0, 3, 5, 7, 12**.

```
 seed               checkpoint      clear       fog     night   low_sun   gate   verdict
    0   S_mixed_depth_d3lr3_s0      1.29      1.34V     0.88      1.45    4/12   fails
    3   S_mixed_depth_d3lr3_s3      1.21      1.18      0.65      1.06    6/12   fails
    5   S_mixed_depth_d3lr3_s5      1.92s     1.50s     6.34s       --    0/0    screened out at night
    7      S_mixed_lr_lr3e4_s7      0.69      1.42      0.87      0.44    9/12   fails
   12     S_mixed_lr_lr3e4_s12      1.25      1.50      0.92      1.29    3/12   fails

  worst-of-3 max|CTE| in ft. s = screen lap (1 lap at full budget). V = VOID.
  GATE = 1.0958 ft (0.5 x the 2.19 ft budget).
```

## The short answer

**Pass 3's conclusion survives, and the confound `OVERALL_STATUS.md` §3.3 recorded is
now resolved — against the learning rate.**

None of the five tuned candidates passes the gate. **Fog is the only condition that fails
every one of them.** That is precisely what pass 3 found across its 16 students, and pass 3
is therefore no longer confounded by the untuned learning rate: the recipe was changed, the
gate was not, and the outcome is the same.

## Q2-P2 — HELD. No candidate passes all four conditions 12/12

Predicted, and measured. The best candidate is **seed 7 at 9/12**, and it is stopped by fog
alone (clear 3/3, night 3/3, low_sun 3/3, **fog 0/3**).

The pre-registration said a candidate passing the full pass-3 gate *"is the single most
consequential outcome available in this queue"*. It did not happen.

## Q2-P1 — FALSIFIED, and this is the more interesting failure

Predicted: at least one candidate holds fog 3/3 under the 1.095 ft margin. **None does.**

That prediction was called *"close to a sanity check"* because E4 had measured seed 0
driving fog at **0.98 ft** — inside the margin — and Q1 re-measured the same checkpoint at
0.98 ft. **In Q2's gate, the same byte-identical checkpoint drove fog at 1.34 ft, and the
cell went VOID.**

```
  S_mixed_depth_d3lr3_s0, fog, worst-of-3 max|CTE|
    E4 (2026-09-04)   0.98 ft
    Q1 (2026-09-05)   0.98 ft
    Q2 (2026-09-05)   1.34 ft   -- and VOID (>25% lap disagreement)
```

Same weights, same harness, same day for the last two. **The one student this study had
that cleared pass 3's fog margin did not clear it on re-measurement**, and the cell that
disagreed is VOID rather than uncertain (standing rule 3). This is the closed-loop
dispersion Q6 characterised, appearing exactly where it is most expensive: in the
measurement that decides whether a policy is good enough to ship.

**Consequence for the record:** E4-F1's *"the first student in this study to clear pass 3's
1.095 ft margin gate on fog"*, repeated in `Q1_FINDINGS.md`, **should be read as a single
draw that did not replicate.** It is the fifth single-draw claim in this study to weaken
under re-measurement, and it is now recorded as such.

## Q2-P3 — FALSIFIED. Fog is still the stopping condition

Predicted: fog is *no longer* the stopper for the majority of failing candidates; night is.
Measured across the four gated candidates:

```
  clear    fails the margin for 3/4
  fog      fails the margin for 4/4     <- the only condition that stops every candidate
  night    fails the margin for 0/4
  low_sun  fails the margin for 2/4
```

**Night stopped nobody.** Night was the second-worst condition in the original study and is
now the *best* — every candidate held it 3/3, worst case 0.92 ft. Fog is the sole universal
stopper.

**A methodological note, because it nearly went the other way.** The first version of the
summariser recorded "the first failing condition per candidate", iterating conditions in
their fixed order (`clear`, `fog`, `night`, `low_sun`). That reported `clear 3, fog 1` and
scored Q2-P3 as **HELD** — the opposite of the truth — purely because `clear` is listed
first. The fix counts failures per condition rather than per candidate. Q2-P3 is exactly
the question that ordering artifact would have answered backwards.

## The distinction that matters for how this is written up

**Every gated lap of every gated candidate was within the 2.19 ft budget.** Not one
departed. The failures here are *margin* failures against a gate set at 50% of budget:

```
  worst lap over all 48 gated laps:  1.50 ft   (68% of budget)
```

So the honest statement is **not** "the tuned students cannot drive Town06". It is:

> Tuned students drive Town06 within budget in all four conditions, and none of them has
> the 50% headroom pass 3 required. Fog is where the headroom goes.

That is a real, if modest, improvement on the original picture — pass 3's students included
outright departures — and it is a considerably weaker claim than "the recipe fixed fog".

Seed 5 is the exception and is reported as what it is: **screened out at night with a 6.34 ft
departure**, on a single screen lap. It never reached the gate, so it has no 12-lap result,
and an unmeasured lap is not a failing lap.

## What this settles, and what it does not

**Settles:** `OVERALL_STATUS.md` §3.3's confound. Pass 3 attributed the fog failure to the
distillation rather than to capacity or luck, and the objection was that all 16 of its
students used `lr=1e-3`, never swept. Q1 swept it; Q2 ran the unchanged gate on the
survivors. **Fog still stops every candidate.** The attribution is no longer confounded by
the learning rate, and §3.3 should be updated from "confounded" to "tested and upheld".

**Does not settle:** whether a certificate *predicts* driving on a good policy. Q2 measured
driving only. That is Q3, and Q2 has just told Q3 which student to use.

## Q3's subject, by the rule declared before Q2 ran

The Q3 pre-registration selects *"the candidate with the most gate laps under 1.095 ft, ties
broken by lowest fog worst-of-3, then by lowest seed"*.

**Seed 7 — `S_mixed_lr_lr3e4_s7` — at 9/12**, the clear winner with no tie to break. It
holds clear, night and low_sun 3/3 under the strict margin and is stopped by fog alone, so
it is the best available subject for a blind certificate-then-drive: good enough that the
certificate has to work to be right, and still failing in the one condition the whole study
turns on.

## What was NOT done

`PROMOTE=0` throughout and the private pins `S_mixed_tuned_gate_A` / `_B` were used, so
neither shipped `.selected` pin moved and no base checkpoint was overwritten. Nothing was
written to `results/town06/ledger`, `ledger_pass2`, or either certificate. Both sweeps
exited 1 ("no seed held every lap"), which is the correct exit for a gate nobody passed.

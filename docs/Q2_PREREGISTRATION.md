# Q2 — the pass-3 gate at the tuned recipe: pre-registration

**Written 2026-09-05, before any Q2 lap.** Queue item `docs/EXPERIMENT_QUEUE.md` §Q2.
Driver `scripts/select_student_seed.sh`, output `results/town06/tuned_gate/`.

## The question

> Pass 3's headline is that **none of 16 students passed a 0.5-margin gate across four
> conditions**, and that fog stopped every one. Every one of those 16 was distilled at
> `lr=1e-3`. Does a student at the tuned recipe pass the same gate?

## Why it matters

Pass 3 concluded the fog failure is *"neither a capacity problem nor an unlucky draw... it
is the distillation to a smaller, shallower student that loses it."* `OVERALL_STATUS.md`
§3.3 already records that attribution as **confounded**, because the learning rate was
never swept. If a tuned student passes the unchanged pass-3 gate, the conclusion must be
restated, and the study gains what its own Limitations calls the thing it most lacks — a
student that both drives and is a fair subject for certification.

**The gate is not changed.** Same four conditions, same 3 laps, same `MARGIN_FRAC=0.5`,
same budget. Only the candidate changes. A gate that moved with the candidate would prove
nothing.

## Candidate selection rule — declared before Q1 reports

Q2 runs on **every seed that Q1's `lr3e4` arm shows holding fog 3/3 under the 2.19 ft
budget**, in ascending seed order, to a maximum of six candidates. If Q1 yields more than
six, the six with the lowest fog worst-of-3 are taken; if it yields none, **Q2 does not run
and that is the result** — the tuned recipe would have failed to produce a single candidate
and pass 3's conclusion would stand as written.

Selecting on **fog driving** and then gating on four conditions is deliberate and is
declared: fog is the failing condition and the screen is a cheap filter, exactly as
`select_student_seed.sh` documents. The gate's verdict is what counts, and it is taken on
conditions the screen did not select for.

## Two corrections to the queue's literal command

The command in `EXPERIMENT_QUEUE.md` §Q2 does not run as written, and both defects are
recorded here rather than quietly fixed:

1. **`CK` must be the base name, not the seeded one.** The script forms
   `SCK="${CK}_s${SEED}"`, so the queue's `CK=S_mixed_depth_d3lr3_s0` with `SEEDS="0"`
   resolves to `S_mixed_depth_d3lr3_s0_s0`, which does not exist. Q2 passes
   `CK=S_mixed_depth_d3lr3 SEEDS=0`.
2. **The script's own distillation fallback is wrong for a tuned candidate.** If the
   checkpoint is absent it distils with no `--lr` and no `DISTILL_DETERMINISTIC`, i.e. at
   the shipped `1e-3` with unpinned kernels — it would silently gate an *untuned* student
   under the tuned student's name. **Q2 therefore asserts every candidate checkpoint exists
   before invoking the script**, and refuses to run if one is missing. The fallback path is
   never entered.

## Declared analysis

**Primary endpoint.** For each candidate, the number of the 12 gate laps (4 conditions x 3)
at or under **1.095 ft** (0.5 x the 2.19 ft budget), and whether the candidate passes the
gate outright (12/12).

**Secondary.** Per-condition worst-of-3 for each candidate; and the condition that stops
each candidate that fails.

**VOID handling.** A candidate whose 3 laps in any condition disagree by more than 25% is
VOID **in that condition**, and the candidate is reported as VOID rather than as passing or
failing. It is not re-driven with more laps (standing rule 3).

## Predictions — written before any Q2 lap

**Q2-P1 — at least one candidate passes fog 3/3 under the margin.** E4 already measured one
seed driving fog at **0.98 ft**, inside the 1.095 ft gate. This is close to a
sanity check on the candidate-selection rule rather than a discovery.

**Q2-P2 — no candidate passes all four conditions 12/12.** Night is the second failing
condition on this route and was never the target of the learning-rate change; the tuned
recipe was selected on validation KD error, which E4 showed improving fog specifically.
**If Q2-P2 is false — a candidate passes the full pass-3 gate — that is the single most
consequential outcome available in this queue**, and it is reported immediately and on its
own, not folded into a summary. It would mean the study's central negative result about
distilled students is a statement about an untuned recipe.

**Q2-P3 — fog is no longer the stopping condition** for the majority of failing candidates;
night is. This is the prediction that distinguishes "the recipe fixed fog" from "the recipe
fixed everything a bit".

## Bound by

`PROTOCOL.md` §5 (this is model **building**, on the same side of the leakage boundary as
the teacher and competence gates — no canonical cell is scored, nothing reaches the ledger),
`CLAUDE.md` R-SIM-1..6, standing rules 1, 3, 7, 8.

**`PROMOTE=0` and a private `PIN_CK` are mandatory.** The shipped `.selected` pins for
`S_clear_t06lap_168x56_w2` and `S_mixed_t06lap_168x56_w4` resolve the certified models and
must not move. Output goes to `results/town06/tuned_gate/`, never to `results/town06`.

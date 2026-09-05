# Experiment queue — everything still to run, in order, with commands

**Written 2026-09-05.** Companion to `docs/OVERALL_STATUS.md`, which says what stands and
what does not. This file is the runnable plan. Total ~16–20 h of wall clock, most of it
CARLA-bound and unattended.

**Every item below needs a pre-registration committed before its first scored run**
(standing rule 1, and it is what made E1–E6 interpretable). Templates:
`docs/E4_PREREGISTRATION.md` is the closest in shape.

---

## 0. Preflight, once, after any restart

```bash
cd ~/ad-assurance--workspace/formal-verification--steering--code

bash scripts/bootstrap_env.sh                  # only if .venv is missing or torch changed
PYTHONPATH= .venv/bin/python -m pytest tests/ -q          # expect 78 passed
PYTHONPATH= .venv/bin/python scripts/audit_repo.py        # expect 249 passed, 0 failed

# CARLA: headless is verified equivalent to windowed (bit-identical oracle CSVs,
# photometry 0.000% off reference), so leave CARLA_WINDOWED=0 unless you want to watch.
export PATH="$PWD/.venv/bin:$PATH"; unset PYTHONPATH
export STUDY_MAP=Town06 CARLA_PORT=3000 CARLA_WINDOWED=0
bash scripts/carla_restart.sh > /tmp/carla_restart.log 2>&1   # never pipe this
grep -E "ready|preflight|photometry" /tmp/carla_restart.log
```

Sanity check that the simulator is the same one: `python3 pipeline/drive_expert.py
--direction all` should reproduce `pipeline/results/oracle_{east,west}bound.csv`
**bit-identically** (`git diff --quiet HEAD -- pipeline/results/`).

---

## Q1. Confirm the learning-rate effect — **BLOCKER for the paper as written**

**Why first.** E4-F1 measured the fog median moving 11.79 → 1.91 ft from `lr` alone, at
p = 0.247 on six seeds. That single result confounds pass 3 and softens a Limitations
sentence. Nothing else should be published until it resolves.

**Design.** Two arms, `lr=1e-3` and `lr=3e-4`, **n = 15 seeds each**, 168x56 w4, kernels
pinned, fog and clear, 3 laps. Add `1e-4` as a third arm if the budget allows — the grid
was only ever sampled at one seed.

```bash
# seeds 0-5 already exist for both arms; this extends them to 15.
CARLA_WINDOWED=0 SEEDS="6 7 8 9 10 11 12 13 14" \
ARMS='lr1e3|32,64,64|128||--lr 1e-3;lr3e4|32,64,64|128||--lr 3e-4' \
PREFIX=S_mixed_lr OUT_DIR=results/town06/lr_confirm \
  setsid nohup bash scripts/arm_sweep.sh > /tmp/q1.log 2>&1 &
```

**Cost** ~30 distillations + ~108 laps ≈ **4 h**. Existing seeds 0–5 for `3e-4` live in
`results/town06/depth` (`d3lr3`) and for `1e-3` in `results/town06/tail_loss_det`
(`a0p0`); fold them in when summarising rather than re-driving them.

**Answer looks like** a Mann–Whitney on 15 vs 15 and the count of seeds holding fog 3/3.
Power at the observed dispersion is still only moderate — see `E2_RERUN_FINDINGS.md`
E2R-F5 — so report the effect size and the interval, not just a p-value.

---

## Q2. Re-run the pass-3 gate at the tuned recipe

**Why.** Pass 3's headline is that none of 16 students passed a 0.5-margin gate across four
conditions. Every one used `lr=1e-3`. If a tuned student passes, pass 3's conclusion must
be restated and the study gains what its Limitations calls the thing it most lacks.

```bash
# the pre-registered pass-3 gate: every lap under 50% of budget, all four conditions
CK=S_mixed_depth_d3lr3_s0 CH=32,64,64 FC=128 IN_W=168 IN_H=56 \
TEACHER=teacher_mixed_t06lap_dagger_r03 BASE=mixed_t06lap \
DAGGER_DIRS=dagger_mixed_t06lap,dagger_student_S_mixed_t06_t06lap \
CONDS="clear fog night low_sun" REPS=3 SEEDS="0" \
MARGIN_FRAC=0.5 PIN_CK=S_mixed_tuned_gate PROMOTE=0 \
OUT_DIR=results/town06/tuned_gate \
  bash scripts/select_student_seed.sh
```

Run it for each seed that Q1 shows holding fog. **Cost** ~12 laps per candidate ≈ 20 min
each. `PROMOTE=0` and the private `PIN_CK` are required — the shipped `.selected` pins must
not move.

---

## Q3. A blind certificate-then-drive on a tuned student — **the study's actual claim**

**Why.** Q2 tests driving. The paper's claim is that a certificate *predicts* driving. That
has never been exercised on a good policy, and E7-F3 says a student driving fog at 0.98 ft
is still `not certified` — so this is where the method's incompleteness gets measured
rather than asserted.

**Order matters and is checkable.** Certify first, commit, then drive.

```bash
# 1. certify, to a NEW path (the canonical certificate must not move)
STUDY_MAP=Town06 \
TOWN06_STUDENTS_OVERRIDE="S_tuned:S_mixed_depth_d3lr3_s0:32,64,64:128" \
  python3 scripts/certify_town06.py --out results/town06/tuned/certificate_tuned.json

# 2. COMMIT IT before any scored lap (PROTOCOL R1)
git add results/town06/tuned/certificate_tuned.json && git commit -m "..."

# 3. then drive, and check the ordering held
python3 scripts/closed_loop_ledger.py --student S_mixed_depth_d3lr3_s0 \
    --channels 32,64,64 --fc 128 --w 168 --h 56 --condition fog --reps 3
python -m study.ledger --check-order
```

**Cost** ~15 min certify + ~1 h driving for four conditions. Needs its own pre-registration
naming the predicted verdicts.

---

## Q4. Confirm balancing

E6 found `--balance` held fog 5/5 against raw's 3/6 and *improved* clear (0.93 vs 1.21 ft),
falsifying the repo's stated reason for rejecting it. At 5/6 seeds that is Fisher p ≈ 0.18.

```bash
CARLA_WINDOWED=0 SEEDS="6 7 8 9 10 11" \
ARMS='bal|32,64,64|128||--lr 3e-4 --balance;curv|32,64,64|128|DISTILL_CURV_BETA=4.0|--lr 3e-4' \
PREFIX=S_mixed_bal OUT_DIR=results/town06/balancing \
  setsid nohup bash scripts/arm_sweep.sh > /tmp/q4.log 2>&1 &
```

**Cost** ~12 distillations + 72 laps ≈ **2.5 h**. Fold in with Q1's raw arm as the control.

---

## Q5. E3 — gradient alignment (KDIGA). **One decision needed before it can run.**

Precomputing the teacher's gradient per batch is fine and is not the obstacle. The obstacle
is that **the teacher takes 200x66 and the student 168x56**, so `∇ₓf_teacher` and
`∇ₓf_student` are tensors of different shape and `‖∇ₓf_s − ∇ₓf_t‖²` is undefined.

**Recommended default, if you want it run without further discussion:** bilinearly resize
the teacher's input-gradient map to the student's 168x56 grid, and align the two after
normalising each to unit L2 norm — so the objective matches *where* the two models are
sensitive rather than *how much*, which is what the KDIGA result is about and which
sidesteps the fact that the two gradients are not commensurable in magnitude across
different input scalings.

That is a modelling choice and it changes what is being aligned, so it belongs in the
pre-registration as a declared decision rather than an implementation detail. Once it is
declared, the work is: load the teacher in `distill.py` (it currently loads only cached
targets), precompute per batch, add the term behind `DISTILL_KDIGA_BETA`, sweep the beta
over a declared set, and gate exactly as Q1 does. **Cost** ~1 day including implementation.

---

## Q6. Why is a fixed objective on fixed data this noisy?

**The highest-value open question the follow-ons produced, and nothing in the study has
asked it.** With kernels pinned, seed fixed and data fixed, distillation is bit-exact — but
*across* seeds the fog p99 has **CV 42.6%**, and correlation between two objectives at the
same seed is r ≈ 0. That dispersion is what makes every training comparison in this lab
expensive (n ≈ 20–60 for a 20% effect).

Cheap things to measure first, none needing CARLA:

* Does the variance shrink with more DAgger data, or is it intrinsic to the 27k-frame pool?
* Is it initialisation or data order? Pin one, vary the other — both are controllable now.
* Does an ensemble or weight average over seeds have a materially better fog p99 than the
  median seed? If so the pipeline has a cheap fix and every later experiment gets cheaper.

**Cost** ~2 h of GPU, no simulator. **Do this before Q5**: if it succeeds it lowers the
cost of every remaining experiment.

---

## Q7. Recapture at 84x28, only if the cross-size certification matters

E7 could not certify a *small-input* Town06 student because captures are stored
pre-projected to 168x56 (`frames` shape `(1,1060,1,1,3,56,168)`). Certifying an 84x28
arterial student — the direct analogue of the Town04 model — needs its own capture set.

Only worth the ~2 h of capture plus the A-3 capture gate if the paper wants to claim the
cross-road comparison at matched *input size* as well as matched capacity. E7 already
answers the size objection without it.

---

## Ordering summary

| | item | cost | gates what |
|---|---|---|---|
| 1 | **Q1** learning rate at n=15 | 4 h | the paper's Limitations sentence |
| 2 | **Q6** training-variance diagnosis | 2 h, no CARLA | the cost of everything after it |
| 3 | **Q2** pass-3 gate at the tuned recipe | 20 min/candidate | pass 3's conclusion |
| 4 | **Q3** blind certificate on a tuned student | ~1.5 h | the study's central claim, on a good policy |
| 5 | **Q4** balancing confirmation | 2.5 h | a cheap default worth turning on |
| 6 | **Q5** KDIGA | ~1 day | needs the §Q5 decision first |
| 7 | **Q7** 84x28 recapture | 2 h | optional |

**Do not** re-run: the Town06 certificate, either ledger, the witness exhibit, or the
two-scope comparison. All were re-verified or are untouched.

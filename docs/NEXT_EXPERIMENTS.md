# Next experiments — start here on the new machine

**Written 2026-09-03 for a fresh Claude Code session started in this repository.**

You are picking up a study that is **complete and being written up**. Nothing below is
required for the paper. The paper's scope is frozen — see `docs/PAPER_HANDOFF.md`, which is
the authority on what gets published. These experiments extend the work; they do not gate
it. **If an experiment here contradicts the frozen result, that is a finding to report to
Zach, not a reason to edit the paper's inputs.**

Read first, in this order:

1. `PROTOCOL.md` — hash-locked, wins over every other file, amendments A-1..A-5 at the end.
2. `CLAUDE.md` — the CARLA rules that still bite (R-SIM-1..6).
3. `docs/TOWN06_FINDINGS.md` — findings T06-F50 through T06-F57 are the current state.
4. `../CLAUDE.md` — the workspace standing rules.

---

## The one-paragraph state of the question

Town04 (highway ODD) established a certification criterion with one fitted constant.
Town06 (urban arterial ODD) tested it blind: the certificate was committed before any
scored lap and agreed with driving on 4 of 5 scored cells, reproduced exactly across two
independent passes. **Every disagreement and every failure localises to one condition:
fog.** The mixed student fails fog; the clear-only student leaves the road in fog.

Pass 3 then eliminated the two explanations the repo had been carrying. Sixteen students —
two widths (101,888 and 152,832 ReLU) × eight distillation seeds — were driven against a
pre-registered margin gate. **None passed, and fog stopped every one.** So the fog failure
is neither capacity nor an unlucky draw.

What makes this tractable: **the teacher drives Town06 fog at 0.37–0.40 ft over three runs**
(T06-F29), against a 2.19 ft budget. Fog on this route is easy for a 5-conv-layer PilotNet
at 200×66. It is the **distillation to a 3-conv-layer student at 168×56** that loses it.

So the open question is narrow and well posed:

> Why does knowledge distillation lose fog robustness that the teacher demonstrably has,
> and what recovers it?

---

## Hardware note

The new machine has a 5090 and plenty of RAM. What that changes:

* Distillation is minutes, so seed sweeps are cheap. **Use them.** This repo has twice
  recorded a conclusion from a single draw and had to withdraw it (T06-F55 on width,
  and the balancing refutation in `config.TOWN06_STUDENTS`). One draw is a coin toss —
  `389f192` measured an unchanged configuration swinging 1.16 → 8.68 ft.
* α-CROWN certification is GPU-bound and will be much faster; the pass-2 capped
  certificate took ~15 min for two students on the old card.
* **CARLA is still the bottleneck and is unchanged.** A lap is ~30 s plus a ~55 s server
  restart, and R-SIM-1 requires a restart before *every* measurement run. A 12-lap gate is
  ~18 min no matter how fast the GPU is. Budget experiments in laps, not FLOPs.

---

## Experiments, in priority order

Each gives: the question, why it is worth running, how to run it, and what would count as
an answer. **Pre-register a prediction before each one** — `docs/TOWN06_PASS3_PREREGISTRATION.md`
is the template, and it is what made pass 3 interpretable.

---

### E1 — Input-resolution ablation on fog  ★ highest expected value

**Question.** Does fog robustness decrease monotonically with student input resolution?

**Why.** It is the only measured trend that tracks the Town04/Town06 split, and Town04's
fog-robust clear-only student sits at the low end of it:

    84x28   ( 2,352 px)  Town04 student   fog-robust (Town04 disposition D-14)
    168x28  ( 4,704 px)  Town06 student   fog  6.85 ft
    168x56  ( 9,408 px)  Town06 student   fog 11.15 ft

Fog lifts the black floor (p01 0.043 → 0.175 measured on the committed captures) and
compresses dynamic range to 75% of clear. A plausible mechanism is that at low resolution
the downsample averages the haze away and leaves gross lane structure, while at high
resolution the network has four times as much low-contrast detail that is noise under fog.

**The catch, which makes this interesting rather than routine.** T06-F11 measured that
Town06's long straights *need* horizontal resolution: at 84 px the whole 0.668 m CTE budget
spans 1.79 px of image shift at 20 m lookahead. So there may be **no resolution that
satisfies both the straights and fog** — which is itself a clean, publishable finding about
this ODD.

**Crucially, the 6.85/11.15 numbers are a single draw each** (T06-F48), exactly the flaw
that made the w6 refutation worthless. They must be re-measured with a seed sweep before
they are believed *or* dismissed.

**How.**

```bash
export STUDY_MAP=Town06 CARLA_PORT=3000 CARLA_WINDOWED=1 DISPLAY=:0
# For each input size, distil a seed sweep and gate it. The sweep script already
# parameterises IN_W/IN_H; the mixed student's channels stay at w4 to isolate resolution.
for WH in "84 28" "168 28" "168 56" "252 84"; do
  read W H <<<"$WH"
  CK=S_mixed_t06lap_${W}x${H}_w4 CH=32,64,64 FC=128 IN_W=$W IN_H=$H \
  TEACHER=teacher_mixed_t06lap_dagger_r03 BASE=mixed_t06lap \
  DAGGER_DIRS=dagger_mixed_t06lap,dagger_student_S_mixed_t06_t06lap \
  CONDS="clear fog night low_sun" REPS=3 SEEDS="0 1 2 3 4 5" \
  MARGIN_FRAC=0.5 PIN_CK=S_mixed_res_${W}x${H} PROMOTE=0 \
  OUT_DIR=results/town06/res_ablation \
      bash scripts/select_student_seed.sh
done
```

**Watch for:** the capture rig projects to the model input *at capture time*, so a new input
size needs its own captures before it can be certified (`config.py` notes this: two input
sizes mean two capture sets). Driving does not — `evaluate.py` takes `--in-w/--in-h`. So
this ablation is drivable immediately and certifiable only after a recapture.

**An answer looks like:** best fog result per resolution over ≥6 seeds, with the straight
sections' CTE reported alongside. If fog improves monotonically as resolution drops while
straight-line CTE worsens, the trade-off is real and the study should say so.

---

### E2 — Tail-sensitive distillation loss  ★ cheapest real shot

**Question.** Does a loss that penalises the error tail recover fog, where MSE does not?

**Why.** T06-F48 measured that fog's **mean** distillation error is *better* than night's,
which passes — RMSE 0.0272 against 0.0333 — while fog's **p99 error is 0.121, ten times the
steering tolerance.** Average-case fine, tail catastrophic. `distill.py` trains with plain
`nn.functional.mse_loss`, which fits the bulk and is blind to exactly that tail.

This is a documented failure mode of knowledge distillation, not a guess. See
*Knowledge Distillation Must Account for What It Loses* (arXiv 2604.25110): "average-case
accuracy can remain high while robustness, group behavior, or **tail behavior** changes."

**How.** One-line change in `pipeline/distill.py` at the training step, behind a flag so the
default stays bit-identical:

```python
# loss = nn.functional.mse_loss(student(x), y)
err = (student(x) - y).abs()
loss = (err.pow(2) * (1.0 + TAIL_ALPHA * err.detach())).mean()   # up-weights large errors
```

Then sweep seeds at the current architecture and gate exactly as E1 does. Sweep
`TAIL_ALPHA` over a small declared set; **fix the set before running**.

**An answer looks like:** fog p99 error and fog closed-loop CTE, both against the MSE
baseline at matched seeds. Watch that clear/night/low sun do not regress — if the tail loss
trades them away, that is the finding.

---

### E3 — Gradient-alignment distillation (KDIGA)

**Question.** Does aligning input gradients transfer the teacher's fog robustness?

**Why.** This is the literature's specific remedy for the exact symptom — a robust teacher
whose student is not robust — and it is reported to work *across different architectures*,
which is this case (5 conv layers → 3). See *How and When Adversarial Robustness Transfers
in Knowledge Distillation?* (arXiv 2110.12072). Higher implementation cost than E2, higher
ceiling.

**How.** Add `‖∇ₓ f_student(x) − ∇ₓ f_teacher(x)‖²` to the distillation objective. Both
models are differentiable and already loaded together in `distill.py`; the teacher's
gradient can be precomputed per batch. Same seed sweep and gate.

**An answer looks like:** the same table as E2. If E2 and E3 both fail, that is strong
evidence the student *class* cannot represent fog-robust steering at this input size, which
points back to E1 and E4.

---

### E4 — Depth, at matched ReLU count

**Question.** Is the student's 3-conv-layer stack the limitation, rather than its width?

**Why.** Pass 3 varied width and eliminated it. **Depth has never been varied in this
study** — `StudentNet` has been `conv 5x5 s2 → 5x5 s2 → 3x3 s2` throughout, on both maps.
The teacher has five conv layers and four FC layers and drives fog at 0.37 ft.

**The tension worth naming.** The verifier prefers shallow-and-wide: each layer compounds
α-CROWN's relaxation looseness, so a deeper student certifies worse at the same neuron
count. If fog needs depth, then **verifiability constrained the architecture in a way that
caused the failure** — a considerably more interesting result than "the model was too
small", and directly relevant to the paper's thesis.

**How.** Add a `layers=` parameter to `StudentNet` and compare 3 vs 5 conv layers at matched
`relu_count`. Certify both: report bound width relative to tolerance alongside the driving
result, per `07c7a6c` ("verification is cost, not looseness"). Report ReLU count next to
every certified rate, per `4ac6002`.

---

### E5 — Is the screen/gate fog discrepancy real?

**Question.** Under fog, the gate's laps were worse than the screen's lap for the same
checkpoint, in every case observed. Is that systematic or sampling?

**Why.** Observed four times, always the same direction, never reversed:

    w4_s0  screen fog 1.48  →  gate fog 1.70, 1.63, 12.19
    w4_s5  screen fog 1.50  →  gate fog 2.14, 1.98,  2.26
    w6_s4  screen fog 1.21  →  gate fog 6.06, 7.10,  7.02
    w6_s7  screen fog 2.00  →  gate fog 12.02, 11.97, 12.09

Screen and gate are the same code path differing only in `--reps 1` vs `--reps 3`. If it is
systematic, something about repeated laps in one process affects the measurement, and that
would touch every gated result in the study.

**How.** Cheap and decisive: one checkpoint, fog, `--reps 10` in a single invocation, then
ten separate `--reps 1` invocations. Compare the distributions and check whether lap index
predicts the outcome.

**An answer looks like:** either a flat distribution (sampling; the screen just gets lucky)
or a trend with lap index (systematic; investigate before trusting any gate number).

---

### E6 — Re-test the balancing refutation, correctly

**Question.** Does the steering-label imbalance matter, when addressed by a method whose
own refutation does not cover it?

**Why.** `distill.py --balance` exists, is **off by default, and no driver anywhere passes
it** — so every certified Town06 student trained on the raw label distribution, on a route
where **83.8% of frames need |steer| ≤ 0.01**. The E2E literature treats this as a standard
failure mode: >90% of steering labels near zero biases a network toward driving straight,
with up-sampling of curved segments and loss weighting as the named remedies.

The refutation in `config.TOWN06_STUDENTS` (`c1e5dfd`, 2026-08-26) predates the seed sweep
by a week, was measured on the **superseded six-section route**, and refutes only
*downsampling*. Its own argument — "on a route that genuinely IS 84% straight, downsampling
straight frames trains the student for a distribution it will not meet" — is sound, and
does **not** apply to loss weighting, which leaves the input distribution untouched and
changes only each frame's gradient contribution. Note E2 subsumes part of this.

**How.** Seed-sweep three arms at fixed architecture: raw (baseline), `--balance`
(downsample, the refuted arm, re-tested honestly), and curvature-weighted loss. Report all
three whatever they show.

---

## Rules that are not optional

These are the ones that have already cost this study time. Violating them produces results
that look fine and are not.

1. **A restart before every measurement run** (R-SIM-1). `scripts/carla_restart.sh`, or
   `carla_restart_retry.sh` which is *the* one retry policy.
2. **Never `kill -9` a CARLA client** (R-SIM-2). SIGTERM, wait, then SIGKILL.
3. **One client per port** (R-SIM-3). Never drive while a sweep is running.
4. **A run ending in a handful of steps is a bug, not a pass** (R-SIM-6). Check step counts
   before reading verdicts.
5. **Seed-sweep anything you intend to conclude from.** Two conclusions in this repo were
   single draws and both had to be withdrawn.
6. **Pre-register the prediction and commit it before running.** Then report what happened,
   including when it contradicts the prediction — that is the result.
7. **Never relax a criterion after it rejects everything.** Pass 3's gate rejected all 16
   students; the gate stands.
8. **An unmeasured lap is not a failing lap.** The harness now exits 3 and aborts rather
   than blaming the model; keep it that way.

## What must not be touched

* `PROTOCOL.md` §3 and `PROTOCOL.lock` — the frozen constants. Changing one invalidates the
  experiment and needs the §9 amendment procedure.
* `results/town06/ledger` (pass 1), `results/town06/ledger_pass2`, and both certificates.
  R4 requires the originals to stand.
* The `.selected` pins for `S_clear_t06lap_168x56_w2` and `S_mixed_t06lap_168x56_w4` —
  these resolve the certified models. New work pins under its own name (`PIN_CK`) and
  passes `PROMOTE=0`.

## Housekeeping

```bash
python3 -m carla_determinism --port 3000   # preflight
bash scripts/carla_restart.sh              # before EVERY measurement run
python3 scripts/audit_repo.py              # before any release; must be 0 failed
python3 -m pytest tests/ -q -p no:anyio    # 78 tests; the -p flag works around a
                                           # broken anyio plugin in the env
```

`pytest` needs `-p no:anyio` on the old machine because of a system plugin conflict; try
without it first on the new one.

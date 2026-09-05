# Q5 — KDIGA gradient alignment: pre-registration

**Written 2026-09-05, before any Q5 implementation or run.** Queue item
`docs/EXPERIMENT_QUEUE.md` §Q5. Driver `scripts/arm_sweep.sh`, output
`results/town06/kdiga/`.

## The question

> Does adding a **gradient-alignment** term to the distillation objective — matching where
> the student is input-sensitive to where the teacher is — improve the student's fog
> behaviour beyond what matching outputs alone achieves?

## The declared modelling decision — this is what blocked Q5

The obstacle was never the cost of precomputing the teacher's gradient per batch. It is that
**the teacher takes 200x66 and the student 168x56**, so `∇ₓf_teacher` and `∇ₓf_student` are
tensors of different shape and `‖∇ₓf_s − ∇ₓf_t‖²` is undefined.

**Decision, declared here as a modelling choice and not an implementation detail:**

1. **Bilinearly resize** the teacher's input-gradient map from 200x66 to the student's
   168x56 grid.
2. **Normalise each gradient map to unit L2 norm** before comparing them.
3. The alignment term is then `β · ‖ ĝ_s − ĝ_t ‖²` over the batch, where `ĝ` denotes the
   normalised, resized map, added to the existing KD MSE.

**Why normalise.** The two gradients are not commensurable in magnitude across different
input scalings — a gradient with respect to a 200x66 image is not on the same scale as one
with respect to a 168x56 image, and the resize changes it again. Normalising makes the
objective match **where** the two models are sensitive rather than **how much**, which is
what the KDIGA result is about.

**This changes what is being aligned, and that is stated up front** so the result is read as
"aligned normalised input-gradient direction" and never as "reproduced KDIGA".

## Implementation, and the two hazards it must avoid

`distill.py` today loads **only cached teacher targets** (`teacher_targets` returns a dict
of scalars and constructs the teacher network only when frames are missing from the cache).
Q5 needs the teacher **live**, plus a second decode of each frame at 200x66.

* **Hazard 1 — a second preprocessing path.** The repo has been bitten by duplicated filter
  logic before (trap 13, called out in `distill.py` itself: a second copy of the condition
  filter landed in `train.py` and missed `distill.py`). The teacher-side decode **reuses
  `preprocess_for_model`**, the same function `teacher_targets` uses, and does not grow a
  private copy.
* **Hazard 2 — bit-neutrality.** The term is behind `DISTILL_KDIGA_BETA`, **off by default**,
  and with it unset not one line of the existing path changes. Proved the same way Q6's
  change is: re-distil seed 0 at `lr=1e-3` and `lr=3e-4` and compare by SHA-256 against
  `S_mixed_taildet_a0p0_s0` and `S_mixed_depth_d3lr3_s0`. **If either hash differs, the
  change is reverted and Q5 does not run.**

## Declared design

Recipe: the tuned one — `lr=3e-4`, 168x56, channels (32,64,64), fc 128, kernels pinned,
teacher `teacher_mixed_t06lap_dagger_r03`.

**Declared β set, fixed before running: `{0.1, 1.0, 10.0}`**, plus the β = 0 control. The
control is **free** — it is Q1's `lr3e4` arm at n = 15.

Seeds 0–5 per β arm (n = 6), fog and clear, 3 laps. That is 18 distillations and 36 drives.
Gated exactly as Q1 is: same budget, same margin, same VOID rule.

**n = 6 is deliberately small and its consequence is declared now.** E2R-F5 and E4 both show
n = 6 is underpowered for a 20% effect on this endpoint. Q5 is therefore a **screen**: it
can find a large effect or rule one out, and it cannot resolve a small one. **If any β arm
looks promising, it is confirmed at n = 15 as a follow-on, not reported from n = 6** — which
is the exact mistake E4-F1 was caught making and that Q1 exists to repair.

## Predictions — written before any Q5 run

**Q5-P1 — no β arm beats the control on the fog median by more than 25%.** Reason: E1, E2,
E4 and E6 have now all found the seed dominating every objective-side lever except the
learning rate, and the correlation between two objectives at the same seed is r ≈ 0 (the
observation Q6 exists to explain).

**Q5-P2 — β = 10.0 degrades clear.** A gradient term weighted an order of magnitude above
the KD term should trade output fidelity for sensitivity structure.

**Q5-P3 — the alignment term does not reduce the certified bound width.** Alignment shapes
where the student is sensitive; CROWN's relaxation width is driven by layer count and neuron
count, which are unchanged. **If P3 is false — if alignment measurably tightens the bound —
that is the most interesting outcome available in Q5** and it would be a genuinely new
handle on the study's central constraint. It is reported separately and immediately.

## What counts as an answer

* **P1 holds:** the objective-side levers are exhausted on this route — tail loss (E2),
  curvature weighting (E6), balancing (E6/Q4) and now gradient alignment have all failed to
  move what the learning rate moved. That is a clean, citable negative and it closes the
  line.
* **P1 fails:** a real second lever exists; it goes to n = 15 before anything is claimed.
* **P3 fails:** report immediately; it changes what the study can say about the
  verification/accuracy trade-off.

## Bound by

`PROTOCOL.md`, `CLAUDE.md` R-SIM-1..6, standing rules 1, 3, 7, 8. No promotion, no
`.selected` pin, nothing written to either ledger or either certificate. Bit-neutrality of
the default path proved against two committed reference hashes before any Q5 number.

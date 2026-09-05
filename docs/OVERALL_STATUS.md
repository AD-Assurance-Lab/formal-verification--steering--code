# Overall status after the 2026-09-03/04 migration and follow-on experiments

**Written 2026-09-04.** Covers the desktop migration and experiments E1, E1b (which
subsumes E5), E2, the E2 re-run, E4 and E6. Per-experiment detail is in the `*_FINDINGS.md`
files; this is the answer to "does the published result still stand, and what is left?"

---

## 1. The short answer

**The Town06 certification result stands. One supporting claim in the write-up does not,
and one framing sentence needs to change.**

Nothing found in these experiments touches the certificate, the ledgers, the agreement
figure, or the endpoint-only-unsoundness result — the things the paper actually leads with.
What did not survive is a set of **single-draw supporting numbers**, and, more seriously,
**pass 3's ability to attribute the fog failure to the architecture**, because every
student it drove was trained at a learning rate that was never swept.

---

## 2. What is now MORE solid than before

| claim | evidence added |
|---|---|
| The Town06 certificate reproduces | All 6 verdicts and pose counts re-derived on new hardware, new OS, new GPU, new torch/numpy |
| The harness is sound | E1b: one long client process vs twelve fresh ones, Fisher p = 0.414. No process effect; every multi-rep number stands |
| The simulator is the same simulator | Oracle CSVs **bit-identical** to the committed ones across machine, GPU, fresh servers, and windowed vs headless; photometry 0.000–0.003% off reference |
| Fog is the failing condition | Every experiment agrees; no other condition rejected an arm |
| **The arterial fog result is not a model-size artifact** | **E7 (exploratory):** shrinking the arterial student toward the highway student's size makes its fog bound *worse* — 1.69x → 4.15x → 10.21x tolerance at 101,888 → 19,104 → 12,736 ReLU. The obvious sceptical reading of the cross-road comparison is refuted by measurement |
| **The verifier prefers shallow-and-wide** | **E4-F2, newly measured:** at matched ReLU count a 5-conv student's bounds are **2.30x / 3.73x / 3.70x wider** than a 3-conv student's, and the cell the shallow one certifies the deep one does not. The paper asserted this; it is now measured |
| Verification is not the obstruction | E4-F3: depth is worse at driving *and* worse to verify. Shallow-and-wide costs nothing here |

The strongest result in the paper — §4.1, that certifying only at the rendered condition
would have issued sound-looking certificates on two policies that leave the road — is
untouched by everything here.

---

## 3. What the previous work got WRONG

### 3.1 The resolution trend (T06-F48) — refuted

The paper's supporting numbers `168x28 fog 6.85 ft` and `168x56 fog 11.15 ft` are single
draws. Over six seeds those sizes span **1.47–30.48** and **1.56–41.54 ft**, with
best-of-six **1.47** and **1.56**. The trend was an artifact of the draw (E1-F2). This is
the third single-draw claim in this study to fail a sweep.

### 3.2 The KD error figures (T06-F48) — the comparison does not reproduce

The paper writes: *"fog's RMSE (0.0272) is BETTER than night's (0.0333), which passes,
while its p99 error is 0.121, ten times tolerance."* Measured across six baseline seeds on
the shipped architecture:

```
  fog RMSE   median 0.0264   (paper 0.0272 — consistent)
  night RMSE median 0.0276   (paper 0.0333 — OUTSIDE the range of all six seeds, 0.0262–0.0299)
  fog beats night in 4 of 6 seeds, by 4% — not the 22% the quoted pair implies
  fog p99 range 0.0755–0.1265 = 6.3x–10.5x tolerance; median 7.4x, not 10x
```

**The qualitative claim survives and is robust** — every seed has a fog p99 of at least
6.3x tolerance while its fog RMSE is comparable to a condition that passes. **The specific
figures are one draw taken from the favourable end** and should be reported as ranges.

### 3.3 Pass 3's attribution — CONFOUNDED, and this is the serious one

Pass 3 drove 16 students (2 widths x 8 seeds) against a 0.5-margin gate, none passed, fog
stopped every one, and the study concluded the fog failure is *"neither a capacity problem
nor an unlucky draw... it is the distillation to a smaller, shallower student that loses
it."*

**All 16 were distilled at `lr=1e-3`, and no experiment in this study ever varied it.**
E4-F1 measured that changing only the learning rate to `3e-4`:

```
  fog median      11.79 ft  ->  1.91 ft        seeds holding fog 3/3   1/5 -> 3/6
  fog KD p99        0.0977  ->  0.0707         clear does not regress (6/6 held)
  and one seed drives fog at 0.98 ft -- the first student in this study to clear
  pass 3's own 1.095 ft margin gate on fog
```

Pass 3's finding is true of what it ran. It **cannot distinguish "fog defeats this
architecture" from "fog defeats this architecture at this learning rate"**, and the
evidence now points at the second.

The honest status of the effect: **a 6x shift in median, consistent in 5 of 6 seeds, at
Mann-Whitney p = 0.247.** Large enough to act on, not yet publishable.

### 3.4 The balancing refutation — its prediction is falsified

`config.TOWN06_STUDENTS` rejects `--balance` on the argument that downsampling straight
frames trains for a distribution the route will not present, so straight-line accuracy
should suffer. E6-F2: **clear got better** (median 0.93 vs 1.21 ft; margin gate 4/5 vs
2/6), and every balanced seed held fog (5/5 vs 3/6). The refutation was made on the
superseded six-section route and had never been tested on this one.

### 3.5 Infrastructure claims that were simply untrue

* `distill.py`: *"Default 0, so every existing result reproduces exactly."* Three draws of
  seed 0 gave fog p99 0.1027 / 0.1427 / 0.1036. Fixed, and `DISTILL_DETERMINISTIC=1` now
  makes it true on request.
* `requirements.txt` documented an environment no published number came from.
* `REPRODUCING.md` promised bounds reproduce *exactly*; they reproduce to ~4e-3.
* `carla_launch.sh` would silently hand you a server in the wrong render mode.
* `config.relu_count` would have under-counted any student deeper than 3 conv layers.

---

## 4. The sentence in the paper that has to change

> *"On this ODD, no policy good enough to certify exists yet, and the obstruction is
> distillation rather than verification."*

The second half is right and now better supported than before (E4-F2 measures the
verifier's preference; E4-F3 shows depth buys nothing). **The first half is no longer
safe.** A policy that drives Town06 fog at 0.98 ft appeared within six seeds of changing
one hyperparameter, and the tuned arm certifies `low_sun` exactly as the shipped one does.

The obstruction is distillation — and a material part of it is **a hyperparameter that was
never swept**, not something intrinsic to distilling into a small verifiable student.

---

## 5. Experiments still needed before this can be closed out

**`docs/EXPERIMENT_QUEUE.md` is the runnable version of this list**, with commands, costs
and preflight. Summary below; priority order, and the first is a blocker for the paper as
currently written.

1. **Confirm the learning-rate effect at n >= 15 per arm, and sweep it properly.**
   Only `1e-3 / 3e-4 / 1e-4` were tried, at one seed, selected on validation KD MSE. Cost:
   ~30 distillations plus ~180 laps, roughly 6–7 h. **Nothing else should be published
   before this resolves**, because it decides whether §6 of `PAPER_HANDOFF.md` is right.

2. **Re-run the pass-3 gate at the tuned recipe.** Drive the tuned students against the
   pre-registered 0.5-margin gate on all four conditions. If any student passes, the study
   gains what §6 says it barely has — a real test of "certified ⇒ drives safely" — and
   pass 3's conclusion must be restated. ~12 laps per candidate.

3. **Certify a tuned student and score agreement against driving.** E4 certified one
   tuned checkpoint (it certifies `low_sun`, bounds comparable to the shipped student) but
   did not run the blind certificate-then-drive protocol. That is the study's actual claim
   and it should be exercised on the better policy. Requires a fresh pre-registration and
   commit-before-drive ordering.

4. **Confirm balancing at more seeds** (5/5 vs 3/6 is Fisher p ~ 0.18). Cheap once item 1
   fixes the recipe.

5. **E3 (gradient-alignment / KDIGA) is BLOCKED on a design decision, not on effort.** The
   teacher takes 200x66 and the student 168x56, so their input gradients live in different
   spaces and `‖∇ₓf_s − ∇ₓf_t‖²` is undefined without choosing how to map between them.
   `docs/NEXT_EXPERIMENTS.md` says the teacher's gradient "can be precomputed per batch",
   which is true and insufficient. Someone has to decide the mapping before this is an
   experiment.

**What does NOT need re-running:** the Town06 certificate, both ledgers, the witness
exhibit, and the two-scope comparison. Those were re-verified or are untouched by anything
found here.

---

## 6. A methodological result worth carrying into the other studies

Comparing two training configurations in this pipeline is far harder than the study
assumed, and the reason generalises to AEB and multi-condition:

* Seeding python/numpy/torch does **not** pin a distillation draw; cuDNN autotuning and
  non-deterministic reductions do the rest. `DISTILL_DETERMINISTIC=1` fixes it (bit-identical
  weights).
* Pinning the kernels makes a run repeatable but **does not make the seed a control for
  comparing objectives** — correlation between arms at the same seed is r = +0.115 and
  −0.015. Paired designs do not rescue power here (E2R-F1).
* At the observed dispersion, detecting a 20% effect needs **n ≈ 20–60 per arm**. Any
  comparison at n = 6 can only see very large effects, and should say so up front.
* **Report the number of seeds that clear the bar, not the best seed** — and note when the
  median and the reliability disagree, because they did in both E1 and E6.

# Q8c — the undecided cells are FALSIFIED, and the β-CROWN wall was a shape bug

**Run 2026-09-06, 00:20–01:00.** Two results, one of which corrects a conclusion I wrote
four hours earlier in `docs/Q8B_FINDINGS.md`. Both are cheap, and neither needed the
complete verifier the queue budgeted a day for.

---

## Result 1 — the β-CROWN wall was the root input SHAPE, not scale

`Q8B_FINDINGS` concluded that complete verification "cannot currently decide the shipped
cells on this hardware", because a 1-D root forces auto_LiRPA's matrix path, which wanted
7.17 GiB on top of 25.30 GiB on a 31.35 GiB card. **That conclusion was wrong.**

auto_LiRPA's patches path — the memory-efficient one — asserts `image.ndim == 4` on the
**root input** when it concretizes. This study's root is the one-dimensional disturbance
parameter, so patches was refused and matrix was forced. That is a shape problem wearing a
scale problem's costume.

Wrapping the identical network behind a `(1,1,1,1)` root that is immediately reshaped to
`(1,1)`:

```
  shipped student, 101,888 ReLU, the same sub-problem that OOM'd
    conv_mode matrix    CUDA OOM (7.17 GiB on top of 25.30)
    conv_mode patches   Result: unsat        Time: 1.29 s
```

The function is unchanged — a reshape of a single scalar — and the A-1 fidelity replay
still passes against the study's own forward pass (**8.20e-07** shipped, **6.26e-07**
small), with abcrown's own CROWN bound still matching the study's `Bounder` to six decimals.
The graph is demonstrably the same network.

**So the honest statement about reach is the opposite of the one I wrote.** A sub-problem on
the shipped network decides in 1.3 s. A full cell is 2,128 sub-problems, so a
single-threshold pass is ~46 minutes rather than impossible.

### On the "patches stride bug"

Zach asked whether a remembered patches/stride bug applied here. It does not, and the early
history says why. The previous generation used a **vendored SDP-CROWN fork** on a
**pixel-space L∞ ball over 7,056 input dims** (`5f74741`) — a 4-D image root, which is
exactly the patches path where such a bug would live. The current disturbance model is a 1-D
physical parameter and, until this fix, could not reach that code at all. The assertion hit
here is `inplace_unfold`'s `image.ndim == 4` on the root, not a stride miscalculation.

---

## Result 2 — both "undecided" cells are FALSIFIED, with witnesses

This is the larger result, and it needed no verifier at all.

```
  S_mixed_t06lap_168x56_w4_s3, 133 poses, 401-point grid per pose

  cell       attained lo      attained hi      witness?     certificate
  fog          -0.402x          +1.179x        YES (hi)     NOT_CERTIFIED
  night        -1.210x          +0.860x        YES (lo)     NOT_CERTIFIED
  low_sun      -0.207x          +0.289x        no           CERTIFIED
                                                 (all in units of tolerance)
```

### Why the cells looked undecided

`falsify_witness.py` searches a **single global intensity** `s` and finds fog peaking at
0.845x tolerance — no witness. Its own docstring says why that is not conclusive:

> The certifier bounds, per pose, the worst case over s, and THEN averages over poses — so
> s is free to vary from pose to pose. That is deliberate and documented (it covers
> spatially varying disturbance, fog thicker in a hollow) and it is sound. But it quantifies
> over a strictly larger set than a single global intensity, so a NOT_CERTIFIED cell may
> have no witness at all: sound, undecided.

**The repo had the reasoning; what was missing was the measurement of that larger set.**
`scripts/q8c_varying_witness.py` searches one intensity per pose — the family the
certificate actually quantifies over — and finds the attained lap-mean bias is **1.179x
tolerance on fog** and **−1.210x on night**.

### Why that settles it

These are **attained** values: a concrete profile `s_1..s_n`, every `s_i` in `[0,1]`, whose
lap-mean bias exceeds the corridor. So

* the true cell bound is **at least** this bad, hence **no sound method can certify either
  cell** — the refusals are correct, and were never relaxation slack;
* the profile is a **member of the declared family**, so it is a witness in the study's own
  sense. Both cells are **FALSIFIED**, not undecided.

It also retires the question Q8 was chartered to answer, quantitatively:

```
  fog:  plain CROWN 1.240   alpha-CROWN 1.198   attained (true >=) 1.179
        CROWN's total slack over the truth: 0.061x tolerance (5%)
        alpha-CROWN's:                      0.019x tolerance (1.6%)
```

The bound was nearly tight all along. Q8a's finding that fog tightened only 3.4% under
α-CROWN was not α-CROWN failing — it was there being almost nothing left to remove.

### The consistency check that had to pass

**`low_sun` is the one `CERTIFIED` cell, and the search finds no witness for it.** A witness
there would have meant an unsound certificate. There is none, at −0.207x to +0.289x —
comfortably inside the corridor.

So all six Town06 cells now resolve cleanly: **five `NOT_CERTIFIED` cells each with a
witness, one `CERTIFIED` cell without one.** The three-way reading in §Results collapses to
two.

---

## The caveat, which is itself worth reporting

The fog witness uses **90 distinct intensities across 133 poses**; night's uses 84. That is
not a smooth fog field — it is a jagged per-pose profile.

It is unambiguously inside the set the certificate quantifies over, so it makes the refusal
correct. But it is a fair question whether a disturbance family that admits pose-to-pose
intensity jumps is the family the paper wants to defend. Standing rule 4 forbids families so
large they are vacuous; this one is not vacuous — it certified `low_sun` and the shipped
student's `low_sun` cell drives cleanly — but the gap between the two readings is now
measured and is large:

```
  fog, single global intensity (falsify_witness)   0.845x tolerance   no witness
  fog, one intensity per pose (the certificate)    1.179x tolerance   WITNESS
```

**That 0.334x gap is the price of quantifying over spatially varying intensity.** The paper
should state it: the cells are correctly refused, and they are refused because of
disturbances that vary along the route, not because of any single global fog density the
ledger could drive.

---

## What this changes for the paper

1. **§`sec:falsified` can be rewritten.** "Two cells are undecided" becomes "every
   `NOT_CERTIFIED` cell carries a witness, and the one `CERTIFIED` cell carries none".
2. **The undecided category may not be needed at all** for Town06.
3. **A new, honest limitation replaces it:** the witnesses for those two cells are spatially
   varying, so the refusal is correct under the declared family but is not exhibited by any
   single global intensity — which is what a closed-loop drive can produce. The 0.845 vs
   1.179 gap quantifies exactly that.
4. **Complete verification is available if wanted**, at ~1.3 s per sub-problem on the
   shipped network — but Q8c means it is no longer needed to answer the question.

## What was NOT done

No canonical artifact touched: the committed certificate, both ledgers and the original
witness exhibit all stand. `varying_witness.json` is a new, separate artifact. The study
venv is unmodified.

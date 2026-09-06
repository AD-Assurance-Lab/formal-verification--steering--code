# Q8b — β-CROWN on the undecided cells: findings (SUPERSEDED IN PART -- see the header)

> **CORRECTION, 2026-09-06 00:45.** Two central claims below are WRONG and are corrected in
> `docs/Q8C_FINDINGS.md`:
>
> 1. **"The shipped cells do not run"** -- they do. The blocker was the ROOT INPUT SHAPE,
>    not scale or memory. auto_LiRPA's memory-efficient patches path asserts a 4-D root;
>    this study's root is the 1-D disturbance parameter. Behind a `(1,1,1,1)` root the
>    identical shipped sub-problem returns **`unsat` in 1.29 s** instead of exhausting a
>    32 GB card.
> 2. **"Neither undecided cell is resolved"** -- both are. Searching the family the
>    certificate actually quantifies over (one intensity per pose, not one global
>    intensity) exhibits a **witness for each**: fog at +1.179x tolerance, night at
>    -1.210x. Both cells are FALSIFIED, not undecided, and no complete verifier was needed
>    to establish it.
>
> Everything else below stands, including the clamp finding and the export gate. The
> document is kept rather than rewritten so the wrong conclusion and its correction sit
> together.


**Run 2026-09-05, 20:20–21:10.** Pre-registration `docs/Q8_PREREGISTRATION.md` with
amendment A-1, both committed before any bound. Environment built by
`scripts/bootstrap_abcrown_env.sh` (alpha-beta-CROWN `e5c7e17`, auto_LiRPA `5a098e8`,
Python 3.11.16, torch 2.11.0+cu130). Drivers `scripts/q8b_export.py` and
`scripts/q8b_build_onnx.py`. **No simulator.**

## Status, stated up front

**Q8b did not decide either undecided cell, and under its own pre-registered rules it is
not allowed to.** The prediction set is answered as far as the measurements reach:

```
  Q8b-P1  the shipped 101,888-ReLU cells time out      CONFIRMED, and more strongly:
                                                       they do not run at all (CUDA OOM)
  Q8b-P2  smaller networks decide within 2 h           SPLIT -- see below
  Q8b-P3  a decided undecided cell comes back CERTIFIED NOT REACHED; no cell was decided
```

The pre-registration required the loop to reproduce `FALSIFIED` on witness-carrying cells
*before* any result on the undecided ones, and said plainly: *"If the loop does not
reproduce all three, no Q8b result on the undecided cells is reported."* It does not yet,
so none is. **That is the pre-registration working, not a gap in it.**

## What was achieved, and it is not nothing

The integration is real and validated end to end on the tractable size class:

```
  export -> ONNX                                            OK
  A-1 fidelity gate, 1000 inputs                            6.3e-07 to 7.5e-07  (tol 1e-5)
  abcrown's own CROWN bound vs the study's Bounder          agrees to 6 decimals
  beta-CROWN decision on a 12,736-ReLU sub-problem          unsat in 5.0 s
```

The CROWN cross-check is the strongest single piece of evidence that the exported graph is
the study's network. On the shipped student abcrown reported `initial CROWN bounds
[0.15689730]` where the study's own `Bounder` gives `-0.15689751`; on the small student,
`[0.25817892]` against `-0.25817922`. **Two independent implementations, two torch
versions, two numpy majors, agreeing to six decimals on a bound.** That is a stronger
statement than the fidelity replay alone, and it means the A-1 export hazard is closed for
these graphs.

## Finding 1 — the clamp is provably inactive, and it was blocking branch-and-bound

`LinearDisturbance` ends in `Clamp01`, which the exported graph expresses with a
subtraction. alpha-beta-CROWN's branch-and-bound raises
`NotImplementedError: BoundSub` when it tries to branch through it. Bound *propagation*
works; **complete verification cannot run at all on the graph as the study builds it.**

It does not need to. The perturbed image is `x0 + s*(x1 - x0)` for `s in [0,1]` — a convex
combination of two real captures, both already in `[0,1]`. So the clamp cannot fire
anywhere in the certified interval.

That is proved, not assumed. The map is affine in one variable, so its exact elementwise
range over `t in [-1,1]` is `b -/+ |W|`:

```
  pre-clamp range over the whole interval:  [0.024301, 0.580778]
  margin below 0: 0.0243      margin above 1: 0.4192
```

`q8b_build_onnx.py` computes that range and **refuses to drop the clamp if it leaves
[0,1]** — dropping an active clamp would verify a different function and the verdict would
be about a network the study does not use. With the clamp removed, the graph still matches
the study's *clamped* forward pass to **6.26e-07**, which is the empirical confirmation of
the interval proof.

**This is worth reporting beyond Q8b.** The study's disturbance head is, over its own
certified interval, exactly an affine map with no clamp — and the clamp is the only thing
in it that a complete verifier cannot handle.

## Finding 2 — the shipped cells do not time out; they do not run

Q8b-P1 predicted timeouts at 101,888 ReLU. What actually happens is more definite, and it
is a hardware wall rather than a search-time wall:

```
  conv_mode patches   AssertionError: image.ndim == 4
                      auto_LiRPA's patches path assumes a 4-D root input; ours is the
                      ONE-DIMENSIONAL disturbance parameter, which is the whole reason
                      this study's spec is cheap to state.
  conv_mode matrix    CUDA OOM: tried to allocate 7.17 GiB with 25.30 GiB already in use,
                      on a 31.35 GiB card.
```

So the reparameterisation that makes the study's property so clean to express — one input
variable feeding an affine head — is exactly what puts it on auto_LiRPA's unoptimised path.
Patches mode, the memory-efficient one, is unavailable *because* the input is 1-D.

**That is a fair and specific statement about the method's reach**, and it belongs in
Limitations in preference to a vaguer "complete verification does not scale": at this
network size, on a 32 GB card, β-CROWN cannot be run on this spec shape at all.

## Finding 3 — even the smallest network is intractable at CELL granularity

Q8b-P2 predicted smaller networks decide within the 2 h budget. Split verdict:

* **At sub-problem granularity: HELD, comfortably.** 12,736 ReLU, `unsat` in **5.0 s**,
  18 unstable neurons.
* **At cell granularity: FALSIFIED.** A cell is **133 poses x 16 sub-intervals = 2,128
  sub-problems**, and the certificate's statistic is the route-mean over them. At 5 s per
  call that is **~3 h for a single threshold pass** — already over the declared 2 h/cell
  timeout — and an *exact* per-pose bound needs a bisection of several calls each, so the
  realistic figure is a day or more per cell.

The separability that makes the decomposition exact (the mean of exact per-pose maxima *is*
the exact cell bound) does not make it cheap: it multiplies one tractable problem by 2,128.

## Finding 4 — the counterexample path needs an attack, and the attack needs a batch

On a deliberately falsifiable instance (threshold set 1e-4 below a value the grid actually
attains, so a counterexample provably exists), β-CROWN **exhausts the search**:

```
  all nodes are split!!   58 domains visited   Result: timeout   Time: 5.6 s
```

Exhausting the split space is decisive information — the property does not hold — but
abcrown reports `sat` only when it produces a concrete counterexample, which is the PGD
attack's job. The attack evaluates a batch of restarts, and the exported graph has a
**static reshape to `(1, 3, 56, 168)`**, so it dies with
`shape '[1,3,56,168]' is invalid for input of size 846720`.

The obvious fix makes bounding worse, and this was measured rather than assumed: exporting
with `(-1, 3, h, w)` emits a dynamic `Shape`/`Split` subgraph, and auto_LiRPA cannot bound a
`Reshape` whose shape is computed — it fails with an `AssertionError` inside `matmul`. So
the graph can be batchable or boundable, not both, without further work.

**This is the concrete blocker to completing Q8b**, and it is a plumbing problem rather than
a scaling one: an ONNX `Reshape` with a leading `0` (ONNX's "copy this dimension") would be
static *and* batch-preserving. That is the next step, not a new experiment.

## What a reader should take from this

1. **β-CROWN cannot currently decide the shipped cells on this hardware**, and the reason is
   specific: a 1-D root input forces auto_LiRPA's matrix path, which needs more than 32 GB
   at 101,888 ReLU.
2. **The three-way reading in §Results is not yet firmed up.** `NOT_CERTIFIED` still means
   *falsified* or *undecided*, and Q8a plus Q8b together have narrowed *why* without
   resolving it: night's excess is mostly relaxation slack (45% removed by α-CROWN alone),
   fog's is mostly not (3.4%).
3. **The honest headline is a negative with a number attached**, which is what the
   pre-registration asked for: *"A timeout is a result too, and an honest one."*

## What was NOT done

No canonical artifact was touched. No cell verdict was changed, claimed, or written. The
committed certificate, both ledgers and the witness exhibit are untouched. The study venv is
unmodified — verified: torch 2.13.0+cu130, numpy 1.26.4.

## Remaining work, in order

1. Re-export with a batch-preserving **static** reshape (leading `0`), so the PGD attack can
   run and `sat` instances return witnesses.
2. Re-run the A-1 gate and the CROWN cross-check on that graph.
3. Complete the pre-registered validation: reproduce `FALSIFIED` on the three witness-
   carrying `S_clear_t06` cells at sub-problem granularity.
4. Only then, and only if the budget allows, attempt an undecided cell — expecting, on the
   evidence above, that it will not finish.

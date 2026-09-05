# Q8 — complete verification on the undecided cells: pre-registration

**Written 2026-09-05, before any Q8 bound is computed.** Queue item
`docs/EXPERIMENT_QUEUE.md` §Q8. Output `results/town06/beta/`. **No simulator at any point.**

## The question

> `NOT_CERTIFIED` means two different things, and the paper says so: **falsified** (a witness
> was found, the policy is proven unsafe somewhere in the interval) or **undecided** (the
> bound sits outside the corridor, no witness was found, and the excess may be pure
> relaxation slack). Can the two undecided Town06 cells be decided?

This is an upgrade to the headline table, not a new study. Every other item in the queue is
about the policy; **Q8 is about what the verifier can say.**

## The two cells, and exactly how far outside they sit

From the committed certificate and the committed witness exhibit — both untouched by Q8:

| cell | bound `hi_x_tol` | densest witness found | witness? | slack, in units of tolerance |
|---|---|---|---|---|
| `S_mixed_t06/fog` | **1.2400** | 0.8454 | no | ≥ 0.395 |
| `S_mixed_t06/night` | **2.8361** | 0.6552 | no | ≥ 2.181 |

The other three `NOT_CERTIFIED` cells (`S_clear_t06` fog / night / low_sun) all carry a
witness and are **falsified**, not undecided. They are not Q8 targets, but they are the
**loop's validation set** — see Q8b.

A cell is decided by moving `hi_x_tol` below 1.0 (`CERTIFIED`) or by producing a witness
above 1.0 (`FALSIFIED`). Anything else is a timeout, and a timeout is reported as a timeout.

## Q8a — α-CROWN spot-check

`certify_town06.py` builds the `Bounder` with `method="CROWN"`. `Bounder` already accepts
`method="CROWN-Optimized"` (α-CROWN) and auto_LiRPA 0.7.2 already provides it, so this
needs **no new dependency**.

**The knob is exposed as a committed `--method` flag rather than edited in place for the
run** (standing rule 8: committed artifacts come from committed drivers). The flag defaults
to `CROWN`, so the canonical path is byte-for-byte unchanged, and the audit is re-run to
prove the script's refusal-to-overwrite guards still hold.

**Cost, computed rather than guessed.** 133 poses x `nsplit` 16 = **2,128 bounds per cell**.
Measured in `Bounder.__init__`: CROWN 47 ms, CROWN-Optimized 3,654 ms. So ~100 s per cell at
CROWN and **~2.2 h per cell** at α-CROWN — ~4.3 h for both, which is the queue's "hours".

**Q8a-P1 — neither cell is resolved by α-CROWN.** The measured α-CROWN gain on this network
is **6%**. Applied to the excess: fog 1.2400 → ~1.166, night 2.8361 → ~2.666. **Both stay
above 1.0**, so both stay `NOT_CERTIFIED`. Night is not close — it would need a 65%
tightening.

**This prediction is the reason to run Q8a anyway.** It is cheap, it is the only step that
could close the question with no new tooling, and if it is *wrong* — if 6% is an
underestimate on a marginal cell — a cell flips to `CERTIFIED` and plain CROWN has been
refusing a safe policy, which is a result about the study's own instrument.

**Q8a-P2 — the gain is larger on fog than on night**, because fog's bound is nearer the
witness and therefore contains proportionally less slack to remove. If night tightens more
than fog, the slack is not where this reasoning assumes and the Q8b branching heuristic
should be reconsidered before it is written.

## Q8b — β-CROWN proper. **Route 1, declared**

**Route 1 is chosen: pin `Verified-Intelligence/alpha-beta-CROWN` as a new dependency
alongside auto_LiRPA.** It is the reference implementation, it is what the literature means
by β-CROWN, and the alternative (writing the branch-and-bound search loop on auto_LiRPA's
shipped `beta_crown.py`) puts the completeness argument in our own unvalidated code — in a
study whose entire contribution is that its verdicts can be trusted.

The integration is small because **this study's spec already fits the format**: `Bounder`
reparameterises each pose to a **one-dimensional** input feeding an affine head, so the
input box is `[0,1]` in one variable and the property is "output in safe set for input in
box".

**Declared before running:**

* The new dependency is **pinned to an exact commit** in `requirements.txt`, and it must not
  move `torch` or `numpy`. If installing it would upgrade either, the install is **aborted**
  — every checkpoint and every published number in this repo is tied to torch 2.13.0+cu130
  and numpy 1.26.4, and a solver is not worth re-deriving them for.
* Q8b runs in a **separate environment** if that constraint cannot be met in `.venv`.
* **Timeout: 2 h per cell**, declared now so it cannot be extended after seeing a run that
  is nearly finished.

### Validation before the targets — non-negotiable

The loop is run **first** on the three `S_clear_t06` cells that already carry witnesses.
Those cells are **falsified** and their witnesses are committed, so a correct complete
verifier must return `FALSIFIED` on all three, and its counterexample must be a real one —
checked by evaluating the student at the returned input and confirming the output leaves the
corridor.

**If the loop does not reproduce all three, no Q8b result on the undecided cells is
reported.** A complete verifier that cannot re-find a known counterexample is not evidence
about a cell where none is known.

### Scope by network size, cheapest first

| target | ReLU | why |
|---|---|---|
| Town04 `S_clear` / `S_mixed` | 5,152 / 15,456 | most tractable; has `FALSIFIED` cells to check the loop against |
| Town06 small students (E7) | 12,736 / 19,104 | same road and captures as the shipped cells |
| Town06 shipped `S_mixed` | **101,888** | the cells that actually matter; likely the hard case |

**Q8b-P1 — the shipped 101,888-ReLU cells time out.** Complete verification does not scale
like bound propagation, and 101,888 ReLU is large for branch-and-bound. **A timeout is the
predicted outcome and it is an honest result**: it says the cell is undecidable at this
network size with today's complete verifiers, which is a fair statement about the method's
reach and belongs in Limitations.

**Q8b-P2 — the smaller networks decide.** At 5,152–19,104 ReLU the loop terminates within
the 2 h budget on a majority of cells attempted.

**Q8b-P3 — where it decides an undecided cell, the verdict is `CERTIFIED`, not `FALSIFIED`.**
The dense 1-D witness search is thorough on a one-dimensional interval, so a counterexample
it missed is unlikely to exist; the excess is more likely relaxation slack. **If instead a
witness is found, the dense search has a gap**, and that is a defect in an instrument this
study relies on everywhere — reported immediately and separately.

## What counts as an answer

* **An undecided cell becomes `CERTIFIED`:** the excess was relaxation slack and plain CROWN
  was refusing a safe policy.
* **An undecided cell becomes `FALSIFIED` with a witness:** the refusal was correct and the
  dense 1-D search missed it.
* **A timeout:** reported as a timeout, **never as `NOT_CERTIFIED`**, and never quietly
  folded into the existing refusal.

Whatever the outcome, the three-way reading in §Results gets firmer: today it rests on a
witness search that can only ever find counterexamples, never prove their absence.

## Do not

Re-run the canonical certificate with a different method and overwrite it. The committed
certificate is a **plain-CROWN artifact** and PROTOCOL R4 requires it to stand. Every Q8
result is a **separate artifact reported alongside it**, and the α-CROWN and β-CROWN numbers
are labelled with their method everywhere they appear — this repo has already had one
findings document read `alpha-CROWN` off a stale docstring when the code ran plain CROWN.

## Bound by

`PROTOCOL.md` R4, standing rules 1, 7, 8. No CARLA, no driving, no promotion, nothing
written to either ledger, either certificate, or any `.selected` pin.

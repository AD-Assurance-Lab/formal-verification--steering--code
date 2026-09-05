# Q7 — Town06 recapture at 84x28: pre-registration

**Written 2026-09-05, before any Q7 capture.** Queue item `docs/EXPERIMENT_QUEUE.md` §Q7.
Output `results/town06/captures_84x28/` and `results/town06/small_input/`.

## The question

> E7 shrank the arterial student toward the highway student's **capacity** and refuted the
> model-size reading of the cross-road fog result. Does the comparison also hold at matched
> **input size** — 84x28, the direct analogue of the Town04 model?

## Why it needs a new capture at all

Town06's captures are stored **pre-projected to 168x56**: `frames` has shape
`(1, 1060, 1, 1, 3, 56, 168)`. There is no path from those to an 84x28 student's input that
is honest — downsampling an already-downsampled frame is not the same image the 84x28
camera pipeline would produce, and certifying against it would certify a policy that does
not exist. E7 could not certify a small-*input* Town06 student for exactly this reason.

So Q7 is a **capture** experiment before it is a certification experiment.

## Why it is last, and the condition under which it does not run

E7 already answers the size objection on capacity. Q7 only adds the matched-**input-size**
claim, and the queue marks it optional for that reason. It runs after everything that gates
the paper.

## Declared scope — and scope is the thing this item is most likely to get wrong

Standing rule 7 is the binding constraint here, and it has already cost this study once: a
Town04 verification capture inherited a **160 m calibration default** and covered **5.6% of
a 2,861 m lap**, and the certificate, the agreement rate and the write-up all read as
complete. It was found by a second person reading the paper.

**Declared before capture:**

* The capture covers **the same scored road as the committed 168x56 Town06 captures — the
  full 2,289.04 m lap, 133 certified poses at stride 8**, and nothing else.
* **Scope is recomputed from the captured poses**, never read from the artifact's own claim
  about itself. The first version of that guard recorded the *route's* length instead of the
  *captured poses'*, so every short capture would have declared full coverage.
* **The check is two-sided.** Covering more than the study scopes is the same error as
  covering less. A capture that runs long is rejected, not trimmed after the fact.
* The new capture is **compared against what it parallels before it is believed** — pose
  count, span and file size against the committed 168x56 set (standing rule 8). Those
  Town04 captures were **1.8 MB against a published 1.7 GB**, visible the whole time and
  never examined. A gross size mismatch aborts Q7.
* The invocation is a **committed script**, not a hand-rolled command. Town06 survived and
  Town04 failed on precisely this.

## The A-3 capture gate is a precondition, not a diagnostic

No certificate is computed against the new captures until `scripts/capture_driven_gate.py`
passes on them: worst mean |capture − driven| **below the 0.05 threshold**, across all cells.
The reference points are the committed gate results — Town06 at **0.0261**, Town04 at
**0.0065**.

**If the gate fails, Q7 stops and reports the gate failure.** It is not retried at a looser
threshold, and no bound is computed "just to see". A-3 exists because a bound computed on
frames from a mis-rigged camera is sound and describes a camera that is not on the car, and
no verdict downstream of the frames can reveal it.

## Declared design

1. Capture Town06 at 84x28 over the declared scope, with the determinism preflight green on
   a fresh server and the condition verified from a frame (R-SIM-4).
2. Run the A-3 capture gate. Stop if it fails.
3. Distil an 84x28 Town06 student at the tuned recipe (`lr=3e-4`), seeds 0–5.
4. Certify against the new captures, to a **new path**, never the canonical certificate.
5. Compare the certified fog bound width, in units of tolerance, against E7's ladder:
   **1.69x → 4.15x → 10.21x** at 101,888 → 19,104 → 12,736 ReLU.

## Predictions — written before any Q7 capture

**Q7-P1 — the small-input student's fog bound is worse than the 168x56 student's**, in the
same direction E7 measured for capacity. Reason: E7's ladder is monotone and steep, and
reducing input size reduces the first layer's width as well.

**Q7-P2 — the capture gate passes**, at a worst mean |capture − driven| below 0.05 and
comparable to Town06's committed 0.0261. The rig is unchanged; only the projection size is.
**If it fails, that is a finding about the 84x28 projection itself** and it matters more than
the cross-road claim Q7 was run to support.

**Q7-P3 — the cross-road comparison survives at matched input size.** The arterial fog bound
stays worse than the highway one. This is the claim Q7 exists to test, and E7 already refuted
the capacity-based objection to it.

## What counts as an answer

* **P3 holds:** the cross-road comparison is now defended at matched capacity *and* matched
  input size, and the sceptical reading is closed from both directions.
* **P3 fails:** the cross-road comparison is an input-size artifact after all. That would be
  a serious correction to a claim in the paper and is reported immediately and separately —
  it is precisely the outcome that makes Q7 worth the 2 h.
* **P2 fails:** Q7 stops at the gate and reports it.

## Bound by

`PROTOCOL.md` A-3 and R4, `CLAUDE.md` R-SIM-1..6, standing rules 1, 3, **7** and 8. Nothing
written to `results/town06/ledger`, `ledger_pass2`, either committed certificate, or any
`.selected` pin.

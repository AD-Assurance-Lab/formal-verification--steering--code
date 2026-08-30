# PROPOSED PROTOCOL AMENDMENT A-3 — draft, NOT applied

**Not committed to `PROTOCOL.md`.** §9 records amendments as requested by Zach, and the
document is hash-locked precisely so it is not edited unilaterally. This is the draft for
review.

---

## A-3. The capture gate is a precondition of certification

**Date:** 2026-08-30. **Requested by:** *(pending)*

**What changed.** §4a names one precondition the certificate assumes but does not verify
— clear-weather competence — and enforces it mechanically. There is a second, and it is
stated in the paper as though it were already enforced:

> Before any certificate is computed we require captured steering to match the steering
> the vehicle actually commanded at the same locations. Over a full lap the mean absolute
> difference is 0.0137 in normalized units across all 1,600 poses, against a threshold of
> 0.05. This check is cheap and it is not optional.

**No script computed it, and neither rebuild ran it.** The number in the paper comes from
the published era. The gate exists now as `scripts/capture_driven_gate.py`, and
`scripts/audit_repo.py` fails when a certificate exists without a gate artifact.

**Why it matters.** The bound is computed offline on captured frames; the claim is about a
driving vehicle. If the capture rig and the driving rig differ — ride height, pitch, FOV —
the bound is sound and about a camera that is not on the car. This is not hypothetical: a
ride-height error made one direction's captures disagree at 0.202 while the other passed
at 0.016, purely because its opening stretch is flat.

**What it invalidates.** Per §9.5, an amendment made after the corresponding result exists
invalidates that result. The Town06 certificate was computed without a gate artifact and
therefore does not satisfy the amended protocol as it stands. It is reinstated only if the
gate passes **on the captures that certificate actually used**, and the result must say
that the gate was run after the fact rather than imply it gated the certificate. If the
gate fails, the Town06 deployment-test certificate is invalid and is withdrawn.

Town04 (discovery test) has been re-gated on its recaptured laps: worst mean
|capture − driven| **0.0070** against the 0.05 threshold, over ~1,510 poses per direction.

**What it does NOT change.** No frozen constant in §3, so `PROTOCOL.lock` is unchanged.
R1, R2 and R3 are untouched. The gate is deterministic given fixed artifacts and has
nothing to tune, so it cannot launder a verdict.

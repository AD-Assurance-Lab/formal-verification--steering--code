# What the previous study established

Two generations of work preceded this repository. Most of it was negative results, and
those negative results are why this study is designed the way it is. The full findings log
is not public; this is the part that constrains the current design.

## Settled

1. **A semantic-segmentation dataset cannot calibrate photometric disturbance models.**
   Not fixable by better technique. The acquisition and processing chain removes exactly
   the quantities a disturbance model needs — pixel correspondence, absolute exposure,
   high-frequency structure, depth. Worth publishing as a caution.

2. **Physics supplies the parameters; the simulator supplies image formation.** Fog → MOR
   (m), rain → mm/h, night → lux, snow → mm/h. A certificate then reads "certified above
   85 m visibility", which is language a safety case can consume.

3. **Physical parameterization is what makes verification tractable**, not the choice of
   verifier. Low-dimensional theta means branch-and-bound costs `k^d` instead of
   `2^thousands`. A full-dimensional pixel-space L2 ball measured ~60x vacuous on the same
   network and frame.

4. **SDP-CROWN is not usable here and never actually ran.** Gated on an L2 ball; with
   L-inf it silently degrades to alpha-CROWN. Given an L2 ball it explodes, because
   auto_LiRPA tracks a scalar radius that cannot represent a low-rank ellipse.

5. **Closed-loop verdicts must be failure rates over repetitions.** Near the stability
   cliff a single run is wrong about 1 in 8 times.

## The result that should have been treated as a bug

A student trained on photometric disturbances certified **worse** in fog than a clear-only
student at every visibility below ~1000 m:

| MOR ≥ | clear-only | photometric |
|---|---|---|
| 1000 m | 94.5% | 96.0% |
| 400 m | 88.5% | 83.0% |
| 150 m | 85.5% | 69.5% |
| 60 m | 66.0% | 44.0% |

This is the exact opposite of what the study design predicts, and it was written up as a
"counter-intuitive finding" rather than triggering a bug hunt. **Two candidate causes were
never ruled out:**

- **Train/verify family mismatch.** The student was trained on affine photometric boxes and
  then certified against a Koschmieder fog model indexed by MOR. It was never trained on
  the thing it was verified against.
- **Capacity cost.** The photometric student was 2x width — 10,304 ReLU vs 5,152 — and its
  UNKNOWN (bound-looseness) rate was 11.5% against 1.5%. Its bounds may simply be looser.

Both are addressable. The first is prevented by construction under this study's design
rule (train on the parameterized family, verify over the same family's interval). The
second is measurable by holding width fixed across the two students.

**This is the reason `study/ledger.py` exists.** The failure was not a lack of rigour at
the local level — the measurement was repeated by independent means. It was that nothing in
the process required the result to be checked against the top-level claim.

## The fog certificate, and why it was qualified

A fog certificate was computed and was correctly computed, but the disturbance it certified
was contrast reduction with almost no brightness change: the model moved the road mean by
0.003 across its whole certified range, while the renderer darkened the road by 0.248. The
airlight constant `A = 0.78` was unidentifiable from data and happened to sit almost exactly
on the simulator's clear road brightness (0.811), which is what made the model
mean-preserving. Moving `A` to 0.64 or 0.90 collapsed the certified rate from 88% to under
5%.

Root cause: the simulator's clear road ROI sat at mu = 0.81 where a real road is ~0.31 —
so a physically correct daylight airlight landed *on top of* the road and did nothing.

**This study's diagnosis (D1 in `STUDY.md`):** the RGB camera was configured with only
`image_size` and `fov`, leaving CARLA's default per-frame histogram **auto-exposure**
active — the same defect that disqualified the real-world dataset. Fixing the camera rather
than the weather preset is M1's first measurement.

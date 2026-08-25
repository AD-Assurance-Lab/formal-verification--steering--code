# Constraints

Each of these is a **measured result** from the previous study, not a preference.
Violating one silently reproduces a bug that has already cost time.

1. **No dataset-derived photometric calibration.** A real-world adverse-weather dataset
   (ACDC) cannot supply the quantities: no pixel correspondence between adverse and
   reference frames, auto-exposed so absolute photometry is gone, video-denoised so sensor
   noise is gone, no controlled clear baseline, no depth. Its role here is an
   exposure-invariant plausibility check and a published caution — nothing more.

2. **No SDP-CROWN.** It requires an L2 ball, never actually ran, and is vacuous on
   low-rank sets. Use **alpha-CROWN + input-space branch-and-bound**. Do not vendor
   `auto_LiRPA`; depend on upstream via pip.

3. **Disturbances apply at full sensor resolution, before crop and downsampling.** Never to
   the network input.

4. **Certify against the closed-loop tolerance**, with the corridor centred on
   **clear-weather** steering. The per-frame corridor is ~3.4x too permissive — a vehicle
   departed the road with every frame inside it.

5. **Every closed-loop number is a failure RATE over >= 10 repetitions.** Never a single
   run. Report Wilson intervals.

6. **Relaunch CARLA before every measurement run.** It leaks ~10.5 GiB over 11 h.

7. **Verify pixel alignment before any paired photometric fit**, including on simulator
   output.

8. **The verifiable student stays ReLU-only, no BatchNorm/Dropout.** Width is the primary
   capacity lever.

   **Refinement (v3, reasoned — not yet measured).** The previous study retired resolution
   sweeps because "resolution enlarges the box the verifier must bound." That held for
   pixel-space L-inf verification. It does **not** hold under the physical
   parameterization: the verifier's input is `u` of dimension 1-2, and the disturbance
   layer maps `u` to the image exactly, so resolution no longer inflates the perturbation
   dimension at all. Resolution still costs — more pixels means more ReLU neurons and
   looseness accumulates through their relaxations — but it is now an ordinary
   network-size cost rather than the dominant penalty.

   **Practical consequence:** if width alone cannot carry a condition (shadows are
   the likely cases), resolution is back on the table. Confirm against the measured bound
   tightness at M5 before relying on it.

9. **Keep a known-bad negative control in every experiment.** `S_clear` must fail the
   conditions it never saw. That control is what caught the corridor-centring bug.

10. **Do not over-optimize in either direction.** No BatchNorm, Dropout, or ResNet-class
    architectures in the verifiable net — they cause interval-bounds explosion. But do not
    collapse to a trivial linear controller either; it must still drive the Town04 curves
    closed-loop.

11. **Scope:** Town04 highway, 20 mph, pure-pursuit centreline labels, fixed reference
    centreline (immune to CARLA's lane-snapping), physics-honest PI speed controller —
    never a velocity override, which corrupts the lateral dynamics CTE measures.
    Disturbance characterization gets 1-1.5 pages total in the paper across all conditions.

12. **No lead condition.** The story is formal verification as a technique, not any one
    weather condition. Execution order is risk-ordered; the paper presents conditions
    symmetrically.

## Derived safety criteria

Derive these from measured primitives in `config.py`. Never hardcode the results.

| quantity | value | derivation |
|---|---|---|
| CTE budget | 0.668 m (2.19 ft) | (lane 3.500 − vehicle 2.164) / 2 |
| per-frame steering corridor | 0.050 rad = 0.041 normalized | 2·L·CTE_budget / (v²T²), T = 1 s |
| closed-loop tolerance | ~0.012 normalized | measured stability cliff; **derive, do not hardcode** |

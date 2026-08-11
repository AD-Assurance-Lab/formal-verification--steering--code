# Traps — the do-not-rediscover list

Twenty mistakes from the previous study. Most are one-line fixes that took days to find.
Roughly half are encoded as runnable checks in `conformance/`; the rest need CARLA or a
GPU and become live tests at their milestone.

## Measurement and data

1. **Verify pixel alignment before ANY paired photometric fit, including on simulator
   output.** Use `study.goc.require_aligned` — ~1.0 aligned, ~0.1 not. Real-world
   adverse/reference pairs sit at the unrelated-image null, and so do **two separately
   driven CARLA laps** (0.235 against a 0.242 null). Three airlight estimates were computed
   on unpaired frames and withdrawn before anyone checked. Only pose-matched capture
   produces aligned pairs. *[conformance]*
2. **CARLA's sensor queue runs a frame behind.** Taking one image per `world.tick()`
   silently returns the *previous* condition's frame, mislabelling the entire dataset while
   looking completely plausible. Synchronize on the frame id `world.tick()` returns. With
   an RGB *and* a depth camera, both must be matched. *[needs CARLA]*
3. **CARLA leaks GPU memory** — ~10.5 GiB over 11 h, degrading results long before it
   crashes. Relaunch the server before every measurement run. *[needs CARLA]*
4. **Closed-loop is stochastic near the stability cliff.** The same configuration gives
   different pass/fail outcomes about 1 in 8 times. Every closed-loop number is a failure
   RATE over >= 10 repetitions. *[needs CARLA]*
5. **n=1 photometric comparisons are worthless.** A single-frame measurement produced a
   confident, wrong sign-reversal claim that survived until it was re-measured over 150
   poses. *[needs CARLA]*

## Verification

6. **Centre the safety corridor on CLEAR-weather steering, not the disturbed midpoint.**
   Centring on the midpoint certifies only insensitivity to the disturbance *parameter*
   while permitting an arbitrary systematic offset from what clear weather would produce —
   which is precisely the hazard. This bug made night read 100% certified while failing 85%
   of closed-loop frames. *[conformance]*
7. **The per-frame corridor (0.041 normalized) is ~3.4x too permissive.** A vehicle
   departed the road with every single frame inside it. Certify against the closed-loop
   tolerance, and derive it from measured primitives rather than hardcoding it.
   *[conformance]*
8. **Model clamping soundly**: `clamp(v) = 1 - relu(1 - relu(v))`. Omitting it makes bright
   additive layers look linear when they are not. *[conformance]*
9. **Apply disturbances at full sensor resolution, before crop and downsampling.** Applying
   them to the network input makes the disturbance model network-specific and averages ~57
   source pixels into each student pixel. *[conformance]*
10. **SDP-CROWN is gated on an L2 ball** (`input_rho`, populated only when `norm == 2.0`).
    With L-inf it silently degrades to alpha-CROWN — a previously published "SDP-CROWN"
    result was an alpha-CROWN result. Given an L2 ball it engages and explodes, because
    auto_LiRPA tracks a scalar radius that cannot represent a low-rank ellipse. Use
    **alpha-CROWN + input-space branch-and-bound**. *[needs GPU]*
11. **auto_LiRPA patches-mode crash:** the elementwise form `x' = x*(1+eps_c) + eps_b`
    triggers a stride-2 `as_strided` RuntimeError. Use the `nn.Linear` reformulation.
    *[needs GPU]*
12. **Linearity probing.** Use the float path with **no clipping** (clipping makes bright
    additive layers look nonlinear), and choose a probe delta large enough to clear uint8
    quantisation — `delta = 0.01` amplifies a +/-1/255 rounding error by 100x. Probe in the
    linearized parameterization, not the physical one. *[conformance]*

## Training

13. **Condition filtering silently drops legacy rows.** Rows predating condition tracking
    have no `condition` field, so `r.get("condition") in keep` discards them — 6,783 base
    frames, surfacing much later as an unrelated "Sample larger than population" crash.
    **Grep for every filter site when fixing a bug like this**; one was patched and the
    other missed. *[conformance]*
14. **DAgger diverges without warm start** on multi-condition data. Fine-tune from the
    previous round's checkpoint at reduced LR (`--lr 5e-4`).
15. **DAgger needs beta-mixing.** Without it the policy drives off the road, crashes, and
    sits there collecting ~43 frames per round instead of a full lap.
16. **DAgger must be resumable**, and the manifest written **per lap**, not per round.
    Non-resumable rounds silently degrade to repeated behaviour cloning.
17. **Preload datasets in parallel.** Single-threaded preload of 67k frames takes >10 min
    and silently outlasts the training it precedes. *[conformance]*
18. **Check `--distill-dirs` and similar defaults.** A default pointing at old directories
    trained a student on stale data. *[conformance]*
19. **Pass the vehicle to `set_weather`** so headlights follow the condition. Without it,
    night rounds drive with headlights off, which is physically impossible for a real
    vehicle and makes any night result an artifact. *[needs CARLA]*

## Interpretation

20. **A behavioural fidelity gate does not prove the disturbance is reproduced.** It
    compares *steering deviation*, so a model can pass while being a materially different
    image transformation from what the renderer produces — fog passed at 1.25-1.38x while
    moving the road mean by 0.003 against the renderer's 0.248. Check image statistics
    (mu, sigma over the ROI, per depth band) as well. See D3 in `STUDY.md`.

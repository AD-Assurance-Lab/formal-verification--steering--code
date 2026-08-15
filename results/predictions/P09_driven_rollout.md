# Driven-offset captures do NOT rescue the rollout: the response is not a function of state

The capture rig built this session (`scripts/capture_driven_offsets.py`) removes the defect
F42 measured: frames now come from a vehicle genuinely driving off-centre, with the
suspension state, sensor motion and camera pose that go with it, instead of from a teleported
and settled one. Coverage is better than the static grid it replaces -- +-1.2 m offset,
+-9 deg heading, offset and heading decorrelated (|corr| 0.057), ~10,215 frames per
condition over 6 phases, 8 conditions eastbound.

It did not fix the rollout, and the reason is measurable.

## The number that decides it

A rollout integrates the steering difference every step, so the model of the local response
has to be accurate to well BELOW the disturbance term it integrates:

    disturbance term a rollout integrates      0.0052
    nominal capture error (gate A)             0.0137
    static grid, gain-corrected (F42)          0.0258
    DRIVEN captures, local plane fit           0.049 - 0.055     <- worse

The local model is a least-squares fit per 6 m bin,

    steer ~ a + b ds + k_o o + k_psi psi

with `ds` the along-road position inside the bin (added specifically to absorb curvature
variation, which improved the residual only from 0.052 to 0.050). Roughly 21 samples per bin,
507 bins used over the lap.

**The residual is ten times the signal.** Any verdict read off this is noise, so the
agreement figure below is reported only to be explicit that it was not used as evidence:

    agreement 4/10   (static-grid rollout scored 2/6 canonical, 2/2 sun)

## What this actually establishes

The failure is not the captures. Driven frames are the best measurement of the policy at an
off-nominal state that this study can make, and the response still does not fit a plane in
(offset, heading) at a pose to better than 0.05.

The natural reading is that **for a moving vehicle the steering output is not a well-defined
function of (offset, heading) at a pose.** It depends on the trajectory taken to reach that
state -- steering history, transient attitude, what the camera saw a moment earlier -- none
of which a state-indexed surface carries. A rollout assumes exactly that such a function
exists. If it does not, no improvement in capture fidelity will make the rollout sound, and
the three capture generations tried here (static grid, gain-corrected static, driven) are
consistent with that: 0.0258 -> 0.049, moving the wrong way.

## Why the per-frame certificate is untouched

It compares one bound to one threshold and never accumulates. Its captures passed the gate
built for that use (0.0137 against a 0.05 threshold), and the canonical twelve stand at
12/12. This finding bounds the loop route, not the certificate.

## Open item, recorded rather than resolved

In the final table `S_mixed / shadows` and `S_mixed / sun15` returned identical peak (1.875 m)
and identical residual (0.05469) to three decimals. Two different captures should not agree
exactly. That smells like a cache or indexing defect in `scripts/driven_rollout.py`, and it
must be resolved before that script is trusted for anything -- though it does not affect the
residual measurement above, which is computed per capture and is ~0.05 for all ten cells.

## If this is picked up again

The question to answer first is not "which statistic" but "is there a state-indexed function
at all". A direct test: drive the same pose from two different approach trajectories and
compare the steering. If they differ by ~0.05, the rollout premise is dead and the loop route
needs a model with memory (the policy is effectively dynamic), not better captures.

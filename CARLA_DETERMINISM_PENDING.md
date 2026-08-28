# PENDING: a CARLA harness defect affects this study's closed-loop runs

**Written 2026-08-28. Nothing in this repo has been changed. No result, figure, checkpoint
or number here has been modified, and the released v1.0.0 artifact is byte-identical to
what it was. This file is a warning, nothing more.**

Do not start any re-measurement without talking to Zach. Town06, on the
`validation/town06-deployment-test` branch, is being finished first and is the reference
implementation for the fix.

## What was found

Measured on the Town06 branch on 2026-08-28 (`docs/TOWN06_FINDINGS.md`, T06-F22, on that
branch). Two defects in the simulator harness, both of which this study's runs also carry:

1. **`vehicle.apply_control()` races `world.tick()`.** Synchronous mode with a fixed
   timestep synchronises the *tick*, not the *command queue feeding it*. The race is
   invisible while a command is unchanged, because a late arrival re-applies the same
   value — so it only bites on a step where the command *changes*, which in a closed-loop
   run is every step. Measured open loop with the feedback cut and an identical scripted
   command sequence, three repetitions finished **60 m apart**.

2. **UE4 streams texture mips asynchronously**, so which mip is resident when a frame
   renders depends on load timing rather than on world state. `-notexturestreaming` cut
   the steering noise the renderer injects by **168x**, and removed the pattern where the
   first run after a server restart disagrees with every later run.

Neither is visible in a result. Both produce physically plausible trajectories, and every
determinism setting this study pinned was pinned correctly — they were aimed at the wrong
layer.

## What this does and does not mean for the published results

**It does not invalidate them.** Every closed-loop number here is already reported as a
failure *rate* over at least ten repetitions with a Wilson interval, which is the correct
reporting form for a stochastic process and remains correct. The rates are rates over
something real.

**What it does mean** is that the run-to-run variation those rates average over was larger
than it needed to be, and its source was uncharacterised at the time. It is now
characterised: after both fixes, bit-exact closed-loop replay is *still* unreachable — a
scene where nothing moves at all renders ~30 differing pixels of 307,200 across
repetitions — so repetitions would still have been required. The defects made the noise
roughly 168x larger than the floor.

**One finding is strengthened rather than weakened.** With physics made bit-exact, a
2.6e-6 steering perturbation still grew to 7.6 ft of cross-track error over 349 steps.
That amplification is a property of the *policy*, not the simulator: a contractive policy
suppresses such a perturbation and a marginal one grows it. Run-to-run spread is therefore
readable as a closed-loop stability-margin measurement — which is this study's own thesis
appearing again, in the instrument rather than in the model.

## If and when Town04 is re-measured

The decision is Zach's and it is queued behind Town06. If it happens:

    pip install carla-determinism        # repo: carla-determinism--simulation--package

    import carla_determinism as cd
    client = carla.Client(host, port); cd.bind_client(client)
    cd.require_deterministic(port, world, fixed_dt=..., deterministic_control=True)
    cd.apply_control(vehicle, control)   # everywhere; never vehicle.apply_control()

and launch with `-notexturestreaming -quality-level=Epic`. Read `RULES.md` in that package
first — D-1..D-11, each a measurement with the cost of violating it recorded. Two are easy
to get backwards: **do not disable `enable_postprocess_effects`** (manual exposure lives
inside the postprocess chain; disabling it measured ~2000x worse) and **do not drop below
`-quality-level=Epic`** (High measured catastrophically worse).

Note rule **D-11**: data captured under a violating harness is not reusable, because the
training images carry texture-mip variation a corrected evaluation never shows. A Town04
re-measurement is therefore a recollection from step 0, not a re-run of the existing
checkpoints — which is precisely why it is a real decision and not a formality.

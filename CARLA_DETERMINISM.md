# CARLA determinism standard — AD Assurance Lab

**Status:** lab-wide. Applies to every study, every repo, every person.
**Origin:** measured in `formal-verification--steering--code` on 2026-08-28, on the
Town06 branch, after a competence gate reported "held 2/3" for a checkpoint that had not
changed. See `docs/TOWN06_FINDINGS.md` T06-F22 for the full measurement record.

This file is hash-locked. `CARLA_DETERMINISM.lock` holds a SHA-256 over the frozen
section below, and `scripts/check_carla_determinism.py` refuses to certify a simulator
whose standard has been edited without going through the amendment procedure in §4.
Editing the rules to make a run pass is the failure this is built to prevent.

---

## 1. What was actually wrong, in one paragraph

Synchronous mode with a fixed timestep synchronises **the tick**, not the **command
queue feeding it**. `vehicle.apply_control()` is a fire-and-forget RPC: it returns as
soon as the message is written, and whether the server has registered it before it
processes `world.tick()` is a wall-clock race. The race is invisible while a command is
unchanged — a late arrival re-applies the same value — so it only bites on a step where
the command *changes*, which in a closed-loop run is every step. Measured open loop,
with the feedback cut and the command sequence a pure function of the step index, three
repetitions of one scripted run ended up **60 m apart**. Nothing in the result reveals
it: both trajectories are physically plausible, and every determinism setting the study
had pinned was pinned correctly.

---

## 2. Frozen rules

Every rule below is a measurement, not a preference. The bracketed figure is what
violating it cost when it was measured.

**D-1. Synchronous mode, fixed timestep, substepping that covers the whole step.**
`fixed_delta_seconds <= max_substep_delta_time * max_substeps`, or physics silently
advances less than the full step and the vehicle covers less ground than its reported
velocity implies.

**D-2. Never issue a vehicle command with a fire-and-forget RPC.** Use an acknowledged
batch command — `client.apply_batch_sync([carla.command.ApplyVehicleControl(...)],
False)` — so the command is provably registered before the tick that consumes it.
[`apply_control()`: physics diverges the first time a command changes; up to 60 m over
200 steps. `apply_batch_sync`: pose, velocity, gear and applied-control readback
bit-identical for every step of every rep.]

**D-3. Launch the server with `-notexturestreaming`.** UE4 streams texture mips in
asynchronously, so which mip is resident when a frame renders depends on load timing
rather than on world state. [Dominant render entropy source: injected steering noise
3.9e-3 -> 2.4e-5, a 168x reduction, and it removes the cold-server first-run outlier
that otherwise makes run 1 of every session disagree with runs 2..N.]

**D-4. Keep `enable_postprocess_effects` TRUE and pin exposure manually.** Manual
exposure lives *inside* the postprocess chain, so disabling postprocessing silently
un-pins it. [postprocess off: injected steering noise rose to 4.8e-2, the worst of any
configuration tested — ~2000x worse than leaving it on.]

**D-5. `-quality-level=Epic`.** Not a visual preference — a determinism result.
[High: 5.2e-1, catastrophically worse than Epic's 2.4e-5.]

**D-6. One client per port, and restart the server before every measurement run.** In
synchronous mode any connected client's `tick()` advances the world, so two processes
ticking one server corrupt each other while both appear to work. A long-lived server
also degrades silently: it keeps answering and keeps reporting plausible velocities
while it stops advancing physics correctly.

**D-7. Bit-exact closed-loop replay is NOT achievable, and no configuration reaches it.**
On a scene where nothing moves at all — vehicle held on the brake, zero displacement to
full float precision, camera rigid, weather fixed, exposure manual — frames at the same
index across repetitions are never bit-identical. The floor is ~30 pixels of 307,200
differing by at most 13 levels, and a longer settle does not converge it away, so it is
generated per frame rather than inherited. **Therefore every closed-loop number remains a
RATE over at least 10 repetitions with a Wilson interval.** D-1..D-6 shrink the noise;
they do not remove it, and no future version of this document may claim they do without
a measurement that shows a frozen scene rendering bit-identically across reps.

**D-8. Measure determinism OPEN LOOP, never closed loop.** A closed-loop probe measures
physics, rendering and feedback amplification at once, so every candidate cause produces
the same symptom and none can be distinguished. Cut the feedback: drive a command
sequence that is a pure function of the step index, and record pose, a hash of the raw
sensor buffer, and the model's output *computed but not applied*. Those three streams
separate physics from rendering from amplification.

**D-9. A determinism probe must be able to fail.** Check subprocess return codes, and
confirm each repetition actually rewrote its artifact before comparing — results files
are usually overwritten in place, so a crashed repetition leaves the previous one on
disk and the probe compares a file with itself and reports IDENTICAL. Copy each
repetition's output to its own path before the next one runs. [This defect produced a
false "runs are reproducible" result that contradicted the true measurement and cost a
day.]

**D-10. Amplification is a property of the POLICY, not the simulator.** With physics
bit-exact and only the render floor left, a 2.6e-6 steering perturbation grew to 7.6 ft
of cross-track error over 349 steps. A contractive, competent policy suppresses that
perturbation; a marginal one amplifies it. So run-to-run spread is a *measurement of
closed-loop stability margin*, and a policy whose verdict flips between repetitions is
reporting its own marginality. Do not "fix" that spread by adding repetitions until the
verdict settles.

---

## 3. Preflight

`scripts/check_carla_determinism.py` asserts D-1 through D-6 against a live server and
the standard's own hash, and is called by every entry point that produces a measurement.
It reads the server's actual command line from `/proc`, so a server launched by hand
without the required flags is caught rather than trusted.

    python3 scripts/check_carla_determinism.py          # verify, exit 1 on violation
    python3 scripts/check_carla_determinism.py --write  # regenerate the lock (§4 only)

## 4. Amendment procedure

A rule changes only by: stating what measurement contradicts it, recording that
measurement in the study's findings file, changing the rule, regenerating the lock in
the same commit, and naming the amendment here. A rule may not be relaxed because a run
is inconvenient. Amendments so far: none.

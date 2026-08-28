# Start here

Updated 2026-08-28. **The determinism question from T06-F21 is RESOLVED** — see
`docs/TOWN06_FINDINGS.md` T06-F22 for the full record, and `CARLA_DETERMINISM.md` for the
rules that came out of it.

## What was wrong, and what changed

Two independent causes, both measured open loop with the feedback cut:

1. **`vehicle.apply_control()` lost a race with `world.tick()`.** Synchronous mode
   synchronises the tick, not the command queue feeding it. Up to 60 m of divergence over
   200 steps from an identical scripted command sequence. **Fixed** — every driving loop
   now goes through `env.apply_control()`, which issues an acknowledged batch command.
   Physics is now bit-identical across reps.
2. **Texture streaming.** `-notexturestreaming` cut the steering noise the renderer
   injects by 168x and removed the cold-server first-run outlier. Now default for Town06.

**Residual, and it is irreducible:** a frozen scene still renders ~30 differing pixels
per frame across reps. In closed loop that 2.6e-6 steering perturbation grows to 4-8 ft
of CTE over 349 steps. So **standing rule 3 stands**: every closed-loop number is still a
rate over >=10 reps — now justified by measurement, with the noise 168x smaller.

**Town04 is untouched and stays that way.** `DETERMINISTIC_CONTROL` is off there,
`-notexturestreaming` is Town06-only, the preflight runs on the Town06 path only.

## Harness self-check, before trusting anything

Drive the oracle twice and compare. It never reads the camera, so under the corrected
harness it is bit-identical, and anything else means the harness has regressed:

    bash scripts/carla_restart.sh > /tmp/r.log 2>&1     # never pipe this; it daemonises
    cd pipeline && python3 drive_expert.py --direction all
    # copy results/oracle_s0*.csv, restart, repeat, then cmp

Verified 2026-08-28: all six sections bit-identical across fresh servers.

## Do this next

1. **The capacity decision, still open and still addressed to Zach**
   (`TOWN06_STATUS.md`). The determinism fix does NOT make a marginal student competent.
   Options unchanged: widen both students, widen the mixed only, or collect more base
   data first. T06-F22 sharpens the argument — run-to-run spread is now readable as a
   stability-margin measurement, so "held 5/6, then 6/6" says the student has no margin.
2. **Re-run the competence gate** under the corrected harness once capacity is decided.
   Every closed-loop student number from the previous session remains untrusted.
3. Then resume the order in `TOWN06_STATUS.md` from step 5.

## Running the simulator

The `carla-determinism` package is now the authority on determinism and is hash-locked;
`CLAUDE.md` keeps the operational hygiene rules (R-SIM-1..6). Both still apply.

    python3 -m carla_determinism --port 3000       # preflight; entry points call it too
    bash scripts/carla_restart.sh                  # before EVERY measurement run

**Never pipe or capture the output of `carla_restart.sh`** — it daemonises CARLA, the
detached child inherits the pipe, and the call dies or hangs. Redirect to a file. This
cost time again this session, having already cost a night once.

## Instruments added this session

- `scripts/determinism_tier0_model.py` — inference bit-exactness, no simulator needed
- `scripts/determinism_tier1_openloop.py` — the diagnostic that worked: feedback cut,
  physics / render / injected-steering separated
- `scripts/determinism_static_scene.py` — frozen scene, cross-run; measures the floor
- `scripts/check_carla_determinism.py` — preflight, reads the server's real `/proc` argv
- `scripts/determinism_probe.py` — closed-loop, now able to fail correctly

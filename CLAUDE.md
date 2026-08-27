# CLAUDE.md

Public artifact repo for the end-to-end steering verification paper.

Rules that still bite:

- **CARLA applies writes on the NEXT tick.** `set_weather()`, `set_transform()` and
  sensor delivery all land one tick later, silently. Construct state, never read it
  back; match frames on the id `world.tick()` returns (`env.grab_frame`), and never
  swallow a missing frame.
- Sync mode only via `env.enable_sync_mode` — it provisions bounded substepping;
  hand-rolled settings run partial physics per tick.
- Every closed-loop number is a failure RATE over ≥ 10 repetitions with a Wilson
  interval; single runs near the stability cliff are wrong ~1 in 8 times.
- One CARLA client per port: every entry point takes `pipeline/carla_lock`. Relaunch
  the server before measurement runs (it leaks ~10.5 GiB / 11 h); kill by the PID
  listening on the port, not the launcher wrapper.
- No pixel-space norm balls as disturbance sets; families are physically
  parameterized. No SDP-CROWN (needs an L2 ball; vacuous here).
- `closed_loop_ledger.py` refuses canonical cell names while `FOG_DENSITY_OVERRIDE`/
  `SUN_ALTITUDE_OVERRIDE`/`ROUTE_ROLL` are set, and records full run provenance.

## SIMULATOR HYGIENE — non-negotiable, and re-derived the hard way

A CARLA server degrades SILENTLY. It keeps answering, keeps reporting plausible vehicle
velocities, and stops advancing physics correctly. Measured on a degraded server:

    sections drove 14-62% of their length at 1.3-5.6 m/s while speed_mph reported 20.0
    throughout; one run flung the car 190 m in 18 steps; a random section per pass hit
    6-10 ft while the others sat at 0.5 ft

Restarted, the same code and the same checkpoint drove every section end to end and
scored 0/6 with max |CTE| 1.02 ft. NOTHING in a result reveals which server you were on.
An entire night was spent theorising about marginal stability, covariate shift and
per-section difficulty on top of corrupted runs.

**R-SIM-1. Restart CARLA before every measurement run.** Not when it looks wrong --
before. `bash scripts/carla_restart.sh`. It costs about 30 s. Parsing bad data costs a
night, and you cannot tell from the data that you are doing it.

**R-SIM-2. Never `kill -9` a CARLA client.** SIGKILL skips `env.cleanup`, which leaves
the world in synchronous mode with nothing ticking -- that is how the server gets wedged.
SIGTERM, wait, and only then SIGKILL. `carla_restart.sh` does this in the right order.

**R-SIM-3. One client at a time.** In synchronous mode ANY connected client's `tick()`
advances the world, so two processes ticking the same server corrupt each other's runs
while both appear to work. Never run a sweep in the background and drive manually against
the same port.

**R-SIM-4. Verify the rendered condition from a FRAME, every run.** `set_condition`
checks the weather struct, but the struct is what was asked for, not what the camera
sees. `scripts/condition_signature.py` identifies the condition from one frame and
`evaluate.py` asserts it. This is the Town04 fog-into-night failure, where fog leaked
into the night cells and no result could reveal it. Validated 24/24 on held-out captures.

**R-SIM-5. Do not drive the oracle as a routine health check.** It costs a full section
and keeps the server up longer, which is the exposure being avoided. Restart instead.
`scripts/carla_health_check.py` exists as a DIAGNOSTIC for when something is already
suspected, not as routine hygiene.

**R-SIM-6. A run that ends in a handful of steps is a BUG, not a pass.** Three separate
attempts at the section-end distance cap each terminated runs after 3-5 steps and
reported a tiny |CTE| as a PASS. Any cell whose step count is far below `steps_for` is
void. Check step counts before reading verdicts.

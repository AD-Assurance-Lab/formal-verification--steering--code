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

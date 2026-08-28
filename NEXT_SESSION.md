# Start here

Written 2026-08-28 at the end of a session that lost a night and most of a day to
infrastructure faults. Full detail is in `docs/TOWN06_FINDINGS.md`, T06-F19 through F21.

## The one question that blocks everything

**Are closed-loop runs reproducible?** Zach's question, and it is the right one: CARLA is
deterministic in synchronous mode, this study pins the timestep, substepping, spawn,
weather and exposure, so a competence gate reporting "held 2/3" should be impossible.

Two measurements disagree:

| test | result | trust |
|---|---|---|
| one section alone, 3x, fresh server each | reported bit-identical | **NO** -- probe defect below |
| `--direction all`, 3 reps, fresh server each | every section differs, incl. the first | yes, parsed from stdout |

The probe defect: `scripts/determinism_probe.py` reads
`pipeline/results/eval_<ckpt>_<section>.csv`, which every run OVERWRITES IN PLACE. A run
that did not rewrite it makes the probe compare a file with itself, so "IDENTICAL" proves
nothing.

### Do this first
1. Fix the probe: copy each rep's CSV to its own path before the next run. Re-run.
2. If isolated runs ARE reproducible but sequential ones are not, chase carried state.
   `env.teleport` zeroes linear and angular velocity and sets the transform, but does not
   touch suspension, wheel or drivetrain state, and CARLA applies transforms on the NEXT
   tick. Instrument the first 20 steps per section and diff across reps.
3. If even isolated runs vary, find the entropy source before trusting any closed-loop
   number: renderer nondeterminism reaching the camera, sensor delivery order, physics
   substep scheduling.
4. Only then resume the competence gate. "2/3" is not interpretable until this is settled.

**This reaches Town04.** The published study drives its lap in two directions in one
process -- the same pattern -- and reports cells as rates over ten runs. Settle this
before any further blind claim.

## State of the work

Trusted:
- Corrected routes: 6 sections, 3,834 m, fingerprint `706db50636cbd6c9`. 100% both lane
  markings, 100% dashed both sides, 3-5 lanes, never a connector.
- Low sun fixed for Town06: 5 degrees gives mean 0.1250 vs Town04's 0.1117 (15 degrees
  gave 0.1841, nearly night). Fog and night unchanged to 4 dp. Town04 untouched at 15.
- Teachers: clear 6/6 @ 0.92 ft, mixed 24/24 @ 1.31 ft in 6 DAgger rounds (was 12).
- Students distilled: clear KD RMSE 0.0300 (was 0.0489-0.0553), mixed 0.0480.

Not trusted:
- Every closed-loop student number from this session.
- T06-F14's "student DAgger is harmful at 168x28" -- measured on contaminated sections.

## Running the simulator

`CLAUDE.md` has the rules (R-SIM-1..6). The ones that cost the most:
- Restart CARLA before EVERY measurement run: `bash scripts/carla_restart.sh`.
- NEVER `subprocess.run(capture_output=True)` on a script that daemonises CARLA. The
  detached child inherits the pipe and the call never returns. Redirect to a file.
- One client at a time. `carla_lock` enforces it and names the offender.
- A run ending in a handful of steps is a bug, not a pass. Check step counts.

## Useful scripts added this session
- `scripts/carla_restart.sh` -- clean restart; `CARLA_WINDOWED=1` for a visible window
- `scripts/wait_carla_ready.py` -- readiness = a successful `get_world()`, loads the study map
- `scripts/condition_signature.py` -- identify clear/fog/night/low-sun from ONE frame (24/24)
- `scripts/audit_section_intersections.py` -- junction content per section
- `scripts/determinism_probe.py` -- **fix the CSV defect before believing it**
- `scripts/carla_health_check.py` -- oracle drive; diagnostic only, not routine (R-SIM-5)

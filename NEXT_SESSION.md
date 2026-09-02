# Start here

Updated 2026-09-02.

## Where the study is

The Town06 deployment test is being **rebuilt from step 0** on the continuous lap. The
blocker that stopped the previous session is found, measured and fixed: see
`docs/TOWN06_FINDINGS.md` **T06-F42**.

**What was wrong.** The CARLA server rendered the identical scene ~15% darker for part of
2026-09-01. Both Town06 lap BC sets and most DAgger rounds were collected on the dark side,
so both teachers trained on frames systematically darker than the frames they are scored
on — and DAgger aggregated both renderings into one set. Clear had the headroom to survive
it; night and low sun did not, which is exactly the failure that was read as "the mixed
teacher will not converge" and, in T06-F41, as "the lap route is darker than the route the
conditions were calibrated on".

**T06-F41 is withdrawn.** Driving one instrument over the lap does not reproduce it: a
pure-pursuit lap of the LAP route matches the SIX-SECTION dataset to within 0.4%. The route
did not get darker; the collection did. **No frozen constant moves and `PROTOCOL.lock` is
untouched** — low sun measures 5.0% from A-2's re-derivation against the 9% T06-F20
accepted, and the night/low-sun axis stays ordered with all four conditions classifying as
themselves.

## What is new, and why it is there

| | |
|---|---|
| `scripts/check_render_photometry.py` | The guard. A fixed camera at the study spawn, no vehicle, ~2 s, run from `carla_launch.sh` on **every fresh server**. The determinism preflight checks the launch argv, `verify_condition()` reads the weather struct back, `identify()` checks which condition it is — a uniform photometric gain passes all three. |
| `scripts/measure_lap_condition.py` | ONE instrument for a condition's rendered outcome, recording both the teacher's and the student's view. Three mutually inconsistent brightness tables had accumulated here, and one of them named a condition. |
| `scripts/calibrate_lap_conditions.sh` | Drives all four, clean server each. |
| `results/photometry_reference.json` | The committed reference. Reproducible across fresh servers to 0.001%. |

Two harness defects fixed alongside it:

* **`carla_restart.sh` killed its own caller.** It stopped clients with
  `pkill -f collect_data.py`, which matches any ancestor whose command line names the
  script — the `[c]ollect` bracket trick only protects against pkill's own argument. That
  is the previous session's "restart failed before gate lap N" with a healthy server in
  the log, which discarded a 12-lap gate that was passing at the time.
* **The drivers asked for `shadows`, the classifier answered `low_sun`.** Harmless while
  both were wrong together; renaming one alone would have aborted every low-sun lap of the
  rebuild, hours in, on a condition that rendered correctly.

## Running it

    export STUDY_MAP=Town06 CARLA_PORT=3000 CARLA_WINDOWED=0
    setsid nohup bash scripts/watchdog_town06.sh > /tmp/t06_watchdog.log 2>&1 &

The watchdog restarts the pipeline if it dies and stops when the lap ledger exists.
`results/town06_logs/pipeline.log` is the stage log.

**CARLA runs HEADLESS here** (`-RenderOffScreen`). Standing rule 6 asks for a windowed
server so runs can be watched; windowed will not start from this session (SDL init fails,
empty log, rc=1). The deviation is measured rather than assumed: the same pure-pursuit
clear lap gives mean 0.2525015 windowed against 0.2524913 headless, with identical sample
count and identical sun-in-FOV fraction — 4e-5, far below the D-7 render floor. Recorded in
T06-F42. **If you can launch windowed, do; nothing else changes.**

**Never pipe or capture the output of `carla_restart.sh`** — it daemonises CARLA and the
detached child inherits the pipe. Redirect to a file.

## After the pipeline

    bash scripts/finish_town06_deployment.sh

Capture → certify blind → **commit the certificate** → drive the scored ledger → compare.
Steps 3 and 4 cannot be reordered: `check_order_town06.py` enforces R1 against commit
timestamps, and `closed_loop_ledger.py` refuses a cell whose certificate is missing,
untracked or dirty.

## Standing hygiene

    python3 -m carla_determinism --port 3000      # preflight; entry points call it too
    bash scripts/carla_restart.sh                 # before EVERY measurement run
    python3 scripts/audit_repo.py                 # before any release

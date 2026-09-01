# Harness conformance check — Town06 lap rebuild, 2026-09-01

Checked against the running system, not against intent. Each line is what was observed,
with where it was observed.

## CARLA determinism (standing rule 5)

| requirement | observed |
|---|---|
| every vehicle command through the package | `pipeline/carla_env.py:64` — `cd.apply_control(...)`. The only raw `vehicle.apply_control()` left in the repo is `scripts/determinism_tier1_openloop.py:186`, which is the open-loop experiment that MEASURES the violation |
| `DETERMINISTIC_CONTROL` on | `True` under `STUDY_MAP=Town06`; default is `"1"` for every map since the Town04 redo |
| `require_deterministic()` on each fresh server | called inside `enable_sync_mode` (`carla_env.py:142`), so it runs on every map and every run rather than at one call site a driver can skip |
| launch flags | live server: `-quality-level=Epic -notexturestreaming -windowed -ResX=1280 -ResY=720` |
| fixed timestep / substepping | `FIXED_DT = 0.2`, `substepping = True`, `max_substeps = 16` |
| preflight green on the live server | `determinism preflight OK (lock intact; D-3/D-5 verified on the live server)` |
| windowed on `DISPLAY=:0` | confirmed on the running server; Zach watches runs |
| one client per port | `CARLA_PORT=3000`, lock under `/tmp/carla-locks/` |

## Lap structure (A-4, continuous with PPC)

    SECTIONS       ['lap']            one continuous traversal, not six sections
    LAP_TOTAL_M    2289.0 m
    LAP_SCORED_M   2119.0 m
    BRIDGE_SPANS   618.8-706.8 m, 1548.3-1630.3 m   (170.0 m, = total - scored)

Bridged steps are steered by pure pursuit and excluded from scoring in all five driving
loops (`evaluate.py`, `dagger.py`, `dagger_student.py`, `closed_loop_ledger.py`,
`gate_teacher_lap.py`). The ledger additionally records failure ONSET rather than peak,
because the peak of a departed run says only where it ended up.

## Three laps per model per condition

    scripts/run_town06_ledger.sh:22    LAPS=3
    scripts/run_town06_ledger.sh:72    for COND in clear fog night shadows
    models                             S_clear_t06, S_mixed_t06

**2 models x 4 conditions x 3 laps x 1 section = 24 runs, 24 CARLA restarts.** One
process per run, `carla_restart` before each, `--only-section` and `--only-rep` so a
process drives exactly one lap. Rain is withdrawn (stochastic rendering; future work), so
four conditions rather than five.

Zach's estimate was 3 models -> 36 restarts. The design has two students, matching Town04.
If a third model is intended, it is not in `TOWN06_STUDENTS` and the matrix would need
changing before the ledger runs.

## Unresolved: D-7 vs A-4

`carla-determinism` D-7 is frozen and hash-locked, and states:

> Therefore every closed-loop number remains a RATE over at least 10 repetitions with a
> confidence interval.

This study's PROTOCOL A-4 supersedes standing rule 3's ">= 10" with three laps, on a
measurement (0 of 48 section-pairs disagreed on the corrected harness). A-4 argues against
standing rule 3 and never mentions D-7, so the package still asserts the floor and prints
it at every restart -- in this repo and in the AEB and multi-condition repos, whose
published numbers were collected under it.

The two are not obviously in conflict on the facts: D-7 measures that rendering never
reaches bit-identity, which remains true and is not what A-4 disputes. A-4 disputes the
INFERENCE from that to a repetition floor, on the grounds that verdict stability, not
frame identity, is what the floor was protecting.

This is not resolvable inside this repo. Amending D-7 needs the package's section 4
procedure (state the contradicting measurement, record it in the study's findings, change
the rule, regenerate the lock in the same commit, name the amendment), and it is a
lab-wide change affecting studies that are already published. Flagged for Zach; no work is
blocked either way, since this study runs under A-4 regardless.

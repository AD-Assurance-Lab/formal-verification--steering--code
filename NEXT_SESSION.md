# Start here

Updated 2026-09-03.

## The study is COMPLETE and frozen for publication

Town04 (discovery test) and Town06 (deployment test) are both finished. Nothing is running.
The result is written up and the artifacts are committed.

**Where to go depends on what you are doing:**

| you are… | read |
|---|---|
| writing the arXiv paper | **`docs/PAPER_HANDOFF.md`** — authoritative on what to publish |
| running the follow-on experiments | **`docs/NEXT_EXPERIMENTS.md`** — E1..E6, prioritised |
| checking a number | `docs/TOWN06_FINDINGS.md`, findings T06-F50..F57 |
| touching anything that drives | `PROTOCOL.md`, then `CLAUDE.md` (R-SIM-1..6) |

## The result in five lines

Town06's certificate was committed to git before any scored lap (`73415e5`; R1 verified
against commit timestamps) and agreed with driving on **4 of 5 scored cells**. Pass 2
re-drove all 24 laps days later and reproduced **all eight verdicts**. Every disagreement
and every failure localises to **fog**. Pass 3 then drove 16 independently distilled
students — two widths × eight seeds — against a pre-registered margin gate; **none passed,
and fog stopped every one**, so the fog failure is neither capacity nor an unlucky draw.
The teacher drives Town06 fog at 0.37 ft, so it is the distillation that loses it.

## The strongest single result

`fog/S_clear` and `low_sun/S_clear` sit *inside* the corridor at the driven intensity
(0.69× and 0.37× of tolerance) and both drive FAIL 3/3, one 21 m off the road. Their
falsification witnesses are interior, at s = 0.41 and s = 0.60. **Certifying only at the
rendered condition would have issued sound-looking certificates on two policies that leave
the road.** Quantifying over the disturbance family is what prevented it.

## Standing hygiene

```bash
python3 -m carla_determinism --port 3000      # preflight; entry points call it too
bash scripts/carla_restart.sh                 # before EVERY measurement run (R-SIM-1)
python3 scripts/audit_repo.py                 # before any release -- 216 passed, 0 failed
python3 -m pytest tests/ -q -p no:anyio       # 78 tests
```

CARLA runs on a non-default port (3000) and must be booked. Launch windowed on `DISPLAY=:0`
so runs can be watched (standing rule 6); `carla_launch.sh` falls back to headless loudly if
the window will not init, and every run records which mode it used in its own provenance.

**Never pipe or capture the output of `carla_restart.sh`** — it daemonises CARLA and the
detached child inherits the pipe. Redirect to a file.

## What must not be touched

* `PROTOCOL.md` §3 and `PROTOCOL.lock` — frozen constants; §9 amendment procedure only.
* `results/town06/ledger` (pass 1), `results/town06/ledger_pass2`, both certificates.
  PROTOCOL R4 requires the originals to stand.
* The `.selected` pins for `S_clear_t06lap_168x56_w2` and `S_mixed_t06lap_168x56_w4` —
  they resolve the certified models. New work pins under its own name (`PIN_CK=`) and
  passes `PROMOTE=0`.

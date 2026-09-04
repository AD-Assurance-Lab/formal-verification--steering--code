# Town06 deployment test — status

**COMPLETE, 2026-09-03. Frozen for publication.**

| you are… | read |
|---|---|
| writing the paper | **`docs/PAPER_HANDOFF.md`** |
| running follow-on experiments | **`docs/NEXT_EXPERIMENTS.md`** |
| checking a number | `docs/TOWN06_FINDINGS.md`, T06-F50..F57 |

**Result:** certificate committed before any scored lap (`73415e5`, R1 verified against
commit timestamps), agreement **4/5** on scored cells, all eight verdicts reproduced by an
independent second pass. Every failure localises to fog. Pass 3 drove 16 students (two
widths x eight seeds) against a pre-registered margin gate and none passed, so fog is
neither capacity nor an unlucky draw — the teacher drives it at 0.37 ft, and the
distillation loses it.

Everything below this line is the historical record of how the study got here. The stage
table it contains was accurate on 2026-09-02 and is superseded by the above.

---

## Why this exists

Town04 is a **discovery test**: `T_CLOSED_LOOP_S = 1.85` was back-solved from the
closed-loop cliff the certificate is then validated against (F45), so its 12/12 measures
sensitivity, not prediction. This branch runs the **deployment test**: criterion frozen
first, certificate committed before the drive, then drive.

---

## REBUILDING from step 0 on the continuous lap

Nothing is contaminated: no lap certificate exists and no lap cell has been scored.

### What stopped the last attempt, and what it actually was

The mixed teacher would not converge on the lap -- night 0 of 29 gate laps, fog 3 of 29 --
while clear passed 20 of 29. **The cause was the simulator, not the models, the route or
the conditions.** `docs/TOWN06_FINDINGS.md` T06-F42:

The CARLA server rendered the identical scene ~15% darker for part of 2026-09-01. Both BC
sets, which seed both teachers, were collected on the dark side; the DAgger sets hold BOTH
renderings, interleaved. At matched poses 0.5 m apart the frames are the same picture at a
different exposure -- per-pixel ratio 0.830, median 0.831, flat across the tonal range,
identical geometry and content. A collection run on 2026-09-02 with unchanged code
reproduces the bright side.

So every lap teacher trained on frames systematically darker than the frames it is scored
on. It predicts the failure pattern exactly: clear has the most headroom and passed
throughout, night and low sun are where a 15% gain bites, and the mixed teacher's gate
reached 6/12 at rounds 10-13 -- precisely the four consecutive BRIGHT rounds. Round 13
passed every lap it was given (clear 0.85/0.74 ft, fog 0.44, night 0.96, low sun 1.53,
against 2.19 ft) and was stopped by an infrastructure failure, not a policy failure.

Nothing caught it because nothing looked at brightness. The determinism preflight checks
how the server was LAUNCHED, `verify_condition()` reads the WEATHER STRUCT back, and
`identify()` asks WHICH CONDITION it is. A uniform photometric gain passes all three.

Fixed by `scripts/check_render_photometry.py`, run from `carla_launch.sh` on every fresh
server. Every Town06 lap artifact produced by driving is archived to the drive and
recollected, under A-2's own reasoning (`docs/ARCHIVE_2026-09-02.md`).

### The capacity question is CLOSED

`TOWN06_STATUS.md` carried an open decision addressed to Zach -- widen both students,
widen the mixed only, or collect more base data -- raised because both students hovered ON
the CTE budget. T06-F28 answered it before the lap rebuild: **the capacity crisis was the
data.** T06-F30 then measured the w3 mixed student at 24/24 across all four conditions with
58% margin. The widths are declared in `config.TOWN06_STUDENTS` and the pipeline distils at
them. Nothing here is waiting on a decision.

### T06-F41's proposed re-derivation is WITHDRAWN

F41 concluded the lap route renders 37.8% darker under low sun than the six-section route
the conditions were calibrated on, and that the frozen condition constants therefore had to
move. It compared the six-section DATASET's frame means against the lap DATASET's; the
first was collected 08-28 (bright), the second 09-01 (dark). It measured the render drift
and named it the route.

Driving one instrument over the lap does not reproduce it. `scripts/measure_lap_condition.py`,
one pure-pursuit lap per condition, clean server each:

| | F41 claimed (lap) | measured, driven | six-section reference |
|---|---|---|---|
| clear | 0.2054 | 0.2525 | 0.2528 |
| fog | 0.3044 | 0.3365 | 0.3361 |
| night | 0.0765 | 0.1008 | 0.1031 |
| low sun | 0.0654 | 0.1045 | 0.1037 |

A driven lap of the LAP route reproduces the SIX-SECTION dataset to within 0.4%.

**The conditions hold and no frozen constant moves.** On the student's view -- the view
`condition_signature`'s thresholds were derived on and the view `evaluate.py` asserts --
low sun measures 0.1264 against A-2's 0.1204, 5.0% away where T06-F20 accepted 9%; the
night/low-sun axis stays ordered (night 0.1844); and all four conditions classify as
themselves with margin on every discriminator. `PROTOCOL.lock` is untouched.

F41 recorded its proposal as "not acted on: re-deriving a frozen-section condition is
Zach's call". That is the only reason this cost nothing.

## The order, and where we are

| # | Stage | State |
|---|---|---|
| 1 | Protocol hash-locked, constants frozen | **done** |
| 2 | Route chosen on geometry alone, committed | **done** |
| 3 | Pipeline made map-aware (`STUDY_MAP`) | **done** |
| 4 | Oracle validated on the route | **done** |
| 5 | Harness: photometry guard, restart self-kill, condition naming | **done** (T06-F42) |
| 6 | Train teachers -> distil students (both policies) | **running, from step 0** |
| 7 | Full-lap captures | pending |
| 8 | Certify, blind | pending |
| 9 | **Commit the certificate** | pending |
| 10 | Scored closed-loop ledger, 3 laps per cell (A-4) | pending |
| 11 | Compare, dispose, write up | pending |

Steps 9 and 10 cannot be reordered: `closed_loop_ledger.py` refuses to run a Town06 cell
whose certificate is missing, untracked, or dirty.

---

## What was decided, and on what evidence

**Route — the LAP, which superseded the six sections.** One continuous loop of
**2,289 m, of which 2,119 m is scored**, 93% policy-driven with two pure-pursuit bridges
across the intersections (`config.BRIDGE_SPANS`, 619-707 m and 1,548-1,630 m). Bridged
spans are driven by the expert and **excluded from scoring**: the lane centreline is
undefined through an intersection, and a lane-follower asked to drive one is being scored
outside its domain. Built by `scripts/build_town06_lap_from_track.py` from a human-driven
track snapped to the lane centreline; lanes chosen by MARKINGS rather than `lane_id`,
because the carriageway gains a lane and shifts 2.3 m laterally across bridge 2, so ids
change meaning across it.

It replaced six discrete sections, which were pieces of road 70-500 m apart and hard to
justify as repetitions of one experiment — the same argument PROTOCOL A-4 makes when it
says the LAP is the repetition.

**The six-section selection below is the historical record of how the road was chosen**,
on map geometry alone and before any Town06 model existed. The lap runs on that road.

| | Town04 | Town06 chosen |
|---|---|---|
| scored length | 2861 m | 2838 m |
| lane width | 3.500 m (σ 0) | 3.500 m (σ 0) |
| mean \|κ\| | 0.00306 | 0.00300 / 0.00337 |
| straight (R>500 m) | 51–56 % | **74–79 %** |
| min radius | 45–63 m | 22–27 m |
| lanes/dir | 4 | 4–5 |
| junction vertices | 18 % | 19–23 % |
| street light, median dist | 12–13 m, 100 % within 30 m | 14–15 m, 100 % |

`δ_tol` recomputes to **0.012011**, numerically identical to Town04, because the lane
width is identical. That is a fact about the maps, not a carried-over number.

**Three assumptions were wrong and got corrected by measurement:**

1. *"The route must be junction-free."* Town04's scored lap is **18 % junction
   vertices** — CARLA marks grade-separated highway merges as junctions and the study
   drove straight through them. What Town04 excluded was one at-grade signalised
   intersection. Filtering on junction-freedom found zero candidates on any map.
2. *"Use the posted speed limit to find highway."* Town06's outer loop carries **no
   OpenDRIVE type-274 landmarks at all** (415/415 vertices return none). Lane count
   carries the signature instead.
3. *"Store the 2861 m route segment."* Town04's cached routes are **closed loops** whose
   scored lap is a prefix, and `pure_pursuit_route` indexes with `(i + lookahead) % n`.
   An open segment makes that modulo wrap the lookahead from the end back to the start:
   the oracle drove a clean lap and then steered off the road at the seam (max\|CTE\|
   4.58 m eastbound, 15.98 m westbound) while over-budget still read 4.4 % and 0.8 %.
   Fixed by storing the full loop rotated to the window start.

After the fix the oracle passes both directions: max\|CTE\| **0.130 m** / **0.234 m**
against a 0.668 m budget, 0.0 % over budget.

---

## The risk, declared before the result

Town06's best window is **74–79 % straight against Town04's 51–56 %**. A straighter road
is easier to hold, so it is possible every cell passes and every cell certifies.

**If that happens this experiment has measured sensitivity only, not specificity** —
exactly as the withdrawn rain condition did, where 4/4 looked clean but all four cells
shared a verdict. It is written into `PROTOCOL.md` §4.2 and `study/town06_design.py`
before any result so it cannot be argued about afterwards. A uniform 16/16 is not
evidence that the certificate discriminates.

The outcome is published whatever it is. 6/12 is the result.

---

## Guards in place

- `check_protocol_lock.py` — SHA-256 over the frozen constants; every writing entry
  point calls it. Verified to reject a tampered section rather than re-lock.
- `check_order_town06.py` — R1 against **commit timestamps**, not file mtimes.
- `certify_town06.py` — **no truth table**; it cannot print an agreement column, and
  refuses any stride/nsplit other than the frozen 8/16.
- `closed_loop_ledger.py` — refuses a Town06 cell with a missing/untracked/dirty
  certificate; writes to `results/town06/ledger`, never the published ledger.

## Known leak, stated honestly

Training requires driving, so the mixed student's DAgger rounds do expose its behaviour
under fog/night/low sun. The clear-only student's do not — it never sees anything but
clear weather — so the informative cells (`S_clear` under night and low sun) are
genuinely blind. Nobody may look at mixed-model training telemetry and adjust anything
(PROTOCOL R3). The honest summary: the clear-only cells are the strong evidence.

---

## Running it

```bash
export STUDY_MAP=Town06 CARLA_PORT=3000 CARLA_WINDOWED=0
setsid nohup bash scripts/watchdog_town06.sh > /tmp/t06_watchdog.log 2>&1 &
# then, once the pipeline reports students competent in clear:
bash scripts/finish_town06_deployment.sh   # capture -> certify -> COMMIT -> drive
```

Logs: `results/town06_logs/pipeline.log`. CARLA runs headless (`-RenderOffScreen`) on port
3000 -- see `NEXT_SESSION.md` for why, and for the measurement showing headless and
windowed render the same lap to 4e-5.

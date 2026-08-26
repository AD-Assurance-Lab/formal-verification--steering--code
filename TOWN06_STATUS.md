# Town06 deployment test — status

Branch `validation/town06-deployment-test`. Nothing here is on `main`; the released
v1.0.0 artifact repo is untouched.

**Read `PROTOCOL.md` first.** It wins over every other file, including this one.

---

## Why this exists

Town04 is a **discovery test**: `T_CLOSED_LOOP_S = 1.85` was back-solved from the
closed-loop cliff the certificate is then validated against (F45), so its 12/12 measures
sensitivity, not prediction. This branch runs the **deployment test**: criterion frozen
first, certificate committed before the drive, then drive.

---

## PAUSED — students are marginal, and a capacity decision is needed

Nothing is contaminated: no certificate exists and nothing has been driven as a scored
cell. Everything upstream is built and verified.

### Where it stopped

Both Town06 students hover ON the CTE budget rather than inside it, and the competence
gate's verdict is therefore not repeatable. The SAME checkpoint
`S_clear_t06_84x28_dagger_r08` scored **5/6, then 6/6, then 5/6** on three consecutive
gate runs with nothing changed between them. Worst |CTE| ranged 1.71 to 2.92 ft against
a 2.19 ft budget: precisely the cliff where standing rule 3 says pass/fail is a coin
flip.

Ten student-DAgger rounds each produced no margin:

| student | ReLU | conditions | trajectory over ~10 rounds |
|---|---|---|---|
| `S_clear_t06` | 5,152 | 1 | 4/6, 5/6, 6/6, 5/6 — flat, noisy |
| `S_mixed_t06` | 15,456 | 4 | 4/6, 4/6, 5/6, 4/6, 3/6 — flat, noisy |

### What a competent student looks like

Town04's published mixed student passed at student-DAgger **round 0**, needing no
rounds at all (commit `4b2ad73`):

| condition | max \|CTE\| both directions |
|---|---|
| clear | 1.27 / 0.53 ft |
| fog | 0.64 / 1.36 ft |
| night | 0.62 / 0.98 ft |
| low sun | — / 1.61 ft |

Comfortably inside the same 2.19 ft budget, 0 % over. The verdict was never in question.
That is the bar, and Town06's students are not at it.

### Why not just add rounds or reps

Both are ways of shopping for a verdict rather than earning one:

* **More rounds** repeats F7 (`5be6862`), which blamed student-DAgger for a gap that
  M3 (`4b2ad73`) then showed was capacity: w1 failed all four conditions, w2 failed
  night 10/10, w3 passed everything.
* **More reps** would eventually stabilise the verdict, but a student that needs ten
  repetitions to prove it can hold clear weather is not one worth certifying.

### Why Town06 is harder for the same architectures

The straight sections punish residual bias. On s03 (dead straight, steering demand
0.0000) the student's CTE runs -0.18 → -1.24 → -8.59 with the sign never changing: a
constant steering bias integrating into departure. The teacher on the same section
oscillates about zero (-0.01 → +0.05 → -0.21). On curved sections the commanded
steering is large enough that the same bias is proportionally invisible.

Incidentally this reproduces the paper's own thesis in a new setting: a small persistent
bias walks the vehicle out of its lane while a large oscillating one integrates to
nothing.

### The decision

Widening needs **no protocol amendment** — capacity is a property of the model under
test, not of the criterion, and PROTOCOL section 3 does not freeze it. F12 (`387f62e`)
shows it is close to free for verifiability: 5,152 ReLU gives 0.78 % UNKNOWN, 15,456
gives 2.5 %, against ~11 % where certification stops being useful, because what binds
is input dimension and ours is one-dimensional.

Options, for Zach:

1. **Widen both** (clear to w2, mixed to w4), re-distil, re-run. Costs hours; gives
   students with margin, which every downstream number depends on.
2. **Widen the mixed student only**, accept a marginal clear student.
3. **Collect more base data first** — 4 laps x 6 sections may be thin for a route with
   this much straight.

Recommendation: (1). A marginal student makes the ledger, the certificate and the
comparison all noisy. But it is a larger departure from the published pair than option
2, and the paper reports the mixed student as 3x width, so whichever is chosen becomes
a declared difference.

## The order, and where we are

| # | Stage | State |
|---|---|---|
| 1 | Protocol hash-locked, constants frozen | **done** |
| 2 | Route chosen on geometry alone, committed | **done** |
| 3 | Pipeline made map-aware (`STUDY_MAP`) | **done** |
| 4 | Oracle validated on the route | **done** |
| 5 | Train teachers → distil students (both policies) | **running** |
| 6 | Full-lap captures, 8 of them | pending |
| 7 | Certify, blind | pending |
| 8 | **Commit the certificate** | pending |
| 9 | Scored closed-loop ledger, ≥10 reps/cell | pending |
| 10 | Compare, dispose, write up | pending |

Steps 8 and 9 cannot be reordered: `closed_loop_ledger.py` refuses to run a Town06 cell
whose certificate is missing, untracked, or dirty.

---

## What was decided, and on what evidence

**Route.** Town06 outer highway loop, 2861 m scored, both carriageways of the same
physical road. Chosen by `scripts/build_town06_routes.py` on map geometry only.

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
export CARLA_PORT=3000 STUDY_MAP=Town06
bash scripts/run_town06_pipeline.sh      # resumable; skips completed stages
bash scripts/capture_town06_laps.sh
python3 scripts/certify_town06.py
git add results/town06/certificate_town06.json && git commit -m "Town06 certificate (pre-drive)"
# only now:
python3 scripts/closed_loop_ledger.py --student S_clear_t06_84x28 --condition night --reps 10
```

Logs: `results/town06_logs/`. CARLA runs headless (`-RenderOffScreen`) on port 3000.

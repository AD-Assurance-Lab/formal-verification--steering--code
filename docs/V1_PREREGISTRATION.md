# V1 — a disposition for the canonical VOID fog cell: pre-registration

**Written 2026-09-05, before any V1 lap.** Output `results/town06/void_fog/` under
`TOWN06_LEDGER_TAG=void_fog`. Driver `scripts/run_town06_ledger.sh` with
`TOWN06_LEDGER_STUDENTS`, i.e. one process and one fresh server per lap.

## The question

> `fog / S_mixed_t06lap_168x56_w4_s3` is the one VOID cell in the committed Town06 ledger.
> `compare_town06.py` prints, correctly, that **the study is not complete while it stands**.
> What is that cell, quantitatively?

The three scored laps were **1.33, 5.25, 1.47 ft** against a 2.19 ft budget. One of three
exceeded it; none departed the road. Under PROTOCOL A-4 the laps disagree, so the cell is
**VOID — not a 33% failure rate**, and it stays void until a cause is written down.

## What is already established, and is NOT re-measured

E1b probed the cleanest of E1's VOID cells (`S_mixed_res_252x84_s1`, fog, 252x84) over 24
laps and found the mechanism:

* the outcomes are **discrete, not continuous** — 24 laps landed on 9 distinct values, seven
  of them agreeing to within 0.03 ft;
* four clusters, one of which departs the road, always near the same step;
* the client process does not matter (Fisher p = 0.414), so it is not a harness artifact;
* the cause is the D-7 floor: the renderer injects ~30 differing pixels per frame, the
  policy amplifies it at one or two decision points, and the trajectory commits to a basin.

**E1b's own disposition is that this explains a VOID cell without rehabilitating it.** V1
inherits that and does not relitigate it.

## What is missing, and is what V1 measures

E1b's evidence is from a **different checkpoint at a different resolution**. Standing rule 3
requires the cause to be found and written down *for the cell that is void*, and no
comparable measurement exists for the canonical one. Three laps cannot distinguish a
multimodal distribution from a bad draw, which is exactly why the rule voids the cell.

**Design.** 24 laps of `S_mixed_t06lap_168x56_w4_s3` under fog, one process and one fresh
server per lap, on the corrected harness. Same student, same condition, same route, same
budget as the canonical cell.

**Endpoints, declared:**

1. The full distribution of worst-lap max|CTE|, and the count of **distinct values** at
   0.01 ft resolution — E1b's discreteness signature.
2. Clusters at a 1 ft gap threshold, and whether any cluster departs the road.
3. The fraction of laps exceeding the 2.19 ft budget, with a Wilson 95% interval.
4. Whether the three canonical laps (1.33, 5.25, 1.47) fall inside clusters V1 finds.

## Predictions — written before any V1 lap

**V1-P1 — the distribution is discrete and multimodal**, in E1b's sense: 24 laps land on
fewer than 15 distinct values at 0.01 ft resolution, in at most 5 clusters. Reason: E1b
measured exactly this on the same route and family, and the mechanism it named is a property
of the renderer and the closed loop, not of one checkpoint.

**V1-P2 — no lap departs the road.** The canonical cell's worst lap was 5.25 ft with
`departed=False`, and 5.25 ft is far from E1b's 22 ft departing cluster. This cell looks
like a corridor excursion, not a lane departure. **If a lap does depart, that is a more
serious finding than the VOID itself** and is reported immediately: it would mean the
shipped student leaves the road under fog, which no scored lap has shown.

**V1-P3 — the over-budget fraction is between 10% and 50%.** One of three exceeded budget;
a rate near zero or near one would both mean the canonical three laps were unrepresentative.

**V1-P4 — the canonical laps fall inside V1's clusters.** If they do not, the harness has
changed between the committed run and today, which would be a defect and not a disposition.

## What counts as an answer

* **P1–P4 hold:** the cell is a draw from a discrete multimodal distribution whose modes
  straddle the budget. The disposition is written, the cell **stays VOID**, and the paper
  can state what the cell actually is and at what rate it exceeds budget — which is strictly
  more than "VOID" conveys.
* **P2 fails:** report immediately and separately; it changes what the study says about the
  shipped policy.
* **P4 fails:** this is a harness question, not a policy question, and it takes priority
  over the disposition.

## What V1 does NOT do

**It does not rehabilitate the cell and it cannot.** PROTOCOL R4 requires the committed
ledger to stand, so nothing here is written to `results/town06/ledger`; V1 runs under an
exploratory tag and its cells live in `results/town06/void_fog/`. A cell whose laps disagree
stays void, and a measured rate from 24 laps is a description of the cell, not a verdict
that replaces it. Turning a VOID into a rate is precisely what standing rule 3 forbids:
*"more laps would turn an identified defect into a plausible failure rate and lose it."*

V1 exists to say **what the defect is**, not to average it away.

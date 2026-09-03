# Town06 pass 2 — what we expect, written before any lap is driven

**Committed before the first pass-2 drive. Not edited afterwards.** If a prediction here
is wrong, the wrongness is the result and it is reported as one.

PROTOCOL amendment A-5 is the change this tests. Read it first.

---

## What pass 2 is, and what it is not

Pass 1 (certificate `73415e5`, `results/town06/ledger`, T06-F50) was a blind deployment
test: the certificate went into git before any scored lap, and `check_order_town06.py`
confirms it against commit timestamps. It scored the full 2,119 m lap and reported
agreement 4/5.

It then turned out that 78 m of that lap demands more steering than `SMAX_CAP = 0.060` —
the constant `build_study_route.py` declares as "steering demand regime that actually
trained on Town04", which the section route enforced and the lap route silently did not.
All three of the mixed student's peak-|CTE| locations are on that road.

Pass 2 drives the same two frozen checkpoints over the same route under the same four
conditions, and scores every lap under **both** scopes from **one** set of drives.

**Pass 2 is not blind.** We know pass 1's outcomes. R1 still holds literally — every
pass-2 certificate is committed before every pass-2 drive — but this is a scope-corrected
re-measurement made with prior knowledge and must never be reported as a blind test. That
is the whole reason this document exists: without it, whatever pass 2 shows will look like
what we expected.

**Nothing about the policies changes.** Same checkpoints (`S_clear_t06lap_168x56_w2_s0`,
`S_mixed_t06lap_168x56_w4_s3`), same training data, same DAgger rounds, same route
geometry, same conditions, same exposure function, same frozen constants,
`PROTOCOL.lock` untouched. The captures are unchanged, so the full-scope certificate is
the one already committed and is not recomputed; only the capped-scope certificate is new.

---

## The scopes

Recomputed by `scripts/scored_scope.py` from the route's own vertices:

| | scored road | excluded beyond the ODD bridges |
|---|---|---|
| `full` | 2119 m | — (this is what pass 1 scored) |
| `capped` | 2041 m | arc 1224.1–1264.5 m and 2249.2–2287.0 m, 78 m over `SMAX_CAP` |

Note what `capped` does **not** remove: the first corner, arc 14.7–64.3 m, peak demand
0.0533. It is over Town04's own `smax` of 0.0467 but under `SMAX_CAP`, so it stays scored.
Every clear-only-student failure begins there, and the fog VOID cell peaks there.

---

## Predictions — driving

Pass 1's per-lap outcomes, and where each lap peaked, are in
`results/town06/ledger/runs/`. Under `capped` the excluded spans contain the pass-1 peak
of `night/S_mixed` (all 3 laps), `low_sun/S_mixed` (all 3 laps) and `clear/S_mixed` rep01.

### P1. Full scope reproduces pass 1, cell for cell

| cell | pass 1 | predicted pass 2, full scope |
|---|---|---|
| `clear/S_clear` | PASS 0/3, 0.392 m | PASS |
| `clear/S_mixed` | PASS 0/3, 0.397 m | PASS |
| `fog/S_clear` | FAIL 3/3, 21.03 m | FAIL |
| `fog/S_mixed` | **VOID 1/3**, 1.601 m | **VOID or PASS — genuinely uncertain** |
| `low_sun/S_clear` | FAIL 3/3, 6.33 m | FAIL |
| `low_sun/S_mixed` | PASS 0/3, 0.667 m (+0.2 %) | PASS, margin below +15 % |
| `night/S_clear` | FAIL 3/3, 7.78 m | FAIL |
| `night/S_mixed` | PASS 0/3, 0.305 m (+54 %) | PASS |

`fog/S_mixed` is the one cell we decline to predict. T06-F50 measured 2 of 9 runs over
budget at one spot, from bit-identical starts, so its lap verdict is a coin flip under the
D-7 render residual. Predicting it either way would be a guess dressed as a prediction.

### P2. Under the capped scope, NO driving verdict changes — only margins

This is the sharp prediction, and it is the one most likely to be wrong.

* `low_sun/S_mixed` margin rises **well above** its +0.2 %. All three pass-1 peaks are in
  the excluded span, so the cell's worst error becomes whatever the in-regime road gives.
* `night/S_mixed` margin rises above its +54 %, same reason.
* `clear/S_mixed` loses its rep01 outlier (1.30 ft against 0.73/0.76 ft).
* `fog/S_mixed` is **unchanged**: its peaks sit at arc 50.8, 55.3 and 1964.3 m, all in
  scope under the cap.
* All three `S_clear` failures are **unchanged**: their onsets are at arc 16.9–66.6 m, in
  scope under the cap, and their peaks at arc 41.8–1734.3 m likewise.

### P3. The question this is actually being run to answer

**Is `low_sun/S_mixed`'s 1.4 mm margin an artifact of scoring out-of-regime road, or is
the mixed student genuinely marginal?**

* If its capped margin is comfortable (say above +30 %), the marginality was the scope.
* **If its capped margin is still under +15 %, the scope was not the cause and the mixed
  student really is borderline** — which is the hypothesis Zach raised, and it would be
  supported rather than explained away.

Both outcomes are reported. The second is the more interesting one and it is the one that
argues for training a stronger student before any further Town06 claim.

---

## Predictions — the certificate

The full-scope certificate is the committed pass-1 artifact and does not change: same
captures, same checkpoints, same frozen stride and nsplit.

For the capped-scope certificate we predict **the bounds tighten slightly and no verdict
changes**, because the excluded spans are 3.7 % of the pooled poses and the statistic is a
route-mean. Concretely: `S_mixed/low_sun` stays CERTIFIED and the other five stay
NOT_CERTIFIED.

A verdict change here would be a genuine surprise and would mean the certificate is more
sensitive to which road it pools than a route-mean over 133 poses ought to be.

---

## What would falsify what

| prediction | falsified by |
|---|---|
| P1 | any pass-2 full-scope verdict differing from pass 1 other than `fog/S_mixed`. That would mean the harness is not reproducible and A-4's premise fails a second time. |
| P2 | any cell changing verdict between scopes. In particular, a clear-only-student cell improving under the cap would mean the cap is rescuing failures rather than removing out-of-regime road. |
| P3 | either branch is informative; the prediction being tested is that the answer is *decidable* from this run, which fails if the capped margin lands between +15 % and +30 %. |
| certificate | any capped-scope verdict differing from the committed full-scope one. |

---

## What pass 2 cannot settle

* It does not make the certificate-vs-driving comparison blind again. Pass 1 spent that.
* It does not test the criterion on a different map, different models, or a re-cut route.
* It does not address `night/S_mixed`'s pass-1 DISAGREE, which traces to the certifier
  quantifying over a spatially varying `s` while the ledger drives one global intensity.
  That has its own disposition and is not a scope question.
* It does not touch the interior-of-the-family question (T06-F51, T06-F52).

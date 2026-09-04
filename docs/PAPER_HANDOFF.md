# PAPER HANDOFF — what to write up, and what not to

**READ THIS FIRST if you are a Claude Code session working in
`formal-verification--steering--arxiv` and were told to look in this repository.**

**Status: the study is FROZEN for publication as of 2026-09-03.** Everything below is
final. Work continues in this repo under `docs/NEXT_EXPERIMENTS.md`, and **none of it
belongs in this paper.** If you find results here dated after 2026-09-03, they are the
follow-on study; ignore them unless Zach says otherwise.

Every number in this document traces to a committed artifact, named inline. Nothing here
is computed in the paper repo — `figures/check_data.py` there verifies against this repo,
and that remains the only path from results into the paper.

---

## 1. What the study is

Two small end-to-end steering CNNs are trained in CARLA, then **certified without being
driven again**, and the certificate is compared against closed-loop driving.

* `S_clear` — trained on clear weather only.
* `S_mixed` — trained on clear, fog, night and low sun.

Each is distilled from a PilotNet teacher (5 conv layers, 200×66 input) trained by
behaviour cloning plus DAgger. Only the **students** are verified: they are ReLU-only CNNs
small enough for α-CROWN.

**The certified property.** For a disturbance family parameterised by intensity `s ∈ [0,1]`,

    x(s) = x_clear + s·(x_cond − x_clear)

bound the **sustained (route-mean) steering bias** relative to the model's own clear-weather
output, and certify iff it stays inside a tolerance derived from the lane-departure budget:

    Δ_p(s) = δ_p(s) − δ_p(0),      SAFE iff |mean over poses of Δ_p(s)| ≤ δ_tol
    δ_tol  = 2·L·CTE_budget / (v²·T²) / MAX_STEER

`s = 0` is clear and `s = 1` is the rendered condition, so the family covers intensities no
closed-loop run ever samples.

---

## 2. The two studies, and why they are not the same experiment

| | **Town04** | **Town06** |
|---|---|---|
| road | highway loop | urban arterial loop |
| role | **discovery test** | **deployment test** |
| ordering | outcomes known when the criterion was set | certificate committed to git **before** any scored lap |
| result | 12/12 agreement (in-sample) | **4/5 agreement on scored cells** |

**Town04's `T_CLOSED_LOOP_S = 1.85` was back-solved from the closed-loop cliff it is then
validated against.** The paper must say this. At its a-priori value of 1.0 s the same
criterion issues *unsound* certificates on two cells that leave the road every run. So
Town04 shows a criterion of this shape exists and separates the cells; it does **not**
show prediction. `pipeline/config.py` states this at the constant's definition.

Town06 is the blind test. `scripts/check_order_town06.py` verifies R1 against **commit
timestamps**, not file mtimes, and `audit_repo.py` reports it green.

### These are different ODDs, and that is the honest framing

Under **ISO 34503:2023** (superseding BSI PAS 1883), road type and road geometry are
first-class ODD attributes. Town04 is a highway; Town06's outer loop is an urban arterial
with corners tighter than anything on Town04. Koopman & Fratrik (SafeAI 2019) frame
validation as a cross-product in which each tuple is either handled or **declared out of
scope** — there is no third option where a result silently carries across.

The paper currently says "we study end-to-end steering on the Town04 highway loop" and
never uses the term ODD. **Recommend: declare the ODD explicitly in ISO 34503 vocabulary,
and present Town06 as an adjacent ODD rather than a replication.** Agreement figures are
then not expected to be comparable across the two, by construction.

This also re-justifies the scope split in §5 below: it is a **declared ODD boundary**, not
a post-hoc exclusion.

---

## 3. The Town06 result

Certificate committed at `73415e5`, before any scored lap. Driven three laps per cell
(PROTOCOL A-4: the lap is the repetition).

    condition  student   driving      certificate      agreement
    clear      S_clear   PASS 0/3     CERTIFIED        vacuous by construction
    clear      S_mixed   PASS 0/3     CERTIFIED        vacuous by construction
    fog        S_clear   FAIL 3/3     NOT_CERTIFIED    agree
    fog        S_mixed   VOID 1/3     NOT_CERTIFIED    excluded (A-4)
    low sun    S_clear   FAIL 3/3     NOT_CERTIFIED    agree
    low sun    S_mixed   PASS 0/3     CERTIFIED        agree
    night      S_clear   FAIL 3/3     NOT_CERTIFIED    agree
    night      S_mixed   PASS 0/3     NOT_CERTIFIED    DISAGREE

**Agreement 4/5 on scored, non-void cells.** Artifacts: `results/town06/certificate_town06.json`,
`results/town06/ledger/`.

**Independently reproduced.** Pass 2 (A-5) re-drove all 24 laps days later: **all eight
verdicts identical**, `night/S_clear` reproducing to 4 mm and `low_sun/S_clear` to 5 mm.
Artifacts: `results/town06/ledger_pass2/`, finding T06-F53.

**The declared degeneracy risk did not materialise.** PROTOCOL §4.2 warned before any result
that Town06's straighter route made a uniform pass/certify outcome possible, which would
measure sensitivity and not specificity. Instead the certificate separates the two students
completely and separates conditions within `S_mixed`.

---

## 4. The four results worth leading with

### 4.1 Endpoint-only certification would have been unsound — the strongest result

For `fog/S_clear` and `low_sun/S_clear` the sustained bias **at the driven intensity** is
inside the corridor — 0.69× and 0.37× of tolerance — yet both drive FAIL 3/3, one of them
**21 m off the road**. Their falsification witnesses are interior, at `s = 0.41` and
`s = 0.60`.

**A certificate computed only at the rendered condition would have issued sound-looking
certificates on two policies that leave the road.** Quantifying over the family is what
prevented it. Demonstrated offline, on the certificate's own frames, with no rendering and
no confound.

Artifact: `results/town06/witness_full.json`, `scripts/falsify_witness.py`, finding T06-F54.

### 4.2 NOT_CERTIFIED now separates into falsified and undecided

`certify_sustained_bound.py`'s own docstring records that FALSIFIED overstates what is
known, and that turning one into a genuine falsification means exhibiting a witness — "which
this repo can do cheaply and does not yet do. Two independent reviewers raised this." It now
does:

    NOT_CERTIFIED with an exhibited witness  -- proven unsafe somewhere in [0,1]
        S_clear/fog (1.01x tol @ s=0.41), S_clear/night (2.88x @ 0.77),
        S_clear/low_sun (1.87x @ 0.61)          -- all three drove FAIL
    NOT_CERTIFIED with no witness            -- sound but UNDECIDED
        S_mixed/fog (drove VOID), S_mixed/night (drove PASS)
    CERTIFIED                                -- proven for every per-pose choice of s
        S_mixed/low_sun (drove PASS)

**Read this way there is no cell where the certificate is wrong.** The 4/5 figure
undercounts. Report both readings; do not replace the pre-registered one.

### 4.3 The one DISAGREE is explained, and it is conservatism

`night/S_mixed` drove PASS and certified NOT_CERTIFIED. Five candidate causes ruled out by
measurement (T06-F54): the bound is tight to **1.0–1.1×** against dense sampling; the cell
reproduces at +55% margin with all six laps across two passes peaking at the identical
location; both scopes agree; flipping it needs `T = 1.10 s` against an admissible window of
1.231–2.128 s; harness clean.

**The cause:** the certifier bounds, per pose, the worst case over `s` and *then* averages —
so `s` may vary along the road, which is deliberate and documented (it covers spatially
varying disturbance). The ledger drives **one global intensity**. No single global `s`
violates the corridor: worst is **−0.66× tolerance at s = 0.678**. Certificate and drive
answer different questions and are not in conflict.

### 4.4 Verification found an instability that three laps did not

`fog/S_mixed` went VOID (laps disagreed). The student's own selection gate had passed fog
3/3 at 1.78 ft and the study would have shipped it. The certificate said NOT_CERTIFIED.

**Note the correction:** T06-F50 attributed this to a decision boundary *at one location*.
Pass 2's failing lap is a kilometre away (arc 1058.6 m vs 55.3 m), so that mechanism is
falsified — see T06-F53. The instability is distributed, and pass 3 showed why (§6).

---

## 5. Two scopes, both reported (PROTOCOL A-5)

`build_study_route.py` declares `SMAX_CAP = 0.060` — "steering demand regime that actually
trained on Town04" — and the six-section builder enforced it. The lap builder does not, and
the lap's smax is **0.0670**. So 78 m of the 2,119 m scored lap demands more steering than
the regime the criterion was calibrated in.

Both scopes are scored **from one set of drives** and both reported:

    full    2119 m   as pass 1 scored it
    capped  2041 m   excluding road over SMAX_CAP

**0 of 8 cells change verdict.** Only two margins move (`low_sun/S_mixed` +32.1% → +67.5%,
`night/S_mixed` +55.8% → +72.2%). Agreement is 4/5 under both.

Report both. Reporting only the capped number would be choosing a scope after seeing which
cells were marginal. Under ISO 34503 the capped scope is the **declared ODD boundary**.

---

## 6. The limitation to state plainly

**Only one cell tests "certified ⇒ drives safely."** `low_sun/S_mixed` is the sole
CERTIFIED disturbance cell, and in pass 1 it passed by **1.4 mm** of a 668 mm budget. It
passed comfortably in pass 2 (+32.1% full scope, +67.5% capped), but the study demonstrates
the **sound** direction well and the **useful** direction barely. This belongs in the
abstract, not a footnote.

**And the reason no better model was available is now measured.** Pass 3 (T06-F57) drove
**16 independently distilled students** — two widths (101,888 and 152,832 ReLU, the latter
3.0× the clear student, matching Town04's ratio) × eight seeds — against a pre-registered
gate requiring every lap under 50% of budget. **None passed. Fog stopped every one, at both
widths.** No other condition rejected a single seed.

So the fog failure is **neither a capacity problem nor an unlucky draw**. And it is not a
property of the task: the **teacher drives Town06 fog at 0.37–0.40 ft** over three runs
(T06-F29). It is the distillation to a smaller, shallower student that loses it — a
documented failure mode in which average-case accuracy transfers and **tail behaviour does
not**. Fog's mean distillation error is *better* than night's, which passes (RMSE 0.0272 vs
0.0333), while its p99 error is **0.121, ten times tolerance** (T06-F48).

Honest summary for the paper: *on this ODD, no policy good enough to certify exists yet, and
the obstruction is distillation rather than verification.*

---

## 7. Claims that must NOT appear

Each was made during the study and withdrawn on evidence. They are in the findings file with
their retractions; do not resurrect them.

1. **"Fog amplifies the D-7 render residual."** Withdrawn (T06-F53, T06-F57). The control
   showed the fog cells breach budget within 31–105 steps, leaving no usable on-road
   baseline, and pass 3 showed fog failure is *reproducible per checkpoint* — `w6_s7` drove
   fog 12.02 / 11.97 / 12.09 ft while driving clear at 0.49 ft.
2. **"The mixed student's gap is capacity; width is the lever"** (T06-F29). Falsified by
   pass 3 across 16 students.
3. **"w6 was tried and did not fix fog"** (T06-F48). Withdrawn (T06-F55): one draw per
   width, when a re-draw of an unchanged configuration was later measured swinging
   1.16 → 8.68 ft. Swept properly, **w6 is the better model everywhere except fog.**
4. **"The VOID cell is a decision boundary at one location"** (T06-F50). Falsified by pass 2.
5. **Rain.** Already withdrawn in the paper; CARLA renders it stochastically.

---

## 8. Methodological points the paper should carry

These are results about how to run the study, and several were bought expensively.

* **Determinism is a precondition, not a detail.** Every measurement goes through the
  `carla-determinism` package; `vehicle.apply_control()` races `world.tick()`, and
  `-notexturestreaming` cut injected steering noise 168×. Bit-exact closed-loop replay
  remains unreachable (D-7).
* **A lap is the repetition, and three laps is a reproducibility check, not a sample**
  (A-4). Measured: rep-to-rep verdict disagreement 0 of 48 section-pairs — and pass 2
  reproduced all eight cell verdicts independently.
* **Report the margin with every verdict.** A pass at 1% of budget and one at 60% are
  different results and a pass/fail bit cannot tell them apart.
* **Scope is recomputed from primary data, never read from an artifact's claim about
  itself** (standing rule 7), and the check is two-sided — covering more than the study
  scopes is the same error as covering less.
* **The selection gate needs the same provenance as the ledger.** The gate that chose the
  shipped student recorded no server command line, no determinism state, no git SHA and no
  timestamp — so a disagreement between two runs of byte-identical weights (11.45 ft vs
  1.48 ft on fog) could not be attributed. Fixed; both are now recorded per lap.
* **An unmeasured lap is not a failing lap.** A failed restart was silently driven through,
  and later counted as a model rejection. Both halves fixed.

---

## 9. Artifact index

    PROTOCOL.md                                  frozen constants, R1-R4, amendments A-1..A-5
    PROTOCOL.lock                                SHA-256 over the frozen section
    docs/TOWN06_FINDINGS.md                      T06-F50..F57 are the current record
    docs/TOWN06_PASS2_PREREGISTRATION.md         predictions committed before pass 2
    docs/TOWN06_PASS3_PREREGISTRATION.md         predictions committed before pass 3
    results/town06/certificate_town06.json       the blind prediction (commit 73415e5)
    results/town06/certificate_town06_capped.json  capped-scope bound
    results/town06/ledger/                       pass 1, 8 cells + 24 per-run artifacts
    results/town06/ledger_pass2/                 pass 2, + per-step traces
    results/town06/witness_full.json             falsification witnesses
    results/town06/pass3/                        51 artifacts, 83 laps, all with provenance
    results/town04_v2/                           the Town04 redo
    pipeline/checkpoints/                        both certified students + their teachers

Verify before quoting:

    python3 scripts/check_order_town06.py     # R1 against commit timestamps
    python3 scripts/compare_town06.py         # the agreement table
    python3 scripts/audit_repo.py             # 216 passed, 0 failed
    python3 -m pytest tests/ -q -p no:anyio   # 78 tests

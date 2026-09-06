# A1 — the best policy this study knows how to build: pre-registration

**Written 2026-09-05, before any A1 lap or certificate.** Output `results/town06/best/`
under `TOWN06_LEDGER_TAG=best`.

## The question

> Q1 found the learning rate matters. Q4 found label balancing matters, and is the only
> lever to reach significance on a **driving** endpoint. **Nobody has run both together
> through the study's own gate and a blind certificate.** Does the best policy this
> pipeline can currently produce change the conclusion that the binding constraint is
> distillation?

This is the experiment the paper's Limitations paragraph implicitly asks for. It says the
constraint "is currently distillation rather than verification" and that "we do not claim
it is a structural one". A1 is the strongest available test of that sentence.

## The subject already exists

Q4's `bal` arm **is** the tuned-and-balanced recipe: `lr=3e-4 --balance`, 168x56,
(32,64,64)/128, kernels pinned, twelve seeds already distilled and driven on fog and clear.
**A1 distils nothing.** It selects, gates and certifies.

## Selection rule — declared before looking further

The candidate is the `bal` seed with the **lowest fog worst-of-3** among seeds holding fog
3/3 under the 2.19 ft budget, ties broken by lowest clear worst-of-3, then lowest seed. A
seed whose fog **or** clear cell is VOID is excluded — an unmeasurable cell is not a
qualification.

From Q4's committed table that resolves to **seed 2** (fog 1.22 ft, clear 1.01 ft).
Recorded here so the choice cannot drift: seeds 7 (fog 1.23) and 9 (fog 1.26) are close, and
seed 7 is excluded by the VOID rule on clear.

## Design

1. **Gate.** Pass 3's gate, unchanged: `MARGIN_FRAC=0.5`, four conditions, three laps,
   via `scripts/select_student_seed.sh` with `PROMOTE=0` and a private `PIN_CK`. Identical
   to Q2's invocation so the two are directly comparable.
2. **Certify, then commit, then drive.** A blind certificate under the exploratory tag,
   committed before any scored lap, R1 checked against commit timestamps.
3. **Drive** four conditions x three laps through the committed ledger driver, one process
   and one fresh server per lap.

## Predictions — written before any A1 run

**A1-P1 — the gate is not passed.** No candidate reaches 12/12 under the 1.095 ft margin.
Reason: Q2 gated five tuned candidates and the best reached 9/12, stopped by fog; balancing
moved the *failure rate* rather than the typical margin (Q4: median 2.33 → 1.68 ft, MW
p = 0.067), and the gate is a margin test. **If A1-P1 fails — if this student passes pass
3's gate — it is the most consequential result in the entire follow-on programme** and the
paper's "sixteen students all failed" framing needs restating. Report immediately.

**A1-P2 — fog is still the stopping condition.** Consistent with Q2 (fog 4/4) and with every
result in this study.

**A1-P3 — the certificate refuses fog.** Its bound stays outside the corridor even if
driving holds 3/3, as in Q3. Reason: Q8a measured fog's bound as nearly tight (3.4%
recoverable under α-CROWN), so a better policy is not obviously a better-bounded one — and
Q3 measured the tuned student's fog bound as 3.3x **wider** than the shipped one's.

**A1-P4 — driving holds all four conditions under budget**, as Q3's student did, worst lap
below 2.19 ft. This is the "good policy" precondition that makes the certificate test
meaningful.

## What counts as an answer

* **P1 holds, P4 holds:** the best policy this pipeline can build drives Town06 in all four
  conditions and still lacks pass 3's headroom, with fog taking it. That is the strongest
  form of the paper's existing claim and it is no longer hedged on an unswept knob.
* **P1 fails:** the constraint is not distillation-as-such but the untuned recipe, and the
  Limitations paragraph is wrong in an important way. This is the outcome worth the run.
* **P3 fails** — the certificate clears fog on a student that drives it — would be the
  first `CERTIFIED` fog cell in the study and needs its own scrutiny before it is believed.

## Bound by

`PROTOCOL.md` R1/R4, `CLAUDE.md` R-SIM-1..6, standing rules 1, 3, 7, 8. Nothing written to
`results/town06/ledger`, `ledger_pass2`, either committed certificate, or either shipped
`.selected` pin. `PROMOTE=0` throughout.

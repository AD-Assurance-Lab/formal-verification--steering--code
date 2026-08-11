# CLAUDE.md — read this before doing anything

## The study, in four steps

1. **Train two experts in CARLA.** One on clear weather only. One on mixed conditions
   (clear + fog + night + shadows).
2. **Distill both into formally verifiable students** (ReLU-only, no BatchNorm/Dropout).
   Call them `S_clear` and `S_mixed`.
3. **Closed-loop test both under disturbances.** `S_clear` should fail conditions it never
   saw. `S_mixed` should pass.
4. **Apply formal verification to both, and get the same answer without simulating.**
   Verification should falsify `S_clear` on unseen conditions and certify `S_mixed` —
   *before* any closed-loop run.

**Step 4 is the contribution.** Steps 1-3 are infrastructure. Training a network to drive
in CARLA is not novel and must not consume the effort. The novelty is that formal
verification *predicts* closed-loop outcomes and closed-loop then agrees.

## The rule that exists because we lost this twice

> **A result that contradicts a ledger cell is a bug until proven otherwise.**
> It may not be written up as a finding until a written disposition lists the
> candidate causes that were ruled out.

Run `python -m study.ledger` before interpreting any result. It exits nonzero when a
measured cell contradicts its pre-registered expectation. If it does, stop and debug —
do not narrate the contradiction into a finding.

**This has already happened once.** In the previous study a disturbance-trained student
certified *worse* than the clear-only student at every visibility below 1000 m — the exact
opposite of step 4 — and it was written up as "the counter-intuitive finding" instead of
triggering a bug hunt. Two candidate causes were never ruled out: the student was trained
on affine photometric boxes but verified against a Koschmieder fog model (train/verify
family mismatch), and it was 2x width so its bounds were simply looser (UNKNOWN rate 11.5%
vs 1.5%). See `docs/PRIOR_STUDY.md`.

## The design rule that prevents that specific bug

**Train on the parameterized family, closed-loop test on points from that family's axis,
and verify over that same family's interval.** One axis per condition, shared by all three
instruments. If training and verification disagree about what the disturbance *is*, the
comparison in step 4 is meaningless.

## Where things are

| file | what it is |
|---|---|
| `STUDY.md` | the experimental design, the ledger, milestones with empirical exit criteria |
| `study/ledger.py` | the executable smell test. `python -m study.ledger` |
| `docs/DISTURBANCE_MATH.md` | how a physical disturbance is made formally verifiable |
| `docs/TRAPS.md` | 20 mistakes that cost real time in the previous study |
| `docs/CONSTRAINTS.md` | measured results that constrain the design; violating one reproduces a known bug |
| `conformance/` | the traps, as runnable tests. Must be green before pipeline code is trusted |

## Standing rules

- **No pipeline code until the ledger prints.** The design is the first artifact.
- **Every closed-loop number is a failure RATE over repetitions** (>= 10), never a single
  run. Report Wilson intervals.
- **Verification verdicts are committed before the corresponding closed-loop run.** This is
  what makes step 4 a prediction. `python -m study.ledger --check-order` verifies it
  against git history.
- **Never trade experimental quality for speed.** No CPU fallback, no lowered CARLA
  quality, no cut epochs. Warn before runs over 1 h.
- **Stop for feedback** after collection, closed-loop, and verification sweeps.
- **Do not vendor `auto_LiRPA`.** Depend on upstream `Verified-Intelligence/auto_LiRPA`
  via pip. Do not use SDP-CROWN; it requires an L2 ball and is vacuous on our sets.
- **CARLA hygiene:** relaunch the server before every measurement run (it leaks ~10.5 GiB
  over 11 h). To kill it: `P=Carla; pkill -9 -f "${P}UE4"`.

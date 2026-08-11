# formal-verification--automated-driving--code

Formal verification of end-to-end driving policies under physically-parameterized weather
disturbances, characterized in CARLA.

**AD Assurance Lab, Western Michigan University.**

## The claim

> Given two trained driving policies and no simulation, formal verification identifies
> which conditions each one is safe in. Closed-loop simulation then agrees.

Two students are trained — one on clear weather only, one on mixed conditions — and handed
over blind. Verification emits a per-condition verdict for each and the verdicts are
committed to git. Only then is closed-loop simulation run. The result is whether
verification recovered which model is which, per condition, without simulating.

Disturbances are indexed by quantities an operational design domain is actually written in
— meteorological optical range in metres, road illuminance in lux, solar elevation in
degrees — so a certificate reads *"certified above 85 m visibility"*: a statement about the
world, not about the simulator.

## Status

**M0.** Study design, ledger, and conformance suite. No pipeline code yet — deliberately.
See `STUDY.md` for milestones and their exit criteria.

## Start here

| | |
|---|---|
| `STUDY.md` | the experimental design, the ledger, milestones, what would falsify the claim |
| `CLAUDE.md` | the four-step logic and the rules that keep it from being lost |
| `docs/DISTURBANCE_MATH.md` | how a physical disturbance is made formally verifiable |
| `docs/TRAPS.md` | 20 mistakes that cost real time, half of them encoded in `conformance/` |
| `docs/CONSTRAINTS.md` | measured results that constrain the design |
| `docs/PRIOR_STUDY.md` | what two prior generations established, including one instructive failure |

## Running

```bash
pip install -r requirements.txt

python -m study.ledger        # the study's state; exits nonzero on a contradiction
pytest conformance/ -v        # the traps, as runnable checks
```

Conformance tests whose subject has not been transplanted yet **skip** with the trap named,
and become live the moment the module lands — so a transplanted file cannot quietly bring
its bug back in. At M0, 3 pass and 7 skip.

If the system `pytest` fails on an `anyio` plugin import, prefix with
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.

The CARLA 0.9.16 client wheel and CUDA PyTorch install separately — see
`requirements.txt`.

## Method

alpha-CROWN with input-space branch-and-bound over a low-dimensional physical parameter,
via upstream [auto_LiRPA](https://github.com/Verified-Intelligence/auto_LiRPA). Not
SDP-CROWN — it requires an L2 ball and is vacuous on the low-rank sets this study produces.

## Honest scope

Image formation is CARLA's; the parameters are real, the rendering is not. Verification
replaces exhaustive sampling *within* a disturbance family, not scenario sampling across
routes and manoeuvres. Transfer to a real camera is unproven. See `STUDY.md` for the full
list.

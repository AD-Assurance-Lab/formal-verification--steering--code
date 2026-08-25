# formal-verification--steering--code

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](requirements.txt)
[![CARLA 0.9.16](https://img.shields.io/badge/CARLA-0.9.16-orange.svg)](https://carla.org)
[![Verifier: α-CROWN](https://img.shields.io/badge/Verifier-%CE%B1--CROWN%20%2B%20BaB-8A2BE2.svg)](https://github.com/Verified-Intelligence/auto_LiRPA)
[![Conformance](https://img.shields.io/badge/conformance-25%20passing-brightgreen.svg)](conformance/)

Formal verification of end-to-end driving policies under physically-parameterized weather
disturbances, characterized in CARLA. **AD Assurance Lab, Western Michigan University.**

## The result

A **per-frame** certificate, computed with α-CROWN over a one-parameter disturbance family
and never simulating vehicle dynamics, reproduces closed-loop lane-departure outcomes on all
twelve canonical cells — two policies × three conditions × two directions.

    dir    model     cond      bias bound (× tol)   verdict        closed loop
    west   S_clear   fog       [-0.75, +0.29]       CERTIFIED      PASS  0/10
    west   S_clear   night     [-6.96, +0.93]       NOT CERTIFIED  FAIL 10/10
    west   S_clear   shadows   [-2.26, +0.64]       NOT CERTIFIED  FAIL 10/10
    west   S_mixed   fog       [-0.25, +0.38]       CERTIFIED      PASS  0/10
    west   S_mixed   night     [-0.61, +0.26]       CERTIFIED      PASS  0/10
    west   S_mixed   shadows   [-0.29, +0.31]       CERTIFIED      PASS  0/10
    east   (same six cells, same verdicts; see results/calibration/sustained_bound.json)

![The 12 canonical cells: certified bounds vs closed-loop outcome](docs/figures/certificate_cells.png)

![Night trace: clear-only departs within 35 m, mixed holds the lap](docs/figures/night_trace.png)

The finding underneath is about the **statistic, not the solver**: bounding the *peak*
per-frame deviation gives a **wrongly ordered** answer — the mixed policy deviates more
under shadows (0.2494) than the clear-only policy does (0.2275) while driving cleanly where
the other departs 10/10, so no threshold on the peak can work. The lap-sustained component
separates the same cells by 3.0×.

## Read this before quoting any of it

Three measured scope limits, all in the paper:

1. **It detects sustained failures, not localized ones.** A committed blind test refuted the
   criterion at an unseen operating point *in the unsafe direction*: a policy certified at
   0.31× tolerance departed on 10/10 runs. See `docs/STATE_OF_PLAY.md` §0b.
2. **The result is in-sample.** The criterion was selected after all twelve outcomes were
   known. Every criterion this project produced scored well in-sample and worse
   out-of-sample (§0b).
3. **The tolerance contains one fitted parameter.** `T_CLOSED_LOOP_S = 1.85 s` was
   back-solved from the observed departure threshold. The verdicts hold for
   T ∈ (1.231, 2.128) s; at the a-priori 1.0 s the criterion issues *unsound* certificates
   on two cells that depart every run (F45).

Rain is out of scope: CARLA's rain rendering is temporally stochastic, which the
deterministic two-endpoint family cannot represent. Future work.

`docs/STATE_OF_PLAY.md` states what is currently believed. `FINDINGS.md` and
`docs/DISPOSITIONS.md` are logs containing claims later corrected or withdrawn — **do not
cite from them directly.**

## Start here

| | |
|---|---|
| `docs/STATE_OF_PLAY.md` | **read first.** What is true, what is dead, what is open |
| `scripts/certify_sustained_bound.py` | the headline instrument, in ~170 lines |
| `docs/DISTURBANCE_MATH.md` | how a physical disturbance is made formally verifiable |
| `STUDY.md` | the pre-registered design and what would falsify the claim |
| `docs/TRAPS.md` | 20 mistakes that cost real time; encoded in `conformance/` |
| `archive/README.md` | every retired approach and the measurement that retired it |

## Running

```bash
pip install -r requirements.txt      # then torch + auto_LiRPA + CARLA: see that file
pytest conformance/                  # 25 passed
python -m study.ledger --check-order # exits 0; warnings are dispositioned, not silenced
```

If the system `pytest` fails on a plugin import, prefix `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.

The ledger checks three instruments side by side: the era-1 full-lap campaign (historical
record, never edited), the final open-road campaign the paper reports, and the sustained
certificate. Every historical contradiction is tied to a written disposition in
`docs/DISPOSITIONS.md` (D-01…D-14); only a *new* problem exits nonzero. The two-era story
(why an era-1 fog cell says FAIL where the paper says PASS: the junction, not fog) is D-14.

## Reproducing

| you need | where |
|---|---|
| the two student checkpoints | **in this repo**, `pipeline/checkpoints/` (403 KB) |
| full-lap captures, 6 × ~1.7 GB | not in git — regenerate with `scripts/capture_offset_yaw.py` |
| CARLA 0.9.16, Town04 | separate install; `CARLA_ROOT`, `CARLA_PORT` |

```bash
python scripts/certify_sustained_bound.py     # writes results/calibration/sustained_bound.json
python scripts/make_readme_figures.py         # regenerates the figures above from artifacts
```

Only the centreline slice of each capture is used by the certificate, so a capture made
with `OY_OFFSETS=0.0 OY_YAWS=0.0` is ~38 MB rather than 1.7 GB. **Record the clear baseline
in the same capture file as the condition** (`OY_CONDS=clear,fog`): a cross-session baseline
silently inverted the sign of one fog measurement (F43/F44, D-11). Ten of the twelve
published cells still use a cross-session baseline; the evidence they are sound is positive
but not proof.

Distillation seeds every RNG it uses; DAgger data *collection* is CARLA-stochastic, so
retraining reproduces the checkpoints statistically, not bit-for-bit. The certificate
records `nsplit`, `stride`, tolerance and git commit in `_meta`; closed-loop cells record
full run provenance. The companion paper checks its figures and numbers against this repo's
artifacts (`figures/check_data.py` there).

## Method

α-CROWN with input-space branch-and-bound over a low-dimensional physical parameter, via
upstream [auto_LiRPA](https://github.com/Verified-Intelligence/auto_LiRPA). **Not SDP-CROWN**
— it requires an L2 ball and is vacuous on the sets this study produces.

## Honest scope

Image formation is CARLA's: the parameters are real, the rendering is not. Verification
replaces exhaustive sampling *within* a disturbance family, not scenario sampling across
routes and manoeuvres. One route, one speed, one vehicle, two policies. Transfer to a real
camera is unproven. The interior of the disturbance family is an interpolation between two
rendered endpoints, not a render. `STUDY.md` has the full list.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

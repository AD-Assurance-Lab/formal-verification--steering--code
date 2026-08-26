# formal-verification--steering--code

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](requirements.txt)
[![CARLA 0.9.16](https://img.shields.io/badge/CARLA-0.9.16-orange.svg)](https://carla.org)
[![Verifier: α-CROWN](https://img.shields.io/badge/Verifier-%CE%B1--CROWN%20%2B%20BaB-8A2BE2.svg)](https://github.com/Verified-Intelligence/auto_LiRPA)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22101297.svg)](https://doi.org/10.5281/zenodo.22101297)

Formal verification of end-to-end steering under physically-parameterized weather,
characterized in CARLA. **AD Assurance Lab, Western Michigan University.** Companion
code for the paper *Proving End-to-End Steering in Poor Visibility* (preprint in
preparation).

Two driving experts are trained, one on clear weather and one on clear + fog + night
+ low sun, and each is distilled into a steering network small enough to verify. The
students are certified with α-CROWN over the disturbance family between the rendered
endpoints, without driving, and the certificate agrees with closed-loop testing in all
twelve cells.

**The setup.** A full Town04 highway lap, driven in both directions, with a Tesla
Model 3 ego vehicle.

<p align="center">
  <img src="figures/route_map.png" width="330" alt="Town04 highway loop, both driven directions">
  <img src="figures/vehicle.png" width="440" alt="The ego vehicle on the route">
</p>

**What the certificate says.** Certified bounds for all twelve cells, computed from
the network weights alone with no simulator in the loop. A cell is certified when the
whole bias interval stays inside the tolerance corridor: the clear-only student clears
clear weather and fog and is not certified under night or low sun, while the mixed
student clears all four.

<p align="center">
  <img src="figures/cert_bounds.png" width="540" alt="Certified bounds vs closed-loop outcome, all twelve cells">
</p>

**What the vehicle does.** Driving the same cells in CARLA reproduces every verdict.
Under night the clear-only student leaves the lane within 35 m and departs on all ten
runs, while the mixed student holds the lane for the full lap.

<p align="center">
  <img src="figures/night_comparison.gif" width="780" alt="Night: the clear-only student departs within 35 m; the mixed student holds the lane">
</p>

**Why the statistic matters.** Cross-track error over the lap, the quantity the
tolerance is defined against. The certificate detects failures that persist along the
route; the peak statistic provably cannot, because it misorders the two networks.

<p align="center">
  <img src="figures/cte_lap.png" width="540" alt="Cross-track error over the lap">
</p>

The twelve-cell agreement is in-sample: the tolerance horizon is fitted to the driven
outcomes, so it shows the sustained statistic is sensitive to what matters rather than
that it predicts. Scope, caveats, and the fitted horizon are in the paper.

## Layout

| | |
|---|---|
| `pipeline/` | CARLA interface, training (BC → DAgger → distillation), evaluation; the two student checkpoints (403 KB) |
| `scripts/certify_sustained_bound.py` | the certificate |
| `scripts/closed_loop_ledger.py` | closed-loop failure rates (≥10 reps, Wilson intervals) |
| `scripts/capture_offset_yaw.py` | full-lap capture rig |
| `results/` | the twelve certified bounds and the eight driven cells the paper reports |

## Reproduce

```bash
pip install -r requirements.txt   # plus torch, auto_LiRPA, and CARLA 0.9.16 (see file)

# 1. closed-loop driving (CARLA server required); the shipped checkpoints are the
#    published students — retraining from scratch is pipeline/train.py -> dagger.py
#    -> distill.py -> dagger_student.py
python scripts/closed_loop_ledger.py --student S_clear_84x28 --condition night

# 2. full-lap captures for verification (only the centreline slice is needed:
#    OY_OFFSETS=0.0 OY_YAWS=0.0, ~38 MB per condition)
python scripts/capture_offset_yaw.py

# 3. formal verification: alpha-CROWN + input-space branch-and-bound over the
#    disturbance family, no simulator -> the twelve certified bounds
python scripts/certify_sustained_bound.py
```

Every number in the paper traces to an artifact in `results/`; the paper repository
carries the checker. The research record behind this artifact — design, findings,
dispositions, retired instruments — lives in this repository's git history.

## License

Apache License 2.0. See [LICENSE](LICENSE).

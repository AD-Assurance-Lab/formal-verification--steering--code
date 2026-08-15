# Where the study stands — 2026-08-13

Written after a full day of experiments. Detail in `FINDINGS.md` (F14–F21),
`docs/DISPOSITIONS.md` (D-01…D-10) and `results/predictions/` (P-01…P-04).

## The headline

**Formal verification predicts closed-loop outcome 14/14** — 8/8 on the preset conditions
and **6/6 out-of-sample** at fog densities the criterion was never built from, with the
prediction committed to git before the cars drove (`e2a4710`).

| | clear | fog | night | shadows |
|---|---|---|---|---|
| **`S_clear`** verification | falsified | falsified | falsified | falsified |
| **`S_clear`** driving | fails 2/20 | fails 20/20 | fails 20/20 | fails 20/20 |
| **`S_mixed`** verification | certified | certified | certified | certified |
| **`S_mixed`** driving | passes 20/20 | passes 19/20 | passes 20/20 | passes 20/20 |

## What made it work, after five criteria failed

Every earlier criterion measured **error on the nominal path** — per-frame magnitude, signed
mean bias, sustained same-signed runs. All failed, and F21 explains why with measured data
rather than argument: at fog densities 25–55 the *true* per-frame biases reverse sign every
8–16 frames while the vehicle departs on every run. A parameter-free bicycle-model
accumulation criterion explains 1 of 4 failures. The frames that cause a departure are
off-centre views that occur **nowhere on the nominal trajectory**, so no bound over those
frames can see them.

The criterion that works asks a **stability** question instead of an accuracy one:

> Place the vehicle at lateral offset `o`. Recovery requires steering of the opposite sign.
> FALSIFIED iff the response is not provably restoring anywhere in the reachable tube
> (|o| ≤ 2 m, outside a 0.5 m dead-band).

`S_mixed` restores across the whole tube in every condition. `S_clear` restores near centre
and **reverses at −2 m** — a one-way trapdoor — and under night loses restoring authority
from −1 m outward, which is where it fails worst. No tuned parameter: it is a sign test.

## Certificate status

Point evaluations gave 14/14. Upgrading to a proof over the *continuous* interval is
underway: α-CROWN bounds the steering between adjacent captured offsets (affine in one
scalar, the same form as every disturbance field here).

**COMPLETE — 8/8.** α-CROWN bounds the steering over every continuous offset interval,
with a declared 0.5 m dead-band (no restoring requirement near the lane centre, where the
required response falls below any achievable bound width).

| condition | `S_clear` | `S_mixed` | driving |
|---|---|---|---|
| clear | **FALSIFIED** [−2.0,−1.5] | **CERTIFIED** | 2/20 vs 0/20 |
| fog | **FALSIFIED** [−2.0,−1.5] | **CERTIFIED** | 20/20 vs 19/20 |
| night | **FALSIFIED** [−2.0,−1.5] | **CERTIFIED** | 20/20 vs 0/20 |
| shadows | **FALSIFIED** [−2.0,−1.5] | **CERTIFIED** | 20/20 vs 0/20 |

**The same interval fails in every condition.** `S_clear` has no provable recovery authority
2 m out regardless of weather — a property of the policy, not of the disturbance. Night
erodes it inward to −1 m, which is where it fails worst. It also explains the clear-weather
row: `S_clear` fails clear only 2/20, at the intersection, and the criterion falsifies it
correctly, because an excursion there becomes a departure precisely because it cannot
recover.

## Disturbance models

Rebuilt on measured physics after F19 showed image fidelity is not behavioural fidelity —
the analytic fog model reproduced CARLA at R² 0.848 while driving `S_mixed`'s steering 23.8×
further than reality, i.e. it was **most wrong about the best policy**.

| condition | model | image R² | behavioural |
|---|---|---|---|
| fog | measured affine field | 0.963 | 0.91× / 1.35× |
| night | measured illumination field | 0.882 | 1.01× / 1.31× |
| shadows | measured per-frame mask | 0.919 | 0.96× / 1.17× |

Night's analytic model (R² 0.243) was retired: it could only *dim*, while CARLA's headlight
pool is 1.42× **brighter** than the overcast baseline near the bumper.

## What is NOT established

* **The tube is straight-road only**, ±2 m, six poses, one route, one town. Curves unprobed.
* **The dead-band is an assumption.** No restoring requirement within 0.5 m of centre,
  justified because the required response there falls below any achievable bound width —
  declared before the remaining conditions ran, but still an assumption.
* **Intersections are an ODD boundary** (D-09), not a defect: every marginal excursion and
  both departures on clear sit inside the western junction where markings vanish.
* **One earlier claim was refuted** (P-03): `S_mixed` does *not* degrade in mid-fog. It
  drove 60 laps across three unseen densities cleanly.

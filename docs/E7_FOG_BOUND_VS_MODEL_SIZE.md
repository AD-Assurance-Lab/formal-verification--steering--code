# E7 — is the Town04/Town06 fog asymmetry an artifact of model size?

**Run 2026-09-05.** **EXPLORATORY, NOT PRE-REGISTERED.** This was run to answer a direct
question about a published comparison, not to test a prediction, and it is labelled that
way deliberately: it does not carry the evidential weight of E1, E1b, E2, E4 or E6, all of
which committed their predictions before their first scored measurement. Anything built on
it should be re-run under a pre-registration first.

Artifacts: `results/town06/depth/cert/cert_size.json`, checkpoints
`S_mixed_size_small19k` / `S_mixed_size_small13k`.

## The question

Town04 certifies fog for both students. Town06 certifies it for neither. Town06's students
are 6.6x and 9.9x larger in ReLU count, and CROWN's relaxation loosens with size — so the
obvious sceptical reading is that the arterial's fog cells fail **because the network is
bigger**, not because the road is harder. If that were true, the cross-road comparison in
the paper would be measuring the architecture rather than the ODD.

## What was measured

Two additional mixed students were distilled on Town06 at the **same input size (168x56)**
and certified against the **same committed captures** through the **same bound math**
(`TOWN06_STUDENTS_OVERRIDE`, which reuses `certify_town06.py` rather than reimplementing
it). Learning rate 3e-4, kernels pinned.

```
FOG certified bound width, in units of tolerance
  Town04  S_mixed   (15,456 ReLU, 84x28)      0.23   CERTIFIED
  Town04  S_clear   ( 5,152 ReLU, 84x28)      0.79   CERTIFIED
  Town06  S_mixed   (101,888 ReLU, shipped)   1.69   not certified
  Town06  S_clear   ( 50,944 ReLU, shipped)   3.58   not certified
  Town06  S_mixed   ( 19,104 ReLU, tuned lr)  4.15   not certified
  Town06  S_mixed   ( 12,736 ReLU, tuned lr) 10.21   not certified
  Town06  S_mixed   (101,888 ReLU, tuned lr)  1.86   not certified
```

## E7-F1. The size explanation is refuted, in the strong direction

Shrinking the arterial student toward the highway student's neuron count makes its fog
bound **monotonically worse**: 1.69 → 4.15 → 10.21 as the network goes 101,888 → 19,104 →
12,736 ReLU. At Town04's own size class (19,104 against 15,456) the arterial's fog bound is
**18x wider** than the highway's.

Fog on the arterial is harder to certify **at every capacity measured**, and the gap widens
as the model shrinks. The sceptical reading is not merely unsupported; the data runs the
other way.

## E7-F2. Within a road, bound width tracks what the policy learned, not its size

At fixed input size and fixed captures on Town06, the **larger** student has the **tighter**
fog bound — `S_mixed` (101,888 ReLU) at 1.69 against `S_clear` (50,944) at 3.58. The clear
student never saw fog in training; the mixed one did. Bound width here is dominated by the
policy's actual sensitivity to the disturbance, not by relaxation slack.

Both statements can be true at once, and together they are the useful ones: **relaxation
slack grows with size, and sensitivity shrinks with relevant training data, and on this
family the second effect is the larger.** E4-F2's depth result is the clean isolation of
the first, because it holds neuron count fixed.

## E7-F3. A well-driving policy is still not certifiable here

The tuned student that drives Town06 fog at **0.98 ft** (E4-F1) carries a fog bound of
**1.86x** tolerance — marginally *wider* than the shipped student's 1.69x, and still
`not certified`.

That is **incompleteness, not unsoundness**: the certifier has never cleared a policy that
then failed. But it means the arterial's fog gap is not closed by getting a better policy,
and the honest statement about the method as applied is that on this road, under fog, the
bound refuses policies that drive acceptably.

## What this does and does not license

* **Does:** the paper's cross-road fog comparison can be defended against the model-size
  objection with a measurement rather than an argument.
* **Does not:** conclude anything about *why* the arterial's fog is harder. Candidates not
  separated here include the route's longer straights (T06-F11), fog's measured lift of the
  black floor and compression of dynamic range on this map, and the arterial's 34% smaller
  training set. Separating them needs its own pre-registered experiment.
* **Does not:** license quoting the small-student numbers as study results. One seed each,
  exploratory, no driving. They answer a yes/no question about an objection.

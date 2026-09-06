---
license: apache-2.0
task_categories:
  - image-feature-extraction
tags:
  - autonomous-driving
  - formal-verification
  - neural-network-verification
  - carla
  - robustness
size_categories:
  - n<1K
---

# Steering verification captures

Rendered camera frames along two full driving routes, in four weather conditions each.
These are the input to the formal certificates in
[AD-Assurance-Lab/formal-verification--steering--code](https://github.com/AD-Assurance-Lab/formal-verification--steering--code),
and they are published because they are what makes those certificates checkable **without
a simulator**. Certification reads captured frames, not a live CARLA server, so with this
dataset and the code repository anyone can recompute every reported bound on one GPU — or
on a CPU, more slowly.

## What is here

| | route | conditions | captured poses | frame size |
|---|---|---|---|---|
| `captures/town06/` | Town06 arterial, one 2,289 m lap (2,119 m scored) | clear, fog, night, low sun | 1,060 | 168×56 |
| `captures/town04_v2/` | Town04 highway, both directions, 2,988 m spanned and 2,861 m scored | clear, fog, night, low sun | 1,492 per direction | 84×28 |

The certifier bounds over every eighth captured pose — 133 per Town06 cell — which is the
stride recorded in the committed certificate.

Each `.npz` holds the frames for one condition along one route, together with the pose
track they were captured at. `capture_gate.json` records the coverage the capture actually
achieved, and `scope.json` the extent the study scores. 641 MB in total.

The conditions are physically parameterized rather than pixel perturbations: fog density,
sun altitude and the night preset are simulator parameters with physical meaning, and the
certificate is quantified over the family that interpolates between two rendered
endpoints. A norm ball in pixel space large enough to contain a night image also contains
physically impossible images, and would make the safety claim vacuous.

## Using it

From a clone of the code repository, one command places every file where the certifier
looks and verifies each one against a recorded digest:

```bash
python3 scripts/fetch_captures.py
```

Then, with no simulator running:

```bash
STUDY_MAP=Town06 python3 scripts/certify_town06.py --out /tmp/cert.json
STUDY_MAP=Town04 TOWN04_REDO=1 python3 scripts/certify_sustained_bound.py
```

`SHA256SUMS` lists the digest of every file, and the same digests are recorded in
`scripts/fetch_captures.py`. **Check them.** A capture is the certifier's entire input, so
a bound computed from the wrong frames is not a weaker result — it is a statement about a
different experiment, and it still prints a verdict and a margin and looks finished.

## What reproduces, and how exactly

Every verdict reproduces. The bounds reproduce to about 4 parts in 1,000, not exactly.
Bound propagation with branch-and-bound makes different splitting choices when tiny
floating-point differences reorder them, and that grows with network size; the same binary
run twice on the same GPU already differs by 2.5 parts in a million. Every verdict in the
study has at least 309 times more headroom than that, so the drift cannot change a
conclusion — but a changed *verdict*, or a bound that moves by more than a percent, means
something real is different and is worth investigating rather than accepting.

## What is not here

The training frames, about 59 GB, are not published. They are regenerable from the code
repository, nothing in the paper is checked against them directly, and they were collected
under a specific simulator configuration that makes them non-reusable across harness
changes.

## Citation

```bibtex
@software{ad_assurance_lab_steering_verification,
  author  = {{AD Assurance Lab, Western Michigan University}},
  title   = {Formal verification of end-to-end steering under
             physically parameterized weather},
  year    = {2026},
  doi     = {10.5281/zenodo.22101297},
  url     = {https://github.com/AD-Assurance-Lab/formal-verification--steering--code}
}
```

Apache 2.0, the same as the code.

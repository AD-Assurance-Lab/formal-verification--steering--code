---
license: apache-2.0
task_categories:
  - image-feature-extraction
tags:
  - autonomous-driving
  - formal-verification
  - carla
  - arxiv:2609.10951
size_categories:
  - 1K<n<10K
---

# Steering verification captures

Rendered camera frames along two driving routes, in four weather conditions each. These
are the input to the formal certificates in
[formal-verification--steering--code](https://github.com/AD-Assurance-Lab/formal-verification--steering--code),
and they are published because they are what makes those certificates checkable **without
a simulator**.

The paper is [*Testing Between the Test Cases: Proving End-to-End Steering in Conditions
You Never Drove*](https://huggingface.co/papers/2609.10951) (arXiv:2609.10951).

| | route | conditions | poses | frames |
|---|---|---|---|---|
| `captures/arterial/` | one 2,289 m lap, Town06 | clear, fog, night, low sun | 1,060 | 168×56 |
| `captures/highway/` | 2,988 m both directions, Town04 | clear, fog, night, low sun | 1,492 each | 84×28 |

Each `.npz` holds one condition along one route with the pose track it was captured at.

`teachers/` holds the four networks the shipped students were distilled from. They are
needed only to re-distil a student without re-running data aggregation, so they live here
rather than in every clone of the code: `python3 scripts/fetch_captures.py --teachers`.

645 MB in total.

## Using it

From a clone of the code repository, one command puts every file where the certifier
looks and checks each against a recorded digest:

```bash
python3 scripts/fetch_captures.py
STUDY_MAP=Town06 python3 scripts/verify/certify_town06.py --out /tmp/cert.json
```

**Check the digests.** A capture is the certifier's entire input, so a bound computed from
the wrong frames is a statement about a different experiment, and it still prints a
verdict and a margin and looks finished. `SHA256SUMS` lists all fifteen.

## What reproduces

Every verdict. The bounds reproduce to about 4 parts in 1,000, not exactly: branch-and-
bound makes different splitting choices when tiny floating-point differences reorder them,
and that grows with network size. Every verdict has at least 309× more headroom than that,
so the drift cannot change a conclusion, but a changed *verdict* means something real is
different.

## Citation

```bibtex
@software{ad_assurance_lab_steering_verification,
  author = {{AD Assurance Lab, Western Michigan University}},
  title  = {Formal verification of end-to-end steering under
            physically parameterized weather},
  year   = {2026},
  doi    = {10.5281/zenodo.22101297},
  url    = {https://github.com/AD-Assurance-Lab/formal-verification--steering--code}
}
```

Apache 2.0, the same as the code.

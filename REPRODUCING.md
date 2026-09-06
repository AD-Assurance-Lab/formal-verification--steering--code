# Reproducing this work

Three levels, in increasing cost. **Level 1 needs no simulator** and reproduces every
certified verdict in the paper. It is the one most readers want, and it runs on a laptop.

---

## What is here, and what is not

| | where | size | why |
|---|---|---|---|
| code, protocol, routes | git | 1.2 MB | the study |
| every artifact behind a reported number | git | 2.4 MB | including each individual lap |
| the README animation | git | 6.2 MB | |
| **every shipped policy and its teacher** | **git** | **8.8 MB** | see below |
| the captures the certifier reads | [Hugging Face](https://huggingface.co/datasets/AD-Assurance-Lab/steering-verification-captures) | 641 MB | `scripts/fetch_captures.py` |
| training frames | **not shipped** | 59 GB | regenerable; see Level 3 |

A clone checks out 19 MB, of which 6.2 MB is the README animation.

**All eight networks are in git.** They total 8.8 MB, so there is no reason to make you rebuild
them — and because the renderer is not bit-reproducible (a scene where nothing moves still
renders about 30 differing pixels per frame across repetitions), a rebuild would not give
byte-identical weights even with identical code and seeds. Shipping the weights is what
makes the numbers checkable.

| checkpoint | road | role | ReLU |
|---|---|---|---|
| `S_clear_84x28_v2` | highway | clear-only policy | 5,152 |
| `S_mixed_84x28_w3_v2_dagger_r00` | highway | mixed policy | 15,456 |
| `S_clear_t06lap_168x56_w2_s0` | arterial | clear-only policy | 50,944 |
| `S_mixed_t06lap_168x56_w4_s3` | arterial | mixed policy | 101,888 |
| four `teacher_*` checkpoints | both | so a policy can be re-distilled without re-running DAgger | — |

The `_v2` on the highway names is provenance, not a choice. An earlier highway run was
collected before the determinism harness existed, and rule D-11 makes that data unusable;
this study is the rebuild, and it is the only highway study here. The committed artifacts
record these names, so they are left alone.

Note `S_mixed_84x28_w3_v2_dagger_r00`: the highway procedure includes student DAgger, so
the policy is the DAgger'd checkpoint, not the distilled intermediate.
`config.final_student` resolves this, and both the certifier and the ledger call it.
Getting it wrong once produced a certificate about a model nobody ships.

The two `.selected` files record which seed was pinned for each arterial policy, which is
part of the blind protocol rather than a convenience.

---

## Level 1 — re-derive the certificates. No simulator, no CARLA.

Certification reads captured frames, not a live simulator.

```bash
bash scripts/bootstrap_env.sh          # builds .venv and proves it works; see below
python3 scripts/fetch_captures.py      # 641 MB, every file checked against a digest

STUDY_MAP=Town06 python3 scripts/certify_town06.py --out /tmp/cert.json     # 6 cells, blind
STUDY_MAP=Town04 python3 scripts/certify_sustained_bound.py                 # 12 cells
```

`--out` is not optional in practice: the default path IS
`results/arterial/certificate_town06.json`, the pass-1 artifact the protocol requires to
stand, so the script refuses to overwrite it without `--force`.

**A GPU is wanted but not required.** The certifier calls `require_cuda()` and refuses to
fall back silently, because a bound computed on another device is a bound about a
different computation. With no usable GPU, pass `--allow-cpu`: the verdicts are unchanged
and each bound lands within about 4e-3. Expect roughly 5 minutes per cell on a CPU against
about 30 seconds on a current card.

### Every verdict reproduces. The bounds reproduce to about 4e-3 relative, not exactly.

This used to read "exactly — this path is deterministic". Measured across a hardware
migration, that is wrong in three separate ways, none of which changes a verdict:

| comparison | worst relative difference in any bound |
|---|---|
| the same binary, run twice, same GPU | 2.5e-06 — **the certifier is not bitwise deterministic** |
| committed vs a different GPU, `S_clear` (50,944 ReLU) | 1.1e-08 … 4.7e-07 |
| committed vs a different GPU, `S_mixed` (101,888 ReLU) | 3.6e-04 … **3.9e-03** |
| GPU with cuDNN TF32 off, vs the CPU | agree with each other to about 1e-06 |

What is going on: cuDNN's TF32 default explains the clear-only student entirely — turn
TF32 off and the GPU reproduces the CPU. The mixed student differs in every configuration,
including the exact recorded environment on a different card, and the differences change
sign between cells. That is the signature of branch-and-bound making different splitting
choices when tiny floating-point differences reorder them, and it grows with network size.
Both bounds remain sound; they are simply not the same bound. Neither numpy nor torch
explains it: certifying under the exact recorded pair reproduces the drift unchanged.

**What you should check** is that all six verdicts and all pose counts match, and that each
bound agrees to about 1e-2 relative. Every verdict in the study has at least **309x**
headroom between its bound and the value that would flip it, so a 4e-3 drift cannot change
a conclusion — but a *verdict* change, or a bound that moves by more than a percent, means
something real is different and should be investigated rather than accepted.

## Level 2 — re-drive the closed loop. Needs CARLA 0.9.16 and a GPU.

```bash
bash scripts/carla_launch.sh             # applies the determinism flags and verifies them
python3 -m carla_determinism --port 3000 # preflight; refuses a misconfigured server
STUDY_MAP=Town06 python3 scripts/closed_loop_ledger.py \
    --student S_mixed_t06lap_168x56_w4_s3 --channels 32,64,64 --fc 128 \
    --w 168 --h 56 --condition night --reps 3
```

**Expect rates, not identical runs.** Bit-exact closed-loop replay is unreachable, which is
why every closed-loop number here is a rate over repeated laps. Two things make it
reproducible in the sense that matters:

* the harness must satisfy the `carla-determinism` rules, which the preflight enforces by
  reading the server's real command line — the flags that matter are set at launch and are
  invisible over the network interface;
* the *oracle* is bit-identical across fresh servers on every section, so if your setup is
  right, `python3 scripts/drive_expert.py --direction all` twice produces identical CSVs,
  which you can diff against `results/oracle/`. That is the cheapest check that your
  simulator is configured correctly.

**A degraded server does not announce itself.** It keeps answering, keeps reporting
plausible speeds, and stops advancing physics correctly, and nothing in the resulting data
reveals which server produced it. Restart before every measurement run — not when something
looks wrong — with `bash scripts/carla_restart.sh`. It costs about 30 seconds.

## Level 3 — rebuild the networks from scratch. Days.

Everything for this level is in `scripts/training/`, kept apart because most readers will
never run it: the networks are shipped, so verifying and re-driving need none of it.

```bash
bash scripts/training/run_town06_pipeline.sh   # or run_town04_pipeline.sh; both resumable
```

The pipeline is the study's method, not its search. It collects laps, trains a behaviour-
cloning teacher, runs teacher DAgger until the teacher holds the road, distils a student
small enough to verify, runs student DAgger, and gates the result on clear-weather
competence. The seed sweeps and architecture searches that chose the shipped students are
**not** here — they are in git history. Reproducing this study means reproducing the
method; it does not mean re-running every experiment that led to it.

Collects the training laps, trains the teachers, runs teacher DAgger, distils, and gates.
Your checkpoints will not be byte-identical to the shipped ones, and **they may not be
equivalent**: one rebuild found a teacher that drove at 0.48 ft and distilled into a
student that departed at 30 ft, because the teacher gate stopped at the first passing
round. The drivers now pass `--min-rounds 8 --gate-reps 3` for exactly that reason. If your
student fails where the shipped one passes, compare teachers before reaching for capacity.

`python3 scripts/training/audit_training_data.py` checks a collected dataset for the degraded-server
signature — reported speed disagreeing with actual displacement — before you train on it.

---

## Publishing the captures again

The dataset is built from this repository, by the same script that fetches it, so the two
cannot come to describe different files:

```bash
python3 scripts/fetch_captures.py --stage /tmp/captures-upload
```

It copies the fifteen files, refuses if any digest differs from the table in
`scripts/fetch_captures.py`, writes `SHA256SUMS`, and adds
`scripts/captures_dataset_card.md` as the dataset's front page. It then prints the upload
command, which needs the Hugging Face client (`pip install -U huggingface_hub`, which
provides `hf`). Publishing a capture whose digest is not the recorded one would leave
every reader's fetch rejecting the real dataset, which is why it refuses rather than
warns.

---

## The environment

`bash scripts/bootstrap_env.sh` builds `.venv` and then refuses to finish unless a real
CUDA kernel runs, OpenCV works against the installed numpy, and the bound-propagation
library imports. Four of the dependencies cannot be installed by a plain resolver and it
handles each:

* **torch** comes from the PyTorch CUDA index, and the build must match the card's compute
  capability. A mismatched build reports `cuda.is_available() == True`, answers
  `get_device_name()` correctly, and then fails every kernel. Never check with
  `is_available()`; the entry points here call `require_cuda()`, which proves the device by
  operating on a tensor.
* **auto_LiRPA** comes from upstream git with `--no-deps`. The PyPI package is years stale
  and downgrades torch on install.
* **the CARLA client** ships with the simulator, one wheel per interpreter version, and the
  right one has to be chosen explicitly.
* **carla-determinism** is the lab's rules package and is pinned in `pyproject.toml`.

Everything else installs with `pip install -e '.[dev]'`.

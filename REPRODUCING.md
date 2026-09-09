# Reproducing this work

Three levels, in increasing cost. **Level 1 needs no simulator**, reproduces every
certified verdict in the paper, and runs on a laptop.

## What you download

| | where | size |
|---|---|---|
| code, routes, and every artifact behind a reported number | git | 4.4 MB |
| the README animation | git | 6.4 MB |
| the four trained policies | git | 4.8 MB |
| the captures the certifier reads | [Hugging Face](https://huggingface.co/datasets/AD-Assurance-Lab/steering-verification-captures) | 641 MB |
| training frames | not shipped, 59 GB, regenerable at level 3 | |

`git clone --depth 1` checks out 16 MB.

All four policies are in git, so nothing needs rebuilding to check the results. A rebuild
would not give identical weights in any case: the renderer is not bit reproducible, and a
scene where nothing moves still renders about 30 differing pixels per frame.

| checkpoint | road | role |
|---|---|---|
| `S_clear_84x28_v2` | highway | clear-only policy |
| `S_mixed_84x28_w3_v2_dagger_r00` | highway | mixed policy |
| `S_clear_t06lap_168x56_w2_s0` | arterial | clear-only policy |
| `S_mixed_t06lap_168x56_w4_s3` | arterial | mixed policy |

The highway's mixed policy is the DAgger checkpoint, not the distilled intermediate.
`config.final_student` resolves this, and both the certifier and the ledger call it.

## Level 1: re-derive the certificates. No simulator.

```bash
bash scripts/bootstrap_env.sh          # builds .venv and proves it works
python3 scripts/fetch_captures.py      # 641 MB, every file checked against a digest

STUDY_MAP=Town06 python3 scripts/verify/certify_town06.py --out /tmp/cert.json
STUDY_MAP=Town04 python3 scripts/verify/certify_sustained_bound.py
```

A GPU is wanted but not required. Pass `--allow-cpu` to run without one: the verdicts are
unchanged, each bound lands within about 4e-3, and it takes roughly 5 minutes per cell
instead of 30 seconds.

**Every verdict reproduces. The bounds do not reproduce exactly.** Running the same binary
twice on the same GPU moves a bound by up to 2.5e-6 relative, and a different GPU moves the
larger network's bounds by up to 3.9e-3. Branch-and-bound makes different splitting choices
when small floating-point differences reorder them, and the effect grows with network size.
Both bounds are sound; they are not the same bound. Check the verdicts and the pose counts,
and compare bounds in units of the tolerance, which is what the `x tol` column prints.

### How much room the verdicts have

A verdict flips when a bound crosses the tolerance.

| | tightest cell is this far from flipping | worst drift seen on re-run | margin |
|---|---|---|---|
| arterial | 0.240 x tol | 0.0009 x tol | **274x** |
| highway | 0.360 x tol | 0.218 x tol | **1.6x** |

Both roads reproduced every verdict and every pose count. They are not equally comfortable.
**The highway certificate reproduces its verdicts with very little room to spare.** Its
bounds are an order of magnitude smaller in absolute terms, so the same divergence moves
them much further in the units that matter. A different GPU could plausibly flip a highway
cell. That is a known sensitivity rather than a new result, but it should be reported.

`tests/test_reported_numbers.py` recomputes this table from the committed certificates, so
it cannot go stale.

## Level 2: re-drive the closed loop. Needs CARLA 0.9.16 and a GPU.

```bash
bash scripts/simulator/carla_launch.sh
python3 -m carla_determinism --port 3000        # refuses a misconfigured server
STUDY_MAP=Town06 python3 scripts/drive/closed_loop_ledger.py \
    --student S_mixed_t06lap_168x56_w4_s3 --channels 32,64,64 --fc 128 \
    --w 168 --h 56 --condition night --reps 3
```

**Expect rates, not identical runs.** Bit-exact closed-loop replay is unreachable, so every
closed-loop number here is a rate over repeated laps. Two things make that reproducible.
The preflight enforces the determinism rules by reading the server's real command line,
because the flags that matter are set at launch and cannot be seen over the network
interface. And the expert driver is bit-identical across fresh servers, so
`python3 scripts/drive/drive_expert.py --direction all` run twice gives identical CSVs that
you can diff against `results/oracle/`. That is the cheapest check that your simulator is
configured correctly.

**A degraded server does not announce itself.** It keeps answering and keeps reporting
plausible speeds while it stops advancing the physics, and nothing in the resulting data
shows which server produced it. Restart before every measurement run rather than when
something looks wrong, with `bash scripts/simulator/carla_restart.sh`. It costs about
30 seconds.

## Level 3: rebuild the networks. Days.

```bash
bash scripts/training/run_town06_pipeline.sh    # or run_town04_pipeline.sh; resumable
```

Everything for this level is in `scripts/training/`, kept apart because verifying and
re-driving need none of it. The pipeline collects laps, trains a behaviour-cloning teacher,
runs teacher DAgger until the teacher holds the road, distils a student small enough to
verify, runs student DAgger, and gates the result on clear-weather competence.

Your checkpoints will not match the shipped ones and may not be equivalent. One rebuild
produced a teacher that drove at 0.48 ft and distilled into a student that departed at
30 ft, because the teacher gate stopped at the first passing round. The drivers now pass
`--min-rounds 8 --gate-reps 3` for that reason. If your student fails where the shipped one
passes, compare teachers before reaching for more capacity.

`python3 scripts/training/audit_training_data.py` checks a collected dataset for the
degraded-server signature, reported speed disagreeing with actual displacement, before you
train on it.

## The environment

`bash scripts/bootstrap_env.sh` builds `.venv` and refuses to finish unless a real CUDA
kernel runs, OpenCV works against the installed numpy, and the bound-propagation library
imports. Four dependencies cannot be installed by a plain resolver:

* **torch** comes from the PyTorch CUDA index and must match the card's compute capability.
  A mismatched build reports `cuda.is_available() == True`, answers `get_device_name()`
  correctly, and then fails every kernel. The entry points call `require_cuda()`, which
  proves the device by operating on a tensor.
* **auto_LiRPA** comes from upstream git with `--no-deps`. The PyPI package is years stale
  and downgrades torch on install.
* **the CARLA client** ships with the simulator, one wheel per interpreter version.
* **carla-determinism** is the lab's rules package, pinned in `pyproject.toml`.

Everything else installs with `pip install -e '.[dev]'`.

To republish the captures, `python3 scripts/fetch_captures.py --stage /tmp/captures-upload`
stages them, refuses if any digest differs from the table in the fetcher, and prints the
upload command.

## How the results are filed

One file per cell rather than one per run. A cell is a student under a condition on a road,
at `results/<road>/ledger/<condition>__<checkpoint>__closed_loop.json`, carrying the
verdict, the lap-level detail, and a `runs` array with every lap and the provenance of the
server it was driven on. Step-by-step trajectories are one `traces.csv` per ledger, whose
`run` column is `<condition>__<student>__<direction>__rep<NN>`, built from the cell's
`student` field rather than its `checkpoint`, which differ where a policy resolves to a
later checkpoint.

The low sun condition is stored as `shadows` in the highway's files and as `low_sun` on the
arterial. It is one condition under two names, and low sun is the one the paper uses.

`results/arterial/hardware_recheck.json` records the mixed policy's fog cell. The two
committed passes each contain one lap over budget while the rest sit near half the budget,
which makes those samples disagree. Four later campaigns of 84 laps resolve it: the shipped
policy drives fog 30 times with no lap over budget and a worst of 1.95 ft against a 2.19 ft
budget. `scripts/drive/summarize_rechecks.py` rebuilds the file.

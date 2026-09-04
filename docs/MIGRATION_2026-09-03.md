# Migration to the new desktop — reproduction check

**Run 2026-09-03.** New machine: Ubuntu with ROS Jazzy, Python 3.12.3, RTX 5090
(sm_120, 32 GiB), 32 cores, 60 GiB RAM. Nothing in the study was re-run for the
paper; this is a check that the frozen result still reproduces here.

## Verdict

**The study reproduces. The environment it was pinned to does not run on this GPU.**

All six defects below are FIXED, not merely recorded. `bash scripts/bootstrap_env.sh`
builds the environment and proves it; `scripts/audit_repo.py` is 249 passed / 0 failed
(was 216) with new checks that stop each one regressing.

| check | result |
|---|---|
| `pytest tests/` | 78 passed (matches the record) |
| `scripts/audit_repo.py` | 216 passed, 0 failed (matches the record) |
| Town06 certificate, 6 cells | **all 6 verdicts + pose counts reproduce** |
| oracle `drive_expert.py --direction all` | **bit-identical to the committed CSVs** |
| oracle across two fresh servers | **bit-identical** (the REPRODUCING.md check) |
| determinism preflight (D-3/D-5) | OK on every fresh server |
| render photometry, Town06/clear | 0.257097 vs reference 0.257106 — **0.003% off**, tol 1.0% |

The photometry and bit-identical oracle together say the 5090 renders and simulates
the same scene the old card did. That was the main risk and it is retired.

## M-1. The pinned torch cannot execute on this GPU, and `torch.cuda.is_available()` lies

`torch 2.5.1+cu121` builds for sm_50..sm_90. The 5090 is **sm_120**. `is_available()`
returns `True`, `get_device_name()` answers correctly, and then every kernel dies with
`no kernel image is available for execution on the device`. `certify_town06.py:234`
selects the device with exactly that predicate, so the certifier picks CUDA and crashes.

**Fixed** by a second environment, `.venv-cu130/`, on **`torch 2.13.0+cu130`** — which is
the version the committed certificates record in their own `_meta`, and which ships
sm_120. The old `.venv/` is left in place and still works CPU-only.

## M-2. `requirements.txt` documents a superseded environment

The "environment of record" block claims torch 2.5.1+cu121 / numpy 2.2.6, and says
"every result in the repo was produced under numpy 2.2.6". Both certificates and the
Town04-redo sustained bound record, at runtime (`torch.__version__`, `np.__version__`),
**torch 2.13.0+cu130 / numpy 1.26.4**. Only `results/calibration/sustained_bound.json` —
the superseded era-1 artifact — carries 2.5.1/2.2.6, and that is the file the block was
evidently read off.

**RESOLVED.** `opencv-python==4.13.0.92` *declares* `numpy>=2`, which is why pip calls it
irreconcilable with the numpy 1.26.4 the certificates record — but that is a declared pin,
not an ABI requirement. Wheels built against numpy 2 run correctly on numpy 1.x, and
`cv2.resize` on a numpy-1.26.4 array is verified on every build by `bootstrap_env.sh`.
Installing opencv with `--no-deps` reconstructs the published environment exactly.
`requirements.txt` now records the pair the artifacts actually carry, and says which
artifact each reading came from.

## M-3. Bounds reproduce to ~4e-3, not exactly — REPRODUCING.md overclaims

REPRODUCING.md says Level 1 bounds "should reproduce **exactly** — this path is
deterministic". Measured here:

| comparison | worst relative difference in any bound |
|---|---|
| same env, run 1 vs run 2 (GPU) | 2.5e-06 — **the certifier is not bitwise deterministic** |
| committed vs here, `S_clear` cells | 1.8e-08 … 4.4e-07 (within its own run-to-run noise) |
| committed vs here, `S_mixed` cells | 3.7e-04 … **3.9e-03** |
| committed vs here, CPU/torch 2.5.1 | up to 4.0e-03 |

The drift is concentrated in the **larger** student (101,888 ReLU vs 50,944) and is
100–1000x its own run-to-run noise, so it is systematic, not sampling.

**Cause, established by measurement rather than guessed:**

* **Not numpy.** Certifying under the exact recorded pair (torch 2.13.0+cu130 + numpy
  1.26.4) reproduces the drift unchanged; numpy 2.2.6 agrees with numpy 1.26.4 to 1e-9.
* **Not the checkpoint.** Both runs certify the same `_meta.checkpoints`
  (`S_clear_t06lap_168x56_w2_s0`, `S_mixed_t06lap_168x56_w4_s3`) at the same ReLU counts.
* **cuDNN TF32 explains the clear student entirely.** `torch.backends.cudnn.allow_tf32`
  defaults to True; with it off, the GPU agrees with the CPU to ~1e-6, and the committed
  values match the TF32-ON GPU to 1e-7. (`matmul.allow_tf32` is already False by default.)
* **The mixed student differs in every configuration**, including the exact recorded
  environment, and **the differences change sign between cells** (−0.062%, +0.009%,
  +0.001% on bound width). That is not a precision bias. It is the signature of
  α-CROWN's branch-and-bound making different splitting choices once floating-point
  differences reorder them — a discrete effect that grows with network size. Both bounds
  remain sound; they are not the same bound.

The practical consequence for the follow-on experiments: **certified bounds are
comparable within a machine, and to ~1e-2 across machines.** E4 compares bound widths
across architectures and must do that on one machine in one session.

**No verdict is threatened.** Headroom from each bound to the value that would flip its
verdict, against the drift, is **309x** at worst (`S_mixed_t06/fog`) and 35,000,000x at
best. All six verdicts and all pose counts are unchanged.

The wording in REPRODUCING.md should become a tolerance, not "exactly".

## M-4. ROS Jazzy leaks into the venv via `PYTHONPATH`

The shell carries `PYTHONPATH=/opt/ros/jazzy/lib/python3.12/site-packages`, and the venv
is `include-system-site-packages = false` — which `PYTHONPATH` overrides anyway. `pytest`
then loads ROS's `launch_testing` plugin and dies (`ModuleNotFoundError: yaml`, then
`PluginValidationError: unknown hook 'pytest_launch_collect_makemodule'`). Zero tests run.

`env -u PYTHONPATH` fixes it. Since ROS is staying, this needs a permanent fix — the
entry points should neutralise `PYTHONPATH` themselves rather than every caller
remembering. Note the old machine's `-p no:anyio` workaround is **not** needed here.

## M-5. `DISPLAY` is `:1` on this machine, not `:0`

There is no `:0`. `carla_launch.sh` uses `${DISPLAY:-:0}` so it inherits correctly when
DISPLAY is exported, but every doc (`NEXT_SESSION.md`, workspace `CLAUDE.md` standing
rule 6, `NEXT_EXPERIMENTS.md`) instructs `DISPLAY=:0`, which would silently take the
headless fallback path and stop Zach watching runs. Launch verified windowed on `:1`.

## M-6. `--out` outside the repo crashes after writing

`certify_town06.py:356` calls `dest.relative_to(REPO)` for its log line, so an `--out`
path outside the repo raises `ValueError` *after* the certificate is written. Harmless
but it exits nonzero on a successful run.

## Note for whoever runs the next certification

`certify_town06.py` writes to `results/town06/certificate_town06.json` **by default** —
the protected pass-1 artifact. Pass `--out`, or back it up first. It was overwritten
during this check and restored from git (sha verified).


---

## What was changed to fix all of this

| # | fix |
|---|---|
| M-1 | `scripts/bootstrap_env.sh` builds `.venv` on torch 2.13.0+cu130 and **proves a real CUDA kernel runs** before returning. The certifiers, the measurement scripts and `train.py`/`distill.py` now call `require_cuda()` (which was already in `pipeline/gpu.py`, and already catches this) instead of the `is_available()` idiom. `audit_repo.py` enforces it across 17 files, up from 4. |
| M-2 | `requirements.txt` records torch 2.13.0+cu130 / numpy 1.26.4, cites the artifact each reading came from, and explains the `--no-deps` opencv install. |
| M-3 | `REPRODUCING.md` states the measured tolerance and what to check, instead of "exactly". |
| M-4 | The venv carries `zzz_strip_system_paths.pth`, which removes ROS and system dist-packages from `sys.path` at interpreter startup. **A `sitecustomize.py` does NOT work** — Ubuntu ships `/usr/lib/python3.12/sitecustomize.py`, which sits earlier on the path, and only the first one found is imported. `pytest` now runs clean with `PYTHONPATH` set. |
| M-5 | `carla_launch.sh` probes `/tmp/.X11-unix/` with `xdpyinfo` for a live display instead of assuming `:0`; docs corrected. |
| M-6 | `certify_town06.py` formats its log line with a helper that tolerates an `--out` outside the repo. |
| — | `certify_town06.py` **refuses to overwrite an existing certificate** (`--force` to override), and refuses *before* certifying rather than after spending the run. |

## Still open

* The opencv four-component version (`4.13.0.90` vs `.92`) cannot be recovered from
  `cv2.__version__`, which reports `4.13.0` for both. `.92` remains an assumption.
* `carla_restart.sh` and the other CARLA scripts call bare `python3`, so they need the
  venv on `PATH` (or an activated venv). Making the entry points resolve their own
  interpreter would remove the last footgun; not done here.
* AEB and multi-condition have the same `is_available()` idiom and the same ROS
  `PYTHONPATH` exposure. `bootstrap_env.sh` and the `require_cuda` change should be
  ported to both before their next measurement run.

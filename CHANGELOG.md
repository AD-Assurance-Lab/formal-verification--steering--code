# Changelog

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] — 2026-09-06

The study is finished. This release turns the working repository into the published
artifact: same results, far less around them.

### Fixed

- **51 files the paper depends on were never committed.** `.gitignore` excluded every
  `runs/` directory, and the un-ignore rules had been written for the arterial study
  only, never extended to the highway rebuild. A fresh clone therefore could not verify
  the highway results table at all — all 48 per-run ledger artifacts and the three
  teacher fog laps quoted in the results were missing. Nothing revealed it: the
  aggregate files beside them were tracked, so the directory looked complete.
- `scripts/audit_repo.py` asserted that two superseded six-section policies were present
  and tracked, rather than the two the paper actually reports on the arterial. It was
  guarding models nothing uses.

### Changed

- **This is now an installable package.** `pip install -e .` and `import steering`.
  Previously nothing imported on its own: modules began with `from config import ...`,
  which resolves only if some caller has already run `sys.path.insert(0, "pipeline")`,
  and there were 96 such inserts in 17 spellings.
  - `pipeline/*.py` → `src/steering/`, the library
  - `pipeline/{train,dagger,distill,collect_data,...}.py` → `scripts/`
  - `pipeline/data/` → `data/`, `pipeline/checkpoints/` → `checkpoints/`
  - helpers that scripts imported from other scripts are now library code:
    `steering.captures`, `steering.ledger`, `steering.model.load_model`,
    `steering.route_design`
- `REPO_ROOT` is defined once, in `steering/__init__.py`, and honours
  `STEERING_REPO_ROOT`. Every module used to count directories up from its own file.
- `pyproject.toml` replaces `requirements.txt` as the dependency source of truth. The
  four packages a resolver can install are declared there; torch, auto_LiRPA and the
  CARLA client stay in `scripts/bootstrap_env.sh`, which installs them in the required
  order and then proves the result works.
- `.gitignore` ignores `results/`, `data/` and `checkpoints/` wholesale. Files already
  tracked are unaffected; what it stops is `git add -A` enlarging the published record
  with working output.

### Added

- `scripts/fetch_captures.py` — retrieves the 641 MB of captured frames from
  [Hugging Face](https://huggingface.co/datasets/AD-Assurance-Lab/steering-verification-captures)
  and checks every file against a recorded digest. This is what makes the certificates
  reproducible with no simulator.
- `tests/test_imports.py` — imports every module as its own process under both maps,
  112 cases. The training and capture paths need CARLA and a GPU, so nothing else here
  touches them; without this a refactor that broke one would surface months later on
  someone else's clone.
- Continuous integration running the tests that need neither CARLA nor a GPU.
- `CITATION.cff`, this changelog, and README figures generated from the paper's own.

### Removed

- 56 pre-registrations, findings documents and archives; two session-status files.
- 63 scripts unreachable from any documented workflow, and the 1,007 result files from
  those experiments.
- The four six-section-era arterial checkpoints — a valid study on a route this paper
  does not report.

Nothing removed is lost: the full research record is in this repository's git history,
before this release. Tracked files went from 1,438 to 371.

### Verified

Unchanged across every step above:

| | |
|---|---|
| the paper's `figures/check_data.py` | 402 checks, 0 failures |
| `pytest` | 209 passed, 4 skipped (was 100 passed) |
| `scripts/audit_repo.py` | 266 passed, 0 failed |

## [1.2.0] — 2026-09-03

Arterial deployment test complete. Criterion frozen and the certificate committed before
any scored lap; agreement four of five on scored cells, with all eight verdicts
reproduced by an independent second pass.

## [1.1.0] — 2026-08-30

Corrected simulator harness. Every measurement now goes through the `carla-determinism`
preflight, the highway study was rebuilt on it, and the arterial deployment test began.
Data collected under the previous harness is not reusable.

## [1.0.1] — 2026-08-25

README figures: route and vehicle visuals, and the night comparison animation.

## [1.0.0] — 2026-08-25

First publication artifact for the end-to-end steering verification study.

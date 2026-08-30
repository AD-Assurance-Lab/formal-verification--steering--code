# Reproducing this work

Three levels, in increasing cost. **Level 1 needs no simulator and no GPU-hours** and
reproduces every certified bound in both papers; it is the one most readers want.

---

## What is in this repository, and what is not

| | where | size | why |
|---|---|---|---|
| code, protocol, routes | git | small | the study |
| **every shipped policy + its final teacher** | **git** | **5.5 MB** | see below |
| verification captures | release asset / Zenodo | 354 MB | the certifier's input |
| training datasets | **not shipped** | 59 GB | regenerable; see Level 3 |

**All ten model checkpoints are in git.** They total 5.5 MB, so there is no reason to make
you rebuild them — and because the CARLA renderer is not bit-reproducible
(`carla-determinism` rule D-7: a scene where nothing moves still renders ~30 differing
pixels per frame across repetitions), a rebuild would not give byte-identical weights even
with identical code and seeds. Shipping the weights is what makes the numbers checkable.

```
S_clear_84x28              Town04 published, clear-only          5,152 ReLU
S_mixed_84x28_w3           Town04 published, mixed              15,456 ReLU
S_clear_84x28_v2           Town04 redo, corrected harness        5,152 ReLU
S_mixed_84x28_w3_v2_dagger_r00   Town04 redo, mixed             15,456 ReLU
S_clear_t06_168x28_w2      Town06 deployment test, clear-only   21,408 ReLU
S_mixed_t06_168x28_w3      Town06 deployment test, mixed        32,112 ReLU
+ the four final teachers, so a student can be re-distilled without re-running DAgger
```

Note `S_mixed_84x28_w3_v2_dagger_r00`: Town04's procedure includes student DAgger, so the
policy is the DAgger'd checkpoint, not the distilled intermediate. `config.final_student`
resolves this, and both the certifier and the ledger call it. Getting that wrong once
produced a certificate about a model nobody ships (T04-R5).

---

## Level 1 — re-derive the certificates. No simulator, no CARLA.

Certification reads captured frames, not a live simulator. Fetch the capture bundle (see
Releases), then:

```bash
pip install -r requirements.txt          # includes the carla-determinism package
tar xf steering-captures-vX.Y.Z.tar.zst  # -> results/town06/captures, results/town04_v2/calibration

STUDY_MAP=Town06 python3 scripts/certify_town06.py          # 6 cells, blind
STUDY_MAP=Town04 TOWN04_REDO=1 python3 scripts/certify_sustained_bound.py   # 12 cells
```

Every bound in both papers should reproduce **exactly** — this path is deterministic, and
the only nondeterminism in the study lives in the renderer, which is upstream of it.

## Level 2 — re-drive the closed loop. Needs CARLA 0.9.16 and a GPU.

```bash
bash scripts/carla_launch.sh             # applies the determinism flags and verifies them
python3 -m carla_determinism --port 3000 # preflight; refuses a misconfigured server
STUDY_MAP=Town06 python3 scripts/closed_loop_ledger.py --student S_mixed_t06_168x28_w3 \
    --channels 24,48,48 --fc 96 --w 168 --h 28 --condition night --reps 6
```

**Expect rates, not identical runs.** Bit-exact closed-loop replay is unreachable (D-7),
which is why every closed-loop number here is a failure rate over >= 10 repetitions with a
Wilson interval. Two things make this reproducible in the sense that matters:

* the harness must satisfy `carla-determinism` D-1..D-6, which the preflight enforces by
  reading the server's real command line — the flags that matter are launch-time and
  invisible over RPC;
* the *oracle* is bit-identical across fresh servers on every section, so if your setup is
  right, `python3 pipeline/drive_expert.py --direction all` twice should produce identical
  CSVs. That is the cheapest check that your simulator is configured correctly.

## Level 3 — rebuild the models from scratch. Days.

```bash
bash scripts/run_town06_pipeline.sh      # or run_town04_pipeline.sh; both resumable
```

Collects ~27k frames, trains BC teachers, runs teacher DAgger, distils, and gates. Your
checkpoints will not be byte-identical to the shipped ones (D-7), and **they may not be
equivalent**: T04-R3 found a teacher that drove at 0.48 ft and distilled into a student
that departed at 30 ft, because the teacher gate stopped at the first passing round. The
drivers now pass `--min-rounds 8 --gate-reps 3` for exactly that reason. If your student
fails where the shipped one passes, compare teachers before reaching for capacity.

---

## Recommended hosting for the captures (354 MB)

They are the certifier's input and the only way to reproduce the bounds without a
simulator, so they should be published, not merely retained.

* **Zenodo — recommended.** Gets a DOI, is permanent, is designed for exactly this, and is
  citable from the paper. 50 GB per record.
* **GitHub Release asset.** 2 GB per file, no LFS quota, no extra service. Simplest if the
  captures are only ever fetched alongside a tagged version.
* **Git LFS — not recommended here.** Bandwidth is metered and shared across the
  organisation, and these files never change, so versioning them buys nothing.

Do **not** ship `pipeline/data/` (59 GB of training frames). It is regenerable, it is the
one artifact rule D-11 makes non-reusable across harness changes, and nothing in either
paper is checked against it directly.

# Reproducing this work

Three levels, in increasing cost. **Level 1 needs no simulator** and reproduces every
certified verdict in both papers; it is the one most readers want.

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
bash scripts/bootstrap_env.sh            # builds .venv and proves it works; see below
tar xf steering-captures.tar.zst         # -> results/{town06/captures,town04_v2/calibration,diagnostic}
# sha256 10fb9b4a05e4b4de8591bf86df35216f1ac51420ceed637027b4efefd6a89e8c

STUDY_MAP=Town06 python3 scripts/certify_town06.py --out /tmp/cert.json     # 6 cells, blind
STUDY_MAP=Town04 TOWN04_REDO=1 python3 scripts/certify_sustained_bound.py   # 12 cells
```

`--out` is not optional in practice: the default path IS
`results/town06/certificate_town06.json`, the pass-1 artifact PROTOCOL R4 requires to
stand, so the script refuses to overwrite it without `--force`.

**A GPU is wanted but not required.** The certifier calls `require_cuda()` and refuses to
fall back silently, because a bound computed on another device is a bound about a
different computation. With no usable GPU, pass `--allow-cpu`: the verdicts are unchanged
and each bound lands within ~4e-3 (the CPU agrees with a TF32-disabled GPU to ~1e-6).
Expect roughly 5 minutes per cell on a CPU against ~30 seconds on a current card.

**Every verdict reproduces. The bounds reproduce to about 4e-3 relative, not exactly.**

This claim used to read "exactly — this path is deterministic". Measured on the
2026-09-03 desktop migration (`docs/MIGRATION_2026-09-03.md`), that is wrong in three
separate ways, none of which changes a verdict:

| comparison | worst relative difference in any bound |
|---|---|
| the same binary, run twice, same GPU | 2.5e-06 — **the certifier is not bitwise deterministic** |
| committed vs a different GPU, `S_clear` (50,944 ReLU) | 1.1e-08 … 4.7e-07 |
| committed vs a different GPU, `S_mixed` (101,888 ReLU) | 3.6e-04 … **3.9e-03** |
| GPU with cuDNN TF32 off, vs the CPU | agree with each other to ~1e-06 |

What is actually going on: cuDNN's TF32 default explains the *clear* student entirely —
turn TF32 off and the GPU reproduces the CPU. The *mixed* student differs in every
configuration, including the exact recorded environment on a different card, and the
differences change sign between cells. That is the signature of α-CROWN's branch-and-bound
making different splitting choices when tiny floating-point differences reorder them, and
it grows with network size. Both bounds remain sound; they are simply not the same bound.

**Neither numpy nor torch explains it.** Certifying under the exact recorded pair
(torch 2.13.0+cu130, numpy 1.26.4) reproduces the drift unchanged, and numpy 2.2.6 gives
results identical to numpy 1.26.4 to 1e-9.

**What you should check** is that all six verdicts and all pose counts match, and that
each bound agrees to ~1e-2 relative. Every verdict in the study has at least **309x**
headroom between its bound and the value that would flip it, so a 4e-3 drift cannot
change a conclusion — but a *verdict* change, or a bound that moves by more than a
percent, means something real is different and should be investigated rather than
accepted.

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

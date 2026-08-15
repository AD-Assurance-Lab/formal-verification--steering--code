# Session handoff -- 2026-08-15, 07:45

Written before a machine restart. Everything below is committed and pushed on `main` in
both repos. Nothing is left only on disk except the driven captures, which are gitignored
and regenerable (see "If you need to regenerate").

Start by reading `docs/STATE_OF_PLAY.md` sections 0, 0b, 0c. This file is the delta on top
of it.

---

## Where to pick up

**The paper is DONE and pushed.** `formal-verification--automated-driving--arxiv` @
`1299f22`. 8-page body, references on 9-10, builds clean (`pdflatex main` x2), no overfull
boxes. It claims the sustained per-frame certificate at 12/12 on the canonical conditions
and reports the localised sun-angle mode as a measured negative result. It does not depend
on anything below.

**The open thread is the loop route, and it is now close to dead in its current form.**
The driven-capture experiment finished and is written up in
`results/predictions/P09_driven_rollout.md`. Short version: better captures made the local
fit WORSE, not better --

    disturbance term a rollout integrates   0.0052
    static grid, gain-corrected (F42)       0.0258
    DRIVEN captures, local plane fit        0.049 - 0.055

so the rollout verdicts are noise (the 4/10 in that file is explicitly NOT evidence). The
reading is that for a moving vehicle the steering output is not a well-defined function of
(offset, heading) at a pose -- it depends on the trajectory taken to reach it. If so, no
capture fidelity fixes a rollout, and the next test is cheap and decisive: drive the same
pose from two different approach trajectories and compare steering. If they differ by ~0.05,
the premise is dead and the loop route needs a model with memory.

**One defect to fix before trusting `scripts/driven_rollout.py`:** two different cells
(`S_mixed`/shadows and `S_mixed`/sun15) returned identical peak and residual to three
decimals, which should be impossible. Likely a cache or indexing bug. It does not affect the
residual measurement above (computed per capture, ~0.05 for all ten cells), but the script
should not be used for verdicts until it is found.

---

## What happened this session, in order

1. **Paper rewritten** around the canonical result. Three factual corrections were made to
   the previous draft: it claimed SDP-CROWN was our verifier (it is alpha-CROWN with
   input-space branch and bound), its peak-statistic numbers did not match F30's recorded
   table, and its disturbance magnitudes were wrong. All regenerated from source.

2. **P-09 sun-angle study, blind protocol honoured.** Split declared before capture
   (`P09_sun_angle_design.md`), held-out verdicts committed before driving (`070a2b2`).
   Result 2/4 (F39). This SETTLES F38's open hypothesis: the misses are not a ~1.2x scale
   error. All four cells certify in a 0.68-0.93 band while driving spans 0/10 to 10/10, and
   no window from 5.4 m to the full lap orders them correctly.

3. **Located why** (F39): at the pose where +30 reproducibly departs, the windowed deviation
   ranks 1064th of 1599 poses. The nominal path does not contain the failure. That single
   fact explains why eight successive criteria all landed at chance on this mode.

4. **Tried the loop route** (F40): rolling vehicle state over the STATIC (offset x heading)
   grid reproduces +30 (11.4 m predicted vs 8.8-13.2 m measured) and +60 (0.24 m), and puts
   the cause ~150 m upstream of the symptom, where the restoring gain inverts sign. But it
   scores 2/6 on the canonical cells, and both excuses were ruled out by measurement.

5. **Found the reason** (F41, F42): the captures are too coarse to integrate.

        off-nominal surface error, in grid    0.021 - 0.048
        static vs driven frame, gain-corr.    0.0258        (n=198)
        nominal capture error (gate A)        0.0137
        disturbance term a rollout integrates 0.0052

   A per-frame verdict never accumulates that error, which is why the certificate is
   unaffected. A rollout does.

6. **Built the fix you approved**: `scripts/capture_driven_offsets.py`. The EXPERT drives a
   sinusoidally shifted copy of the route, so frames come from a genuinely moving off-centre
   vehicle carrying real suspension state and camera motion. The student never enters the
   loop; it is scored offline. Coverage measured at +-1.2 m offset and +-9 deg heading with
   offset and heading decorrelated (|corr| 0.057), which is better than the static grid.

7. **Captured 8 conditions** eastbound, 6 phases each, ~10,215 frames per condition:
   clear, sun +60/+30/+37/+15, fog, night, shadows. ~4 min per condition.

8. **Scored** with `scripts/driven_rollout.py`. See `P09_driven_rollout.md`.

---

## The thing to check FIRST when reading that result

The verdict column is meaningless unless the plane-fit residual is well below `0.0052`,
the disturbance term the rollout integrates. That is exactly the test static captures failed
at `0.0258`. The script prints the residual next to every verdict for this reason.

If the residual is not small, the correct conclusion is "still dominated by capture noise",
NOT "the criterion works/doesn't work" -- regardless of how the agreement column reads.

---

## Standing rules that bit this session

- **`grep` block-buffers into a file.** Use `--line-buffered`, or a run that is fine looks
  stalled. Cost a 35-minute run earlier in the project.
- **`pkill -f` matches your own command line.** Use bracket patterns (`[c]apture`) or PIDs.
  It killed this shell once and silently removed a queued job.
- **Long runs must be detached** (`setsid nohup ... &`). Foreground and harness-waited jobs
  were killed several times this session; the detached ones survived every time.
- **CARLA is on port 3000 here**, not the default 2000. `CARLA_PORT=3000`.
- **Verdicts before driving.** `python -m study.ledger --check-order` verifies it against
  git history. The P-09 runner would have driven a held-out cell before its verdict was
  committed; that was caught and stopped, and the blind held.

---

## If you need to regenerate

Driven captures are gitignored (`results/**/*.npz`), ~250 MB each, ~2 GB total:

    # CARLA must be up on port 3000, windowed on DISPLAY=:0
    bash scripts/driven_campaign.sh           # all 8 conditions, resumable
    CARLA_PORT=3000 [SUN_ALTITUDE_OVERRIDE=30] python -u scripts/capture_driven_offsets.py \
        --direction eastbound --condition clear --phases 6 \
        --out results/calibration/driven_<name>_eastbound.npz

    python -u scripts/driven_rollout.py       # scores all ten cells

---

## What is NOT affected by any of the above

The canonical twelve stand at 12/12 under the sustained per-frame certificate (F34-F37),
both directions, sound alpha-CROWN bounds over s in [0,1], no fitted parameters. Every
finding in this session concerns either the localised sun-angle mode or the loop route,
neither of which feeds that certificate. The paper says so.

# Town04 redo — findings

Redo of the published Town04 study under the corrected simulator harness (T06-F22). A
DISCOVERY test, as the published one was: `T_CLOSED_LOOP_S` was back-solved from Town04's
own closed-loop cliff, so its agreement measures sensitivity rather than prediction.
Everything is namespaced under `_v2` / `results/town04_v2` so the published artifacts,
which are tracked in git under the unsuffixed names, are untouched and comparable.

## T04-R1  Reproduction fidelity of the build

    base dataset       27,112 frames against the published 27,109 (±3, lap-closure timing)
    clear BC teacher   val RMSE 0.0038 against the published 0.0042
    clear teacher      converged round 3, i.e. 4 rounds -- the published count exactly
    mixed teacher      converged round 4, i.e. 5 rounds, against the published 9
    clear student KD   0.0292 against the published 1x width-sweep figure of 0.0338
    mixed student KD   0.0156 against the published 3x figure of 0.0327

The mixed teacher converging in 5 rounds rather than 9 is consistent with T06-F24: the
gate is a conjunction of single-run cells (8 here) and the round count is a waiting time,
not a property of the task.

## T04-R2  MIXED STUDENT: reproduced, and it needed student DAgger

`S_mixed_84x28_w3_v2` at the published (24,48,48)/fc96, 15,456 ReLU. Re-measured on a
FRESH SERVER per condition:

    clear     eastbound 0.93 ft   westbound 0.47 ft
    fog       eastbound 1.51 ft   westbound 1.91 ft
    night     eastbound 1.71 ft   westbound 1.20 ft
    low sun   eastbound 0.95 ft   westbound 0.76 ft
                                                    8/8 PASS, worst 1.91 ft, budget 2.19

Distilled-only it was 7/8 (fog/westbound 2.43 ft); **one round of student DAgger took it
to 8/8**, and the published study used exactly one round as well
(`dagger_student_w3/round00`). Student DAgger is part of Town04's procedure and it is
doing real work here, unlike Town06 where T06-F14 removed it and the rebuild confirmed it
was not needed at w3.

## T04-R3  CLEAR STUDENT: the teacher is a good DRIVER and a bad DISTILLATION TARGET

The redo's clear student fails `clear/eastbound` at step ~415-440 of ~1700 with 28-40 ft
of CTE, while over-budget stays around 4% -- it drives most of the lap and departs in one
curve, under-steering where the expert commands roughly 3x more (nn_steer -0.0435 against
expert -0.1191). Ruled out, in order:

  - **The harness.** The PUBLISHED student checkpoint, driven on the corrected harness,
    passes both directions (eastbound 0.79 ft, westbound 2.11 ft). The harness is fine.
  - **Capacity.** w1 5,152 ReLU fails at step 420; w2 10,304 at 418; w1 at 168x28 (10,704)
    at 417; w2 at 168x28 (21,408) at 456. **Quadrupling capacity moves the failure by two
    steps.**
  - **The teacher's own driving.** `teacher_clear_v2_dagger_r02` drives eastbound 3/3 PASS
    at 0.48 / 0.48 / 0.48 ft on freshly restarted servers.
  - **Distillation data volume.** Enriching the DAgger set 12,914 -> 16,305 frames improved
    KD RMSE to 0.0292, BETTER than the published 0.0338, and it still failed. Another
    instance of T06-F28: KD RMSE does not predict closed-loop competence.
  - **The draw.** Five distillation seeds, architecture and data held fixed: all five fail
    eastbound at step 413-440. Not seed variance, which T06-F14 had measured as flipping a
    student 4/6 -> 6/6.
  - **On-distribution behaviour.** Offline on identical frames the redo and published
    students are near-identical -- on sharp-steer frames the redo steers slightly HARDER
    (mean |steer| 0.0662 vs 0.0630) and on mild frames it is MORE accurate (RMSE 0.0088 vs
    0.0121). It is not systematically under-steering on the training distribution.

**The A/B that settles it.** Distilling with the PUBLISHED teacher and the REDO's data
produces a student that passes both directions, 1.48 / 2.09 ft.

    published teacher + redo data  ->  PASS / PASS
    redo teacher      + redo data  ->  FAIL eastbound, every seed, every width

**So the teacher is the difference, and the property that differs is not its driving.**
Both teachers meet the gate; only one distils into a competent student. The redo teacher's
output is a harder function to approximate: distillation target sd 0.0676 against the
published teacher's 0.0510 on comparable sets.

The likely mechanism, and it is testable rather than asserted: the redo teacher converged
in 4 DAgger rounds and the published one ran 5. Extra rounds collected once the policy is
already good add gentler recovery data, which both enlarges the set and smooths the
function the student has to fit. `dagger.py`'s own `--min-rounds` help says exactly this --
"keep collecting through this round even once the teacher passes; the DAgger set is an
input to distillation, not just a means of fixing the teacher" -- and the redo driver did
not use it. **The teacher gate stopping at the first passing round is the bug.**

Under test now: continuing teacher DAgger with `--min-rounds 9`, then re-distilling.

### Why this matters beyond Town04

A teacher gate that stops at the first passing round selects a teacher that can drive and
says nothing about whether it can be distilled. Every student in this study is distilled
from such a teacher. Town06's teachers were selected the same way (T06-F24 showed that gate
also stops on a lucky round), so the same exposure exists there -- it simply did not bite,
because those teachers happened to run 7 and 12 rounds rather than 4.

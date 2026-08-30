# Town04 redo — findings

> ## WITHDRAWN, 2026-08-30: T04-R5 and T04-R7 rest on invalid captures.
>
> The redo's verification captures covered **160 m of the 2,861 m scored lap (5.6%)**.
>
> **Affected: T04-R5 and T04-R7 only.** T04-R6 was briefly listed here and is
> reinstated: it is closed-loop driving and reads no captures.
> `capture_offset_yaw.py --length-m` defaulted to 160 m — a calibration-probe length — and
> the captures were driven by a hand-typed command rather than a committed script, so the
> default was never passed and never noticed. The certificates below were therefore computed
> on 5.6% of the road and compared against **full-lap** driving. The agreement numbers are
> not evidence and are withdrawn.
>
> Found by the arxiv session reading the paper, not by anyone running the study. Nothing in
> the pipeline objected: the array shapes are identical, the bound computes cleanly, and the
> certificate reproduces exactly. The one loud signal — 1.8 MB captures against the published
> 1.7 GB, 81 poses against 1,600 — was visible throughout and went unexamined.
>
> **Unaffected:** T04-R1 through T04-R4, and T04-R6. Those are training, distillation and
> closed-loop driving results that never read a capture.
>
> Re-running now against full **scored-length** captures (2,861 m, not the 3,042 m route
> geometry — the last 181 m cross an ODD boundary the study excludes). Guards added so this
> class of defect fails loudly: coverage is recomputed from the pose track and checked in
> both directions, sibling certifiers must carry the same guards, a redo is compared against
> what it replaces, and the capture-vs-driven gate is a precondition of certification rather
> than a claim in the paper. See standing rules 7 and 8.

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

## T04-R4  CONFIRMED: smoothing the teacher fixes the student, at the published architecture

Continuing teacher DAgger past the gate with `--min-rounds 9` -- six more rounds, DAgger
set 12,914 -> 23,084 frames -- and re-distilling, with NOTHING else changed:

    teacher                       clear/eastbound 0.49 ft, clear/westbound 0.46 ft
    distillation target sd        0.0676 -> 0.0611   (published teacher's was 0.0510)
    clear student KD RMSE         0.0292 -> 0.0107
    clear student, closed loop    eastbound 0.92 ft PASS, westbound 0.51 ft PASS

Same architecture the published study used -- (8,16,16)/fc32, 5,152 ReLU. No widening, no
input-size change, no seed shopping. **The lever was the teacher's distillability, and the
way to get it was to keep collecting after the teacher already met budget.**

This closes T04-R3's hypothesis with the experiment it named. The chain is:

    teacher gate stops at the first passing round
      -> fewer DAgger rounds
      -> the target function the student must fit is less smooth (higher target sd)
      -> a fixed-capacity student cannot fit it
      -> the student departs in the sharpest curve while the teacher drives it at 0.48 ft

### Both arms now meet the criterion

    S_clear_84x28_v2       clear                          0.92 / 0.51 ft
    S_mixed_84x28_w3_v2    clear, fog, night, low sun     8/8, worst 1.91 ft
                                                          budget 2.19 ft

### The recommendation this makes concrete

T06-F24 recommended the teacher gate require a RATE rather than one conjunctive round, and
left it as a protocol matter. This adds a second, independent reason to change it, and a
different one: even a teacher whose competence is genuine and repeatable can be a poor
distillation target, and the gate cannot see that because it only ever asks whether the
teacher drives.

A minimum-rounds floor is the cheap fix and the flag already exists. `--min-rounds` is not
used by either study's driver, and its own help text describes exactly the failure it
prevents: "the DAgger set is an input to distillation, not just a means of fixing the
teacher."

## T04-R5  RESULT: the redo reproduces the published agreement, 6/6 — REDONE on full laps

> **The original T04-R5 was computed on 160 m of the 2,861 m scored lap and is withdrawn.**
> Redone 2026-08-30 on full scored-length captures (1,421-1,429 poses per direction,
> 2,862 m of a 2,861 m scored route), preceded by the capture gate the paper states as a
> precondition and which had never been run: worst mean |capture − driven| **0.0065**
> against the 0.05 threshold. The corrected result is below and the headline is unchanged.
>
> ### The short capture DID flip a verdict, and the agreement number could not see it
>
> This is the part worth keeping. On the 160 m captures, `eastbound / S_clear / shadows`
> came out **CERTIFIED [-0.55, +0.01]**. On the full lap it is **FALSIFIED [-0.76, +1.53]**
> — a wrong verdict, not merely an unsupported one: the 160 m window sat on clean road and
> missed the region where shadows drive that student out of bounds. Eastbound / S_clear /
> night was likewise understated, [-3.13, +0.45] against [-4.32, +0.93] on the full lap.
>
> **And 6/6 was reported both times.** A condition-level cell is CERTIFIED only if BOTH
> directions certify, and westbound/S_clear/shadows already falsified, so the aggregation
> absorbed the flipped direction. The agreement statistic is therefore **insensitive to a
> single-direction verdict flip** — it was 6/6 with a wrong verdict inside it. That the
> number reproduces is not evidence the captures were sound; it is evidence this statistic
> cannot detect this class of error. Any paper reporting it should say so.
>
> Direction-level verdicts are the honest granularity for detecting capture defects, and
> the certificate records them (`results/town04_v2/calibration/sustained_bound.json`).

Certificate on the policy checkpoints, ledger 12 runs per cell, both under the corrected
harness.

    cond      student   driving                  certificate    agreement
    clear     S_clear   PASS  0/12 [ 0, 24]%     vacuous        --
    fog       S_clear   PASS  0/12 [ 0, 24]%     CERTIFIED      AGREE
    night     S_clear   FAIL 12/12 [76,100]%     FALSIFIED      AGREE
    low sun   S_clear   FAIL 12/12 [76,100]%     FALSIFIED      AGREE
    clear     S_mixed   PASS  0/12 [ 0, 24]%     vacuous        --
    fog       S_mixed   PASS  0/12 [ 0, 24]%     CERTIFIED      AGREE
    night     S_mixed   PASS  0/12 [ 0, 24]%     CERTIFIED      AGREE
    low sun   S_mixed   PASS  0/12 [ 0, 24]%     CERTIFIED      AGREE

                                        agreement on scored cells: 6/6

The published study reports 12/12 over twelve direction-level cells; this is 6/6 over six
condition-level cells, the same outcome at the granularity the redo scored. **The
published discovery-test result survives the corrected harness**, with the clear-only
student failing night and low sun and the mixed student holding all four conditions.

### Two bugs found on the way, both of which produced plausible wrong answers

**1. The certifier carried its own copy of the student registry.**
`certify_sustained_bound.py` defined `STUDENTS` with the PUBLISHED checkpoint names rather
than reading `config.STUDENTS`, so under `TOWN04_REDO` it certified the published students
while the ledger drove the redo's. What exposed it: re-running after an unrelated fix
produced BYTE-IDENTICAL bounds across all twelve cells, which cannot happen when the
checkpoint changes -- the two mixed checkpoints differ by up to 0.17 in weights and 0.0044
in output. A registry that exists in config must be read from config.

**2. Neither the certifier nor the ledger called `config.final_student`.**
Town04's procedure includes student DAgger, so the checkpoint that IS the student is the
newest DAgger round; both scripts used the distilled intermediate. They therefore agreed
with each other while neither described the policy. This is precisely what
`final_student`'s docstring warns about -- "the gate, the certifier and the ledger would
each have used a model nobody intended to ship" -- and it happened because the function
existed and was never called from either place.

**Before both fixes the comparison read 5/6 with one CERTIFIED cell failing 10/12** -- an
apparently unsound certificate, which is the most alarming result this study could
produce. It was an artefact of comparing one study's certificate against another study's
driving, on a model neither of them shipped. Recorded because the failure mode is the
important part: every intermediate number was well-formed, plausible, and wrong.

### Status

Town04 redo complete. Both arms competent, certificate and ledger on the policy
checkpoints, 6/6 agreement, all under the harness whose two defects T06-F22 measured.

## T04-R6  Town04's interior: fog is clean, low sun is not, and it supports T06-F38

> **Briefly mis-withdrawn on 2026-08-30 and reinstated the same day.** A blanket
> withdrawal swept this finding in with the capture defect. It reads no captures: every
> number here is a full closed-loop lap (1,694-1,698 steps, loop closure) with the
> rendered signature measured from the drive's own frames. Nothing here touches an
> `.npz` or a certificate. Withdrawing a sound result costs as much credibility as
> keeping an unsound one.

Exploratory, one run per direction. Town06's headline finding -- a policy passing both
endpoints of a disturbance axis and failing between them -- tested on Town04.

**Fog: no interior failure.** Endpoints 0 and 70 both drove 0/12, and the interior is
clean too:

    density 17.5   eastbound 1.00 ft   westbound 1.04 ft
    density 35     eastbound 1.40 ft   westbound 2.00 ft
    density 52.5   eastbound 1.57 ft   westbound 1.96 ft

So Town06's fog interior failure (11/11 at density 35) does NOT reproduce on Town04. The
finding is real on Town06 and is not a universal property of the method or of fog.

**Low sun: it fails below the tested condition.**

    sun 90 (clear)    0/12 PASS (ledger)
    sun 15 (preset)   0/12 PASS (ledger)      frame mean ~0.19
    sun 10            PASS  1.45 / 0.81 ft    frame mean 0.1537
    sun  5            FAIL  westbound 3.76 ft frame mean 0.1123
    sun  2            FAIL  westbound 18.52 ft frame mean 0.0341

### The cross-map number worth keeping

    Town06   trained at low sun 5 deg  (mean 0.1155)   passes 3 deg, fails 2 deg
    Town04   trained at low sun 15 deg (mean ~0.19)    passes 10 deg, fails 5 deg

**Town04's mixed student fails at 5 degrees, frame mean 0.1123 -- essentially the
brightness Town06's mixed student was TRAINED at (0.1155).** Each policy holds down to
roughly its darkest trained condition and departs below it, and "low sun" denotes a
different physical angle on each map because the terrain shadows the road differently
(T06-F20). The angle is map-specific; the brightness is what the policy sees.

That is direct support for T06-F38's hypothesis -- that the dusk failure band tracks the
distance to the nearest TRAINED illumination rather than being a property of dusk -- from
a second map, and it was recorded there as untested. It is now supported by two maps and
still not proven, because neither test held the training set fixed while moving the
trained illumination; that is the experiment that would settle it.

### Consequence for the story

The interior result is **not** a general claim about this method. On Town06 it holds on the
fog axis; on Town04 it does not. What holds on BOTH maps is the low-sun result: a policy
tested at its declared low-sun condition passes, and fails at a lower sun the test never
sampled. That is the claim to make, and it is the one the AEB study found independently.

## T04-R7  ~~The night axis IS faithful~~ WITHDRAWN (interpolation-fidelity captures,
81 poses over 160 m; the fidelity measurement validates the disturbance family itself)

The night chord was left unmeasured deliberately: its endpoints carry different declared
exposures (daylight shutter 800, night 200), so a pixel chord between them interpolates an
exposure change as well as a lighting change, and there is no single exposure at which to
render an intermediate. Rendering the whole sweep at night's exposure is exactly what
invalidated T06-F33.

It became necessary when an audit showed a **CERTIFIED verdict resting on it**:
`S_mixed/night` certifies in both directions on Town04, and an optimistic family is a
soundness risk for CERTIFIED verdicts specifically -- it produces missed alarms, not false
ones. Same argument that motivated measuring the low-sun axis in T06-F37.

Method: each intermediate is rendered at the exposure the study would DECLARE for its
angle -- daylight above the horizon, night below it, since `headlights_on()` switches at 0
-- which is the physically sensible path a vehicle takes through this family.

    S_mixed (S_mixed_84x28_w3_v2_dagger_r00)   s=1 bias +0.00081 = +0.07x tol
      sun    exposure     s*     pixel err   steer err   x tol
       45     shadows   0.096      0.02282    +0.00025   +0.02
       20     shadows   0.249      0.07187    -0.00130   -0.11
        5     shadows   0.545      0.12346    -0.00223   -0.19
      -10       night   1.000      0.00034    -0.00000   -0.00

    S_clear (S_clear_84x28_v2)                 s=1 bias -0.03125 = -2.60x tol
       45 +0.18x   20 +0.39x    5 +0.64x    -10 -0.01x

**Every interior steering error for the mixed student is at most 0.19x tolerance.** The
chord is behaviourally faithful along the path a vehicle would actually take, and the
CERTIFIED night cells do not rest on a pixel construct. The clear-only student's errors are
larger (up to 0.64x) but its night cells are FALSIFIED, so nothing rests on them.

Two details worth keeping:

* **Pixel error is large where steering error is not.** At sun 5 the chord sits 0.123 away
  from the render in pixel space -- an order of magnitude worse than the fog axis -- while
  the mixed student's steering error stays under 0.2x tolerance. Image fidelity is not the
  property that matters, which is the same lesson that disqualified the analytic
  Koschmieder model despite its road-ROI R^2 of 0.848.
* **Below the horizon the family is degenerate.** Sun -10 projects to s* = 1.000 with a
  pixel error of 0.00034 -- it IS the night endpoint. That matches the Town06 measurement
  where -1 through -40 degrees rendered identically to four decimals, and it means the
  night family's whole interior lies between 0 and 90 degrees.

### Fidelity is now measured on every axis that carries a CERTIFIED verdict

    fog        T06-F34   faithful for the clear student; OPTIMISTIC for the mixed student
                         at low density (render drives the policy ~18x harder than chord)
    low sun    T06-F37   faithful; interior steering error at most 0.17x tolerance
    night      T04-R7    faithful for the mixed student, at most 0.19x tolerance

The fog result remains the exception, and it is the one where an interior failure was
actually found. That is consistent rather than coincidental: a chord that understates the
real disturbance is a chord whose interior the closed loop can still fail in.

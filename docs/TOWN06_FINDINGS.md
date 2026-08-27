# Town06 deployment test — findings log

Written as the work happened. Measurements, not conclusions, except where labelled.

## T06-F1  The route is valid; the students are not

The pure-pursuit oracle drives all six sections at max|CTE| 0.001–0.066 m against a
0.668 m budget, 0.0 % over. Both teachers pass: clear 6/6 sections, mixed 24/24
section-conditions (round 13). The distilled students do not, and every plausible cause
below has been measured rather than assumed.

## T06-F2  More student-DAgger is not the fix  (REFUTED)

Ten-plus rounds each. The clear student reached 5/6–6/6 and the mixed 4/6–5/6, then
both oscillated without trend. Repeats the error F7 (`5be6862`) made on Town04, which
M3 (`4b2ad73`) corrected.

## T06-F3  The verdict itself was noise  (METHOD ERROR, FIXED)

The SAME checkpoint `S_clear_t06_84x28_dagger_r08` scored 5/6, then 6/6, then 5/6 on
three consecutive gate runs, worst |CTE| 1.71–2.92 ft against a 2.19 ft budget. The
gate was driving each section ONCE, violating standing rule 3. Now 3 reps, every rep
must hold. A student sitting on the budget cannot be told from an unlucky one.

## T06-F4  Label imbalance is real; balancing makes it worse  (REFUTED)

    fraction of route needing |steer| <= 0.01
      Town04 eastbound  60.4 %     Town06 overall  83.8 %
      Town04 westbound  56.0 %     Town06 s02     100.0 %
                                   Town06 s03     100.0 %  (std 0.0000)

Town04 curves continuously; Town06 has ~1250 m of 3874 m whose correct steering is
identically zero. But `distill.py --balance` (straight-frame downsampling, which
`train.py` has always had for teachers and `distill.py` never had) took the clear
student from 5–6/6 down to **0–2/6**, worst |CTE| 23.08 ft. On a route that genuinely
IS 84 % straight, downsampling straight frames trains for a distribution the policy
will not meet. Flag retained, off.

## T06-F5  No route overrun  (REFUTED)

Warmup travels 101 m along the route. Warmup plus the scored drive uses 591 m of s05's
792 m stored route, so pure pursuit never wraps at the seam. (An earlier 404.7 m figure
was a misread straight-line measurement.)

## T06-F6  The Town04 crop transfers  (REFUTED)

Semantic segmentation, road rows in frame:

    Town04 eastbound  231–479   91.2 % occupancy in the student's [240:450] crop
    Town06 s00        242–479   87.5 %
    Town06 s01        242–479   90.1 %

`ROAD_ROI_ROWS`, measured on Town04, is fine on Town06.

## T06-F7  Distillation fidelity is not the discriminator  (REFUTED, and the useful one)

Same diagnostic on both maps, teacher vs student on identical frames:

    Town04 published clear pair (WORKS)     bias -0.00159   RMS 0.0582 = 4.84x tolerance
    Town06 clear pair          (MARGINAL)   bias -0.00049   RMS 0.0309 = 2.57x tolerance

The Town06 student tracks its teacher BETTER -- half the RMS error, a third of the bias
-- and drives worse. A student can be a poor copy and still drive; these are good copies
that do not.

## T06-F8  Working hypothesis: the straight sections are the substrate problem

What is left after F2 and F4–F7 is the route's closed-loop character, not the model.
On a continuously curving road a steering error meets constant corrective signal; on a
dead-straight one it integrates unopposed. Measured on s03 (steering demand 0.0000):

    student  CTE -0.18 -> -1.24 -> -8.59, sign never changing, departs at step 47
    teacher  CTE -0.01 -> +0.05 -> -0.21, oscillating about zero

This is the paper's own thesis appearing in a new setting: a small persistent bias walks
the vehicle out of its lane while a large oscillating one integrates to nothing.

The awkwardness worth stating: s02 and s03 are simultaneously the MOST diagnostic
sections -- they expose bias mercilessly -- and the ones defeating the students.
Dropping them would remove the most discriminating road, and PROTOCOL section 6 forbids
re-selecting a route on policy behaviour in any case.

## T06-F9  The route is NOT a fair analogue: my selection dropped the curvature match

Longest unbroken dead-straight run (|kappa| < 1e-5):

    Town04 eastbound   258 m        Town06 s03   620 m   (of a 622 m section)
    Town04 westbound   200 m        Town06 s01   558 m
                                    Town06 s02   404 m
                                    Town06 s04   264 m
                                    Town06 s05   232 m
                                    Town06 s00   166 m

Town04 is continuously curving: nothing in it exceeds 258 m without curvature to
correct against. FOUR of the six Town06 sections contain straights longer than
anything in the reference study, and s03 is a single 620 m straight line.

This is a selection error of mine, not a property of Town06. The FIRST route criterion
did match Town04's curvature distribution. When selection was rewritten around "longest
clean run" after the lane-marking discovery (T06-F6's sibling), the curvature match was
dropped entirely -- optimised for clean road, stopped checking it was Town04-LIKE road.

So the students have been failing on a substrate with 2-3x longer unbroken straights
than the reference ever contained, which is precisely the geometry in which a small
steering bias integrates unopposed (T06-F8). The plateau in T06-F2 and the
capacity/balance/crop/fidelity refutations in F4-F7 were all measured against a route
that was never the right comparison.

## T06-F10  Town04 students do not transfer to Town06  (EXPECTED, no information)

`S_clear_84x28`, which drives Town04 at 0/10 failures, departs every Town06 section
within 19-25 steps at 22-53 ft. This is visual non-transfer across maps, already known
to the lab, and it separates nothing. Recorded so the CARLA time is not spent again.

## T06-F11  Horizontal resolution is the lever on straights, and F11's rejection used the wrong aspect ratio

Width x input-resolution sweep, distilled from the same clear teacher, scored CLOSED
LOOP over all six sections (single run each; a repeated-drive confirmation follows).

    config       ReLU   px per 0.668 m   held   worst_ft   s01/558m   s03/620m
    84x28  w1   5,152        1.79        1/6      16.71      16.71       5.84
    84x28  w2  10,304        1.79        2/6      18.65       7.89       3.19
    168x28 w1  10,704        3.57        2/6      22.60      22.60       1.76
    84x28  w3  15,456        1.79        4/6      11.05      11.05       2.61
    224x28 w1  14,400        4.76        5/6      12.24      12.24       1.59
    112x38 w2  21,504        2.38        4/6      12.97      12.97       2.69
    168x28 w2  21,408        3.57        6/6       0.97       0.75       0.97

CONFIRMED OVER REPETITIONS. Re-driven 3x per section; a section counts as held only if
it holds on EVERY rep (worst |CTE| ft over reps, budget 2.19 ft):

    config       ReLU  held   s03/620m   s01/558m   s02/404m   s04/264m  s05/232m  s00/166m
    168x28 w2  21,408  6/6    1.45(3/3)  1.62(3/3)  0.58(3/3)  0.40(3/3) 0.30(3/3) 0.55(3/3)
    224x28 w1  14,400  5/6    0.87(3/3) 12.32(0/3)  0.83(3/3)  0.83(3/3) 0.54(3/3) 0.83(3/3)
    84x28  w3  15,456  3/6    3.32(0/3) 11.25(0/3)  4.30(2/3)  0.34(3/3) 0.36(3/3) 0.95(3/3)
    112x38 w2  21,504  3/6    4.17(0/3) 12.57(2/3) 11.73(0/3)  0.46(3/3) 0.47(3/3) 0.91(3/3)

Repetition sharpens both conclusions. 112x38 w2 falls to 3/6 with three sections failing
EVERY rep. And s01 is the discriminator: resolution alone (224x28 w1) nails s03 at
0.87 ft yet fails s01 on 0 of 3 reps, width alone fails both, and only the combination
holds everything. In the single-run data s01 looked like noise; it is not.

THE CONTROLLED COMPARISON. 112x38 w2 and 168x28 w2 cost the SAME -- 21,504 against
21,408 ReLU -- and differ only in how the pixels are spent. Splitting the budget across
both axes holds 4/6 at 12.97 ft; spending it all horizontally holds 6/6 at 0.97 ft,
inside the 2.19 ft budget with 2.3x margin, and with NO student-DAgger at all. That is
the same condition in which Town04's students passed at round 0 (0.53-1.61 ft).

WHY. The control error is LATERAL, so it is horizontal resolution that carries it.
Vertical resolution buys nothing for lane-keeping and F11 (4badcfa) spent half its
budget there, which is why "resolution loses on both axes" was the honest reading of
what it measured. Widening ONE axis also costs ReLU linearly rather than k^2.

NEITHER LEVER ALONE SUFFICES. At 84 px, tripling width takes s03 only from 5.84 to
2.61 and still misses budget. At w1, doubling resolution fixes s03 (1.76) but leaves
s01 at 22.60. Only the combination holds both. s01 was not a counterexample to the
mechanism -- it needed both.

This does not overturn F11 on Town04, whose longest straight is 258 m and where the
sub-pixel regime is never entered. It says the conclusion is route-dependent and the
aspect ratio was the confound.

## T06-F12  The verifier is tractable at 21,408 ReLU, and CARLA must be down to run it

Cost probe on synthetic input (no capture, no disturbance, so nothing leaks into the
blind protocol). Bounds are finite at every size; the question was only cost.

    config       ReLU     s/pose (CPU)   finite
    84x28  w1   5,152        0.72         yes
    84x28  w3  15,456        1.25         yes
    168x28 w2  21,408        2.55         yes

Cost grows about linearly in ReLU count, not explosively, so 21,408 needs no relief.

Two operational facts came out of it, both of which would have cost a night:

1. **CARLA must be stopped before certifying.** It holds ~10.25 GiB of the 12 GiB card
   after a long run (the documented leak). alpha-CROWN then OOMs outright on a batched
   graph and, unbatched, runs launch-bound at 1.43 s/pose on GPU against 2.55 on CPU --
   a 12 GiB GPU buying 1.8x. Certification needs no simulator, so the simulator goes
   down first. At 9,600 poses (6 sections x 200 x 4 conditions x 2 students) that is
   the difference between hours and a long night.

   MEASURED AGAIN, the hard way: with CARLA resident at 10.65 GiB, distilling the w3
   mixed student died with `torch.AcceleratorError: CUDA error: out of memory` at
   `StudentNet(...).to(device)` -- allocating a 62k-parameter model, with ~30 MiB free.
   So this is not only a certification concern; ANY GPU stage that shares the machine
   with a long-lived CARLA is exposed, and the simulator does not have to be in use to
   break it. Stopping CARLA took the card from 11,247 MiB to 517 MiB and the same
   command then ran.

   Partly self-healing already: dagger_student.py re-distils once per round, and if that
   OOMs it exits nonzero, which makes student_dagger_until_competent.sh restart CARLA
   before the next attempt. That costs one attempt rather than the run.

2. **The 16 sub-intervals can be batched, and the reformulation is exact.** Because
   `half = 0.5*(b-a) = 1/32` for every sub-interval, W is IDENTICAL across all 16 and
   only the bias moves. The whole split is therefore a box on the parameter itself:

       frozen loop:  W_j = half*(x1-x0), b_j = x0 + mid_j*(x1-x0), s in [-1,1]
       equivalent:   W   = (x1-x0),      b   = x0,                 t in [a_j,b_j]

   Both give x = x0 + t*(x1-x0) with t confined to the same sub-interval, so this
   changes the parameterisation of the box and not the box, nsplit, or stride.
   Verified numerically: max per-sub-interval difference 2.2e-08, which is float32
   epsilon. NOT adopted -- on CPU it is 0.7x, i.e. slower, since CPU is compute-bound
   rather than launch-bound, and the GPU comparison could not be run with CARLA
   resident. Recorded because the equivalence is proven and the option is now cheap to
   take if certification time ever becomes the constraint.

## T06-F13  Student DAgger is not harmful; the MIXED student lacks capacity for four conditions

Student DAgger took the mixed student from clear 6/6 to clear 4/6, and the first reading
of that was "DAgger is destroying the student". That reading was wrong, and the control
that refutes it was already in hand.

Mixed student (168x28 w2, 21,408 ReLU), CLEAR weather only, by round. Its DAgger spans
four weathers:

    round        held   s01/558m   s03/620m
    0 (base)     6/6      1.11       0.93
    1            5/6      1.02       3.09
    2            4/6      5.01      11.38
    3            4/6     23.00      23.04
    4            4/6     11.10       1.16

Clear student (168x28 w2, same 21,408 ReLU), CLEAR weather. Its DAgger is clear-only:

    round 0 (base)  4/6, worst 4.36     round 2  5/6, worst 11.00 (s00)
    round 1         6/6, worst 1.72     round 3  6/6, worst 1.97   PASSED

Same mechanism, same architecture, same code path, opposite outcome. What differs is
the weather span of the aggregated data, so the cause is not DAgger.

RULED OUT, in order, before this was written (standing rule 2):

- *Section-skewed collection.* Frame counts per section are flat across rounds and
  proportional to section length (s00 1,996 : s05 1,096 against 894 m : 490 m). The
  failing sections are not over-collected, so there is no departure feedback loop.
- *Preprocessing mismatch.* dagger_student.py and evaluate.py both call
  `student_preprocess(bgr, model.in_w, model.in_h)`. Same function, same crop.
- *Resolution mismatch.* --w 168 --h 28 is threaded from the registry into every driver.
- *Wrong checkpoint evaluated.* `final_student` returns the highest round index; the
  round checkpoints it selected were the ones the log names.
- *Disagreeing evaluations.* DAgger's own round-0 clear numbers (6/6, worst 0.93 ft)
  match the competence gate's independent run (6/6, worst 1.18 ft). They agree.

WHAT IT ACTUALLY IS. The base distillation set is TEACHER-visited states, which sit near
lane centre. Student DAgger adds STUDENT-visited states, which include departures, and
for the mixed student three quarters of those are fog, night or shadows. At w2 the
network cannot absorb off-nominal states across four conditions and keep the
straight-line cue, and the straight-line cue is what goes first -- s01 and s03, the two
longest straights, exactly the capability T06-F11 bought with horizontal resolution and
exactly the one that rests on a sub-pixel signal.

So Town04's finding and F11 are BOTH true, and they are about different things:

    horizontal resolution -> straights   (the lateral cue is sub-pixel)
    width                 -> conditions  (capacity to carry four of them)

Town04 needed its mixed student at 3x the clear student's width and reached that
conclusion through night failures; the same constraint arrives here through clear-weather
straights after DAgger.

**CORRECTED BY T06-F14. Do not act on this finding.** Its diagnosis rested on
single-pass drives, and repetitions reversed both halves. Mixed at w3 holds 4/6 against
w2's 6/6, so the widening was wrong. And the clear student's DAgger, which this finding
cites as the control PROVING the cause is weather dilution, does not actually improve it
on 3 reps -- so the control does not hold and the weather-dilution explanation with it.
What survives is the ruled-out list above, which is still correct.

This is a clear-weather competence decision. Clear is the s=0 anchor of the disturbance
family, not one of the disturbance conditions, so it does not weaken the blind protocol
(PROTOCOL R3). Student capacity is a property of the model under test rather than of the
criterion, so widening is declared, not amended.

## T06-F14  Student DAgger is harmful at 168x28, w2 beats w3, and the clear student is seed-marginal

Six checkpoints, one CARLA session, three repetitions each, clear weather. A section
counts as held only if it holds on EVERY rep (standing rule 3). Budget 2.19 ft.

    candidate               ReLU   held    s03/620m   s01/558m   s02/404m   s00/166m
    clear w2 base         21,408   4/6     2.23(2/3)  0.87(3/3)  0.80(3/3)  3.45(1/3)
    clear w2 +DAgger      21,408   4/6     1.66(3/3)  1.27(3/3)  4.38(1/3) 11.97(0/3)
    mixed w2 base         21,408   6/6     1.11(3/3)  0.83(3/3)  0.73(3/3)  0.46(3/3)
    mixed w2 +DAgger      21,408   3/6    17.27(2/3) 11.37(0/3)  0.91(3/3)  1.06(3/3)
    mixed w3 base         32,112   4/6     1.26(3/3)  5.44(0/3)  0.85(3/3)  0.34(3/3)
    clear w2 (sweep seed) 21,408   6/6     1.42(3/3)  1.29(3/3)  0.59(3/3)  0.72(3/3)

THREE RESULTS, two of which overturn a decision taken earlier the same night.

1. **Student DAgger is harmful here.** Both paired comparisons hold architecture fixed
   and vary only the procedure: mixed goes 6/6 -> 3/6, and clear stays 4/6 while its
   worst section goes 1/3 at 3.45 ft to 0/3 at 11.97 ft. There is no comparison in which
   DAgger helps.

   This INVERTS the Town04 procedure, where student DAgger was essential, and the reason
   is visible in the numbers rather than mysterious. At 84x28 the distilled student held
   1 of 6 sections at 16.50 ft: DAgger was rescuing an incompetent policy, and almost
   anything helps from there. At 168x28 distillation alone already produces a competent
   one, and DAgger's contribution -- student-visited off-nominal states, labelled by the
   teacher -- then buys nothing and costs the marginal capability, which T06-F11 showed
   is the sub-pixel straight-line cue.

2. **w3 is worse than w2 for the mixed student**, 4/6 against 6/6, with 50% more ReLU.
   The T06-F13 widening was decided on single-pass drives and is withdrawn. Cheaper AND
   better, so nothing is being traded away.

3. **Two clear students, identical architecture, identical data, identical 120 epochs,
   differ 4/6 from 6/6 on distillation seed alone** (KD RMSE 0.0553 against 0.0489). The
   clear student sits close enough to the boundary that initialisation decides it.

WHY THE CLEAR STUDENT AND NOT THE MIXED ONE. Clear trains on 21,923 frames (8,652 base
plus 13,271 teacher-DAgger); mixed trains on 143,425 (25,956 plus 117,469). The gap is
mostly teacher DAgger: the clear teacher passed at round 5 and the mixed teacher took 12,
so the mixed student inherited far more data. More teacher DAgger rounds cannot close it
-- dagger.py breaks as soon as the teacher passes, and the clear teacher already does.

ACTION: both students at 168x28 w2, 21,408 ReLU, distilled only, NO student DAgger. The
mixed student is done and holds 6/6. For the clear student, collect more clear laps and
re-distil, which attacks the variance at its source.

NOT DONE, deliberately: shipping `sweep_168x28_w2` because it passes. It differs from
the pipeline's clear student only by seed. Choosing the seed that clears a gate turns a
precondition into a selection step, and the gate's whole purpose is to be a precondition
the model meets rather than one the model is picked to satisfy. It is in the table for
the variance record, not as a candidate.

## T06-F15  collect_data.py silently corrupted a dataset re-collected for the same weather

Found before it was run, not after. Frames are written to
`{weather}_{direction}_lap{NN}/frames/{step:05d}.png` and the lap loop was
`range(args.laps)`, always starting at 0, while the manifest APPENDS. A second collection
for a weather already on disk therefore rewrote lap00.. with new images while the old
manifest rows kept pointing at those same paths: old labels, new pixels, no error
anywhere.

The append behaviour is documented and correct across WEATHERS, which get distinct
directory names. It was never safe across repeated runs of the same weather, and growing
a dataset is exactly when that happens. Lap indices now continue past whatever is on
disk (`clear: 4 lap(s) already on disk, collecting lap04..lap19`).

## T06-F16  DEPLOYMENT TEST RESULT: the certificate agreed with driving on 5 of 6 cells

The certificate was computed blind and committed at e0a461f BEFORE any scored drive.
check_order_town06.py verifies that ordering independently of the script that ran it.
245 poses per cell, stride 8, 16-way BaB, both students 168x28 w2 at 21,408 ReLU.

    condition  student       driving              certificate      agree
    ------------------------------------------------------------------------
    clear      S_clear_t06   PASS  0/12 [ 0, 24]%  CERTIFIED        vacuous
    clear      S_mixed_t06   PASS  0/12 [ 0, 24]%  CERTIFIED        vacuous
    fog        S_clear_t06   FAIL 12/12 [76,100]%  NOT_CERTIFIED    yes
    fog        S_mixed_t06   PASS  3/12 [ 9, 53]%  NOT_CERTIFIED    NO
    night      S_clear_t06   FAIL 12/12 [76,100]%  NOT_CERTIFIED    yes
    night      S_mixed_t06   FAIL  9/12 [47, 91]%  NOT_CERTIFIED    yes
    low sun    S_clear_t06   FAIL 12/12 [76,100]%  NOT_CERTIFIED    yes
    low sun    S_mixed_t06   PASS  0/12 [ 0, 24]%  CERTIFIED        yes

    agreement on scored cells: 5/6 (clear excluded, vacuous by construction)

The single disagreement, mixed/fog, is in the CONSERVATIVE direction: the certificate
declined to certify a cell that then drove clean. That is the direction a sound bound is
allowed to be wrong in, and it was flagged before the drives as the near-miss -- its
bound was [-0.62, +1.67] x tolerance, failing on one side only. An unsound bound would
have certified a cell that then failed, and none did.

This is the deployment test, not the discovery test: new map, new teachers, new students,
criterion frozen by PROTOCOL section 3 and unchanged from the published Town04 study.

## T06-F17  EXPLORE PHASE 2: night is a CONTRAST problem, and the width sweep is confounded by under-training

Under PROTOCOL amendment A-1 (R1 suspended). None of this is a blind prediction.

**The teacher is not the problem.** teacher_mixed_t06_dagger_r12 passes all 24 teacher-gate
cells -- four conditions x six sections. The entire gap is distillation.

**Where the student diverges, split by condition** (no CARLA; teacher outputs are cached
so only the student runs):

    condition   KD RMSE   x tolerance   teacher |steer|   student |steer|
    clear        0.0116      0.97           0.0207            0.0197
    shadows      0.0203      1.69           0.0236            0.0223
    fog          0.0227      1.89           0.0267            0.0242
    night        0.0344      2.86           0.0525            0.0483

Night error is nearly 3x the whole steering tolerance, and the teacher steers 2.5x harder
there -- a larger-magnitude function to imitate. The student under-predicts that
magnitude, i.e. it UNDER-STEERS exactly where the teacher works hardest. The pooled KD
RMSE of 0.0370 hid all of it.

**Not a sampling problem.** The training set is clear 25.3%, fog 25.3%, shadows 25.3%,
night 24.1%.

**Not a brightness problem, which kills the obvious fix.** Image statistics over the
training set:

    condition   mean     sigma    p01     p99     frac < 0.05
    clear       0.3039   0.0636   0.0471  0.4118     1.0%
    fog         0.2803   0.0601   0.1804  0.4549     0.0%
    night       0.2002   0.1380   0.0000  0.5176    13.8%
    shadows     0.1842   0.0559   0.0157  0.3333     2.8%

SHADOWS IS DARKER THAN NIGHT and drives 1/12 against night's 8/12. So a mean-subtraction
front end -- which is linear, exactly verifiable, and adds no ReLUs -- would have bought
nothing, and this table refuted it before it cost any CARLA time. What separates night is
CONTRAST: sigma more than double every other condition, 13.8% of pixels crushed near
black, and the highest p99. It is high-dynamic-range, not dim.

**Camera exposure is NOT implicated.** The night exposure is a declared function of
condition, set deliberately (config.py, 2026-08-11), and the measured 13.8% clipping
matches its recorded ~12% expectation for the genuinely unlit far field beyond the
headlight throw. Not touched.

**The failure mode is lane drift, not departure.** Every night run has departed=False
while exceeding budget by 21-35 ft. On a 4-5 lane highway the student wanders across
lanes and stays on the road. It also fails 5 of 6 sections, with no relation to straight
length -- unlike the clear-weather s03 failure of F11.

### The width sweep, and why it settles less than it appears to

    config    ReLU   KD RMSE   clear    fog    night  shadows   total
    w2      21,408    0.0370   0/12    5/12    8/12    1/12     14/48
    w3      32,112    0.0387   2/12    4/12    5/12    4/12     15/48
    w4      42,816    0.0405   6/12   11/12    8/12    8/12     33/48

Read carelessly this says "capacity is harmful". It does not. KD RMSE rises MONOTONICALLY
with capacity under a fixed recipe of 120 epochs at lr 1e-3, and driving failures track
it exactly. A larger network can always represent what a smaller one represents, so a
worse fit to the TRAINING objective is under-training, not a capacity limit. The recipe
was tuned for w2.

So capacity has not actually been tested. The clean experiment is to re-distil w3 on a
longer schedule and check whether its KD RMSE falls below w2's 0.0370; only then is
driving it informative. Recorded because the earlier w3 withdrawal (T06-F14) rested on
the same untested assumption, and repeating it would be the same error twice.

One useful by-product: within this sweep KD RMSE ORDERS the driving results correctly
(0.0370 -> 14, 0.0387 -> 15, 0.0405 -> 33), so it is a legitimate cheap screen HERE. That
does not overturn F7, which was about width at fixed resolution and fixed fit quality.

### Under test now: does night need VERTICAL resolution?

student_preprocess crops 210 rows x 640 columns into 28 x 168 -- vertical downsampled
7.5x against horizontal's 3.8x, twice as hard. The teacher, which passes night 6/6 through
the identical camera, keeps 66 rows to the student's 28. Night's usable signal is the
headlight-lit near field, a horizontal BAND low in the crop, which is what aggressive
vertical downsampling destroys. That is the opposite of clear weather, where F11 found
horizontal resolution was the lever because the error is lateral and sub-pixel.

If clear wants width and night wants height, then ANY architecture chosen on the
clear-weather competence gate is wrong for night by construction -- and that gate is
exactly how this student was sized.

Cost-matched, mirroring the design that settled F11:

    168x28 w2 = 21,408 ReLU (budget on WIDTH)
    168x56 w1 = 25,472 ReLU (budget on HEIGHT)

Both are small enough to train properly under the current recipe, so this pair is free of
the confound above. The larger vertical configs are not, and must be read with it in mind.

## Open
 dispositions -- three cells contradict the pre-registration

Standing rule 2: each is a BUG until a written disposition rules out the candidate
causes. None of these is a finding yet, and none should be written up as one.

**D-T06-1  fog/S_clear_t06 drove FAIL 12/12; expected PASS.**
The pre-registration carried Town04 disposition D-14 forward, which established that the
clear-only student is genuinely robust in fog on open road. It did not transfer. Candidate
causes not yet ruled out: Town06 fog renders differently against this geometry; the
Town06 clear student is a different model trained on different data, including the
borrowed off-nominal frames of T06-F14; D-14 may itself have been map-specific and was
carried over without re-derivation.

**D-T06-2  fog/S_mixed_t06 drove PASS but was NOT_CERTIFIED; expected CERTIFIED.**
This is the 5/6 disagreement. Candidate causes: bound looseness at 21,408 ReLU rather
than real behaviour, since it misses on one side by 1.67x; the pooled route-mean over 245
poses may be dominated by a few sections. Check the per-section bounds already recorded
in the certificate before concluding anything about the criterion.

**D-T06-3  night/S_mixed_t06 drove FAIL 9/12; expected PASS.**
The mixed student was TRAINED on night and still fails it. This is the one that matters
most, because it is a competence claim rather than a certificate claim, and the
certificate agreed with the failure. Candidate causes: the mixed student at w2 lacks the
capacity for night on this map (Town04 needed 3x the clear student's width and this one
is the SAME width as its clear counterpart -- see T06-F14, where w3 measured worse in
CLEAR weather, which is not evidence about night); the clear-weather competence gate says
nothing about night by construction; night on Town06's unlit sections may be materially
harder than Town04's lit highway.

Note for D-T06-3: the clear-weather gate passed the clear student at 2.17 ft against a
2.19 ft budget, a 1% margin on s03, while every other section sat at 15-48%. That student
is competent by the declared criterion and barely so. It is not implicated in the night
cells, but any future reading of these results should know it.

## Open


Whether more clear data makes the clear student clear the 3-rep gate reliably rather than
by seed. 16 additional clear laps are being collected, taking the base set from 8,652 to
roughly 43,000 frames. The prediction to check it against: the mixed student, on 6.5x the
data, passed its gate first try at 6/6 with every section at or under 1.11 ft.

If it does not close, the next lever is more teacher-DAgger data for clear, which needs
dagger.py to keep collecting after the teacher passes rather than breaking -- a change to
data collection, not to any criterion.

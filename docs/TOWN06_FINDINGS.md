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

## T06-F18  A bigger INPUT fixes night; and the teacher ceiling is 2/48, not 0/24

Under PROTOCOL amendment A-1 (R1 suspended). Nothing here is a blind prediction.
Every number is 12 runs per condition, 6 sections x 2 reps (standing rule 3).

    policy                        ReLU    clear   fog   night  shadows   total
    teacher_mixed_t06_dagger_r12   ---     0/12   1/12   1/12    0/12     2/48
    S_mixed 320x64 w3          172,848     0/12   4/12   1/12    0/12     5/48
      (confirmation run)                   0/12   5/12   1/12    0/12     6/48
    S_mixed 224x64 w2           79,904     2/12   1/12   6/12    6/12    15/48
    S_mixed 168x28 w3           32,112     2/12   4/12   5/12    4/12    15/48
    S_mixed 168x28 w2           21,408     0/12   5/12   8/12    1/12    14/48
    S_mixed 168x28 w2 +jitter   21,408     3/12   7/12   8/12    2/12    20/48
    S_mixed 168x28 w4           42,816     6/12  11/12   8/12    8/12    33/48

### 1. Input size is what night needed

Night goes 8/12 -> 1/12, reproduced exactly on a second independent run, and that is
teacher parity: the teacher is also 1/12 at night. Zach called this: high contrast with
headlights argues for a bigger input, vertically and horizontally. It is not capacity --
w3 and w4 at 168x28 changed nothing and w4 made everything worse.

### 2. THE TEACHER IS NOT PERFECT, and much of tonight was written as though it were

The teacher gate reported 0/24 on ONE pass per cell. Under 12 runs per condition it is
2/48, failing fog once and night once. So "the teacher passes everything, therefore the
entire gap is distillation" -- which this log asserted repeatedly, and on which the
covariate-shift hypothesis was built -- was overstated. Part of the apparent gap was the
ceiling being under-measured.

That is the FOURTH single-pass number to mislead a conclusion in this study
(competence gate, DAgger rounds, arch sweep, and now the teacher ceiling). The gate
should be re-run at repetition before any future claim rests on it.

Consequence for the deployment test: a 0/48 student is probably not reachable, because
the TEACHER is not 0/48. At 5/48 the mixed student would still likely take a FAIL verdict
on fog -- but so would its teacher.

### 3. My floor hypothesis was wrong

Three architectures landed at 14, 15, 15 and this log concluded that 14/48 was a
distillation floor, that the failure mode was covariate shift from behaviour-cloning
teacher-visited states, and that only on-policy data could break it. The next
architecture broke it to 5/48. Three points are not a floor, and the reasoning ran ahead
of the evidence.

The covariate-shift story is not disproved -- it may still explain the residual fog gap,
4-5/12 against the teacher's 1/12 -- but it was not the binding constraint.

### 4. Photometric augmentation: REFUTED

Jitter 0.3 at 168x28 w2 gave 20/48 against 14/48 without it. Worse in clear and fog, NO
change at night, the condition it was built for. It could not have worked: the jitter is
a*x+b, which models BRIGHTNESS, and night is not a brightness shift -- SHADOWS IS DARKER
(mean 0.184 vs 0.200) and drives fine. Night is high contrast, sigma 0.138 against
0.056-0.064, with 13.8% of pixels clipped to black. Linear jitter cannot reproduce
information that clipping destroyed. The --augment flag stays, off by default.

### 5. An accidental empirical instance of the vacuous certificate

448x64 w3 failed to train: val MSE flat at 4.80e-3 from epoch 1 to 20, the network
collapsed to a constant. It then failed 48/48 with max|CTE| of EXACTLY 28.16 ft in all
four conditions -- byte-identical, because the trajectory does not depend on the input.

This is the model the competence gate was written to exclude, produced by accident. It
ignores its input, so Delta_p(s) = 0 identically, so it would certify PERFECTLY under
every condition while driving off the road in all of them. The study has only ever argued
that case hypothetically. Keep the checkpoint.

### Verifiability

172,848 ReLU certifies in about 0.85 h at 3.5 GB with bound width 0.2x tolerance, against
a measured ceiling near 325k ReLU where MEMORY -- not wall clock, not bound looseness --
is the limit. 508k OOMs at 12 GB. So the working student sits comfortably inside the
envelope with room above it.

## T06-F19  HARNESS BUG: runs overshot each section's clean window. Prior numbers superseded.

Under PROTOCOL amendment A-1. Nothing here is a blind prediction.

`steps_for()` caps STEPS, computed as `length / (TARGET_SPEED * dt)`. That bounds distance
only if the vehicle holds target speed exactly. It runs slightly hot, so runs overshot,
and the excursion found in the road each section was CLIPPED TO EXCLUDE was recorded as
that section's max |CTE|.

Found by asking WHERE failures peak rather than how large they were:

    fog  s02   639 m and 634 m of a 628 m section   101-102% through
    night s03  101%,  s00 100%,  s01 99%,  s05 97% and 94%

steps_for's own docstring already names this failure mode -- "it fails there for reasons
that have nothing to do with the policy" -- and fixes it with a step cap. A step cap is
the wrong instrument for a distance bound. evaluate.py now stops at the scored end
measured ALONG THE ROUTE. Town04 is unaffected: SECTION_BASED is False, so no cap applies.

### Everything re-measured. These supersede T06-F17 and T06-F18.

12 runs per condition, 6 sections x 2 reps, all on the FIXED harness and therefore
mutually comparable. The old figures are NOT comparable and appear only to size the
correction.

    policy                    ReLU   clear   fog   night  shadows  total   (old)
    teacher_mixed_..._r12      ---    0/12   2/12   2/12    0/12    4/48    2/48
    S_mixed 320x64 w3      172,848    0/12   3/12   1/12    0/12    4/48    5-6/48
    S_mixed 168x28 w2       21,408    0/12   6/12   4/12    0/12   10/48   14/48
    S_mixed 224x64 w2       79,904    2/12   2/12   6/12    3/12   13/48   15/48

### What survives, and what does not

**Survives, at half the claimed size.** The 320x64 w3 student reaches TEACHER PARITY at
4/48, and is better than its teacher at night (1/12 against 2/12). But night improved
4/12 -> 1/12, not 8/12 -> 1/12: half of the baseline's night failures were the harness.

**Does not survive.** Three separate teacher ceilings were reported in one session --
0/24, then 2/48, then 4/48 -- each stated as settled. The real figure is 4/48, and 2/48
against 4/48 is well inside sampling noise at these counts. Any claim resting on "the
teacher is perfect" is void; it fails 4-8% of runs.

**Does not survive.** The "14/48 floor" that motivated the covariate-shift hypothesis was
10/48, partly harness artifact.

**Retracted.** From ONE s02 run going 25.00 ft -> 2.29 ft this log concluded "roughly 90%
of that failure was the harness". In aggregate fog barely moved, 5/12 -> 6/12. That was
extrapolation from n=1, the same error the log had already flagged twice that night.

**Bigger input is NOT monotone.** 224x64 w2 is WORSE than the 168x28 baseline, 13/48
against 10/48, on 4x the input pixels. So "a bigger input fixes night" is too coarse:
320x64 w3 works and 224x64 w2 does not, and those differ in BOTH input width and channel
count. That is still unresolved.

### Consequence for the study narrative

Under the ledger's cell rule -- FAIL when failures >= half the runs -- the 320x64 w3
student now PASSES all four ODD conditions, as does the teacher. That is the precondition
for the revised framing (build, test the ODD, then verify the continuum): verification
only has something non-redundant to say once closed-loop ODD testing has already passed.

NOTE FOR THAT NARRATIVE: the rule marks 3/12, a 25% failure rate, as PASS. Town04's cells
were 0/10 or 10/10, so the rule was never stressed. Here it decides an outcome. "Passes
its ODD" resting on 3/12 is within the letter of the criterion and arguably not its
spirit. Flagged for Zach rather than resolved here, because changing a scoring rule after
seeing the scores is exactly what must not happen unilaterally.

## T06-F20  Low sun is defined by its RENDERED OUTCOME, not its sun angle. Town06 moves to 5 degrees.

Under PROTOCOL amendment A-1. The condition definition is NOT in the frozen section, so
this needs no amendment; the criterion, tolerance, stride and BaB split are untouched.

Zach, watching a run, said the Town06 low-sun condition looked almost like clear with
shadows on one stretch, and remembered Town04's low sun as "night without headlights".
Both halves of that turned out to matter, and one of his other recollections was wrong,
so it was worth checking all of it against the published artifact rather than either
memory.

### What the published Town04 artifact actually does (v1.0.0)

    CONDITION_DELTAS   low sun 15 deg, night -25 deg          -- identical to Town06
    CONDITION_EXPOSURE night at 4x daylight (shutter 200/800)  -- ALREADY in Town04

So night exposure was NOT introduced for Town06. Zach believed Town04 used no exposure
modification; it did, and v1.0.0 shows it. Worth stating plainly because the rest of his
recollection was right and it would be easy to discount all of it together.

### Measured brightness, from lap captures, of the network's own input

                        Town04 (published)   Town06 at 15 deg   Town06 at 5 deg
    clear                    0.2411               0.2963              --
    fog                      0.2641               0.2551              --
    night                    0.2075               0.2058              --
    low sun                  0.1117               0.1841             0.1215
    night MINUS low sun      0.0958               0.0217             0.0843

**Night IS brighter than low sun, on both maps.** Zach remembered that correctly, and it
is the physically right ordering: night has headlights and 4x exposure, low sun has
neither.

**But at 15 degrees Town06's low sun is 65% brighter than Town04's**, and sits only 0.022
below night -- a seventh of Town04's separation. The illumination axis the study depends
on being ORDERED had effectively collapsed at one end.

**The cause is terrain, which is what Zach guessed.** Identical sun angle, identical
exposure, identical code: Town04's terrain puts the whole road in shadow at 15 degrees
and Town06's does not. The paper's own justification says so -- "we call the 15 degree
case low sun rather than shadows because the whole road is in shadow at that elevation,
not just part of it" -- and that sentence is a statement about TOWN04'S TERRAIN, not
about 15 degrees.

### Sweep, and the choice

s00, 16 poses, what the network sees:

    sun alt    mean    pose CV%   vs Town04   night - low sun
      15      0.1809     6.81      +0.0692        0.0249
      10      0.1634     5.08      +0.0517        0.0424
       6      0.1335     3.55      +0.0218        0.0723
       5      0.1194     3.29      +0.0077        0.0864
       4      0.0996     3.09      -0.0121        0.1062
       3      0.0721     3.24      -0.0396        0.1337

5 degrees, validated on all six sections: means 0.1194 to 0.1253, route mean 0.1215
against Town04's 0.1117 (within 9%), worst pose CV 3.29% against 6.81% at 15 degrees.
Town04's own low sun has CV 0.32%, so Town06 will never be as uniform -- its darkness
comes from sun angle rather than terrain occlusion -- but the gap narrows by half.

Headlights key off angle < 0, so 5 degrees stays lights-off low sun and does not drift
toward night.

### ACTION and its cost

`_LOW_SUN_DEG = {"Town06": 5.0}`, applied in CONDITION_DELTAS. **The angle is map-specific
and the CONDITION is what is held fixed.** Town04 keeps 15 degrees exactly: the constant
is shared by both maps, and changing it globally would have silently altered the published
study while every file still looked correct.

This invalidates every Town06 low-sun frame collected so far -- training data, captures
and results. Teachers and students both need rebuilding, which was already required.

## T06-F21  HANDOFF: run-to-run reproducibility is UNRESOLVED and may affect Town04

Written at the end of a session that lost a night and most of a day to infrastructure
faults. This section is the state of play, what is trusted, what is not, and what to do
next. Read it before running anything.

### The open question, and why it matters beyond Town06

Zach asked the right question: if CARLA is deterministic in synchronous mode -- and this
study pins the timestep, substepping, spawn, weather and camera exposure -- how can a
competence gate report "held 2/3"? A deterministic process cannot produce that.

Measured so far, and the two measurements DISAGREE:

    A. same section driven ALONE, 3x, fresh server each
       -> reported bit-identical, 348 steps, 6.74 ft
       -> BUT THIS PROBE IS SUSPECT. scripts/determinism_probe.py reads
          pipeline/results/eval_<ckpt>_<section>.csv, which every run OVERWRITES IN
          PLACE. If a run did not rewrite it, the probe compared the file with itself
          and "IDENTICAL" means nothing. The probe must be fixed to copy each run's CSV
          to a per-rep path BEFORE the next run, then compare those copies.

    B. the gate's own pattern, --direction all, 3 reps, fresh server each
       (results/town06_logs/seq_det.log, parsed from STDOUT so not subject to the same
       flaw)
         rep 0: s00=0.36 s01=0.71 s02=10.28 s03=0.62 s04=0.62 s05=0.60
         rep 1: s00=0.35 s01=0.54 s02= 9.53 s03=0.43 s04=0.57 s05=0.40
       EVERY section differs, including s00, the FIRST one driven.

B is the more trustworthy of the two and says runs are NOT reproducible. A said the
opposite and has a known defect. Do not treat either as settled.

**Why this reaches Town04.** The published study drives its lap in two directions inside
one process, the same pattern as `--direction all`, and reports cells as rates over ten
runs. If runs are not reproducible, those rates are rates over something real and the
published numbers stand as rates -- but the STUDY has never characterised the source of
that variation, and a 0/10 versus 10/10 split is only as meaningful as the process
generating it. If runs ARE reproducible and the variation is an artefact of our harness,
then "10 repetitions" was measuring the harness. Either way it needs resolving before the
next blind claim, and it is the first thing to settle.

### What to do first, in order

1. **Fix determinism_probe.py** so each rep's CSV is copied to its own path before the
   next run overwrites it. Re-run A. This is cheap and decides everything below.
2. If runs ARE reproducible in isolation but NOT in sequence, the carried state is the
   target: `teleport` zeroes linear and angular velocity and sets the transform, but does
   not touch suspension, wheel or drivetrain state, and CARLA applies transforms on the
   NEXT tick. Instrument the first 20 steps of each section for pose, velocity and
   steering and diff them across reps.
3. If runs are not reproducible even in isolation, find the entropy source before
   trusting any closed-loop number. Candidates in order of likelihood: renderer
   nondeterminism reaching the camera, sensor delivery ordering, physics substep
   scheduling.
4. Only then return to the competence gate. A "held 2/3" is not interpretable until this
   is settled.

### What IS trusted, and can be built on

  - **The corrected routes.** 6 sections, 3,834 m, independently verified: 100% both lane
    markings present with no gap >= 10 m, 100% DASHED on both sides, 3-5 lanes throughout,
    never a single-lane connector. Route fingerprint 706db50636cbd6c9.
  - **The low-sun correction.** Town06 at 5 degrees renders 0.1250 mean against Town04's
    0.1117; at the inherited 15 degrees it was 0.1841 and nearly indistinguishable from
    night. Fog and night are unchanged to four decimal places, verified old-vs-new.
  - **Both teachers.** clear 6/6 at 0.92 ft; mixed 24/24 at 1.31 ft, and the mixed teacher
    converged in 6 DAgger rounds against 12 on the contaminated routes.
  - **Both students distilled.** clear KD RMSE 0.0300 (was 0.0489-0.0553 on the old
    routes, on MORE frames), mixed 0.0480.

### What is NOT trusted

  - Every closed-loop student number from this session. The competence gates ran on
    degraded or un-restarted servers, and the one clean-looking gate is subject to the
    open question above.
  - T06-F14's "student DAgger is harmful at 168x28". Measured on the contaminated
    sections; never re-tested on the corrected ones. The chain is set up to re-test it.
  - Any per-section claim. s02 looks like the hard section for both students, but s02 also
    read 6.74 ft alone and 9.53-10.28 ft in sequence.

### Infrastructure faults found and fixed this session

  1. Runs overshot each section's clean window; the excursion in excluded road was scored
     as the section's max |CTE|. Fixed: stop at the scored end by unwrapped route index.
  2. A degraded CARLA silently stops advancing physics while reporting plausible
     velocities: sections drove 14-62% of their length at 1.3-5.6 m/s while speed_mph read
     20.0. Fixed: restart before every measurement run, plus six hygiene rules in
     CLAUDE.md.
  3. `subprocess.run(capture_output=True)` on a script that daemonises CARLA hangs
     forever on the inherited pipe. THIS is what cost the night: 12h52m at 0% CPU. Same
     script takes 57 s standalone. Fixed by redirecting to a log file.
  4. wait_carla_ready declared the server ready on the default map; the first run then
     paid a Town06 load that blew evaluate.py's 120 s client timeout. Fixed: the probe
     loads the study map, capped by its own deadline.
  5. Condition leakage (Zach's Town04 fog-into-night). Fixed: the rendered condition is
     identified from a real frame and mismatches RAISE. Validated 24/24 on captures.
  6. Three separate bugs in the section-end distance cap, each ending runs after 3-5 steps
     and reporting the tiny |CTE| as a PASS.

Common thread, and the reason for R-SIM-6: **an infrastructure fault reliably looks like a
model result.** Five times this session a broken pipeline produced a plausible number.
Treat any surprising closed-loop value as suspect until it reproduces on a fresh server.

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

---

## T06-F22  RESOLVED: run-to-run reproducibility. Two causes, both found, one fixed and one bounded.

Answers T06-F21, and it answers Zach's question directly: CARLA in synchronous mode with
a fixed timestep is **not** sufficient for reproducibility, and the study's protections
were all real but all aimed at the wrong layer.

### Method: the closed-loop probe could never have found this

T06-F21 proposed re-running the closed-loop probe. That would have failed again, because
a closed-loop probe measures physics, rendering and feedback amplification at once and
every candidate cause produces the same symptom — a trajectory that drifts apart. The
diagnosis needed the feedback **cut**: a scripted command sequence that is a pure
function of the step index, with pose, a hash of the raw camera buffer, and the model's
steering **computed but not applied** all recorded per step. Three streams, three
questions, separable. `scripts/determinism_tier1_openloop.py`.

Tier 0 first, with the simulator switched off (`determinism_tier0_model.py`): the
inference path is bit-exact within and across processes — weights load, preprocessing,
and both batched and batch-1 forwards. torch, cuDNN and OpenCV are ruled out. (Aside,
recorded because it will matter to offline analysis: batch-N and batch-1 forwards of the
same frames differ by 2.2e-6. The closed loop is always batch-1.)

### Cause 1 — `apply_control` loses a race with `tick`. FIXED.

`vehicle.apply_control()` is fire-and-forget: it returns once the message is written, and
whether the server registers it before it processes `world.tick()` is a wall-clock race.
**Synchronous mode synchronises the tick, not the command queue feeding it.**

The race is invisible while a command is unchanged, because a late arrival re-applies the
same value. So it only ever bites on a step where the command *changes* — which in a
closed-loop run is every step, and which is why divergence always appeared to begin
mid-run for no reason.

Measured, open loop, identical scripted commands, three reps:

    vehicle.apply_control()   pose bit-identical until the first command CHANGE, then
                              splits; the APPLIED-CONTROL READBACK differs between reps
                              at the same step; up to 60 m apart over 200 steps
    apply_batch_sync()        pose, velocity, gear and applied control bit-identical at
                              every step of every rep

Controls that make the diagnosis stick: with the camera removed entirely, physics still
diverged, so the renderer was not causing it; with the command held constant, physics was
bit-identical for 200 steps, so physics itself was never the problem.

Fixed via `env.apply_control()`, one choke point every driving loop now goes through,
gated on `config.DETERMINISTIC_CONTROL` — **on for Town06, off for Town04**, so the
published artifact keeps reproducing exactly.

### Cause 2 — texture streaming. FIXED, 168x.

With physics pinned bit-exact, the renderer was still nondeterministic. UE4 streams
texture mips in asynchronously, so which mip is resident when a frame renders depends on
load timing rather than on world state. Launching with `-notexturestreaming`:

    injected steering noise   3.9e-3  ->  2.4e-5     (168x)
    cold-server outlier       rep0 disagreed with reps 1..N  ->  gone

It also explains a pattern that had been read as random: the FIRST run after a restart
disagreed with every later run, because it alone rendered while textures were still
resident-loading.

Negative results, kept because each was a plausible fix that measurement rejected:

  - `enable_postprocess_effects=False` made it **2000x WORSE** (4.8e-2). Manual exposure
    lives inside the postprocess chain, so disabling postprocessing silently un-pins the
    exposure this study depends on.
  - `-quality-level=High` was catastrophic (5.2e-1). Epic is a determinism result here,
    not a visual preference.
  - Zeroing motion blur, bloom and lens flare: no material effect.
  - Removing the spectator chase camera: no material effect.
  - A 100-tick warmup helped; a 300-tick settle did not converge the residual further.

### The residual, and why it cannot be argued away

On a scene where **nothing moves at all** — vehicle held on the brake with zero
displacement to full float precision, camera rigid, weather fixed, exposure manual —
frames at the same index across repetitions are never bit-identical. The floor is
~30 pixels of 307,200 differing by at most 13 levels, ~7 of them inside the student's
ROI. A longer settle does not converge it, so it is generated per frame rather than
inherited history. `scripts/determinism_static_scene.py`.

An earlier version of that probe compared frame N to frame N+1 *within* one run and found
40 distinct frames of 40. That is temporal accumulation — TAA, screen-space reflections
and volumetric fog all evolve on a static scene — and it is not a determinism result.
Only frame N of run A against frame N of run B is, and the corrected probe does that.

### Consequence: the closed loop is a six-order-of-magnitude amplifier

With Cause 1 fixed and only the render floor left, the real closed loop over section s02,
349 steps, three reps on fresh servers:

    diverges at step 0 from dsteer 2.6e-06
    grows to  max dCTE 4.2-7.6 ft
    max|CTE|  7.97 / 4.47 / 11.83 ft

**So standing rule 3 survives, and is now justified by measurement rather than by
folklore.** Every closed-loop number remains a RATE over at least 10 repetitions with a
Wilson interval. What has changed is that the noise is 168x smaller, its source is named,
and the residual is bounded and documented.

### The reframing that matters for the paper

That amplification is a property of the **policy**, not of the simulator. A contractive,
competent policy suppresses a 2.6e-6 perturbation; a marginal one grows it to feet. So
run-to-run spread is a *measurement of closed-loop stability margin*, and a checkpoint
whose verdict flips between repetitions is reporting its own marginality rather than
being unluckily sampled.

This says the Town06 "held 5/6, then 6/6, then 5/6" was never purely an instrumentation
artefact: instrumentation contributed the perturbation, and the student's own lack of
margin contributed the amplification. **The capacity decision in `TOWN06_STATUS.md` is
therefore still open and still necessary** — the determinism fix does not make a marginal
student competent, and it was never going to.

Incidentally this is the paper's own thesis appearing a third time: a small persistent
bias walks the vehicle out of its lane, and a small transient one does too when the
policy has no margin to absorb it.

### Effect on Town04 — none, and deliberately so

Nothing in this finding touches Town04. `DETERMINISTIC_CONTROL` defaults off there,
`-notexturestreaming` is applied only when `STUDY_MAP=Town06`, and the preflight is
called only on the Town06 path. The published rates stand as rates. Whether they should
be re-measured under the corrected harness is a real question and a separate decision;
Town04 stays frozen until the Town06 work is finished.

### What was ALSO wrong: the probe that said the opposite

`determinism_probe.py` reported "bit-identical" and contradicted the true measurement.
The handoff blamed in-place CSV overwriting, which was not quite it: the probe read each
CSV into memory immediately after its run. The actual defect was that the subprocess
**return code was captured and never checked**, so a crashed rep left the previous rep's
file on disk and the probe compared it with itself. Now guarded three ways — non-zero
exit raises, the CSV must be newer than the run's start, and each rep's file is copied to
its own path before the next runs.

### Standing outcome

The rules are extracted into the lab-wide `carla-determinism` package (repo
`carla-determinism--simulation--package`), hash-locked, and enforced by
`carla_determinism.require_deterministic()`, which reads the server's real command line
from `/proc` (the launch flags that matter are invisible over RPC) and refuses to let a
measurement run on a misconfigured simulator.

### T06-F22 addendum: the oracle is now bit-identical, which localises the residual exactly

The pure-pursuit oracle steers from route geometry and the vehicle pose. **It never reads
the camera.** So under the corrected harness it should be perfectly reproducible, and it
is: all six sections, two runs, a fresh server between them.

    s00 s01 s02 s03 s04 s05 -- BIT-IDENTICAL, whole per-step CSV, byte for byte

That is worth more than the open-loop probe, because it is the real pipeline — the real
`drive_expert.py`, the real route code, the real speed controller, a real full-length
section — rather than an instrument built to prove a point. It establishes three things
at once:

  1. the `apply_control` fix works in production code, not only in the probe;
  2. physics, route indexing, the speed controller and the section-end cap are all
     fully deterministic;
  3. **the entire remaining entropy is the camera path**, since the only difference
     between this and a student run is where the steering comes from.

It also gives the study a cheap standing regression test for the harness: drive the
oracle twice and `cmp` the CSVs. Anything other than bit-identical means the harness has
regressed, and it costs two oracle runs to find out rather than a night of theorising.

Oracle competence on the corrected harness, for the record: PASS on all six sections,
max|CTE| 0.01-0.34 ft against a 2.19 ft budget.

### T06-F22 addendum 2: the conditions survive the harness change; 5-degree low sun holds

PROTOCOL A-2 required the Town06 low-sun angle to be re-derived under the corrected
harness before the mixed policy is collected, because T06-F20 chose 5 degrees from
brightness measured on captures taken under the old one. Re-measured at all six section
spawns:

    condition     s00     s01     s02     s03     s04     s05     CV%
    clear      0.2963  0.2963  0.2969  0.2929  0.3056  0.3018    1.40
    fog        0.2542  0.2723  0.2702  0.2698  0.2352  0.2690    5.08
    night      0.2060  0.1983  0.2385  0.1907  0.1819  0.2596   12.96
    shadows    0.1222  0.1178  0.1179  0.1163  0.1233  0.1249    2.65

Low sun means 0.1204 against Town04's published 0.1117 -- 7.8% away, inside the 9% T06-F20
accepted, where the inherited 15 degrees was 65% away and read as night. The night-minus-low-sun
gap is 0.0921 against Town04's 0.0958, so the lighting axis stays ordered, which is the
property the study depends on. Per-section uniformity improved slightly, 3.29% -> 2.65%.

**5 degrees holds and A-2 needs no clause.**

Also checked, and the reason this ran before the rebuild rather than during it: all four
conditions still classify as themselves under `condition_signature.identify()`, whose
thresholds were fitted on old-harness captures. `evaluate.py` raises on a mismatch, so a
threshold crossing would have aborted every run of the affected condition hours into an
unattended campaign. Margins are healthy on every discriminator.

One stale artefact worth naming: the reference table in `condition_signature.py`'s
docstring still lists shadows at mean 0.1842. That is the pre-T06-F20 15-degree value,
not a drift caused by the harness change. The thresholds themselves are unaffected,
because shadows is identified by falling below clear's 0.250, not by matching 0.1842.

### T06-F23 (PRE-REGISTERED, result not yet in): what the mixed teacher must do to be normal

Written 2026-08-28 while `dagger_mixed` is still running, so that the check means
something when the result arrives. Standing rule 2: a result contradicting this is a bug
until a written disposition rules out the candidate causes.

The mixed teacher's first three rounds looked alarming -- worst max|CTE| RISING, 40.19 ->
46.12 -> 59.31 ft, with only 5 of 24 cells passing. It is not alarming, because the
clear-only teacher on the SAME corrected harness did the same thing and then converged:

    clear-only teacher              mixed teacher
    round  passed  worst |CTE|      round  passed   worst |CTE|
      0     0/6      17.91            0     2/24      40.19
      1     1/6      17.57            1     4/24      46.12
      2     3/6      25.64  <-- rose  2     5/24      59.31  <-- rose
      3     3/6       8.81  <-- turn
      4     4/6       3.24
      5     5/6       3.08
      6     5/6       2.28
      7     6/6       1.25  PASS

DAgger gets worse before it gets better by construction: it aggregates expert corrections
on the states the current policy visits, so a policy that is still bad visits bad states
and the peak excursion grows before the aggregated data pays off. Both teachers show it.
Pass count, which is the less noisy signal, improved monotonically for both.

**The prediction.** If the mixed teacher is merely slower than the clear one and not
broken, its worst max|CTE| turns downward by round 4 and is under 20 ft by round 5, with
the pass count still climbing. It has 14 rounds and the clear one needed 7 for a quarter
of the cells.

**What falsifies it.** Worst max|CTE| still above 20 ft at round 5, or a pass count that
stalls or reverses across two consecutive rounds. That would be a real finding about
capacity or about the mixed dataset, not DAgger noise, and it must be disposed in writing
before anything downstream is trusted.

Recorded because the honest failure mode here is the other direction: watching a bad
trend, waiting, and then rationalising whatever happens as expected. `teacher_gate` in
`run_town06_pipeline.sh` independently refuses to distil a teacher that exhausts its
rounds without meeting budget, so a failure cannot pass silently either way.

Note also cleared, and worth recording because it was flagged as suspicious: R-SIM-6 is
clean across every round so far. Ten runs aborted early (steps 53-351), and every one of
them reported FAIL with a large max|CTE|. R-SIM-6's concern is a SHORT run reporting a
tiny |CTE| as a PASS; zero did. These are genuine lane departures by a policy still being
trained, which is what DAgger is for.

### T06-F23 DISPOSITION: the falsifier FIRED, and it fired for a real reason

The pre-registered prediction had two parts. One was confirmed, one was falsified, and the
falsification is informative rather than a badly chosen threshold.

**Confirmed: the teacher turned, at exactly the round the control predicted.** Round 3,
the same round the clear-only teacher turned on this harness.

    round  passed   median |CTE|   worst |CTE|
      2     5/24        --            59.31
      3    18/24       1.48            4.09   <-- the turn
      4    17/24       1.86           10.29
      5    22/24       1.18           55.59
      6    (running)

**Falsified: "worst max|CTE| under 20 ft by round 5".** Round 5 was 55.59 ft.

**Disposition.** The falsifier did not fire because worst-of-24 is a fragile max statistic
-- that was the tempting rationalisation and it is wrong. It fired because ONE CELL is
diverging while every other cell converges. At round 5, 22 of 24 cells pass, the median is
1.18 ft, and the only serious failure is `night/s02`:

    night/s02   round 3:   2.66 ft FAIL
                round 4:  10.29 ft FAIL
                round 5:  55.59 ft FAIL

Failing in every round since the turn, monotonically worse, while the aggregate improves.
That is the opposite of DAgger noise, which would move a different cell each round.

**What this is NOT yet evidence of.** Each cell-round here is ONE run, and standing rule 3
says a single run near the cliff is wrong about one time in eight. So the SEVERITY trend
(2.66 -> 10.29 -> 55.59) is weak evidence -- three single runs. The PERSISTENCE is the
stronger signal: `night/s02` has failed 3 for 3 since the turn while the rest of the route
converged. `dagger.py`'s own `--margin-frac` docstring already names this tension: a
single-run gate can stop on a lucky pass, and it can equally fail on an unlucky one.

**Prior, held loosely.** The previous generation's D-T06-3 was also night on the mixed
policy, and s02 was already suspected as the hard section. That measurement is discarded
by A-2 and cannot be used as evidence -- but the same cell resurfacing on independently
collected data, under a corrected harness, on a route chosen without driving, is worth
noting as a pattern to test rather than a coincidence to ignore.

**What happens next, and why nothing can pass silently.** `dagger.py` requires ALL 24
cells to pass in a single round. If `night/s02` does not come in, the run exhausts its 14
rounds, prints "Exhausted N rounds without passing", and `teacher_gate` in
`run_town06_pipeline.sh` FATALs rather than distilling. So the outcome is either a teacher
that genuinely met budget on every cell, or a hard stop -- not a quiet degradation.

**If it stops.** The question to answer first is whether `night/s02` is a policy problem or
a scene problem, and the cheap discriminator already exists: drive the ORACLE on
`night/s02`. The oracle is bit-identical under this harness and never reads the camera, so
if it holds the section, the geometry is fine and the failure is perception under night;
if it does not, the section itself is the problem and no amount of training fixes it.

### T06-F23 RESOLUTION: the teacher passed at round 12, and my reading of night/s02 was wrong

**Result: the mixed teacher met budget on all 24 cells at round 12, worst max|CTE| 1.78 ft.**
`teacher_gate` passed and the pipeline moved on to distillation.

`night/s02`, which the disposition above singled out as "diverging while every other cell
converges", in full:

    round  0:   4.48 FAIL      round  7:   1.47 PASS
    round  1:  11.35 FAIL      round  8:   2.47 FAIL
    round  2:  27.41 FAIL      round  9:   3.56 FAIL
    round  3:   2.66 FAIL      round 10:   2.49 FAIL
    round  4:  10.29 FAIL      round 11:   1.13 PASS
    round  5:  55.59 FAIL      round 12:   0.74 PASS
    round  6:   0.51 PASS

**55.59 ft, then 0.51 ft in the very next round.** The disposition called the 2.66 ->
10.29 -> 55.59 sequence "monotonically worse... the opposite of DAgger noise, which would
move a different cell each round." That inference was wrong, and it was wrong in an
avoidable way: it read a trend out of three consecutive SINGLE runs, which is precisely
what standing rule 3 says cannot be done. The disposition even stated the caveat -- "the
severity trend is weak evidence, three single runs" -- and then led with the trend anyway.
The caveat was right and the headline was wrong.

What survives, and it is the smaller claim: **`night/s02` is genuinely the hardest cell on
the route.** It failed 9 of 13 rounds, more than any other, and it is the last thing the
teacher fits. Identifying it was correct; calling it divergent was not. A cell that
oscillates 55.59 -> 0.51 -> 1.47 -> 2.47 is a cell sitting on the stability cliff, which is
exactly what T06-F22's D-10 predicts: run-to-run spread is a stability-margin measurement,
and the widest spread appears where the margin is thinnest.

So the pre-registration did its job in both directions. It caught a real signal -- s02 at
night is the hard cell, and that is worth carrying into the certification cells -- and it
caught me over-reading that signal, because the falsifier and the caveat were both written
down before the answer existed rather than chosen afterwards.

**One number to carry forward, not yet explained.** The mixed teacher needed **12 DAgger
rounds** under the corrected harness against 6 on the old one, while the clear teacher
needed 7 against a previous 6-ish. That is a real difference and it has NOT been
diagnosed. Candidate causes, none ruled out: the corrected harness genuinely presents a
harder learning problem; the recollected data differs in composition; ordinary run-to-run
variation in DAgger convergence, which the oscillation above shows is large. It must not
be written up as a harness effect without a measurement that separates these.

## T06-F24  The extra DAgger rounds are the GATE's arithmetic, not the harness

Diagnosing the number left undiagnosed in T06-F23: the mixed teacher needed 12 rounds
under the corrected harness against 6 before. The answer is that round count is not a
measure of task difficulty, and comparing 12 with 6 measures almost nothing.

### The gate is a conjunction of N single runs, and N differs by 4x

`dagger.py` stops when EVERY cell passes in ONE round. The clear teacher has 6 cells
(6 sections x clear). The mixed teacher has 24 (6 sections x 4 conditions). Each cell is
a SINGLE run, which standing rule 3 says is wrong about one time in eight near the cliff.

Measured per-cell pass RATES from the turn onward -- the rate rule 3 asks for, which the
gate itself never computes:

    CLEAR teacher, rounds 3-7    pass counts  [3, 4, 5, 5, 6] of 6     mean 4.6/6
    MIXED teacher, rounds 3-12   pass counts  [18,17,22,16,20,19,22,20,19,24] of 24
                                                                       mean 19.7/24

Both teachers sit at ~77-82% per-cell competence. **They are equally good. The mixed one
simply has to win four times as many coin flips simultaneously.**

    clear:  P(all 6 pass)  = 0.173  -> expected wait  6 rounds;  actual 5
    mixed:  P(all 24 pass) = 0.0036 -> expected wait 276 rounds;  actual 10

The clear teacher's wait matches the independent prediction almost exactly. The mixed
one's does not, and the reason is visible in the dispersion: its round-to-round pass count
has sd 2.33 where independent cells would give 1.63. **Rounds are overdispersed, so cells
are positively correlated within a round** -- each round is a differently-retrained
network that is uniformly better or worse, and the gate is waiting for one that happens to
be good everywhere at once. That correlation is what rescues the wait from 276 rounds down
to 10, and it is also what makes the wait enormously variable.

**So 12 versus 6 is two draws from a high-variance waiting time.** It is not evidence that
the corrected harness presents a harder learning problem, and it must not be written up as
one. The candidate cause named in T06-F23 -- "the corrected harness genuinely presents a
harder learning problem" -- is not ruled out by this, but it is no longer needed to explain
anything, and nothing here supports it.

### The consequence that actually matters: the gate selects a LUCKY ROUND

The teacher we are distilling from, `teacher_mixed_t06_dagger_r11`, was chosen because on
one round it scored 24/24. Its typical round scores 19.7/24. Its true per-cell rates were
never measured, because the gate measures one run per cell and then stops.

`dagger.py`'s own `--margin-frac` docstring already says this out loud -- "a single-run
gate can stop on a lucky pass" -- and the same applies to the clear teacher, selected on
one 6/6 round with a 4.6/6 typical.

This is not fatal: distillation copies the teacher's steering OUTPUTS over a fixed
dataset, not its closed-loop trajectories, so an occasional departure does not
automatically transfer. But it means the phrase "the teacher met budget" carries less than
it appears to, and any claim resting on teacher quality should quote the rate above rather
than the gate verdict.

**Recommendation, not yet acted on because it is a protocol matter:** the teacher gate
should require a RATE over repetitions like every other closed-loop number in this study,
rather than one conjunctive round. Changing it mid-study needs an amendment and it would
cost real simulator time, so it is recorded here for Zach rather than done.

### The per-cell rates predict where the STUDENT will fail first

A distilled student mimics its teacher, so the teacher's weak cells are the student's
likely weak cells. Ranked worst first:

    night/s05  0.30      clear/s02   0.70      fog/s01   0.80
    night/s02  0.40      night/s00   0.70      fog/s03   0.80
    fog/s00    0.60      shadows/s02 0.70      (13 cells at 0.90-1.00)
    fog/s02    0.60      clear/s00   0.80

Two things fall out of this list. `night/s02` and `night/s05` are the worst cells, which
is consistent with night being the hard condition on this route. And **`clear/s02` at 0.70
is the immediate risk**, because the competence gate that runs next is clear-weather only
and requires every section to hold on every one of 3 repetitions.

### PRE-REGISTERED, before the competence gate runs

If the students inherit their teacher's per-cell rates, the clear gate is a conjunction of
6 sections x 3 reps that must ALL hold. Using the clear teacher's own clear-cell rates
(s00 0.80, s01 0.90, s02 0.70, s03 1.00, s04 1.00, s05 1.00 for the mixed teacher's clear
row; the clear-only teacher's are similar):

**Prediction: if either student fails the clear competence gate, it fails on s02, and
possibly s00 or s01. It does not fail on s03, s04 or s05.**

That is falsifiable and cheap to check. If a student instead fails on s03/s04/s05 -- the
sections both teachers hold reliably -- then the student is NOT merely inheriting teacher
weakness and the cause is distillation capacity, which is a different problem with a
different fix (width, or input size).

## T06-F25  The student registry encodes two conclusions from data that A-2 discarded

Found while planning the student stage. Both are live decisions in the running pipeline
and both rest on T06-F14, which the handoff already listed as untrusted ("measured on the
contaminated sections; never re-tested on the corrected ones") and which A-2 has now
discarded outright along with the data underneath it.

**1. Both students are the SAME width.** `TOWN06_STUDENTS` declares clear and mixed both
at channels (16,32,32), fc 64, 168x28 -- 21,408 ReLU each. That came from T06-F14's "w2
beats w3", measured on contaminated sections with single-pass numbers.

It contradicts the published Town04 study, which is the reference this whole deployment
test is calibrated against: there the mixed student is **3x the clear student's width**,
and M3 (`4b2ad73`) established that width was exactly what the mixed policy needed --
w1 failed all four conditions, w2 failed night 10/10, w3 passed everything. T06-F11/F13
reached the same conclusion on Town06 before T06-F14 reversed it on data now discarded.

**2. There is no student-DAgger stage at all.** `run_town06_pipeline.sh` goes distil ->
competence gate, with a comment block explaining that T06-F14 removed it. Same discarded
evidence.

### Why this matters tonight rather than later

The prior from every source that survives A-2 -- the published Town04 result, T06-F11,
T06-F13, and the mixed teacher needing 4x the cells of the clear one -- says the mixed
policy needs more capacity than the clear one. The pipeline is currently building them
identical, on the authority of a finding that no longer has data.

That does not mean widening now. It means the w2 mixed student is being tested against a
prior that expects it to fail, so a failure is the EXPECTED outcome and not a surprise
requiring diagnosis, and a pass is the informative result.

### The levers, and what each costs to verify

`T06_IN_W` / `T06_IN_H` are environment-overridable, so input size needs no config edit.
ReLU counts, against T06-F12's finding that what binds certification here is the
DISTURBANCE dimension (1-D) rather than network size:

    current  w2  168x28    21,408   1.00x
    w3           168x28    32,112   1.50x
    w4           168x28    42,816   2.00x
    w2           224x28    28,800   1.35x
    w2           168x56    50,944   2.38x

T06-F12 measured 5,152 ReLU -> 0.78% UNKNOWN and 15,456 -> 2.5%, against ~11% where
certification stops being useful. There is real headroom, and widening is the cheap axis.

Distillation is also cheap: the clear student distilled in about 7 minutes from an
existing teacher, and changing the student needs NO new teacher and NO new data. So an
architecture sweep here costs distillation plus a competence gate, not a rebuild.

### Order of levers if the gate fails

Zach's framing governs and it is the right one: **it does not matter what architecture is
optimal, only that one works, because this study is about formal verification.** So the
order is cheapest-first and stops at the first thing that passes, rather than searching:

  1. **Width on the mixed student** (w3, then w4). Cheapest, best-supported by the
     surviving prior, and matches what published Town04 actually did.
  2. **Input size** (168x56 first: night and the straight sections are where the failures
     are, and vertical resolution is what T06-F17/F18 found night needed).
  3. **Both**, if neither alone does it.
  4. **Re-enable student DAgger** last -- not because it is worst, but because its removal
     is the decision here with the least surviving evidence either way, so re-adding it
     changes two things at once unless the others are settled first.

The clear student stays at w2 unless it fails on its own; there is no reason to widen a
policy that only ever sees one condition, and Town04 did not.

## T06-F26  The conjunctive gate degrades the STUDENT, by way of the DAgger set

Diagnosing why the freshly distilled clear student fits its teacher much worse than the
superseded one did. This connects T06-F24 to the student problem, and it is a causal
chain rather than a coincidence.

### First, an A-2 premise that turns out to be wrong

A-2 justified recollection on two grounds: the images carry texture-mip variation a
corrected evaluation never shows, and "the trajectories those frames were sampled along
are not the trajectories the corrected harness produces." **The second is false for the
base datasets, and measurably so.**

Comparing the recollected `clear_t06` against the archived one:

    manifest.csv   md5 IDENTICAL   (poses, steering labels, CTE, speed -- byte for byte)
    frames/*.png   md5 DIFFER
    mtimes         new written today; it WAS recollected, not reused

Same for `mixed_t06`. So the expert-driven collection reproduces its trajectory and its
labels exactly across the harness change, and only the rendering moved.

Two candidate explanations, and this does not distinguish them: the pure-pursuit expert is
strongly contractive, so a one-tick-late command decays instead of compounding (the
converse of D-10, where a marginal policy amplifies the same perturbation); or the
`apply_control` race simply did not fire during either collection, which the Tier-1
measurements show is possible -- several probe runs were clean for 200 steps.

**A-2's conclusion still stands on the first ground alone.** The images differ, D-11
applies, recollection was correct. But the amendment claims one reason too many and should
not be cited for the trajectory claim.

### The regression, measured properly

    clear student KD RMSE      old harness 0.0300      new 0.0728      2.43x worse

That comparison is not apples-to-apples, because the two students were distilled against
different targets. Normalising by the standard deviation of the actual teacher targets:

    target sd (teacher outputs)   old 0.0808        new 0.1081     1.34x harder target
    relative error KD/sd          old 0.371         new 0.673      1.81x worse FIT

So a third of it is a genuinely harder target and the rest is the student fitting it
worse. In R^2 terms the student went from explaining ~86% of the teacher's variance to
~55%. **It is under-fitting, not mis-measured.**

### Why the target got harder, and it traces straight back to T06-F24

The distillation set is base + every DAgger round. The clear teacher needed 7 rounds this
time against 5, and T06-F24 showed those extra rounds are the conjunctive single-run
gate's waiting time, not extra task difficulty. Each extra round appends more off-nominal
recovery data, and recovery states carry large corrective steering:

    dagger_clear_t06   old  n=12,228  mean|s|=0.0494  sd=0.1048  p99=0.4859
                       new  n=17,064  mean|s|=0.0617  sd=0.1330  p99=0.5772
    distillation set   old  59% DAgger        new  67% DAgger

So: **the gate waits for a lucky round -> each round of waiting appends more off-nominal
data -> the distillation target's variance rises -> a fixed-capacity student fits it
worse.** The gate's statistical defect propagates into the student's competence. That is
worth stating plainly because it means the round count is not merely uninformative, as
T06-F24 concluded, but actively harmful downstream.

The mixed student is the same story amplified: 12 rounds produced **109,834** DAgger
frames against 57,601 before, and it is being distilled at the same 21,408 ReLU.

### Predictions, recorded before the competence gate reports

1. **The clear student fails the clear-weather competence gate**, at relative error 0.673.
2. **If it fails, it fails on s02 first** (T06-F25's prediction, from the teacher's own
   per-cell rates), not on s03/s04/s05.
3. **The mixed student is worse than the clear one**, having twice the off-nominal data at
   identical capacity.

If 1 holds, the lever is capacity, and Zach's ordering applies: width first, then input
size, and it does not matter which architecture is optimal as long as one works. Note that
widening is the right response to an UNDER-FITTING student, which is what the relative
error says this is -- so the diagnosis and the cheapest lever agree, which is not always
the case and is worth noticing.

### Latent hazard found while reading the deployment script

`results/town06/competence_clear.json` is keyed to nothing. `finish_town06_deployment.sh`
gates on its `all_competent` flag, so a STALE record from a previous generation of
students would let certification proceed on evidence about different checkpoints. Right
now the file on disk is from 11:47 today, describing the students A-2 discarded, and it
happens to say "not competent" -- so it would refuse rather than wrongly proceed. The
guard works by luck, not by construction. It should record the checkpoint file hashes it
was measured on, and the deployment script should verify they match.

## T06-F27  Prediction 3 FALSIFIED: the mixed student is fine; the CLEAR one regressed

T06-F26 predicted the mixed student would be worse than the clear one, "having twice the
off-nominal data at identical capacity." Measured, both distilled:

    student      KD RMSE  target sd        n   rel err    R^2    x tolerance
    clear NEW     0.0728     0.1081    25,628    0.673    0.55       6.06x
    clear OLD     0.0300     0.0808    20,792    0.371    0.86       2.50x
    mixed NEW     0.0391     0.0914   135,526    0.428    0.82       3.26x
    mixed OLD     0.0480     0.1151    83,293    0.417    0.83       4.00x

**The mixed student is unchanged** -- relative error 0.428 against 0.417 before, R^2 0.82
against 0.83. Its absolute KD RMSE even improved, 0.0480 -> 0.0391, because its target got
easier: the mixed DAgger set came out LESS extreme this time (sd 0.0914 against 0.1151),
not more, despite twice the rounds.

**The clear student is what regressed**, and badly: relative error 0.371 -> 0.673, R^2 from
0.86 to 0.55. It now explains barely half its teacher's variance.

### Why the inversion, and it is not the one anyone expected

The two students face opposite data situations:

    clear:  25,628 samples, target sd 0.1081, 67% of it off-nominal DAgger recovery data
    mixed: 135,526 samples, target sd 0.0914, and four conditions to average over

The clear student has **five times less data against a HIGHER-variance target**. T06-F26's
mechanism was right -- extra DAgger rounds raise target variance -- but it bites the
CLEAR student, not the mixed one, because clear's base set is small enough that each extra
round of recovery data moves its distribution substantially. The mixed set is large enough
to absorb the same rounds without shifting.

So the causal chain from T06-F24 stands and lands somewhere different from where it was
aimed: **the conjunctive gate's lucky-round wait degrades whichever student has the least
data to dilute the recovery states it appends, and that is the clear one.**

### This contradicts the standing prior, and the prior should not simply win

Zach's experience, and Town04, both say the clear student is the easy one and the mixed
student is the hard one needing width and input sweeps. On Town04 that is exactly right,
and its student sizes encode it: `S_clear` (8,16,16)/fc32 against `S_mixed` (24,48,48)/fc96,
3x width.

This measurement says the opposite for THIS build, and the reason is specific and
traceable rather than mysterious: it is a property of how much data each student got
relative to its target's variance, not a property of the task. The mixed policy is still
the harder TASK. The clear student is simply the more data-starved MODEL right now.

Both can be true, and the fix differs for each:
  - mixed: capacity, if it fails the four-condition drive -- the Town04 lever, w3 then input
  - clear: capacity too, but the cheaper first move is more clear base data, since its
    problem is a small dataset rather than a hard function

### What the clear-weather gate can and cannot settle

Recorded before the gate reports, because it bears on how its result should be read:
**passing the clear competence gate does not clear the mixed student.** Town04's own
history is the proof -- there, w2 mixed passed clear and then failed night 10/10, and w3
was what fixed it (`4b2ad73`). The clear gate is the s=0 anchor, not a capacity test.

So whatever the gate says, the mixed student still needs a four-condition exploratory
drive before its width is settled. A-1 permits exactly that -- R1 is suspended, and A-1's
re-entry condition is literally "a mixed student drives every condition."

## T06-F28  BOTH STUDENTS COMPETENT WITH MARGIN. The capacity crisis was the data.

The clear-weather competence gate, 3 repetitions x 6 sections per student, every section
required to hold on every repetition:

    S_clear_t06_168x28_w2   6/6 sections, 3/3 reps each, worst max|CTE| 1.31 ft
    S_mixed_t06_168x28_w2   6/6 sections, 3/3 reps each, worst max|CTE| 1.01 ft
                                                          gate 2.19 ft

Against the build A-2 discarded, same architecture, same gate:

    old S_clear_t06   5/6, then 6/6, then 5/6 on three consecutive runs, nothing changed
                      worst |CTE| ranging 1.71 to 2.92 ft -- straddling the budget

**That is the whole reason this study was paused.** `TOWN06_STATUS.md` opens with "PAUSED
-- students are marginal, and a capacity decision is needed", and lays out three options,
all of which amount to spending days on width or data. The students are not marginal. They
have 40% and 54% margin, and they are the SAME architecture the marginal ones were.

So the capacity question that blocked the study for a week was, at least for clear
weather, an artefact of the contaminated harness and the data collected under it. Nobody
could have known that without fixing the harness first, which is the argument for having
done so.

**This does not settle the mixed student**, and it must not be read as settling it. Town04
is the proof: there, the w2 mixed student passed clear weather and then failed night 10/10,
and 3x width was what fixed it (`4b2ad73`). The clear gate is the s=0 anchor of the
disturbance family, not a capacity test. The mixed student is being driven under fog,
night and low sun now, under A-1.

### Both of T06-F26's predictions about the students were wrong

    1. "The clear student fails the clear competence gate"   FALSIFIED -- 6/6, 1.31 ft
    3. "The mixed student is worse than the clear one"       FALSIFIED -- 1.01 vs 1.31 ft
    2. "if it fails, it fails on s02"                        moot; nothing failed

Prediction 1 was made from the distillation relative error: 0.673, R^2 0.55, six times the
steering tolerance. It looked damning and it predicted nothing.

**The lesson is about the metric, and it is worth carrying.** KD RMSE is computed over the
distillation set, which is 67% DAgger recovery data by construction -- deliberately
off-distribution states the student visits only when it is already in trouble. A student
can fit those states poorly, carry a large pooled RMSE, and still drive well, because when
it drives well it never goes there. The error is concentrated exactly where it does not
matter.

That also explains the direction of the earlier surprise in T06-F27: the clear student's
relative error was worst precisely because its small base set left the recovery states
dominating its distillation mix. The metric was measuring how DAgger-heavy the set was,
more than how good the student was.

**So KD RMSE should not be used to predict closed-loop competence, and no decision in this
study should rest on it.** It remains useful for what it actually measures -- whether
distillation converged at all, and per-condition breakdowns like T06-F17's, where the
comparison is between conditions on one student rather than between students.

## T06-F29  The mixed student's gap is CAPACITY, proved by driving the teacher on the same cells

Exploratory under A-1 (R1 suspended); ONE run per cell, so these are triage, not rates,
and no verdict here is a blind prediction.

### Mixed student at w2 (21,408 ReLU), all four conditions

    condition   result   worst cell
    clear        6/6     s02 1.51 ft
    fog          5/6     s00 8.52 ft  FAIL
    night        6/6     s05 2.10 ft  (tight: gate is 2.19)
    shadows      5/6     s02 2.99 ft  FAIL
                22/24

**Night passes 6/6 at w2**, which is worth recording because Town04's w2 mixed student
failed night 10/10 and needed 3x width to fix it (`4b2ad73`). Whatever makes night hard is
not the same on both maps, and the Town04 prior does not transfer cell-for-cell. The
clear-weather competence gate had already passed this student 3/3 on every section, so
this is the first evidence about it under disturbance.

### Is that a student limit or a teacher limit? Drive the teacher on the same two cells.

A distilled student mimics its teacher and cannot exceed it, so a failure where the
teacher is ALSO weak means widening cannot help. Both failing cells were among the
teacher's weakest by the pooled per-round rates in T06-F24 (fog/s00 0.60, shadows/s02
0.70), which made this the live possibility. So it was measured rather than assumed:

    teacher_mixed_t06_dagger_r11, 3 reps each, fresh server every run

    fog/s00        PASS 0.40 ft   PASS 0.37 ft   PASS 0.37 ft
    shadows/s02    PASS 0.42 ft   PASS 0.41 ft   PASS 0.49 ft

**The teacher holds both cells 3/3 with an order of magnitude of margin**, against a
student that fails them at 8.52 and 2.99 ft. The teacher is competent and the student
cannot reproduce it, so the gap is student capacity. Width is the direct lever.

Note also what those six numbers say about the harness: 0.40 / 0.37 / 0.37 across three
freshly restarted servers. A competent, contractive policy is now extremely repeatable,
which is D-10 read from the other end -- the run-to-run spread that made the old build
uninterpretable appears where the margin is thin, not everywhere.

### A correction to how T06-F24's per-cell rates should be used

Those rates pooled every DAgger round from the turn onward, i.e. a different checkpoint
each round. They describe the DAgger TRAJECTORY, not the selected checkpoint. The final
teacher holds fog/s00 at 0.37 ft where the pooled rate said 0.60. So the rates are a
useful guide to which cells are hard -- and they did correctly rank the two cells the
student failed -- but they must not be quoted as properties of the teacher being
distilled from.

### Action

Mixed student widened to **(24,48,48)/fc96, 32,112 ReLU**, matching published Town04's
ratio of a wider mixed student than clear. The clear student stays at w2: it passed its
gate 6/6 at 1.31 ft and there is no reason to widen a policy that only ever sees one
condition, which is also what Town04 did.

T06-F12 puts 32,112 ReLU well inside tractability -- 5,152 measured 0.78% UNKNOWN and
15,456 measured 2.5%, against ~11% where certification stops being useful -- because what
binds here is the disturbance dimension, which is 1-D, not network size.

If w3 does not close it, the next levers in order are input size (168x56 first, since
T06-F17/F18 found night needed vertical resolution), then both, then re-enabling student
DAgger -- whose removal by T06-F14 rests on data A-2 discarded and which Zach's experience
says has always been needed. Per Zach: it does not matter which architecture is optimal,
only that one works, because this study is about formal verification.

## T06-F30  w3 mixed student: 24/24, all four conditions, 58% margin. A-1's re-entry condition is met.

Exploratory under A-1, one run per cell. Same teacher, same data, same input size; the
only change is student width, w2 (21,408 ReLU) -> w3 (24,48,48)/fc96, 32,112 ReLU.

    condition    w2 worst        w3 worst
    clear      6/6  1.51 ft    6/6  0.91 ft
    fog        5/6  8.52 ft    6/6  0.84 ft      fog/s00  8.52 -> 0.35 ft
    night      6/6  2.10 ft    6/6  0.54 ft      night/s05 2.10 -> 0.54 ft
    shadows    5/6  2.99 ft    6/6  0.52 ft      shadows/s02 2.99 -> 0.34 ft
               22/24           24/24             gate 2.19 ft

**Worst cell across all 24 is 0.91 ft against a 2.19 ft budget, a 58% margin.** The two
cells that failed at w2 improved by 24x and 9x. Distillation fidelity improved in step:
KD RMSE 0.0391 -> 0.0325, relative error 0.428 -> 0.356, R^2 0.82 -> 0.87.

For scale, published Town04's mixed student ranges 0.53-1.61 ft on the same budget. This
one is at least as comfortable.

That is the capacity hypothesis confirmed end to end: the teacher held the failing cells
at 0.37-0.49 ft (T06-F29), the student could not reproduce it at w2, and 50% more ReLU
closed the entire gap. It is also the conclusion Town04 reached independently at
`4b2ad73`, and the one Zach predicted from experience before any of this was measured.

### What this settles, and what it does not

**Settled: the mixed student needs to be wider than the clear one.** They are not matched
and there was never a reason for them to be. T06-F14's contrary finding is discarded with
its data.

**Not settled, and deliberately not pursued: whether w3 is optimal.** It is not being
swept further. Per Zach: it does not matter which architecture is optimal, only that one
works, because the study is about formal verification and the network is the object under
test, not the contribution. w3 works with margin and is well inside tractability
(T06-F12: 32,112 ReLU against ~11% UNKNOWN being the useful limit, since the binding
dimension is the 1-D disturbance family).

**Not needed: student DAgger.** Its removal by T06-F14 rests on discarded data and is
evidentially unsupported, and Zach's experience is that it has always been required. It
simply is not required here -- w3 reaches 24/24 with 58% margin distilled only. The stage
and its tooling (`pipeline/dagger_student.py`) remain available if a later result needs
it, and nothing in this build should be read as re-establishing F14's claim that it is
harmful.

**Not a rate.** Every number above is ONE run per cell, which standing rule 3 forbids
treating as a failure rate. It is triage that says where the student stands, and the
margin is wide enough that the ordering is not in doubt. The competence gate (3 reps) and
the scored ledger (>=10 reps) supply the rates.

### A-1 re-entry

A-1 suspended R1 with the re-entry condition: "R1 resumes when a mixed student drives
every condition." **A mixed student has now driven every condition.** So R1 is back in
force, and everything from here needs a fresh certificate committed before its drives. No
result in T06-F29 or F30 may be presented as a blind prediction; they are exploratory by
construction and are labelled so.

Next: re-run the clear-weather competence gate against the w3 checkpoint -- the existing
record is keyed to the w2 digest and the new guard correctly refuses it -- then capture,
certify blind, commit, and drive the scored ledger.

## T06-F31  TOWN06 DEPLOYMENT TEST RESULT: 4/6, and 3/3 on the cells that are actually blind

Certificate committed at `bfea31a` before any scored drive; `check_order_town06.py`
confirms R1. Ledger: 8 cells, 6 sections x 2 reps = 12 runs each.

    condition  student       driving              certificate      agreement
    clear      S_clear_t06   PASS  1/12 [1,35]%   CERTIFIED        vacuous
    clear      S_mixed_t06   PASS  0/12 [0,24]%   CERTIFIED        vacuous
    fog        S_clear_t06   FAIL 10/12 [55,95]%  NOT_CERTIFIED    AGREE
    fog        S_mixed_t06   PASS  0/12 [0,24]%   NOT_CERTIFIED    disagree
    night      S_clear_t06   FAIL 12/12 [76,100]% NOT_CERTIFIED    AGREE
    night      S_mixed_t06   PASS  0/12 [0,24]%   NOT_CERTIFIED    disagree
    low sun    S_clear_t06   FAIL 12/12 [76,100]% NOT_CERTIFIED    AGREE
    low sun    S_mixed_t06   PASS  0/12 [0,24]%   CERTIFIED        AGREE

### The headline number 4/6 mixes two kinds of cell and should not be quoted alone

**The three clear-only cells are genuinely blind.** Audited: before the certificate was
written at 23:16, the clear student appears in no log with any disturbance weather flag.
Its only closed-loop exposure was the clear-weather competence gate, which is the s=0
anchor by construction. The captures do not drive it either -- `capture_offset_yaw.py`
holds the brake and captures at teleported poses. **Those three cells agree 3/3.**

**The three mixed cells are NOT blind, and no claim may say otherwise.** T06-F29 and F30
drove the mixed student under fog, night and low sun at 21:34 and 21:58, before the
certificate at 23:16. `certify_town06.py` had no access to those results -- it has no truth
table and cannot print an agreement column -- so the certificate is not computationally
contaminated. But the decision to certify THIS checkpoint, at w3, was made using them.
**Those three cells agree 1/3.**

So the honest statement is **3/3 blind, 1/3 non-blind**, not "4/6". The repo already
declares a weaker version of this leak in PROTOCOL section 5 ("the clear-only cells are
the strong evidence and the mixed cells are the weaker"); this makes it concrete and
stronger than declared, because the mixed student was explicitly driven rather than merely
exposed through training.

### The comparison itself has a logical gap, and it is the interesting one

`certify_town06.py` runs alpha-CROWN **over the one-parameter disturbance family** with 16
branch-and-bound sub-intervals. `NOT_CERTIFIED` therefore means:

    THERE EXISTS an s in the family whose sustained-bias bound exceeds tolerance

The ledger drives **one point** of that family, the preset endpoint (fog_density 70,
sun -25, sun 5). So a NOT_CERTIFIED verdict does NOT predict failure at the preset, and a
preset drive that passes does not contradict it. The agreement column treats
NOT_CERTIFIED as "predicts FAIL here", which is a stronger claim than the certificate
makes.

For the clear student this did not matter -- it failed at the preset too. For the mixed
student it is the whole story: **fog/S_mixed and night/S_mixed may not be false alarms at
all.** They are statements about the family that a preset-only drive cannot test.

Completing the test therefore requires driving the s the certificate implicates, and the
s must be chosen BY RULE from the committed certificate rather than by searching for a
failure. That rule is registered in T06-F32 below, before the drive.

### Dispositions -- standing rule 2, three cells contradict the pre-registration

**D-T06-4  fog/S_clear_t06 drove FAIL 10/12; the pre-registration expected PASS.**
The certificate said NOT_CERTIFIED and was RIGHT; the prior was wrong. The
pre-registration carried Town04's D-14 forward -- "the clear-only student is genuinely
robust in fog on open road" -- and it did not transfer. Candidate causes not yet ruled
out: D-14 may be map-specific and was carried over without re-derivation; Town06 fog
renders against different geometry, 74-79% straight against Town04's 51-56%; and this is
a different clear student on different data. **This is the most favourable kind of
contradiction: the criterion beat the human prior on a genuinely blind cell.** It should
be reported as such and not buried.

**D-T06-5  fog/S_mixed_t06 drove PASS 0/12; certificate NOT_CERTIFIED.**
**D-T06-6  night/S_mixed_t06 drove PASS 0/12; certificate NOT_CERTIFIED.**
Both miss by little pooled -- 1.26x and 1.24x tolerance -- but by more per section: fog
peaks at 2.35x on s02, night at 2.16x on s05. Candidate causes, none yet ruled out:
  1. **The family/point mismatch above.** The most likely explanation and the one that is
     testable: the bound may be driven by an intermediate s the ledger never drove.
  2. **Bound looseness** at 32,112 ReLU. alpha-CROWN over-approximates, and 0/12 failures
     against a 2.35x bound means the over-approximation is at least that large if (1) is
     false.
  3. Not the route-mean averaging -- see the robustness check below, which rules it out.

### Robustness check on the criterion, and it passes

The bound is a route MEAN over scored poses, not a worst-case envelope, deliberately:
the criterion is a SUSTAINED bias, which is the paper's own thesis that a small persistent
bias walks the vehicle out of its lane while a large oscillating one integrates to
nothing. Per-section means therefore exceed the pooled mean, and a section-level sustained
bias could in principle be diluted by averaging over six sections.

Re-scored against the stricter reading -- worst SECTION rather than route mean:

    cell                    pooled xtol   worst section xtol   verdict        strict verdict
    S_clear_t06/fog                2.76                 4.51   NOT_CERTIFIED  NOT_CERTIFIED
    S_clear_t06/night             13.63                17.72   NOT_CERTIFIED  NOT_CERTIFIED
    S_clear_t06/shadows            1.79                 3.75   NOT_CERTIFIED  NOT_CERTIFIED
    S_mixed_t06/fog                1.26                 2.35   NOT_CERTIFIED  NOT_CERTIFIED
    S_mixed_t06/night              1.24                 2.16   NOT_CERTIFIED  NOT_CERTIFIED
    S_mixed_t06/shadows            0.27                 0.69   CERTIFIED      CERTIFIED

**No verdict changes.** The one CERTIFIED cell certifies under the stricter reading too,
with its worst section at 0.69x. So the averaging is a real limitation of the criterion in
principle and has no effect on this result, and the CERTIFIED verdict is not an artefact
of it. Worth stating explicitly because it is the first thing a reviewer should ask.

### Also recorded

clear/S_clear_t06 drove **1 failure in 12** in CLEAR weather, its own anchor condition,
having passed the competence gate 3/3 on every section. The interval [1,35]% includes low
rates and the cell is scored PASS, but it is not zero, and the certificate for that cell
is vacuous by construction (Delta_p = 0 at s=0). It belongs in the write-up as a measured
property of the anchor rather than being quietly dropped.

## T06-F32  THE INTERIOR RESULT: the mixed student passes both endpoints and fails between them

Exploratory under A-1. The certificate for `S_mixed_t06/fog` said NOT_CERTIFIED while the
scored ledger drove the fog PRESET and passed 0/12. The certificate quantifies over the
whole one-parameter family; the ledger drove one point of it. So the interior was the one
place neither had looked.

### The fog axis, mixed student w3

    fog density   sections failing        worst |CTE|      how measured
      0 (clear)   0/6                        ~1.5 ft       ledger, 0/12 failures
      17.5        4/6  (s01,s02,s03,s04)      8.56 ft       1 run per section
      35          1/6  (s02)                 11.57 ft       1 run per section
      52.5        0/6                         2.01 ft       1 run per section
     70 (preset)  0/6                         0.84 ft       ledger, 0/12 failures

**Both endpoints are clean and the interior is not.** Endpoint-only closed-loop testing --
which is what the ledger and the published Town04 study both do -- declares this policy
safe under fog. It is not.

### The failure is a rate, not a run

Sharpest cell, fog density 35 on s02, repeated on a freshly restarted server each time:

    FAILURE RATE 11/11 = 100%,  Wilson 95% CI [74, 100]%
    max|CTE| per run: 3.66  3.70  3.71  4.30  11.44  11.55  11.56  11.56  11.57  11.57  11.57
    budget 2.19 ft -- every run exceeded it; step counts 349 on all 11 (R-SIM-6 clean)

One rep was lost to a CARLA startup segfault and skipped rather than substituted.

The values are **bimodal** -- either ~3.7 ft or ~11.6 ft, nothing between. The closed-loop
system falls into one of two trajectories from a render-floor-sized perturbation, which is
D-10 again: the spread is largest where the margin is thinnest, and here it is not spread
but bifurcation.

### The certificate flagged the right SECTION, not just the right cell

`S_mixed_t06/fog` per-section bounds put **s02 worst at 2.35x tolerance**, ahead of s04
(2.24x), s05 (1.55x), s01 (1.54x). s02 is the section that fails at every interior density
tested, and the only one still failing at density 35. The correspondence is specific
rather than a general "something in this cell is wrong".

### What this does and does not establish

**Does:** a policy can pass both endpoints of a disturbance family 0/12 and fail its
interior 11/11; the certificate marked that cell NOT_CERTIFIED and its worst-bounded
section is the one that fails. That is the specificity evidence the deployment test needed
-- `TOWN06_STATUS.md` declared in advance that a uniform pass-and-certify outcome would
measure sensitivity only, and this is the opposite of that outcome.

It also reproduces, in the steering domain, what the AEB study found independently: a
camera-only policy that passes both FMVSS 127 lighting endpoints and is falsified by
certificate between them.

**Does not, and must not be claimed:** that the certificate *predicted this specific
failure*. The certified family is a pixel-space chord between two RENDERED endpoints,
`x0 + s(x1 - x0)`. A CARLA render at density 35 is not the pixel-wise midpoint of
densities 0 and 70, because fog is nonlinear in density -- so the rendered point tested
here lies off the certified chord by an unmeasured amount. `scripts/interpolation_fidelity.py`
exists to measure exactly that, its own docstring records that both blind reviewers raised
it, and **it has never been run on Town06**; its captures are from 2026-08-15, Town04-era,
pre-harness-fix, at 84x28 rather than 168x28.

Until it is run the defensible claim is the weaker one, which is still strong:

    the certificate marked the cell not certifiable; endpoint driving passed 0/12;
    interior driving fails 11/11 on the section the bound implicated most

Making it the stronger claim -- that the failure lies inside the certified set -- requires
the chord-vs-render agreement to be measured in STEERING terms on Town06. That is the next
experiment and it is cheap.

### Also open

The night axis has not been swept. It is not a clean analogue: `headlights_on()` switches
at sun altitude 0, so the clear-to-night family contains a discontinuity the pixel chord
does not model, and the family also passes through the low-sun preset at 5 degrees. Worth
doing, worth designing rather than just running.

## T06-F33  A SECOND interior failure, with a physical mechanism: the sun on the horizon

Exploratory under A-1. The clear->night family is a sun-altitude sweep, and **three points
on it are already measured and all pass**: clear (90 deg, ledger 0/12), low sun (5 deg,
0/12), night (-25 deg, 0/12). This drives the gaps.

    sun altitude   signature   frame mean   sections failing   worst |CTE|
      90 (clear)   clear          0.2983    0/6  (0/12 ledger)     ~1.5 ft
      45           'fog'          0.5740    3/6                    11.68 ft
      20           'fog'          0.5112    2/6                    10.68 ft
      10           'fog'          0.4652    3/6                    11.41 ft
       5 (low sun) shadows        0.1204    0/6  (0/12 ledger)      ~0.5 ft
       0           'shadows'      0.0910    6/6  ALL SECTIONS       10.23 ft
      -8           night          0.2058    1/6                     6.07 ft
     -16           night          0.2058    0/6                     0.97 ft
     -25 (night)   night          0.2125    0/6  (0/12 ledger)      ~0.54 ft

### Rate at the worst point

    sun altitude 0, section s00, fresh server per run
    FAILURE RATE 11/11 = 100%,  Wilson 95% CI [74, 100]%
    max|CTE| 10.48 - 10.82 ft against a 2.19 ft budget; steps 499 on every run

The spread is TIGHT, 0.34 ft across eleven runs, unlike the fog interior's bifurcation.
This is not a marginal policy occasionally falling over; it is a deterministic failure.

### It has a mechanism, and the mechanism is a switching threshold

`carla_env.headlights_on()` returns `sun_altitude_deg < 0.0`. At **exactly 0 degrees** the
sun contributes no direct illumination -- the frame mean is 0.0910, DARKER than the low-sun
preset at 0.1204 and darker than night at 0.2125 -- **and the headlights are still off**,
because 0 is not less than 0. It is the darkest lights-off condition the family can reach.

So the failure is not a quirk of the policy. It is a gap created by where the headlight
rule switches, and the policy is being asked to steer on almost no signal. Both immediate
neighbours pass: 5 degrees above (lights off, but brighter) and 8 degrees below (darker,
but lights ON). **The failure sits precisely in the notch between them.**

That is a genuine safety finding with a physical explanation rather than a number, and it
is the kind of thing endpoint testing cannot reach by construction.

### The methodological catch, stated plainly

**The rendered sun sweep is NOT monotone in image space, and the interior leaves the
range spanned by the endpoints in BOTH directions:**

    endpoint clear   0.2983
    interior 45 deg  0.5740   <- BRIGHTER than either endpoint (low sun ahead = glare)
    interior  0 deg  0.0910   <- DARKER  than either endpoint
    endpoint night   0.2125

The certified family is a pixel-space chord between 0.2983 and 0.2125. Neither excursion
lies on it. **So these interior failures are real, reproducible, physically meaningful
failures, and they are NOT points inside the certified set.** They must not be described
as failures the certificate bounded.

This also qualifies a claim the study currently makes. `_sun_override`'s docstring says
clear, shadows and night "are not separate phenomena -- they are sun_altitude_angle 90, 15
and -25 of one continuous physical parameter", and treats sweeping it as turning a
three-point comparison into a curve. The PARAMETER is continuous; the rendered images
along it are not monotone, and a straight line between two of them does not pass through
what the simulator actually renders in between. That is worth stating in the paper rather
than being found by a reviewer.

Minor, and worth a look: sun -8 and -16 produce IDENTICAL signatures to four decimals
(mean 0.2058, sigma 0.1469). CARLA appears to clamp illumination once the sun is below the
horizon, which would make the family degenerate below 0 and is easy to confirm.

### What the two interior results support, together

Fog (T06-F32) and sun altitude (here) are independent axes, and both show the same shape:

    axis      endpoints driven          interior driven
    fog       0 and 70:  0/12, 0/12     density 35:      11/11 FAIL
    sun       90, 5, -25: 0/12 each     altitude 0 deg:  11/11 FAIL

**A policy that passes every endpoint of every disturbance axis, 0/12 each, fails 100% of
runs at interior points of two different axes.** Formal verification declined to certify
four of those six cells. Endpoint closed-loop testing passed all of them.

The honest and sufficient claim is therefore:

    verification withheld the certificate; endpoint driving said the policy was fine;
    driving the physically reachable interior found 100% failure rates on two
    independent axes.

That stands without needing the failures to lie inside the certified chord, and it is the
argument for verification: the endpoints are where testing looks, and they are not where
this policy breaks.

## T06-F34  INTERPOLATION FIDELITY on Town06: the chord UNDERSTATES the real condition

> **SCOPE DEFECT, 2026-08-30 — this finding is under re-measurement.** The captures behind
> it cover **81 poses over 160 m** (`results/diagnostic/interpolation_fidelity.json`,
> `n_poses: 81`), inherited from `capture_offset_yaw.py --length-m`'s 160 m default, and
> they cover **one section**, which is at most 23% of Town06's 3,834 m of scored road. The
> fidelity measurement validates the DISTURBANCE FAMILY that every certified bound is
> quantified over, so a narrow measurement here narrows every downstream claim at once
> while the JSON still reads as complete. Being re-measured across all six sections with
> `scripts/capture_interp_fidelity.sh`; the analysis now refuses a short capture and records
> `sections`, `poses_per_section` and `route_span_m`. Same root cause as the Town04 160 m
> defect — see standing rules 7 and 8.


The test both blind reviewers asked for, never before run on Town06. Fresh captures under
the corrected harness at the students' resolution, fog densities 17.5 / 35 / 52.5 / 70,
clear and fog in the same file so the chord's endpoints are same-session (F43/F44: a
cross-session baseline once inverted the sign of a fog measurement). 81 poses on s02.
`scripts/interpolation_fidelity.py`, made map-aware -- it was hardcoded to Town04's
students and 28x84 input and would otherwise have loaded the wrong checkpoints silently.

Each rendered intermediate is projected onto its pose's chord to find the s it corresponds
to, then chord and render are compared where it matters -- what the POLICY does.

    density   s*      pixel err    S_clear steer err        S_mixed steer err
     17.5    0.262     0.0212     -0.0094  (-0.78x tol)    -0.0449  (-3.74x tol)
     35.0    0.615     0.0088     -0.0016  (-0.14x tol)    +0.0065  (+0.54x tol)
     52.5    0.990     0.0132     +0.0006  (+0.05x tol)    -0.0019  (-0.16x tol)

**Fog saturates.** Density 52.5 already projects to s* = 0.99 -- in image space it is
essentially the full-fog endpoint. The physical parameter maps very non-linearly onto the
chord, so equal steps in density are nothing like equal steps in s.

### The clear student: the chord is faithful

Steering error 0.05-0.78x tolerance against an s=1 bias of 2.89x, and chord/render bias
ratios 0.67, 0.96, 1.02. For this policy the chord's interior behaves like a real render
and the coverage claim holds.

### The mixed student at low density: the chord is NOT faithful, and it is OPTIMISTIC

    density 17.5:  bias from the REAL RENDER   +0.04758  =  3.96x tolerance
                   bias from the CHORD point   +0.00267  =  0.22x tolerance
                   ratio chord/render            0.056    -- the render drives the policy
                                                             ~18x HARDER than the chord

The steering error at that point, -3.74x tolerance, is **thirteen times the cell's entire
s=1 bias** (-0.28x). The interior of the certified family, at that end, is a pixel
construct that does not behave like the condition it is supposed to stand for.

**And it errs on the optimistic side.** This is the opposite failure to the analytic
Koschmieder model, which drove the policy 23.8x HARDER than reality and was rejected for
it. A chord that is gentler than reality does not produce false alarms; it produces
**missed ones**.

### What this settles, and it settles T06-F32 cleanly

T06-F32 recorded that the mixed student fails 11/11 at fog density 35 and said the failure
"is not inside the certified set". This quantifies why: at the low-density end the real
condition induces a lap-mean bias of **3.96x tolerance** while the certified chord induces
**0.22x**. The certificate bounded the gentler object. The closed-loop failure is real,
the certificate's NOT_CERTIFIED on that cell is right, and the mechanism is now measured
rather than asserted.

Note what that does to the argument, which is stronger rather than weaker: **verification
flagged the cell while modelling a disturbance three times gentler than the real one.**
The flag survived the understatement.

### The limitation this creates, and it must be in the paper

An optimistic family model is a soundness risk for **CERTIFIED** verdicts specifically. A
cell can certify because the chord is mild where the real condition is not. This test was
run on the fog axis only; **`S_mixed_t06/shadows`, the one CERTIFIED cell in the whole
deployment test, has not had its family's fidelity checked.** Doing so is the obvious next
measurement and it is cheap -- the same capture-and-project procedure on the sun-altitude
axis.

The honest scope for the coverage claim, as the script's own guidance puts it: small
steering error means the chord is behaviourally faithful and the claim holds; comparable
means the interior is a pixel construct and the claim must be scoped to the endpoints.
**On Town06 the answer differs by policy** -- faithful for the clear student, not faithful
for the mixed student at low fog density -- so the claim must be scoped per cell rather
than made once for the family.

Caveat on this measurement itself: 81 poses, section s02 only, fog axis only. It is enough
to show the chord is not uniformly faithful; it is not enough to characterise the whole
route.

## T06-F35  CORRECTION to T06-F33: the sun sweep used the wrong exposure. Most of it is withdrawn.

Zach's scoping prompted the check that found this. **"Low sun" is a uniform DARKENING with
headlights off** -- a single-axis disturbance that is easy to model, which is why the study
calls it low sun and not shadows. Sideways sun casts shadows ON the road, a different
disturbance, modelled differently and out of scope at this stage.

Checking whether the T06-F33 sweep had strayed into cast shadows turned up a bigger
problem.

### The error

T06-F33 swept sun altitude with `--weather night`. `evaluate.py` applies the condition's
DECLARED EXPOSURE, and night's is shutter 200 against daylight's 800 -- a 4x difference.
**The sweep therefore rendered daylight scenes through a night camera.** Measured at s02:

    sun    daylight exposure (800)     night exposure (200)
      0    mean 0.0081                 mean 0.1150
      5    mean 0.1155  <- the preset  mean 0.3922   reads as 'clear'
     10    mean 0.1574                 mean 0.4501   reads as 'clear'
     20    mean 0.1911                 mean 0.4904   reads as 'clear'

The 5-45 degree points in T06-F33 were massively overexposed. They are not operating
points on any family and their failures are an artefact of the wrong camera setting.

### What is WITHDRAWN from T06-F33

  - The failures at sun 45, 20 and 10 degrees (3/6, 2/6, 3/6). Artefact.
  - **The claim that the sun axis is non-monotone in image space and "leaves the endpoint
    range in BOTH directions" (0.5740 at 45 degrees).** That was the night exposure, not
    the scene. Under the correct daylight exposure the axis is MONOTONE and well behaved:
    mean 0.0032 / 0.0366 / 0.1155 / 0.1705 / 0.1913 at sun 0 / 2 / 5 / 10 / 15, with sigma
    rising smoothly 0.0059 -> 0.0633 and no contrast blow-up.
  - The consequent claim that the study's "one continuous physical parameter" framing is
    misleading about the rendered path. On this axis, correctly exposed, it is fine.

This also removes the basis for the corresponding limitation in the arXiv staging
document, which is corrected there.

### What SURVIVES, re-measured correctly

Swept with `--weather shadows`, i.e. the daylight exposure low sun is defined under:

    sun    mean     sigma    sections failing   steps        note
      0   0.0032   0.0059    6/6                17-67   DEGENERATE, see below
      2   0.0366   0.0198    3/6                full     s00 6.36, s02 7.78, s04 6.23 ft
      5   0.1155   0.0374    0/6                full     the preset; ledger 0/12
     10   0.1705   0.0580    0/6                full
     15   0.1913   0.0633    0/6                full

**Sun 0 is degenerate and is not a result.** The frame mean is 0.0032 -- a black image --
and the runs end after 17 to 67 steps against normal lengths of 274 to 499. R-SIM-6 says a
run ending in a handful of steps is a bug rather than a verdict; here they are genuine
immediate departures with 30-51 ft of CTE rather than false passes, but a policy given no
input at all is not an interesting measurement. It is reported as degenerate, not as a
failure of the policy.

**Sun 2 degrees is the real finding.** Full-length runs, 3 of 6 sections over budget, and
sigma 0.0198 is LOWER than the 5 degree preset's 0.0374 -- so there is no cast-shadow
component. It is squarely inside the low-sun class as Zach defines it: uniform darkening,
headlights off.

So the surviving statement is narrower than T06-F33's and still holds the shape that
matters: **the policy is tested at low sun 5 degrees and passes 0/12; at 2 degrees -- a
marginally lower sun, same disturbance class, same exposure, no shadows -- it fails half
its sections.** Both 10 and 15 degrees pass cleanly, so the failure is a band just below
the tested condition rather than a general low-light weakness.

### Why this was worth catching

Nothing in the T06-F33 numbers looked wrong. The runs completed, the CTEs were plausible,
the step counts were normal, and the condition-signature line printed a value rather than
raising -- because the override path deliberately skips the preset assert. An exposure
mismatch produces a perfectly well-formed result that means something else. It is the same
class as the Town04 fog-into-night leak and the degraded-server episode, and the same
lesson: **a plausible number is not a checked one.**

The concrete gap: `evaluate.py`'s override path prints the rendered signature but nothing
compares it against what the condition is supposed to look like. At sun 5 with night
exposure the signature said `clear` while the run was labelled `shadows`, and that
disagreement was printed and ignored. Worth a warning at minimum.

## T06-F36  The clear-only student's failure ONSET is very early, which is what its bound said

The clear-only student already fails at every disturbance endpoint (fog 83 %, night 100 %,
low sun 100 %), so an interior sweep is not looking for a hidden failure. The informative
question is the **onset**: how little disturbance does it take? That is what a bound of
2.76x / 13.63x / 1.79x tolerance is a claim about.

Exploratory, one run per section, correct per-condition exposure on both axes.

    FOG (preset density 70)              LOW SUN (clear 90 deg -> preset 5 deg)
    density   sections failing            sun     sections failing
       5      1/6  (s02 3.56 ft)           60      0/6
      10      1/6  (s02 11.05 ft)          45      1/6  (s00 10.75 ft)
      17.5    2/6  (s02, s04 ~11.7 ft)     30      2/6  (s00 10.63, s05 2.73 ft)
      70      10/12 = 83 %  (ledger)        5      12/12 = 100 %  (ledger)

**Fog onset is density 5 of 70 — seven percent of the preset intensity.** **Low-sun onset
is 45 degrees, barely darkened from the 90-degree clear baseline.** A policy trained only
on clear weather departs its lane at a fog a person would struggle to notice.

That is the behaviour its certificate described. The three clear-only cells carry the
largest bounds in the study, and night's 13.63x tolerance is the largest of all -- these
are not marginal calls near the threshold, and the closed loop agrees: the policy is
fragile from the first perceptible disturbance.

s02 is again the first section to go on the fog axis, as it was for the mixed student and
as the certificate's per-section bounds ranked it.

### Why this matters to the argument

The interior results so far (T06-F32, F35) show a policy passing endpoints and failing
between them, which is the case for verification over a family rather than at test points.
This is the complementary case: **where a policy is genuinely fragile, the certificate's
bound is correspondingly large, and the fragility begins almost immediately.** The bound
magnitude carries information, not just its side of the threshold.

## T06-F37  The CERTIFIED cell's family IS faithful — the soundness gap from T06-F34 is closed

> **SCOPE DEFECT, 2026-08-30 — this finding is under re-measurement.** The captures behind
> it cover **81 poses over 160 m** (`results/diagnostic/interpolation_fidelity.json`,
> `n_poses: 81`), inherited from `capture_offset_yaw.py --length-m`'s 160 m default, and
> they cover **one section**, which is at most 23% of Town06's 3,834 m of scored road. The
> fidelity measurement validates the DISTURBANCE FAMILY that every certified bound is
> quantified over, so a narrow measurement here narrows every downstream claim at once
> while the JSON still reads as complete. Being re-measured across all six sections with
> `scripts/capture_interp_fidelity.sh`; the analysis now refuses a short capture and records
> `sections`, `poses_per_section` and `route_span_m`. Same root cause as the Town04 160 m
> defect — see standing rules 7 and 8.


T06-F34 found the fog chord optimistic for the mixed student and flagged the consequence:
an optimistic family threatens **CERTIFIED** verdicts specifically, and
`S_mixed_t06/shadows` — the only CERTIFIED cell in the deployment test — had never had its
family checked. This checks it.

`scripts/interpolation_fidelity.py` is now axis-parameterised (`--axis fog|lowsun`) rather
than hardcoded to fog. Re-running the fog axis after the refactor reproduces its numbers
exactly, which is the regression check that the generalisation changed nothing.

### A prerequisite fix: the two overrides were inconsistently scoped

`_density_override` applies only to `fog`, so a fog sweep leaves the clear baseline alone.
`_sun_override` applied to **every** condition, so a sun sweep moved clear too. That is
fatal for a fidelity capture, which must hold an unperturbed clear baseline and a
perturbed condition in ONE session: without the fix the chord's origin moves with its
endpoint and the projection is meaningless. `_sun_override` is now scoped to skip `clear`,
mirroring the fog path. Verified: under `SUN_ALTITUDE_OVERRIDE=30`, clear stays at 90 while
shadows and night follow; with no override every preset is unchanged.

`clear` is the s = 0 anchor of every disturbance family here. It is not a point to sweep;
it is what the sweep is measured against.

### Result — low-sun axis (clear 90 deg -> low sun 5 deg, daylight exposure at both ends)

    S_mixed_t06   (lap-mean bias at s=1: -0.00210 = -0.17x tol)
      sun deg    s*     pixel err   steer err    x tol
        60      0.083    0.00306    +0.00001    +0.00
        30      0.374    0.00792    -0.00062    -0.05
        15      0.666    0.00927    -0.00202    -0.17

    S_clear_t06   (lap-mean bias at s=1: +0.01018 = +0.85x tol)
        60      0.083    0.00306    +0.00246    +0.20
        30      0.374    0.00792    +0.00319    +0.27
        15      0.666    0.00927    +0.00482    +0.40

**For the mixed student every interior steering error is at most 0.17x tolerance**, and
pixel errors are 0.003-0.009 — a third of the fog axis's. The chord's interior behaves
like the real render. **The CERTIFIED verdict on `S_mixed_t06/shadows` is not resting on
an optimistic family model, and it stands.**

The s = 1 bias measured here (-0.00210, 81 poses on s02) sits inside the certificate's
route-pooled bound for that cell (-0.00327 to +0.00209 over 243 poses), which is a
consistency check on both.

For the clear student the chord understates by more (ratios 0.16-0.36) but the absolute
errors stay under half a tolerance, and that cell is NOT_CERTIFIED regardless, so nothing
rests on it.

### Why the two axes differ, and it is not arbitrary

Fog is nonlinear in density and saturates — density 52.5 already projects to s* = 0.99,
so most of the chord's parameter range is spent on a narrow band of physical densities and
the low-density end is poorly represented. The low-sun axis is a near-uniform darkening:
s* runs 0.083 / 0.374 / 0.666 for 60 / 30 / 15 degrees, spreading smoothly across the
chord, and both endpoints share the daylight exposure. **A chord is a good model of a
family that is close to linear in image space and a poor one where the physics saturates.**
That is a per-axis property, so fidelity has to be measured per axis rather than assumed
from one.

### Standing scope for the coverage claim

  - `S_mixed_t06/shadows` — CERTIFIED, family faithful. Claim holds.
  - fog cells — chord optimistic at the low-density end; NOT_CERTIFIED verdicts are
    unaffected (an optimistic family cannot manufacture a false alarm), and the interior
    failures at density 17.5-35 are outside the certified set.
  - `night` cells — not measured. Both endpoints of that family carry DIFFERENT exposures
    (daylight 800 vs night 200), so a pixel chord between them interpolates an exposure
    change as well as a lighting change. That is a harder object to justify and is left
    open rather than asserted.

## T06-F38  Cross-study: the steering dusk band is under 3 degrees; AEB's is 25.5

The AEB study found a dusk failure independently (`formal-verification--aeb--code` F4):
Property S falsified in a **single contiguous band from +25.899 to +0.360 degrees**, 25.5
degrees of dusk between the two FMVSS 127 regulatory endpoints, certified only at the
extremes. Its lead campaign's band was 10.8 degrees.

This study's low-sun result has the same shape. Bracketing it:

    sun     verdict                     evidence
     15     0/6 pass                    1 run per section
     10     0/6 pass                    1 run per section
      5     0/12 pass (LEDGER)          the trained low-sun condition
      4     0/6 pass, max 0.67 ft       1 run per section
      3     0/6 pass, max 0.86 ft       1 run per section
      2     12/12 FAIL, 8.11-8.48 ft    Wilson [76,100]%
      0     degenerate (black image)    runs end in 17-67 steps

**The steering dusk band is under 3 degrees wide** — clean at 3, failing at 2 — against
AEB's 25.5.

### The comparison is real but the two numbers are NOT the same object

AEB's 25.5 degrees is the band where a **certificate is falsified**; its witness drives
(M7) were still queued at F4. This study's band is where **driving fails**, measured as a
rate. A falsified band is an upper bound on what driving would show, so quoting 25.5
against <3 as if they were the same measurement would be wrong, and the paper must not.

What IS comparable, and is the point: **both studies find that the interval between tested
illuminations contains a failure that testing at the endpoints cannot see** — AEB by
certificate between two regulatory conditions, this study by driving between clear and its
trained low-sun condition.

### A candidate explanation, offered as a hypothesis and not a result

The band widths track how close the nearest TRAINED illumination is. The mixed steering
student trains on low sun at 5 degrees and fails only in a narrow band just below it. The
AEB `P_pts` policy trains on the two regulatory endpoints with nothing between, and its
falsified band spans essentially the whole interior.

That would say the failure is not "dusk is hard" but "the untrained interval is hard, and
its width is the width of the untrained interval." It is consistent with both results and
with Zach's own reading -- one model handles dusk untrained and another does not -- and it
is **not tested**. Testing it needs a steering student trained WITHOUT the low-sun
condition, whose band should then widen towards clear. The clear-only student is nearly
that experiment and it fails from 45 degrees downward (T06-F36), which is suggestive and
not conclusive, since it also lacks fog and night.

Two further reasons to hold it loosely: the tasks differ (lateral control against
longitudinal braking, different hazards and budgets), and the 3 and 4 degree points here
are single runs per section rather than rates -- though at 0.16-0.86 ft against a 2.19 ft
budget they are nowhere near the cliff.

---

## T06-F39  What the R-SIM-1 violation actually cost: negligible in the mean, 1.4x tol in a frame

`capture_town06_laps.sh` took all 24 Town06 verification captures in ONE server session
with no restarts, while its Town04 sibling restarted before every capture. R-SIM-1 says
restart before every measurement; the rule lived in prose and was re-typed into each
driver, so it drifted the moment a second driver existed. Found 2026-08-30 by auditing
every measurement path rather than by anything in a result.

The captures were recaptured with a restart before each. Because the pose sampling is
deterministic, the two sets are pose-identical and the difference is purely rendering,
which makes the cost directly measurable rather than a matter of judgement.

**Pixels (s00, normalised):**

    clear    mean|d| 0.00081   max 0.0667
    fog      mean|d| 0.00084   max 0.0257
    night    mean|d| 0.00173   max 0.0276
    shadows  mean|d| 0.00189   max 0.0280

**Steering, against the 0.012011 tolerance:**

    S_clear_t06  clear    mean -0.01x tol    max |d| 0.41x tol
    S_clear_t06  night    mean +0.04x tol    max |d| 1.39x tol
    S_mixed_t06  clear    mean -0.01x tol    max |d| 0.29x tol
    S_mixed_t06  night    mean -0.02x tol    max |d| 1.38x tol

**Read it both ways, because it cuts both ways.** The criterion is a route-MEAN sustained
bias, and the mean shift is 1-4% of tolerance, so the certificate's verdicts are very
unlikely to move — the old captures were not badly wrong. But an individual frame moves by
up to **1.4x the entire tolerance**, which is not noise: it is larger than the whole safety
margin at that pose. A per-frame claim built on those captures would have been unsound
while the route-mean claim was fine.

That distinction is the value of the number. "It was probably fine" and "the mean moved 1%
while the worst frame moved 139%" are different statements, and only the second says which
claims survive.

**Why this is a finding and not a footnote.** Both this and the 160 m capture defect are
the same disease: a rule that each new script must remember. The fix is not diligence, it
is placement — `require_deterministic()` and the session-hygiene checks now run inside
`enable_sync_mode` and `spawn_vehicle`, the choke points every measurement passes through,
and in the `carla-determinism` package (>= 1.1) so AEB and multi-condition inherit them
rather than copying them. Six audit checks fail the build if a driver bypasses them.


### Addendum: s05's elevated gate value is the SECTION, not server age (predicted, then tested)

The pre-rebuild capture gate read 0.0244 / 0.0236 at s05 against ~0.010 everywhere else,
in both students. s05 was also the LAST section captured in the non-compliant single-session
run, so server ageing was the obvious suspect.

Prediction recorded before the rebuilt gate ran: s05 would stay near 0.024, because its
recaptured frames differ from the old ones by no more than s00's do (mean |d| 0.00073 at
s05 against 0.00081 at s00). If ageing were the cause, the last-captured section should
have moved MOST on recapture.

Result on captures taken with a fresh server before each:

    S_clear_t06  s05   0.0261   (was 0.0244)
    S_mixed_t06  s05   0.0228   (was 0.0236)

Unchanged. **s05 is intrinsically harder ground for capture-to-driving agreement**, and
the old captures were not degraded there. It is the shortest section (490 m), it carries
the widest certified bounds of the six, and it now shows the largest capture-driven
disagreement -- three independent signals on the same section, worth remembering before
anything is concluded from s05 alone.

This also settles the honest reading of the rebuild: it was correct under the standing
rule -- captures taken in violation of R-SIM-1 are suspect by definition, and the worst
frame moved 1.39x tolerance -- but the evidence now says the original captures were
probably sound. The rebuild turned "probably" into "measured", which is the only form
that belongs in a paper.

---

## T06-F41  The conditions were calibrated on the six-section route and did not move with the lap

Zach's read, before any of this was measured: "This route I think is easier than Town04 so
not converging says to me that there is a bug." He was right, and the bug is not in code.

The mixed teacher's gate laps localise the failure completely:

    clear     20/29 laps passed
    low sun   15/27
    fog        3/29
    night      0/29        <- never once, in 29 laps

Night has never passed. That is not slow convergence.

### What was ruled out first

* **Train/test rendering mismatch.** Every driving loop -- collection, teacher DAgger,
  student DAgger, evaluate, the gate and the ledger -- goes through `env.set_condition`,
  which respawns the camera with the condition's declared exposure. Measured on the
  frames themselves, the expert's view and the policy's view agree to four decimals:

        clear   BC 0.2074 +/- 0.0040   DAgger 0.2075 +/- 0.0040
        fog     BC 0.3095              DAgger 0.3094
        night   BC 0.0759 +/- 0.0154   DAgger 0.0758 +/- 0.0153
        low sun BC 0.0649              DAgger 0.0667

* **Headlights.** `set_condition` passes the vehicle, so `headlights_on(alt < 0)` fires at
  night. The night frames carry the headlight cone's variance (sigma 0.0154) against low
  sun's flat 0.0012, so the lights are on.

* **The sun in frame.** Real -- sun azimuth 0 at 5 degrees elevation, and 504 of 1,146 lap
  steps head into azimuth 0 (44% of the route). But `preprocess_for_model` crops sky and
  hood, and the blown-pixel fraction of the network's input under low sun is 0.0002. The
  glare Zach saw in the viewport does not reach the network directly. It still backlights
  the scene, which is part of what follows.

### The measurement

Identical preprocessing, identical camera, crop and exposure (git confirms none of them
changed between the two collections), both collected under the corrected harness after
A-2. The ONLY difference is the route:

    cond       six-section       lap          change
    clear        0.2624        0.2054        -21.7%
    fog          0.3295        0.3044         -7.6%
    night        0.1153        0.0765        -33.7%
    low sun      0.1053        0.0654        -37.8%

**The lap route is darker than the six-section route in every condition, and night and low
sun are hit twice as hard as clear.** T06-F20 chose Town06's 5 degrees to make low sun's
rendered outcome match Town04's, and night's shutter of 200 was chosen to place night at a
particular ratio to clear. Both were calibrated on the six-section route. The route changed
under them and the constants did not move.

Against the calibration targets, on the lap:

    low sun / clear   0.300   (T06-F20 target 0.410, Town04 0.463)
    night   / clear   0.373   (intended ~0.69)

Night on Town06's lap is roughly half as bright, relative to its own clear, as the night
the criterion was calibrated against. A deployment test whose night is twice as dark as
the discovery study's night is not comparing like with like, and the 0/29 says so.

### Why this follows T06-F20's own rule rather than contradicting it

T06-F20 states it directly: "LOW SUN IS DECLARED BY ITS RENDERED OUTCOME, NOT BY ITS SUN
ANGLE ... the angle is MAP-SPECIFIC and the CONDITION is what is held fixed." A route
change inside a map is the same kind of change as a map change. The rule already says what
to do; nobody applied it when the route moved.

### What it costs

Re-deriving the angle and night's exposure changes the rendered conditions, and A-2/D-11
say data collected under a superseded rendering is not reusable. The mixed teacher's 64,946
frames were collected under the current constants and would have to be recollected. That is
the honest price, and it is smaller than certifying a night the study cannot compare to
Town04's.

Not acted on: re-deriving a frozen-section condition is Zach's call.

## T06-F42  THE BLOCKER: the server rendered 15% darker for half a day, and both teachers trained on it. T06-F41 is WITHDRAWN.

The mixed teacher would not converge on the lap route -- night 0/29 gate laps, fog 3/29 --
and T06-F41 concluded the lap route renders darker than the six-section route the
conditions were calibrated on, so the condition constants had to be re-derived. That
conclusion is wrong. The route is fine, the constants are fine, and the frozen section of
PROTOCOL.md does not move.

### What is actually true

`pipeline/data/dagger_clear_t06lap` contains TWO RENDERINGS of the same road under the
same declared condition, aggregated into one training set:

    round00-05   (07:55-13:21)   clear mean 0.2508 - 0.2537
    round06-14   (14:10-16:23)   clear mean 0.2140 - 0.2141

`dagger_mixed_t06lap` is interleaved rather than split -- rounds 00,01,02,04,06,07,08,09
dark; rounds 03,05,10,11,12,13 bright. Both BC sets, which seed both teachers, are dark:
`clear_t06lap` 0.2136, `mixed_t06lap` 0.2147. A collection run on 2026-09-02 with
unchanged code produces 0.2526.

At matched poses the two renderings are the same picture at a different exposure. Round05
against round06, same step indices, vehicle within 0.5 m:

    idx     pose                       round05   round06   ratio
       0    (656.9, 15.4)                43.16     36.22   0.839
     200    (314.9,-17.2)                41.40     34.37   0.830
     600    (-362.9, 61.7)               44.95     38.98   0.867
    1000    (190.1, 241.2)               41.00     34.53   0.842

Per-pixel on lit pixels the ratio is 0.830 with median 0.831 -- a photometric gain, flat
across the tonal range, with identical geometry, identical content and no LOD difference.

### Why this is the blocker, and not a subtlety

Every Town06 lap teacher was trained on frames systematically darker than the frames it is
scored on. That is a train/test shift in the images themselves -- the same class of defect
as A-2's texture streaming, and the reason A-2 forced RECOLLECTION rather than
re-evaluation.

It also predicts the failure pattern exactly. Clear has the most headroom and passed
throughout (20/29). Night and low sun sit where a 15% gain matters most, and they are what
never passed. And the gate results track the rendering round by round: the mixed teacher's
gate went 0/12, 2/12, 3/12 through the dark rounds and reached 6/12 at rounds 10-13, which
are precisely the four consecutive BRIGHT rounds. Round 13 passed every lap it was given --
clear 0.85/0.74 ft, fog 0.44, night 0.96, low sun 1.53, against a 2.19 ft budget -- and was
stopped by an infrastructure failure, not by a policy failure.

Zach's read before any of this was measured -- "this route I think is easier than Town04 so
not converging says to me that there is a bug" -- was right, and T06-F41 agreed with him
for the wrong reason.

### Why nothing caught it

Three checks were green throughout and none of them looks at brightness:

* the determinism preflight verifies HOW THE SERVER WAS LAUNCHED (`/proc` argv, D-1..D-11);
* `verify_condition()` reads the WEATHER STRUCT back after the tick lands;
* `condition_signature.identify()` asserts the condition CLASSIFIES as itself, and a
  uniform 0.84 gain does not move night's sigma or fog's p01 across a threshold.

A 15% photometric drift passes all three, and nothing downstream of the frames can reveal
it. This is R-SIM-4's own argument -- "the struct is what was asked for, not what the
camera sees" -- one level deeper: the classifier is what the camera saw, not how bright it
saw it.

**Fixed by `scripts/check_render_photometry.py`,** run from `carla_launch.sh` on every
fresh server. A fixed camera transform at the study spawn, no vehicle and no physics, so
only the render path can move it; ~2 s. Reproducibility across fresh servers is 0.001%,
and headless against windowed on a full driven lap is 4e-5, so the 1% gate is ~250x the
noise floor and ~15x below the drift it exists to catch. A map with no recorded reference
prints `photometry NOT CHECKED` on every launch rather than passing quietly.

The cause of the drift itself is NOT identified. It is not the code (no exposure, camera
or weather constant changed in git across the flip), not headless-vs-windowed (measured
identical, below), and not quality or texture streaming (those change content, and the
content is identical). It flipped twice in one day on one machine. That is exactly why the
guard measures the OUTCOME rather than any suspected cause.

### What T06-F41 got wrong, mechanically

F41 compared the SIX-SECTION dataset's frame means against the LAP dataset's frame means
and attributed the difference to the route. The six-section sets were collected 2026-08-28
(bright); the lap sets 2026-09-01 (dark). The comparison measured the render drift and
named it the route.

Driving one instrument over the lap does not reproduce F41's numbers. A pure-pursuit lap,
clean server each, `scripts/measure_lap_condition.py`:

| | F41 claimed (lap) | measured, driven | six-section reference |
|---|---|---|---|
| clear | 0.2054 | 0.2525 | 0.2528 |
| fog | 0.3044 | 0.3365 | 0.3361 |
| night | 0.0765 | 0.1008 | 0.1031 |
| low sun | 0.0654 | 0.1045 | 0.1037 |

A driven lap of the LAP route reproduces the SIX-SECTION dataset to within 0.4%. The route
did not get darker. The collection did.

### The conditions HOLD on the lap. No constant moves.

Measured on the STUDENT's view -- rows 240:450 at 168x28, which is the view
`condition_signature`'s thresholds were derived on and the view `evaluate.py` asserts.
(The teacher's view crops 180:400 and keeps ~60 rows of sky; on this lap the sky renders
black, so CLEAR carries 12% dead pixels and sigma 0.123 there and "classifies as night".
That is a fact about which crop you measure, not about the condition, and it is why three
mutually inconsistent brightness tables accumulated in this repo.)

| condition | mean | sigma | p01 | dark | classifies as itself |
|---|---|---|---|---|---|
| clear | 0.3064 | 0.0616 | 0.0641 | 0.009 | 97.2% |
| fog | 0.2840 | 0.0610 | 0.1855 | 0.000 | 100% |
| night | 0.1844 | 0.1393 | 0.0002 | 0.216 | 100% |
| low sun | 0.1264 | 0.0389 | 0.0111 | 0.042 | 100% |

Against the thresholds, with margin on every discriminator: night's sigma 0.1393 against
0.100 with no other condition above 0.062; fog's p01 0.1855 against 0.120 with no other
above 0.064; clear's mean 0.3064 against 0.250 with low sun at 0.1264. The 2.8% of clear
frames that misclassify are mid-lap; the assert fires once per run on the fixed spawn
frame, which is deterministic and classifies correctly, so it cannot abort runs at random.

Against A-2's re-derivation on the six sections (low sun 0.1204, night - low sun 0.0921):

* **low sun 0.1264 is 5.0% from A-2's 0.1204.** T06-F20 accepted 9%. The 5-degree angle
  HOLDS on the lap, and A-2's re-derivation clause is satisfied a second time.
* **night 0.1844 sits 0.0580 above low sun.** Narrower than the six sections' 0.0921 and
  than Town04's 0.0958, and it is a declared route difference rather than a defect: the
  axis stays ORDERED and both ends classify as themselves 100% of the time, which is the
  property T06-F20 required and the property whose loss would have collapsed the axis.

So the night shutter does not move, the low-sun angle does not move, PROTOCOL section 3 is
untouched and `PROTOCOL.lock` is unchanged. **F41's proposed re-derivation is withdrawn
before it was acted on**, which is the only reason this costs nothing: F41 recorded it as
"not acted on: re-deriving a frozen-section condition is Zach's call", and that was right.

### Headless is measured, not assumed

Windowed CARLA will not start in the session running this rebuild (SDL init fails, empty
log, rc=1), so the rebuild runs `-RenderOffScreen`. That is a harness change and it is
measured rather than declared safe. The same pure-pursuit clear lap, windowed on 09-01
against headless on 09-02:

    windowed   mean 0.2525015   std 0.0119831   sun-in-FOV 44.13%   n=639
    headless   mean 0.2524913   std 0.0119834   sun-in-FOV 44.13%   n=639

4e-5 relative, with identical sample count and identical sun-in-FOV fraction, so the
trajectory is the same to the sampling resolution. This is far below the D-7 render floor
and it is what licenses the photometry gate's 1% tolerance. Standing rule 6 asks for a
windowed server so runs can be watched; that is not available here and the deviation is
recorded rather than silently taken.

### What it invalidates

Every Town06 LAP artifact produced by driving: `clear_t06lap`, `mixed_t06lap`,
`dagger_clear_t06lap`, `dagger_mixed_t06lap`, and every `teacher_*_t06lap_*` checkpoint.
Under A-2's own reasoning these are not re-evaluable, only recollectable. Nothing is
contaminated downstream: no lap certificate exists and no lap cell has been scored.

The six-section era (2026-08-28) is unaffected by this defect and is superseded for a
different reason -- the route.

### A second, independent defect found on the way

`scripts/carla_restart.sh` killed its own caller. It stops clients with
`pkill -f collect_data.py` and friends, which matches EVERY process whose command line
contains that string, including the shell that invoked the restart. The `[c]ollect` bracket
trick only stops pkill matching its own pattern argument; it does nothing about an ancestor.

That is the previous session's unexplained failure: a restart log ending
`GPU after restart: 5693 MiB` followed by `Terminated`, with a healthy server at the end of
it, reported by the DAgger driver as "restart failed before gate lap N" -- which discarded
a 12-lap gate that was passing at the time. Round 13 died that way with 5 of 5 laps passed.
Now fixed: a candidate must be a python interpreter AND must not be this script or any of
its ancestors.

## T06-F43  Every collected lap ended with a garbage expert LABEL, because an open route has no loop to close

Found on the first mixed collection of the rebuild, before its teacher was trained.

`collect_data.py` reported the mixed set's steering range as `[-0.754, 0.079]` where the
clear set's was `[-0.086, 0.079]`. The expert is pure pursuit driving from GROUND-TRUTH
pose and never reads the camera, so a steering label that depends on the weather is
impossible by construction. It was not the weather.

### The measurement

Every outlier is in the last three steps of a lap, at the route's end point, with the
vehicle perfectly on the line:

    low_sun/lap1  step 1277  steer -0.754  |CTE| 0.002 m  speed 20.0
    fog/lap2      step 1278  steer -0.639  |CTE| 0.001 m  speed 20.0
    night/lap0    step 1277  steer -0.623  |CTE| 0.001 m  speed 20.0

13 frames of 15,360, at steps 1277, 1278 and 1279 only. The steering column across the
last six steps of every lap:

    weather/lap      1274     1275     1276     1277     1278     1279
    clear/0        -0.045   -0.016   -0.002    0.028   -0.030   -0.010
    fog/0          -0.030    0.007    0.037   -0.546   -0.058   -0.111
    night/0        -0.030    0.007    0.036   -0.623   -0.059   -0.116
    low_sun/1      -0.030    0.007    0.037   -0.754   -0.061   -0.116

### The cause

Every driving loop ends a lap with the same test: leave the start, then come back to it.

    d0 = loc.distance(start)
    if d0 > 50.0: left_start = True
    if left_start and d0 < 12.0: break

**On an open route that test can never fire.** The Town06 lap's start and end are 174 m
apart -- the route was cut before a double intersection outside the ODD -- so the loop
runs to its step budget instead and drives past the last vertex, where pure pursuit's
lookahead is clamped onto the final point (`_step_idx` clamps rather than wraps on an
open route, correctly) and the commanded steering degenerates.

Whether a given lap reaches that vertex within its step budget depends on millimetres of
accumulated pose, which is why the clear laps escaped and the others did not. That is
also why it looked like a weather effect.

`gate_teacher_lap.py` already stopped at `hint >= n_route - 2`, and its comment says why:
"STOP AT THE END OF THE ROUTE, not a step count with slack ... The lap is open (start and
end are 171 m apart), so there is no wrap to absorb it." The fix was applied to the loop
that MEASURES a policy and not to the three that BUILD one -- the same shape as T06-F41's
bridging omission, where evaluate.py and the ledger bridged the intersections and
dagger.py did not.

### Why 0.08% of frames is worth a rebuild

They are behaviour-cloning LABELS, not measurements; they are all at ONE place; and that
place is the end of the scored road. A policy trained on them learns to jerk in the last
few metres of every lap -- and would then be diagnosed as "the teacher cannot hold the end
of the lap", which is exactly the kind of story this study has spent a week not telling
itself again.

The cost of not fixing it is a defect at the boundary of the scored region in every
dataset and every DAgger round, forever. The cost of fixing it was 35 minutes of clear
teacher.

### Fixed

`route.lap_finished(route, hint, margin=2)` -- one definition, true only on an OPEN route,
so Town04's closed loop is unaffected and its behaviour is byte-for-byte unchanged.
Called by `collect_data.py`, `dagger.py` and `dagger_student.py` **before the frame is
written**, so the bad frame is never recorded rather than recorded and filtered.

`scripts/audit_training_data.py` now flags any expert label above 0.25 -- pure pursuit
commands at most ~0.09 on these routes at 20 mph, so an order of magnitude above that is
the lookahead degenerating, not a corner. It is checked on the DATA, not on the source.

### It was never lap-specific

Running that check over the archive shows the same signature in the SIX-SECTION era
datasets, at the end of individual sections:

    clear_t06  clear/s00/lap3   max |steer| 0.337
    mixed_t06  fog/s02/lap0     max |steer| 0.268   (2 frames)
    mixed_t06  night/s00/lap1   max |steer| 0.336

Those are superseded for a different reason (the route) and are not being repaired. But
the defect predates the lap, survived A-2's full recollection, and was never visible
because nothing looked at the labels.

### What it invalidates

`clear_t06lap`, `mixed_t06lap`, `dagger_clear_t06lap` and the clear teacher trained on
them, all collected earlier the same day. Archived, not deleted. No certificate exists and
no cell has been scored.

## T06-F44  Every evaluate.py run on the lap stopped at 44% of it, and the competence gate called that a PASS

The mixed student failed the clear-weather competence gate at 17.88 ft. Chasing that
turned up something worse about the gate itself.

### The measurement that did not add up

Driving the DISTILLED mixed student, `scripts/compare_student_variants.py`:

    lap1  max|CTE| 12.46 ft  steps 511
    lap2  max|CTE|  4.33 ft  steps 510

511 steps of a 1,280-step lap, twice, within one step of each other. The trace says the
run did not depart -- at its final recorded step the vehicle is at **0.52 ft of CTE, on
the road, at 20.0 mph**, with the network and the expert commanding almost the same
steering. It is not a policy leaving the road. It is the measurement stopping.

Neither stop condition explains it. The vehicle is 982 m from the start, so the
loop-closure test (`left_start and d0 < 12`) cannot fire; the route index is 501 of
1,147, so `lap_finished` cannot fire; speed is 20 mph and |CTE| is 0.5 ft, so neither
the stall nor the off-road counter can fire.

### The cause

`drive_nn` bounds a run by distance as well as by steps -- correctly, and for a good
reason recorded in its own comment (a step cap is the wrong instrument for a distance
bound, and runs were overshooting section boundaries). It computed that distance as

    seg_len = np.linalg.norm(np.diff(route, axis=0), axis=1)

**The Town06 lap's route array is (N, 3) and the third column is YAW IN DEGREES.** So
`seg_len` averages 4.62 "m" per index instead of 2.00, `travelled_m` accrues 2.3x too
fast, and the cap at `SECTION_LEN_M = 2,289 m` trips at route index 501 -- **1,006 m of
the 2,289 m lap, 44%**.

    at route index 501:  true arc 1,006 m,  yaw-inflated arc 2,478 m

Town04's routes are (N, 2), so the same line is correct there. The defect is invisible on
the map that has published results and silent on the one being measured.

### What it invalidates

**The clear student's COMPETENT verdict.** It was measured over the first 1,006 m of the
lap, three times, and the last 1,283 m -- including the 1,700 m region where the clear
TEACHER takes its own worst |CTE| -- was never driven. `results/town06/competence_clear.json`
from 10:29 is withdrawn.

Everything else built on `evaluate.py` on this lap is truncated the same way, including
the driven traces `capture_gate_drives.py` produces for the A-3 capture gate: the gate
matches captured poses to driven poses and keeps those within 2 m, so it would have
gated on the first 44% of the road and reported a pass over `keep.sum()` poses without
saying which road they were.

No scored ledger cell and no certificate exists, so nothing downstream is affected.

### The third instance of one defect

This is the same defect as the capture rig's, in a different file, found four hours
later:

| file | symptom |
|---|---|
| `capture_offset_yaw.py` | the lap measured 5,299 m instead of 2,289 m, so every metres-along-the-route lookup landed at ~40% of the distance it named |
| `evaluate.py` | `travelled_m` accrued 2.3x too fast; every run stopped at 44% of the lap with the vehicle still on the road |
| `certify_sustained_bound.py` | harmless today only because Town04's routes are (N, 2) |

Each caller computed arc length for itself. That is the whole cause: there was no
definition of "how long is this route" to be wrong in only one place.

### Fixed

`route.arc_lengths()` and `route.route_length_m()` -- x and y only, one definition, used
by the driver and the capture rig. `tests/test_route_arc_length.py` asserts that a wild
third column cannot change a route's length, that the lap measures its declared 2,289 m,
and -- by source inspection -- that no driver measures a route distance over every column
again.

## T06-F45  "Top up this dataset" silently REPLACED it

Raising the base sets from 4 laps to 8 (T06-F44's response: both students failed the full
lap while both teachers held it) produced eight lap directories on disk and a manifest
referencing four of them.

    pipeline/data/clear_t06lap:  8 lap directories
    manifest.csv:                5,098 rows, laps 4,5,6,7 only

The first four laps' labels are gone. The dataset did not grow, it was replaced, and
nothing said so -- the stage logged "collecting 4 more" and exited 0.

### Cause

`collect_data.py` merges a re-collection into the existing manifest with

    prior = [r for r in csv.DictReader(f) if r.get("weather") not in weathers]

Every prior row whose weather is being collected again is dropped. Its comment gives the
reason, and the reason was true when it was written: "`range(args.laps)` always restarted
at 0, so a SECOND collection for the same weather rewrote lap00.. with new images while
the manifest kept the old rows pointing at those same paths -- old labels, new pixels, no
error. Appending is only safe across weathers, which get distinct directories."

That hazard was then fixed a different way: lap numbering CONTINUES from what is on disk
(`base_lap`), so a re-collect writes new directories and cannot overwrite the old frames.
Once that landed, the weather filter stopped protecting anything and started deleting
data. Two correct fixes for one hazard, and the older one became the bug.

### Why it was caught

`scripts/audit_training_data.py` prints a lap count per dataset, and it said
`clear_t06lap (4 laps)` immediately after a stage that was supposed to make it eight.
The check was not looking for this -- it exists for degraded-server signatures -- but it
reports the shape of the data, and the shape was wrong.

### Fixed

The guard is no longer the weather. A prior row is kept unless THIS run rewrote that exact
(weather, direction, lap), and unless its frame is missing from disk -- a row whose image
does not exist is a lie whatever else is true about it.

### Cost, and what was recovered

* `mixed_t06lap`: caught mid-collection. Its 15,288-row manifest was copied before the
  in-flight run could overwrite it, and the three original laps per condition were merged
  back afterwards.
* `clear_t06lap`: laps 0-3 were already lost. Frames without labels cannot be relabelled
  without re-driving the poses that produced them, so those four directories were deleted
  and re-collected. Four laps, about five minutes.

No teacher, student, certificate or scored cell was built on the truncated manifest: the
failure landed between a collection and the distillation that consumes it.

## T06-F46  A WINDOWED server sometimes renders 14% darker, and the photometry gate caught it before a frame was collected

Zach came back to the machine and asked for a watchable window (standing rule 6). The
campaign was switched to `CARLA_WINDOWED=1`, which now starts -- the SDL failure recorded
in T06-F42 was a property of the session, not of the machine.

The first windowed launch passed the photometry gate at **0.002% off** reference. The
second, three minutes later, same script, same flags, same map:

    photometry Town06/clear: 0.220557 vs reference 0.257106 (14.215% off, tol 1.0%)
    FATAL: THE SERVER IS RENDERING AT A DIFFERENT BRIGHTNESS.

**0.220557 / 0.257106 = 0.858.** T06-F42's contamination ratio was 0.846. It is the same
defect, and this is the first time it has been caught in the act.

### It is a property of the SERVER INSTANCE, not of the frame

Five consecutive measurements against that one live server:

    0.220562  0.220565  0.220566  0.220566  0.220566

A spread of 4e-6. So this is not per-frame noise and not something that drifts during a
run: a server comes up either right or 14% dark, stays that way for its whole life, and
answers every RPC identically either way. That is exactly the shape T06-F42 measured
across DAgger rounds -- rounds 00-05 at 0.2508-0.2537 and rounds 06-14 at 0.2140-0.2141,
each round internally consistent.

### What is NOT the cause

* Not headless vs windowed as such. A windowed lap on 2026-09-01 measured 0.2525015
  against a headless 0.2524913 -- 4e-5 -- and a windowed launch passed at 0.002% minutes
  before this one failed.
* Not the launch flags: `/proc` argv is identical between a passing and a failing windowed
  launch, and the determinism preflight (D-1..D-11) is green on both.
* Not the map, the weather, the camera or the exposure: all constructed identically, and
  `verify_condition` reads the weather struct back on every run.

The trigger is still unidentified. What is now established is that it is decided at
LAUNCH, that it survives for the life of the server, and that a windowed launch can land
on either side of it.

### CORRECTION, same day: it happens HEADLESS too

The section below concluded "every headless launch today has passed the gate; a windowed
launch has now failed it" and moved the campaign to headless on that basis. Two hours
later a HEADLESS launch failed it:

    restart attempt 1/3 FAILED (round 2); FATAL: the server on 3000 renders at a
    different brightness

So the mode is not the trigger. Windowed was over-represented in the first sample because
only two windowed servers had ever been measured, one of which was bad. The defect is
intermittent across launches in BOTH modes, and the trigger remains unidentified.

What survives from the reasoning below is the part that matters: the state is decided at
LAUNCH and constant for the server's life, so it is detectable in two seconds and curable
by throwing that server away. `carla_launch.sh` now relaunches on a photometry rejection,
up to four times, instead of failing the restart -- which is what turned a two-second
retry into a stopped campaign. Four bad servers in a row is a different problem and still
stops everything.

The headless decision stands anyway, on the unchanged measurement that a windowed server
gives no benefit here (nobody is watching an unattended overnight run) and one more thing
to go wrong.

### Decision: headless, and the deviation from standing rule 6 is deliberate

Standing rule 6 asks for a visible window so runs can be watched. Every headless launch
today has passed the photometry gate; a windowed launch has now failed it by 14%. A window
that changes the image the network sees by 14% is not a viewing convenience, it is a
second copy of the defect that cost this study two rebuilds.

So the campaign runs headless. **The runs are not watchable, and that is the price of the
frames being comparable.** Recorded here rather than taken silently, and reversible the
moment the trigger is identified.

### What this validates

`scripts/check_render_photometry.py` was written after the fact for T06-F42, on the
argument that the determinism preflight verifies the launch and `verify_condition` reads
the weather struct, and neither looks at brightness. It has now stopped the exact defect
it was written for, at server launch, before any frame reached a dataset -- which is the
only place it could have been stopped.

## T06-F47  The dark server is RARE, and it did not reproduce on either map in a quiet period

Zach asked whether Town04 sees the T06-F46 defect too, and whether CARLA might simply be
unwell after being exercised this hard. `scripts/probe_dark_server.py` launches a fresh
server per sample and measures the same fixed-pose frame the gate uses.

    Town06   5 servers   min 0.257108  max 0.257110   spread 0.00%
    Town04   4 servers   min 0.241813  max 0.241813   spread 0.00%
                         (a fifth Town04 measurement failed to return)

Nine consecutive clean launches, both maps, no bimodality. Against two bad servers
observed earlier the same day out of on the order of fifty launches, the incidence is a
few percent at most.

**This does not clear Town04.** Nine samples cannot distinguish "immune" from "rare", and
the two bad servers were seen during sustained heavy use -- hours of restart-per-lap
campaigning -- while this probe ran in a quiet period. Zach's suggestion that the server
degrades under exercise is consistent with everything observed and is not established by
it. What can be said: the defect is not frequent, not obviously map-specific, and not
reproducible on demand.

Which is the argument for the gate rather than against it. A defect at a few percent per
launch is invisible in any single run and near-certain across a campaign of hundreds of
restarts -- which is exactly how T06-F42's contamination came to be split across DAgger
rounds, each round internally consistent and the set as a whole ruined. Two seconds per
launch buys immunity to it whatever its cause turns out to be.

A Town04 photometry reference is now committed (0.241813) so the same gate protects the
published study's re-measurement.

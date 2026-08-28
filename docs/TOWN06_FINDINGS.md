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

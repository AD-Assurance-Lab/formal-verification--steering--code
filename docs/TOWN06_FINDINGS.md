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
straights after DAgger. ACTION: mixed re-distilled at 168x28 w3, 32,112 ReLU. The clear
student stays at w2, 21,408 ReLU, where its own DAgger passes.

This is a clear-weather competence decision. Clear is the s=0 anchor of the disturbance
family, not one of the disturbance conditions, so it does not weaken the blind protocol
(PROTOCOL R3). Student capacity is a property of the model under test rather than of the
criterion, so widening is declared, not amended.

## Open

Whether the mixed student at w3 survives its own DAgger. If it degrades in clear again
at 32,112 ReLU, then two independent width points say the mixed student should not be
DAgger-ed at all at this resolution, and the base checkpoint is the one to ship. That
would be a real result rather than a workaround, but it needs the second point first.

Verifier cost at 32,112 ReLU follows T06-F12's roughly linear trend, so about 3.8 s/pose
on CPU with CARLA down. Watched, not assumed.

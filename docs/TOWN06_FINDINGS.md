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

## Open

Capacity for the mixed student (w3 -> w4, 15,456 -> 20,608 ReLU) is the one lever Town04
evidence supports and is under test. The clear student stays at Town04's 5,152 ReLU:
widening it was tried, then reverted, because nothing measured implicates its capacity.

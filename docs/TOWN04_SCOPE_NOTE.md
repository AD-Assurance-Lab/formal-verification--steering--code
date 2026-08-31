# Town04: what each stage of the study actually covers

Internal reference, not paper text.

## The three extents, before the fix

    training data          0 -> 3,042 m   (collection drove to loop closure)
    captures + certificate 0 -> 2,861 m   (the scored prefix)
    closed-loop drives     0 -> ~3,035 m  (no cap; drove to loop closure)

Three stages of one study covering three different extents, and nothing compared them.
Verification saw the least, driving saw almost everything, and the agreement number was
computed between two of them as though they described the same road.

Consequence, measured: **48 of 96 ledger runs took their worst |CTE| beyond the scored
road** -- every mixed-student run, none of the clear-student runs. `fog/S_mixed` was
declared a failing cell on a peak recorded at step 1695, about 174 m past the end of what
the certificate covered, in the junction where the markings leave the camera's view.

## After the fix

    training data          0 -> 3,042 m   (unchanged; see the note below)
    captures + certificate 0 -> 2,988 m
    closed-loop drives     0 -> 2,988 m   (capped)

Verification and driving now cover exactly the same road.

## Why 2,988 m

Measured on the route and confirmed by parking the car there and looking:

    2,880 -> 2,982 m   the final 90-degree corner, constant 1.54 deg/step
    2,982 m            corner complete, heading east
    2,988 m            THE CUT -- 6 m past the exit, enough to see the car straighten
    2,996 m            junction begins
    3,022 m            lane markings end
    3,042 m            loop closure

The old 2,861 m cut stopped 19 m BEFORE the corner even started, discarding 127 m of
marked road including the most informative stretch on the lap for a lane-keeper. At the
cut there are about five dashed markings visible on each side.

## Training data beyond the scored road — a known, accepted confound

Training covers the full 3,042 m, so ~1.66% of frames lie beyond the new scored end:

    beyond 2,988 m (unscored)        449 frames   1.66%
    inside the junction (>2,996 m)   380 frames   1.40%
    no lane markings (>3,022 m)     ~165 frames   0.61%

On those ~165 frames the expert still commands "follow the route", so the policy receives
a small amount of supervision that amounts to *keep going when the markings disappear*.
That couples weakly to the disturbances under study, since fog and night reduce marking
visibility: a policy taught to hold heading without markings could fail differently there
than a pure lane-follower would.

**Decision (Zach, 2026-08-31): accept it, do not retrain.** At 0.61% the effect is
expected to be negligible, retraining costs ~10 hours, and the published run has the same
property so comparability is preserved.

**How we will know if that was wrong, at no extra cost.** The re-driven ledger shares
0 -> 2,861 m with the runs it replaces. If behaviour on that common stretch is unchanged,
the extension perturbed nothing and the decision holds. That comparison falls out of data
we are collecting anyway.

**For Town06, which is being rebuilt from zero, collection is filtered to the scored
extent** so training, verification and driving cover the same road by construction. The
clean design costs nothing there because the data does not exist yet.

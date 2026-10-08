# Commit notebook

Commit bodies of 30 lines or more, exported once on 2026-10-07 from the
history of `formal-verification--steering--code`, newest first. Before the lab's commit convention these bodies
held the working notes: measurements, defects found and the reasoning behind a change.
They are copied here so they can be searched and cited. The commits themselves are
unchanged; `git show <hash>` returns the original.

| Date | Commit | Subject |
|---|---|---|
| 2026-09-08 | [`182f490`](#182f490) | Publish the void cell's disposition, which existed but was not in the repo |
| 2026-09-08 | [`993d681`](#993d681) | Two artifacts the paper's figures need: highway traces and highway witnesses |
| 2026-09-08 | [`ea925a6`](#ea925a6) | Date the cross-session drift measurement, and bound it with the current one |
| 2026-09-08 | [`82d94d6`](#82d94d6) | Act on the external reviews: broken tools, wrong numbers, and a soundness check that was never called |
| 2026-09-08 | [`66e1e9f`](#66e1e9f) | Fix the repository root in all 19 entry points and 15 shell drivers |
| 2026-09-07 | [`e733a40`](#e733a40) | Remove 490 lines of dead code |
| 2026-09-07 | [`bd8dc43`](#bd8dc43) | Group the library, make config answerable, and fix pre-release loose ends |
| 2026-09-06 | [`42aeab5`](#42aeab5) | Plain language throughout: no lab record numbers, no dates, no names |
| 2026-09-06 | [`d8bbbd0`](#d8bbbd0) | Consolidate 171 per-run files, and group scripts by what they are for |
| 2026-09-06 | [`9e33b8f`](#9e33b8f) | Put the training pipeline in its own folder, and the paper's figures back in the paper |
| 2026-09-06 | [`dd1d758`](#dd1d758) | Cut to what the study needs, and name things for what they are |
| 2026-09-06 | [`1767719`](#1767719) | Make a clean checkout actually work, and prove it from one |
| 2026-09-06 | [`42e1b10`](#42e1b10) | Documentation, packaging metadata, lint, and the capture fetcher |
| 2026-09-06 | [`34d81b9`](#34d81b9) | Make this an installable package instead of 96 sys.path inserts |
| 2026-09-06 | [`f6ab839`](#f6ab839) | The driver mismatch was six ticks, and the scored driver was missing R-SIM-4 |
| 2026-09-06 | [`14a6277`](#14a6277) | Q7: the cross-road fog comparison survives at matched input size, by 9-31x |
| 2026-09-06 | [`29b5866`](#29b5866) | Q8c findings, and a correction header on Q8b |
| 2026-09-06 | [`c998ea8`](#c998ea8) | Q8c: both "undecided" cells are FALSIFIED, with witnesses -- and no beta-CROWN needed |
| 2026-09-06 | [`ce8232a`](#ce8232a) | A1: the best policy passes every scored ledger cell, and the bound refuses two |
| 2026-09-05 | [`2f918d5`](#2f918d5) | V2: the paper's 0.98 ft student drives fog at 1.42 ft, twelve times out of twelve |
| 2026-09-05 | [`3f6da90`](#3f6da90) | V1: the VOID cell's excursion has a location, and the lap that voided it was measured on different hardware |
| 2026-09-05 | [`d8d9feb`](#d8d9feb) | Q8b: integration validated, both undecided cells still undecided, reasons measured |
| 2026-09-05 | [`d7f40e1`](#d7f40e1) | Q8b machinery: export a sub-problem, and PROVE the exported graph |
| 2026-09-05 | [`0832810`](#0832810) | Q8a: alpha-CROWN resolves neither undecided cell, and the slack is not where I predicted it was |
| 2026-09-05 | [`f5b4db3`](#f5b4db3) | Q4: balancing replicates at twelve seeds, and is the first driving-endpoint win |
| 2026-09-05 | [`5b99317`](#5b99317) | Q3: the certificate is sound, and expensively incomplete on a good policy |
| 2026-09-05 | [`394f5ca`](#394f5ca) | Let the ONE ledger driver drive an exploratory student, gated on the tag |
| 2026-09-05 | [`b59ef91`](#b59ef91) | An exploratory blind scope, so Q3 need not choose between two wrong options |
| 2026-09-05 | [`401b809`](#401b809) | Q2: pass 3's conclusion survives the tuned recipe, and the confound resolves |
| 2026-09-05 | [`6feded8`](#6feded8) | Q6: there is no cheap variance lever, and the dispersion is intrinsic |
| 2026-09-05 | [`e30c0ed`](#e30c0ed) | Q6: separate the init seed from the data seed, opt-in and proved bit-neutral |
| 2026-09-05 | [`5636855`](#5636855) | Q1: the learning-rate effect is confirmed on KD error and not on driving |
| 2026-09-05 | [`0e674cc`](#0e674cc) | Q8 amendment A-1: Route 1 cannot be installed into .venv, measured |
| 2026-09-05 | [`ad3dc2f`](#ad3dc2f) | Q8 pre-registration: alpha-CROWN then beta-CROWN, Route 1 declared |
| 2026-09-04 | [`3dea682`](#3dea682) | Overall status: the certification result stands, pass 3's attribution does not |
| 2026-09-04 | [`621aeb3`](#621aeb3) | E4: depth costs verification 2.3-3.7x, does not help driving, and the learning rate dwarfs both |
| 2026-09-04 | [`62bfdac`](#62bfdac) | Headless equals windowed, the launcher can no longer hand you the wrong server, and the study's learning rate does not fit a deeper student |
| 2026-09-04 | [`801337a`](#801337a) | E2 re-run: pinning makes a run repeatable, not the seed a control |
| 2026-09-04 | [`b6ae99d`](#b6ae99d) | E2: the tail loss did nothing measurable, and the reason the noise was that large is fixed |
| 2026-09-04 | [`daec967`](#daec967) | E1b: multimodal not bimodal, the harness is exonerated, and E5 is answered |
| 2026-09-04 | [`70c71c5`](#70c71c5) | E1: the resolution trend was three unlucky seeds, and fog is unreliable rather than absent |
| 2026-09-03 | [`6796743`](#6796743) | The pinned environment could not run on the new card, and nothing said so |
| 2026-09-03 | [`366b1b9`](#366b1b9) | Freeze the study for publication, and hand off the follow-on experiments |
| 2026-09-03 | [`d5503e7`](#d5503e7) | T06-F57 PASS 3: neither width met the gate, and width is eliminated properly this time |
| 2026-09-03 | [`09726f5`](#09726f5) | An unmeasured lap is not a failing lap, and my last fix only got half of it |
| 2026-09-03 | [`26e5d9d`](#26e5d9d) | The gate that picks the shipped model recorded nothing about the harness |
| 2026-09-03 | [`4882cb4`](#4882cb4) | Pass 3 stages 1-2: a margin gate, and pin namespaces that cannot clobber pass 1/2 |
| 2026-09-03 | [`b86d4d8`](#b86d4d8) | Pass 3 pre-registration: the wider student, and a gate that selects for margin |
| 2026-09-03 | [`99a08b4`](#99a08b4) | The audit drove CARLA, and standing rule 1 was never checked for Town06 |
| 2026-09-03 | [`c2a8bfd`](#c2a8bfd) | Exhibit the witness: three NOT_CERTIFIED cells are genuine falsifications |
| 2026-09-03 | [`c294c1c`](#c294c1c) | Town06 pass 2: 24 laps, both scopes, and the arc-parameterisation bug found scoring them |
| 2026-09-03 | [`9bb70a3`](#9bb70a3) | T06-F51/F52: the interior is not closed-loop testable as the family is defined |
| 2026-09-03 | [`3a9da5d`](#3a9da5d) | The comparison re-derived a verdict the ledger had already decided, and lost a VOID |
| 2026-09-02 | [`f6e921c`](#f6e921c) | T06-F49: repeating a lap is not data; T06-F48's remedy is withdrawn |
| 2026-09-02 | [`364e623`](#364e623) | T06-F48: the Town06 students train on a third of Town04's data |
| 2026-09-02 | [`35b32cd`](#35b32cd) | T06-F46: a windowed server sometimes renders 14% darker; back to headless |
| 2026-09-02 | [`bdfd186`](#bdfd186) | T06-F43: every collected lap ended with a garbage expert LABEL |
| 2026-09-02 | [`bc1819c`](#bc1819c) | The loose gate's FAILURE was outranking the strict gate's PASS |
| 2026-09-02 | [`f39aeb7`](#f39aeb7) | The lap capture would have certified 170 m of intersection nobody drives |
| 2026-09-02 | [`4a2cff6`](#4a2cff6) | T06-F42: the server rendered 15% darker for half a day, and both teachers trained on it |
| 2026-09-01 | [`d370c31`](#d370c31) | The condition is low_sun; "shadows" was always a bug, and the protocol already said so |
| 2026-09-01 | [`b364a2c`](#b364a2c) | A clean server before every lap, and cells that record the harness they ran under |
| 2026-09-01 | [`25f64e3`](#25f64e3) | Archive the superseded eras to the drive, and stop gating checkpoints a round did not train |
| 2026-09-01 | [`46f69a2`](#46f69a2) | Restore the blind-order check the prune deleted, which then caught me |
| 2026-08-29 | [`b98f8d1`](#b98f8d1) | T06-F31: deployment test result 4/6, and 3/3 on the genuinely blind cells |
| 2026-08-28 | [`d2292f5`](#d2292f5) | Reproducibility RESOLVED: apply_control raced the tick, and textures streamed |
| 2026-08-27 | [`72dd65f`](#72dd65f) | T06-F20: low sun is defined by rendered outcome; Town06 moves to 5 deg |
| 2026-08-27 | [`d974c45`](#d974c45) | T06-F19: harness overshoot bug; all closed-loop numbers re-measured and superseded |
| 2026-08-27 | [`a3f94a5`](#a3f94a5) | explore phase 2: 320x64 w3 breaks the floor at 5/48; my floor hypothesis was wrong |
| 2026-08-26 | [`1b7ad5b`](#1b7ad5b) | T06-F14: student DAgger is harmful at 168x28, w2 beats w3; F13 corrected |
| 2026-08-26 | [`9bb6e50`](#9bb6e50) | Size each student to its own task, and put the sizes in ONE registry |
| 2026-08-25 | [`6c706ac`](#6c706ac) | Ledger v2: two tiers, three instruments, and a hardened order check (D-14) |
| 2026-08-15 | [`fa7f127`](#fa7f127) | F47/D-13: held-out rain drives FAIL 10/10 -- the blind certificate scored 4/4 |
| 2026-08-15 | [`fd83345`](#fd83345) | F46: run the Koschmieder test on our own family -- it passes, and fog is non-monotonic |
| 2026-08-15 | [`ea38e2d`](#ea38e2d) | Prune to the published result: 48 scripts -> 13, and make the repo runnable elsewhere |
| 2026-08-15 | [`e76f3b1`](#e76f3b1) | F45: the tolerance horizon is fitted, and at its a-priori value the certificate is unsound |
| 2026-08-15 | [`6e1fa73`](#6e1fa73) | Re-certify all twelve with paired baselines: 12/12, ten cells bit-for-bit |
| 2026-08-15 | [`a9d040e`](#a9d040e) | F43/F44: the eastbound fog cell was certified against another session's baseline |
| 2026-08-11 | [`b9ad55b`](#b9ad55b) | S_clear verify cells (night FALSIFIED, shadows CERTIFIED), and fog model fails D3 |
| 2026-08-11 | [`f71efdc`](#f71efdc) | Spectator: restore one-tick extrapolation, now backed by measurement |
| 2026-08-11 | [`99df778`](#99df778) | F11: width is the capacity lever; resolution loses on both axes |
| 2026-08-11 | [`11bbb4f`](#11bbb4f) | M2.5 COMPLETE: mixed teacher passes all four conditions, both directions |
| 2026-08-11 | [`9763e82`](#9763e82) | F10: retract the d=2 result -- my BaB search order was wrong |
| 2026-08-11 | [`d08408e`](#d08408e) | Spectator: revert my extrapolation, fix the real cause (frozen during warmup) |
| 2026-08-11 | [`4f034ec`](#4f034ec) | F9: verification is decisive on this disturbance family -- UNKNOWN under 2.5% |
| 2026-08-11 | [`4d7bebd`](#4d7bebd) | DENSE: record availability uncertainty and a fallback that may be better |
| 2026-08-11 | [`a531a64`](#a531a64) | M6 machinery: adaptive BaB over the fog axis produces ODD sub-ranges |
| 2026-08-11 | [`d412ca8`](#d412ca8) | F8: the 6-band depth discretization was the binding constraint, not the physics |
| 2026-08-11 | [`de4e93a`](#de4e93a) | DENSE: we were pointing at the wrong dataset; request PADB, not Seeing Through Fog |
| 2026-08-11 | [`65ec8ae`](#65ec8ae) | Stand up the verification stack on upstream auto_LiRPA; all cross-checks pass |
| 2026-08-11 | [`c2ebb33`](#c2ebb33) | Close trap 2 properly: frame-id matched capture everywhere, one implementation |
| 2026-08-11 | [`3e413c6`](#3e413c6) | STUDY M7: add combined disturbances to the stretch goals |
| 2026-08-11 | [`993e3ad`](#993e3ad) | Fix preset read-after-write race: night was running at fog_density 70 |
| 2026-08-11 | [`a1dea9f`](#a1dea9f) | Fix two bugs in dagger_student: missing exposure switch and no beta-mixing |
| 2026-08-11 | [`e93e261`](#e93e261) | Width sweep: S_mixed is NOT capacity-bound; expose distill's warm-start on the CLI |
| 2026-08-11 | [`a86f47e`](#a86f47e) | Exposure becomes a declared function of condition; retire old night data |
| 2026-08-11 | [`5e2f6ae`](#5e2f6ae) | M2: mixed teacher trained; fix single-base DAgger/distill and trap 13's second site |
| 2026-08-10 | [`2dd919f`](#2dd919f) | M1 transplant + D1 measured: auto-exposure confirmed, fog preset confounded |
| 2026-08-10 | [`0c1feff`](#0c1feff) | M0: study design, executable ledger, conformance suite |

<a id="182f490"></a>
## 2026-09-08 `182f490` Publish the void cell's disposition, which existed but was not in the repo

Author: Zach Asher. Full hash: `182f490cb5a3aeabd43eece6d8037aadd1f05a1b`.

The committed ledger's one void cell -- the mixed student under fog -- has had a
cause on record since the campaigns of 5-6 September, and none of it was in the
published artifact. A reader saw "VOID" and nothing else, which reads as a
policy that cannot drive the condition it was built for. That is not what was
measured.

84 laps, folded into one file rather than four directories of per-lap records:

  the cell alone, 24 laps          0 over budget, worst 1.66 ft
  every cell re-driven             fog/mixed PASS 1.95, and 7 of 8 reproduce
  every cell again, fixed driver   fog/mixed PASS 1.46, same 7 of 8
  the tuned policy                 all four conditions PASS, fog 1.34 ft

So the mixed student drives all four of its conditions, and the lap that voided
the cell was measured on the graphics card the lab has since replaced. Cells
that are not marginal reproduce across that change to two decimals -- a 25 ft
departure lands within 0.01 ft of where it landed before -- so the hardware is
not moving the simulation generally. It moves the one cell sitting on the
boundary, which is what a basin-selection mechanism predicts.

The committed passes are untouched and stay the reported numbers. This sits
beside them and says what was learned after, which is what lifting a void asks
for: the cause written down, not the failure averaged away over more laps.

Note for the paper rather than the repo: un-voiding this cell would LOWER the
Town06 agreement figure from 4/5 to 4/6, because the cell it un-voids is one
the bound refuses. That is a real consequence and it belongs to whoever writes
the sentence, not to this file.

pytest 294 passed, 24 skipped. Paper checker 464 checks, 0 failures.

<a id="993d681"></a>
## 2026-09-08 `993d681` Two artifacts the paper's figures need: highway traces and highway witnesses

Author: Zach Asher. Full hash: `993d6817357201fabce649b2cdb292fb06bb1cea`.

The highway had neither the step-by-step trajectories the arterial ships nor a
witness search, so two of the paper's figures had no primary data on this road.

TRACES. The eight highway cells re-driven, three laps each direction, 48 runs,
one process and one clean server restart per run, determinism preflight green
on each. Folded to results/highway/ledger/traces.csv in the arterial's schema.

Every verdict held, so the committed ledger is unchanged and the traces are
added beside it:

  condition  student   committed        re-drive         move
  clear      clear      0.58 PASS        0.91 PASS      +0.33
  clear      mixed      0.41 PASS        0.39 PASS      -0.01
  fog        clear      1.35 PASS        1.32 PASS      -0.04
  fog        mixed      0.40 PASS        0.37 PASS      -0.03
  night      clear     41.42 FAIL       37.36 FAIL      -4.05
  night      mixed      1.40 PASS        0.85 PASS      -0.56
  low sun    clear     31.59 FAIL       31.86 FAIL      +0.26
  low sun    mixed      0.82 PASS        0.54 PASS      -0.28

No cell's laps disagree, so none is void. The clear/clear move is the largest
and is the expected one: the committed ledger was driven before the frame-level
condition check was added to this driver, and that check brings six settling
ticks with it, which selects a different basin. That consequence was declared
when the check landed rather than discovered here. The two departed cells moved
most in feet and least in meaning -- once a lap leaves the lane its worst error
is wherever it drifted to.

WITNESSES. falsify_witness.py only ever ran on the arterial; it now runs on
both. The highway needs its own pose selection, because its certifier truncates
to the scored extent, and the two certifiers spell the same verdict differently
-- NOT_CERTIFIED against FALSIFIED -- which had been silently excluding every
highway cell from the summary, including the two that matter most.

Twelve per-direction cells, matching the certificate's own unit. Two witnesses,
both the clear-only student at night, about three times tolerance. Two more
where the bound refuses and no witness exists, both that student under low sun,
just inside tolerance -- sound but undecided, which is the honest reading. The
remaining eight certify. No highway witness is interior-only: unlike the
arterial, driving the full-strength condition would find both.

Also here: here_m was empty in every highway trace, because the column was
computed only for the lap-based road. It is the one field saying where on the
road a departure happened. Both roads have fixed vertex spacing, so it is the
route index times that spacing; Town04 declares no bridge spans, so bridging
stays off there and the change is behaviour-neutral on both roads.

And a re-drive now writes somewhere else. HIGHWAY_LEDGER_SUBDIR redirects the
ledger directory, so re-driving cannot overwrite the committed numbers it is
being compared against. The default is unchanged.

pytest 294 passed, 24 skipped. The paper's checker: 401 checks, 0 failures.

<a id="ea925a6"></a>
## 2026-09-08 `ea925a6` Date the cross-session drift measurement, and bound it with the current one

Author: Zach Asher. Full hash: `ea925a6931642b090c186d0a7ebacc6c780c5da1`.

An external reviewer read this repository cold and concluded that every shipped
certificate is contaminated: that the clear baseline comes from a different
simulator session and that the drift between sessions is about twice the size of
the arterial fog disturbance. That would make the bounds meaningless.

It is not true, and the reason a careful reader believed it is a stale comment
in this repository.

The +0.049-per-pixel figure the certifier's docstring quotes was measured on
2026-08-15, on captures this study does not ship. The photometry gate landed on
2026-09-02; the shipped captures were rendered on 2026-08-31 and 2026-09-02.
Every server that renders a capture is now checked against a recorded absolute
brightness at launch, and the reference records the variation:

    cross-session clear drift, fresh server each time   std 1.2e-04
    the figure the docstring quotes                         4.9e-02
    arterial fog disturbance, mean |shift| per pixel        6.3e-02

The drift is 0.2% of the fog disturbance and about 400x smaller than the number
the docstring reports. The docstrings now say when their measurement was taken
and what the current bound is, and tests/test_cross_session_drift.py asserts the
ratio so neither figure can drift away from the artifacts again.

The structural observation stands and is worth keeping: every shipped cell does
use a foreign baseline, because each capture holds one condition and the server
is restarted between them so a previous condition cannot leak into the next. The
preference for a paired baseline stays in the code for the generation where that
mattered. What changed is that the cost of the foreign one is now measured rather
than asserted.

  pytest   294 passed, 24 skipped
  ruff     clean

<a id="82d94d6"></a>
## 2026-09-08 `82d94d6` Act on the external reviews: broken tools, wrong numbers, and a soundness check that was never called

Author: Zach Asher. Full hash: `82d94d68c4ded6c634d29b7f8d08a47deeeede67`.

Two reviewers read this cold. Beyond the repository-root regression already fixed,
these are the findings that were real. Nothing about the study changed: no capture,
no drive, no certificate.

THE CONDITION VALIDATOR SKIPPED LOW SUN AND REPORTED SUCCESS. It took the
condition from the filename with a split on the last underscore, so `lap_lap_low_sun`
asked for "sun", matched nothing, and silently continued -- then printed "3 correct,
0 misclassified out of 3". The one condition it skipped is the one carrying the only
certified cell. It now matches the filename against the conditions the file declares
and reports 4/4, all correct.

THE LEDGER DRIVERS DELETED THE CARLA LOCK BEFORE EVERY SCORED RUN. Eight scripts did
`rm -f` on it, which defeats the one-client-per-port rule in the path that produced
the published numbers. The lock reclaims itself when its holder is dead, so this
bought nothing except the ability to start a second client over a live one. And the
guard meant to stop that parsed the holder's pid by stripping non-digits from the
whole lock file -- which includes the owner's command line, and every checkpoint name
here has digits in it. It read pid 12345 as 1234506, concluded the holder was dead,
and killed it. First line only now.

THE LAUNCHER STARTED A SECOND SERVER WHEN IT MEANT TO REUSE ONE. The reuse branch
printed "reusing the server already on port" and then fell through to the launch,
because it had no exit.

THE SOUNDNESS SELF-CHECK WAS DEAD CODE. The bounder rebinds the leading layer's
weights in place instead of rebuilding the module per sub-box, which is what makes
certification minutes rather than hours, and check_equivalence exists to prove the
library really reads the rebound weights. It was called only from a retired entry
point, so every published bound rested on an unvalidated shortcut. Wiring it in
exposed a second defect in the check itself: it built the fresh module with
CROWN-Optimized while the certifiers use plain CROWN, so it compared two different
bound methods and reported a mismatch. Holding the method fixed, it passes at
4.3e-07, and the certificate is unchanged.

THE REPRODUCTION GUIDANCE WAS WRONG IN THE DIRECTION THAT MATTERS. REPRODUCING
claimed "at least 309x headroom" and used it to justify accepting any bound agreeing
to 4e-3. Recomputed from the artifacts in the units the certifier decides in:

    arterial   tightest cell 0.240 x tol from flipping, drift 0.0009   274x
    highway    tightest cell 0.360 x tol from flipping, drift 0.218      1.6x

Both reproduce, every verdict and pose count, on this machine. But the highway does
so with under twice the room it needs, and a reader told only "it reproduces" would
absorb a flipped verdict as noise. That is now stated. Neither numpy nor torch
explains the drift: 1.26.4 and 2.4.6 agree to 5e-7 x tol.

TWO OF THREE ORACLE REFERENCES WERE JUNK. REPRODUCING calls them the cheapest check
that a simulator is configured correctly. One was 380 steps of the ARTERIAL lap filed
under a highway direction name; the other was sixteen steps ending 7 m off any route,
at 7.8 m of cross-track error against a 0.67 m budget. Both are removed and the
remaining one is guarded by a test that checks a reference lies on the route it names
and stayed on the road. drive_expert now writes where the documentation says.

THE PROTOCOL CITED NUMBERS ITS OWN ARTIFACTS REFUTE. Amendment 3 quoted the capture
gate as "0.0261, 12/12 cells"; the file it names says 0.0148 over 2 cells. Amendment
4 named a cell as passing "within 1.0% of the budget"; it passes with 41% in hand.
Both belonged to the superseded six-section generation. Section 3's frozen constants
still say ten reps and 200 poses where the study ran three laps and 133 poses -- that
is left byte-identical on purpose, because rewriting a frozen section to match the
outcome defeats the only thing it is for, and Amendment 4 now says so explicitly.
The lock still verifies the original registration.

tests/test_reported_numbers.py recomputes every one of these figures from the
artifacts, so prose can no longer drift away from them.

Also: auto_LiRPA is credited in the README and its version is recorded in new
certificates -- the whole formal claim rests on it and it was cited nowhere; CARLA's
asset terms are named; seed_screen.json is tracked, so the paper's checker works on a
public clone; the patch file for the private paper repository is removed now that it
is applied.

  pytest                          290 passed, 24 skipped
  ruff                            clean
  PROTOCOL.lock                   verifies, same digest
  the paper's checker             0 failures
  the arterial certificate        6/6 verdicts and pose counts, drift 3.9e-03
  the highway certificate         12/12 verdicts, restored untouched

<a id="66e1e9f"></a>
## 2026-09-08 `66e1e9f` Fix the repository root in all 19 entry points and 15 shell drivers

Author: Zach Asher. Full hash: `66e1e9f2e32a40994e03e96bae0d87e5703b589a`.

Two external reviewers were asked to read this repository cold. Both found the
same defect first, independently, and it is the one I introduced: grouping
scripts/ into folders moved every entry point one directory deeper without
updating how it finds the repository root. All of them resolved to
<repo>/scripts, looked for the study's artifacts under scripts/results/, and
failed in words that blamed the data.

    $ STUDY_MAP=Town06 python3 scripts/verify/certify_town06.py --out /tmp/cert.json
    REFUSING: no clear-weather competence record.

The record is present and tracked. That is the README's headline command, and
it exited 1 on a clean checkout.

This is exactly the failure src/steering/__init__.py documents and that the
library was fixed for -- "moving a file changed where it thought the repository
was, and the failure is silent". The fix was applied to the library and to none
of the entry points. Every one of them now takes REPO from the package.

The shell drivers had the same defect in the same commit: `cd "$(dirname
"$0")/.."` from two directories deep lands on scripts/. Fifteen of them,
including the CARLA launcher, whose photometry reference could not be found --
so the gate that exists because a server once rendered 15% dark for half a day
was falling through to "photometry NOT CHECKED" and passing.

tests/test_repo_root.py is the check that was missing. It imports every entry
point and asserts its REPO equals steering.REPO_ROOT, and asserts each shell
driver climbs as many directories as it is deep. Nothing caught this before
because the suite only ever ran an entry point as far as --help, and --help
touches no path.

The blind-order checkers were broken by the same rename, differently. One
globbed under scripts/results/, found nothing, and printed "verdicts precede
their runs" -- a green light from a check that examined zero cells. The other
resolved paths correctly but used `git log --diff-filter=A` without --follow, so
the rename commit looked like every artifact's first appearance and it reported
the study's central claim as VIOLATED.

Both now use --follow with -M100%. The exact-match requirement is not
decoration: plain --follow matches on similarity, and a pass-2 ledger cell is
about 80% identical to its pass-1 sibling, so it hopped files and dated a cell
twelve hours early -- which read as a violation. With exact matching all four
scopes verify, and the ordering agrees with the timestamps inside the artifacts:
the capped certificate was committed at 12:46:02 and the first pass-2 run
started at 12:49:27.

  the README's headline command      runs, 6/6 verdicts and pose counts
                                     identical to the committed certificate,
                                     worst drift 3.94e-03
  pytest                             283 passed, 24 skipped
  ruff                               clean

<a id="e733a40"></a>
## 2026-09-07 `e733a40` Remove 490 lines of dead code

Author: Zach Asher. Full hash: `e733a403c3232fc2796411cd9b2715d7e1eb78aa`.

Asked whether any is left, and there was. Every module-level definition in the
tree was checked against every real code reference -- names in the syntax tree,
not text in comments -- and twenty-two were referenced nowhere at all.

  perturbations.py     237   nine classes and functions, an earlier generation of
                             the disturbance models. Only Clamp01 is still used,
                             by verifiable_disturbance; the other 90% of the file
                             was superseded and never removed.
  verifiable_disturbance 71  linear_map_for, banded_transmission_box
  carla_env.py           41  set_tire_friction, spawn_depth_camera,
                             decode_depth_metres -- this study uses no depth camera
  route.py               38  build_route, save_route, orphaned when the route
                             builders went; the routes are committed
  expert.py              35  pure_pursuit_steer
  metrics.py             32  signed_cte, within_budget, within_corridor
  config.py              13  exposure_ratio and three constants whose only readers
                             were scripts removed earlier
  dataset, town06_design 12

Four constants that looked dead are kept and they are worth naming, because a
scan cannot tell the difference: ROAD_ROI_ROWS is the region of interest the
paper quotes; TOWN06_PASS3_GATE_MARGIN is read by a test through a subprocess;
T_CLOSED_LOOP_ADMISSIBLE_S records the window the verdicts are insensitive to.
No code reads them and they are still the study's record.

Also checked and clean: no argument is parsed and never read; no file is
unreachable from every import and every documented workflow.

  180 tracked files, 13,626 lines of Python, 15.7 MB
  pytest              248 passed, 14 skipped
  ruff                clean
  PROTOCOL.lock       verifies
  the paper's checker  404 checks, 0 failures

<a id="bd8dc43"></a>
## 2026-09-07 `bd8dc43` Group the library, make config answerable, and fix pre-release loose ends

Author: Zach Asher. Full hash: `bd8dc43b5d7098c8920b60514ec0539cd501d06b`.

The library had the same problem scripts/ had: 22 modules in one flat folder is
where a reader stops. Five subpackages, named the same way the scripts are, so
`scripts/verify/` and `steering/verify/` mean the same thing:

  steering/verify/       certification, captures, scope, the protocol locks
  steering/drive/        routes, the expert, cross-track error, the ledger
  steering/simulator/    the CARLA interface, the port lock, condition checks
  steering/networks/     teacher, student, dataset
  steering/disturbance/  the physically parameterized weather families

config.py stays flat and stays where it is: it is the one module almost every
file imports, and it now opens with a table naming the constant that holds each
number a reader is likely to want, plus the safety criterion in two sentences.
Seven hundred lines of reasoning stay where they are, next to the values they
explain. tests/test_config_header.py fails if the table points at a name that no
longer exists -- a map into a long file is worse than no map when it is stale,
and a docstring cannot fail on its own.

Pre-release loose ends found by checking every path the documents name:

  - PROTOCOL.md cited fifteen files that do not exist -- scripts deleted in this
    release, scripts that moved into folders, pre-registrations that live only in
    history, and a superseded results directory. Same defect as the finding
    numbers: a citation a reader cannot follow.
  - LICENSE still carried Apache's unfilled `Copyright [yyyy] [name of copyright
    owner]` placeholder. It now names the university.
  - CITATION.cff release date.

  180 tracked files
  pytest                     248 passed, 14 skipped
  ruff                       clean
  PROTOCOL.lock              verifies, same digest
  the paper's checker         402 checks, 0 failures
  every path named in a document now exists

<a id="42aeab5"></a>
## 2026-09-06 `42aeab5` Plain language throughout: no lab record numbers, no dates, no names

Author: Zach Asher. Full hash: `42aeab51e19637aad5bbe7c00579fa1a1578c85d`.

Three hundred and fifty comments and docstrings cited the research record by
label -- finding numbers, amendment numbers, question and experiment tags,
simulator rule numbers, protocol section numbers -- and almost none of those
documents ship. A reader met "this is the measurement T06-F25 asks for" and had
nowhere to look. Where the label pointed at something real, the sentence now
says the thing; where it added nothing, it is gone.

  finding numbers      78 -> 0
  protocol sections    54 -> 0
  amendment numbers    51 -> 0
  determinism rules    47 -> 0
  dates                42 -> 0
  simulator rules      38 -> 0
  question tags        19 -> 0
  the author's name    13 -> 0 (it stays in CITATION.cff, where it belongs)

Dated session narrative is gone with them. "Measured 2026-09-02", "destroyed
the evidence twice today", "cost a 12h52m hang overnight" -- the measurement is
what matters and the calendar is not part of it.

The rules that were cited by number are now stated: "restart before every
measurement run" rather than R-SIM-1, "data collected under a violating harness
is not reusable" rather than D-11. The amendments in PROTOCOL.md are numbered
1 to 5 in plain words, and all 27 edits there fall outside the hash-locked
constants -- the lock still verifies against the same digest.

The four teachers moved to Hugging Face. They exist only to re-distil a student
without re-running data aggregation, and nothing else reads them, so they are
3.9 MB that every clone was carrying for a step almost nobody takes:
`scripts/fetch_captures.py --teachers`. Verified by fetching all seventeen files
into a clean tree with every digest matching.

README now opens with `git clone --depth 1`, which is 13 MB. A full clone also
pulls 128 MB of history -- worth having to read how the work happened, and not
otherwise.

  174 tracked files, 15.7 MB
  pytest                        245 passed, 14 skipped
  ruff                          clean
  PROTOCOL.lock                 verifies, same digest
  the paper's checker           402 checks, 0 failures

<a id="d8bbbd0"></a>
## 2026-09-06 `d8bbbd0` Consolidate 171 per-run files, and group scripts by what they are for

Author: Zach Asher. Full hash: `d8bbbd0e39786814a1d69b9286a2781cdf9025ad`.

Approachability, not disk. Opening a folder of fifty files is where a reader
gives up, and most of what was here said the same thing many times over.

DATA. One file per cell instead of one per lap. A cell already had an aggregate
carrying the verdict and the lap detail; each lap's own record now lives inside
it as a `runs` entry, with the provenance of the server that lap was driven on.
The step traces are one traces.csv per ledger with a `run` column, and the 51
seed-screening files are one table.

  96 per-run ledger json  ->  absorbed into the 24 cell files
  24 trace csv            ->  1 traces.csv
  51 seed json            ->  1 seed_screen.json
  results/                227 files -> 57

aggregate_ledger_runs.py already wrote `runs`; it now attaches each run's own
provenance rather than describing three laps by the first one's, and it folds
the traces. Rebuilding a committed cell from its per-run artifacts reproduces
the committed file exactly apart from its aggregation timestamp -- checked.

SCRIPTS. Five folders by purpose, so a reader can skip four of them:

  scripts/verify/     11   recompute the certificates, no simulator
  scripts/capture/     5   render the frames the certifier reads
  scripts/drive/       7   the closed-loop ledger
  scripts/simulator/   7   launch, restart, health-check CARLA
  scripts/training/   14   build the networks

requirements.txt is back, as a pointer. Its absence reads as an omission rather
than a decision, and researchers look for it. Three lines: use `pip install -e .`,
or the bootstrap for the exact recorded environment, and why four dependencies
cannot come from a resolver.

  346 tracked files -> 178
  pytest   245 passed, 14 skipped
  ruff     clean

The paper's checker reads six things that moved. CHECK_DATA_UPDATE.patch is the
change, verified against this tree at 402 checks and 0 failures -- the same count
as before, so nothing it checks was lost. It applies cleanly and is for Zach to
apply in his own repository.

<a id="9e33b8f"></a>
## 2026-09-06 `9e33b8f` Put the training pipeline in its own folder, and the paper's figures back in the paper

Author: Zach Asher. Full hash: `9e33b8f09a8c8ac2de63f57b50fc18d04075d650`.

Most readers never build a network -- the eight are shipped -- so the thirteen
files that do it now sit in scripts/training/ and can be skipped wholesale.
What is left at the top of scripts/ is the two things a reader actually does:
recompute the certificates, and re-drive the closed loop.

  scripts/                 certify, drive, capture, fetch, simulator control
  scripts/training/        collect, train, DAgger, distil, gate, the pipelines

The three paths the paper's checker reads by name -- certify_town06.py,
certify_sustained_bound.py, capture_offset_yaw.py -- are untouched, so nothing
in the paper repository has to move again for this.

To be clear about what "reproducible training" means here: these are the files
that built the shipped networks, and running them again rebuilds them by the
same method. They are not a separate re-training path. The searches that CHOSE
those networks -- the seed sweeps, the width sweeps, the architecture probes --
were removed in the previous commit and stay in git history. Reproducing this
study means reproducing the method, not re-running every experiment behind it.

The rendered paper figures are gone. They belong in the paper repository, which
generates them; keeping PNGs of them here was a second copy that could drift.
The night animation stays: it is not in the paper, it shows the policy driving,
and it is the one thing that makes the result visible at a glance.

Two harness details the move exposed. scripts/training/dagger.py imports its
neighbour `train`, which works when you run it -- Python puts the script's own
directory on the path -- and does not when a test loads it by file path. The
import probe now adds that directory, which is what running it does.

  the paper's figures/check_data.py, run directly   402 checks, 0 failures
  pytest                                            245 passed, 20 skipped
  ruff                                              clean

A clone checks out 19 MB, of which 6.2 MB is the animation and 8.8 MB the
networks. The code, protocol and routes are 1.2 MB.

<a id="dd1d758"></a>
## 2026-09-06 `dd1d758` Cut to what the study needs, and name things for what they are

Author: Zach Asher. Full hash: `dd1d758a56d802dbedd70af3cc8ba813a0e03089`.

The previous version kept the whole apparatus on the principle that a committed
artifact needs a committed generator. That rule earns its keep for artifacts the
paper cites, and not for anything else, so the rest is gone.

Removed, 16 files:
  - audit_repo.py, 759 lines of assertions about findings documents that now
    live only in git history. check_blind_order.py stays: it is the standing
    rule-1 check, and it is the one an outsider can run.
  - the seed-search cluster -- select_student_seed.sh, select_mixed_student_seed.sh,
    pass3_sweep_widths.sh, gate_candidates.py, compare_student_variants.py,
    finish_town06_lap.sh. It searched for the shipped students; the students are
    shipped and pinned by their .selected files, and neither retraining pipeline
    calls any of it.
  - the route builders -- build_routes.py, build_town06_lap.py,
    build_town06_sections.py, route_design.py, mapsurvey.py. The routes are
    committed; these build a NEW road.
  - carla_health_check.py, which R-SIM-5 says not to run routinely anyway.
  - CHANGELOG.md. Git history and releases already carry it.
  - the two pre-harness highway checkpoints. The paper reports the rebuild, and
    rule D-11 calls the data behind those unusable, so they were shipping a
    policy nothing here uses.

Renamed, because a reader should not have to learn the lab's bookkeeping:
  results/town04_v2  -> results/highway
  results/town06     -> results/arterial
  results/town06_logs-> results/arterial_logs
  results/diagnostic -> results/fidelity
  data/routes*       -> routes/highway, routes/arterial

The routes moved out of `data/` entirely. They are a committed study artifact;
`data/` is 59 GB of regenerable training frames that are not shipped, and having
both under one name is what made the folder confusing.

TOWN04_REDO is gone. With the pre-harness checkpoints removed there is nothing
left to switch between, so the highway study is simply the highway study and its
commands take no flag. That deleted the certifier's hardcoded answer key too --
it belonged to students this repository no longer contains, and a certifier
carrying a truth table is the wrong shape regardless.

README is 101 lines and two images, down from 130 and six. It describes the
study; it no longer reproduces the paper's figures.

  the paper's checker, run from a scratch copy   402 checks, 0 failures
  pytest                                         245 passed, 20 skipped
  ruff                                           clean
  fetch_captures round trip from a clean tree    12 downloaded, all digests match

70 Python files and 16 shell, 13,992 lines. A clone checks out 19 MB.

NOTE: the paper repository's figures/check_data.py reads the old paths and will
need the same rename. It was verified here against a scratch copy; that
repository is deliberately untouched.

<a id="1767719"></a>
## 2026-09-06 `1767719` Make a clean checkout actually work, and prove it from one

Author: Zach Asher. Full hash: `17677198b833dc5b5f8b86298626f1f377cdaf34`.

Building the repository from a clean checkout in an empty virtual environment
found three defects, none of which anything here could have caught, because
every check ran on the one machine that already had everything installed.

`pip install -e .` was unsatisfiable. numpy was pinned to the 1.26.4 the
published bounds record, and opencv-python declares numpy>=2, so the first
command the README gives failed for every reader. pyproject now declares a
floor and bootstrap_env.sh installs the recorded version with opencv under
--no-deps, then checks which numpy actually survived the resolve -- an install
that quietly lands on numpy 2 still certifies and still prints margins, and is
no longer the environment the artifacts record. Certifying under numpy 2.2.6
was measured against 1.26.4 and agrees to 1e-9, so the floor is safe for the
casual install and the bootstrap is what reproduces the environment of record.

`interpolation_fidelity.py --help` hung for two minutes. It called
require_cuda() above its argument parser, and require_cuda retries for two
minutes on purpose, because CARLA holds the device while it starts. On a
machine without a GPU -- every machine a reader checks this work on -- asking
for help waited for hardware it did not need. The new ordering test reads the
call order inside main() rather than in the file, because two other entry
points call require_cuda from a helper defined above the parser and invoked
after it, which a text-position check reads as a defect.

steering.route imported the CARLA client at module scope for one function that
needs a live world map anyway. That put a wheel shipped with the simulator in
front of every geometry helper and, with it, in front of the certification path
the README calls simulator-free. The import is now local, and the level-1 path
no longer reaches a single module that imports CARLA.

Tests that genuinely need CARLA or auto_LiRPA now skip with a reason instead of
failing. The judgement is in one helper in conftest and stays narrow: only
those two names, and only when they are really absent, so a real ImportError
still fails.

tests/test_capture_manifest.py checks the fetcher's digest table is well formed,
lands every file where a certifier reads, covers both studies, and matches the
captures byte for byte on a machine that has them.

  the paper's figures/check_data.py    402 checks, 0 failures
  pytest                               276 passed, 19 skipped
  scripts/audit_repo.py                267 passed, 0 failed
  ruff                                 clean
  the same suite on a clean checkout,
  no CARLA, CPU torch                  129 passed, 45 skipped

<a id="42e1b10"></a>
## 2026-09-06 `42e1b10` Documentation, packaging metadata, lint, and the capture fetcher

Author: Zach Asher. Full hash: `42e1b10c3e3825f63bb1bc914b46cae9f6199ff9`.

The public-facing half of the finalisation.

README is rewritten around the study's actual result rather than the layout of
the repository, and around the paper's own figures, regenerated here as images:
the witness plot first, because a network whose steering error at the captured
condition sits inside tolerance and which leaves the road on every lap is the
finding. Every number in it was checked against the artifacts -- the night
departures are 34.0 m on all six runs, the shipped networks are ten and 9 MB,
agreement is twelve of twelve on the highway and four of five on the arterial
with one void cell and one real disagreement.

REPRODUCING keeps its three levels and its measured account of what reproduces
to what precision. Its checkpoint table named the superseded six-section
students; it now names the two the paper reports.

CLAUDE.md is one short file in plain English, and it is the only one.

scripts/fetch_captures.py retrieves the 641 MB of captured frames from Hugging
Face and checks every file against a digest recorded in the script. A capture
is the certifier's entire input, so a bound computed from the wrong frames is
not a weaker result, it is a statement about a different experiment -- and it
still prints a verdict and a margin and looks finished.

.gitignore now ignores results/, data/ and checkpoints/ wholesale. Tracked
files are unaffected; what it stops is `git add -A` quietly enlarging the
published record with working output -- there are 653 MB of sweep checkpoints
and 22 GB of superseded captures sitting in those directories right now.

Linting found a real defect I had just introduced: `wilson` was extracted into
steering/ledger.py without carrying `import math`, and every one of the 112
import tests passed, because nothing calls it at module scope. It would have
failed the first time somebody aggregated a ledger, which happens after the
driving, at the end of a long run. tests/test_extracted_helpers.py now calls
each extracted helper, and the new test does fail when the import is removed
again. The extracted `wilson` agrees with the original on all 91 cases up to
n=12.

Two entry points ran their body on --help: audit_training_data.py and
report_laps.py, the second exiting non-zero when the ledger it reads is empty.
Both now parse arguments first, and the entry-point test covers 26 scripts
rather than 11.

Ruff is configured to pyflakes, the pycodestyle errors and RUF100, and
deliberately not the stylistic families: this is a finished record and the
paper's checker asserts on strings inside three of these files. Those strings
are unchanged and verified.

  the paper's figures/check_data.py   402 checks, 0 failures
  pytest                              253 passed, 4 skipped
  scripts/audit_repo.py               267 passed, 0 failed
  ruff                                clean

<a id="34d81b9"></a>
## 2026-09-06 `34d81b9` Make this an installable package instead of 96 sys.path inserts

Author: Zach Asher. Full hash: `34d81b9243bb428304273384ecc8a098b54061b2`.

Nothing imported cleanly on its own. `pipeline/route.py` began with
`from config import ...`, which resolves only when some caller has already run
`sys.path.insert(0, "pipeline")` -- there were 96 such inserts in 17 different
spellings, and a module that is only importable via its callers cannot be
tested, reused or reviewed in isolation.

The rule now is that scripts/ holds things you run and src/steering holds
things you import.

  pipeline/*.py          -> src/steering/          the library
  study/                 -> src/steering/study/
  pipeline/{train,dagger,distill,collect_data,...}.py -> scripts/
  pipeline/data/         -> data/
  pipeline/checkpoints/  -> checkpoints/
  pipeline/results/*.csv -> results/oracle/

Five scripts imported helpers from four other scripts, which is the same defect
one level up. Those helpers are now library code where they belonged:

  steering/captures.py     capture loading and pose scoping, out of certify_town06
  steering/ledger.py       the ledger directory and the Wilson interval
  steering/model.py        load_model, out of evaluate
  steering/route_design.py the route-selection criterion, was build_study_route

REPO_ROOT is defined once, in steering/__init__.py, and honours
STEERING_REPO_ROOT. Every module used to count directories up from its own
file, so moving a file changed where it thought the repository was -- and that
fails silently, because a missing checkpoint reads as "not built yet" rather
than "looked in the wrong place".

pyproject.toml replaces requirements.txt as the source of truth for the four
dependencies a resolver can install. torch, auto_LiRPA and the CARLA client
stay out of it: none of the three installs correctly from a plain resolver, and
bootstrap_env.sh already installs them in the right order and proves the result.

New tests/test_imports.py imports every module as its own process under both
maps -- 112 cases. The training and capture paths need CARLA and a GPU, so no
other test touches them; without this, a refactor that broke one would surface
months later on someone else's clone.

The paper's checker reads three scripts by path and asserts on strings inside
them. Those paths and strings are unchanged; the two data paths it reads moved,
and figures/check_data.py plus five figure generators are updated in the paper
repository to match.

  pytest                              209 passed, 4 skipped   (was 100)
  scripts/audit_repo.py               266 passed, 0 failed
  the paper's figures/check_data.py   402 checks, 0 failures

<a id="f6ab839"></a>
## 2026-09-06 `f6ab839` The driver mismatch was six ticks, and the scored driver was missing R-SIM-4

Author: Zach Asher. Full hash: `f6ab83918eb0b02b5dc262b206dc518e4f38ff42`.

DIAGNOSIS. pipeline/evaluate.py ticks the world SIX times before driving, to
grab a rendered frame for the R-SIM-4 condition check. closed_loop_ledger.py
went straight from set_condition to teleport + warmup. Six ticks of extra
settling changed where warmup ended by about a millimetre, and the closed loop
amplified that into a different discrete basin.

  step 0, same checkpoint and condition
    evaluate.py  x 656.866  y 15.377  steer -0.03149
    ledger       x 656.867  y 15.380  steer -0.03291

That is the whole cause. Ruled out earlier by measurement: scoring scope (both
exclude bridged steps and both drive 1274 rows), route, spawn, warmup
procedure, and the departure threshold. The loops are otherwise equivalent.

Supporting evidence that it is basin selection rather than noise: the ledger
is bit-REPRODUCIBLE across reps -- rep00, rep01 and rep02 agree to 0.000000 m
and 0.000000 steer over the whole lap, with rep03 landing in another basin. So
each driver deterministically re-lands its own basin, which is why one gave
1.42 ft twelve times and the other 0.97-1.34.

THE REAL FINDING, and it is worse than the mismatch. R-SIM-4 -- "verify the
rendered condition from a FRAME, every run" -- was implemented ONLY in
evaluate.py, the sweep and gate driver. The driver that writes the SCORED
LEDGER, the numbers that get published, never did it. The rule was enforced on
the diagnostic path and not the authoritative one, and the failure it guards
against (Town04 fog leaking into the night cells) is invisible in every
downstream number. set_condition's verify_condition reads the weather STRUCT
back, but the struct is what was asked for, not what the camera sees.

FIX. The ledger now runs the same check, before it drives. That closes the gap
AND aligns the tick counts, and the two drivers now agree:

  ledger before   1.42 x12
  ledger after    0.97, 0.97, 0.98
  evaluate.py     0.97 x3, 0.99, 1.34 x2

CONSEQUENCE, declared rather than discovered later: this shifts the ledger's
basin selection, so future ledger numbers will differ from the committed ones
on marginal cells. PROTOCOL R4 keeps pass 1 and pass 2 standing and neither
was touched; this is a change for work from here on.

audit 292 -> 297, including a check that both drivers settle the same number
of ticks before driving, because a mismatch there selects a different basin.

<a id="14a6277"></a>
## 2026-09-06 `14a6277` Q7: the cross-road fog comparison survives at matched input size, by 9-31x

Author: Zach Asher. Full hash: `14a6277cd29a58ce05bb4a13f76070d595ce4d9c`.

E7 refuted the CAPACITY reading of the Town04/Town06 fog asymmetry but could
not address input size -- its Town06 students were all 168x56 while Town04's
are 84x28, so the published comparison still confounded road with projection.
Q7 removes that confound.

  road    student                ReLU     input    fog bound   verdict
  Town04  S_mixed (published)   15,456    84x28       0.23     CERTIFIED
  Town04  S_clear (published)    5,152    84x28       0.79     CERTIFIED
  Town06  S_q7    (Q7)          20,608    84x28       7.14     not certified

At the SAME projection, Town06's fog bound is 9x to 31x wider, and on the
wrong side of a corridor where both Town04 cells certify comfortably.

All three predictions held. P1: the 84x28 student's bound is worse than the
168x56 one's (7.14 vs 1.86). P2: the A-3 capture gate passes at 0.0150 over
1055 poses against a 0.05 threshold -- better than Town06's committed 0.0261.
P3: the comparison survives.

And it is conservative in the right direction. Q7's student is LARGER than
Town04's (20,608 vs 15,456 ReLU), and E7 established that Town06's fog bound
gets worse as the network shrinks -- so matching Town04's capacity exactly
would widen the gap, not close it. 9-31x is a lower bound.

The capture set was compared against what it parallels before being believed:
same 1060 poses, same 2111.0 m scored span, correct projection, 25.1 MB
against 98.2 MB where quarter resolution predicts 0.25. That is the check
Town04's redo failed at 1.8 MB against a published 1.7 GB.

Caveats recorded rather than buried: the recipes are not identical (Q7 uses
the tuned+balanced recipe, Town04's students are published-era), it is one
seed on the new projection, and the 84x28 student was never driven under the
ledger -- Q7 is a certification result, not a driving one.

So the sceptical reading of the published comparison now fails on both axes:
capacity (E7) and input size (Q7). Fog on Town06 is harder to certify at every
capacity and every projection measured.

<a id="29b5866"></a>
## 2026-09-06 `29b5866` Q8c findings, and a correction header on Q8b

Author: Zach Asher. Full hash: `29b5866c2c9cfdf4c363b1787cb1fb35188c6ab0`.

Two results, one of which corrects a conclusion I wrote four hours earlier.
Neither needed the complete verifier the queue budgeted a day for.

1. The beta-CROWN wall was the ROOT SHAPE. auto_LiRPA's patches path asserts
   image.ndim == 4 on the root, and this study's root is the 1-D disturbance
   parameter, so patches was refused and the memory-hungry matrix path forced.
   Behind a (1,1,1,1) root the same shipped sub-problem goes from CUDA OOM to
   unsat in 1.29 s. My "the shipped cells do not run" was a shape problem
   wearing a scale problem's costume.

   Zach's remembered patches/stride bug is not this and does not apply: the
   early history (65ec8ae) shows the previous generation on a vendored
   SDP-CROWN fork over a pixel-space L-inf ball across 7,056 dims -- a 4-D
   image root, the patches path. The current 1-D model could not reach that
   code at all until now.

2. Both "undecided" cells are FALSIFIED, with witnesses, and this needed no
   verifier. falsify_witness searches a single GLOBAL intensity; the certifier
   quantifies over one intensity PER POSE. Searching that larger set gives
   attained lap-mean bias of +1.179x tolerance on fog and -1.210x on night.
   Attained means the true bound is at least that bad, so no sound method can
   certify either cell -- the refusals are correct and were never slack. CROWN
   was within 5% of the truth on fog all along, which is also why alpha-CROWN
   could only find 3.4%.

   The check that had to pass: low_sun, the one CERTIFIED cell, has NO
   witness. All six cells now resolve as five refusals with witnesses and one
   certification without.

The caveat is reported rather than buried: the fog witness uses 90 distinct
intensities across 133 poses. It is inside the declared family, so the refusal
is correct, but it is not a smooth fog field. The gap between the two readings
-- 0.845x for a single global intensity, 1.179x for per-pose -- is 0.334x
tolerance, and that is the measured price of quantifying over spatially
varying disturbance. The paper should state it.

Q8B_FINDINGS keeps its wrong conclusion with a correction header rather than
being rewritten, so the error and its fix sit together.

<a id="c998ea8"></a>
## 2026-09-06 `c998ea8` Q8c: both "undecided" cells are FALSIFIED, with witnesses -- and no beta-CROWN needed

Author: Zach Asher. Full hash: `c998ea88a1182d9c6dd98a11e4907ae7178a94f7`.

  fog      attained hi  +1.179 x tol   WITNESS (hi side)
  night    attained lo  -1.210 x tol   WITNESS (lo side)
  low_sun  -0.207 .. +0.289 x tol      no witness   <- and it is the CERTIFIED cell

The two Town06 cells the paper calls undecided are not undecided. They are
correctly refused, and a witness for each can be exhibited.

WHY IT WAS OPEN. falsify_witness.py searches a single GLOBAL intensity s and
finds fog peaking at 0.845x tolerance -- no witness. Its own docstring says
why that is not conclusive: the certifier bounds, per pose, the worst case
over s and THEN averages, so s is free to vary from pose to pose, covering
spatially varying disturbance. It quantifies over a strictly larger set than
one global intensity, "so a NOT_CERTIFIED cell may have no witness at all:
sound, undecided".

The missing measurement was that larger set. Searching one intensity per pose
-- which is what the certificate quantifies over -- the attained lap-mean bias
is 1.179x tolerance on fog and -1.210x on night. Both are ATTAINED values, so
the true cell bound is at least this bad, and no sound method can certify
either cell. The refusals are correct.

That also settles Q8 without a complete verifier: CROWN's slack on fog is only
1.240 - 1.179 = 0.061x tolerance (5%), and alpha-CROWN's is 0.019x (1.6%). The
excess over the corridor was never relaxation slack; it was real.

The consistency check that matters: low_sun is the one CERTIFIED cell and the
search finds NO witness for it. A witness there would have meant an unsound
certificate.

So all six Town06 cells now resolve cleanly -- five NOT_CERTIFIED cells each
with a witness, one CERTIFIED cell without. The three-way reading collapses to
two, which is a stronger statement than the paper currently makes.

<a id="ce8232a"></a>
## 2026-09-06 `ce8232a` A1: the best policy passes every scored ledger cell, and the bound refuses two

Author: Zach Asher. Full hash: `ce8232a7c31c329b555d564eae08f37aadf11dcb`.

lr 3e-4 plus --balance, the two levers Q1 and Q4 found. Certificate committed
before any lap; R1 verified.

  ledger      clear PASS 0.79   fog PASS 1.34   low_sun PASS 1.30   night PASS 0.85
  certificate                   fog +2.11x NOT  low_sun +0.29x CERT  night +3.38x NOT
  agreement 1/3

A1-P2 FALSIFIED, and it is the result that matters: FOG IS NO LONGER THE
STOPPING CONDITION. Fog held 3/3 at 1.08 ft inside pass 3's own margin -- the
first student in this study to do it -- and LOW SUN stopped the gate instead.
Balancing did not just improve fog, it moved the failure. "Fog stopped every
one" describes pass 3 accurately and is no longer a general statement about
this pipeline.

The soundness question was live and is answered. Before the drives the
certificate and the gate disagreed in BOTH directions at once: the bound
refused fog (which the gate had just cleared) and certified low sun (which had
just stopped the gate at 2.12 ft). Had low sun then driven FAIL that would
have been a false certificate. It drove PASS 3/3 at 1.30 ft. No cell has ever
been CERTIFIED while driving failed, in any experiment here -- Q3, V3 and A1
tested it on three different students.

The driver discrepancy V2 opened is bigger than "one runs hot": it is not a
constant offset and it changes verdicts.

  fog       gate 1.08 -> ledger 1.34   (+0.26)
  low_sun   gate 2.12 -> ledger 1.30   (-0.82)   gate-failing vs comfortably passing

So comparisons crossing the two driver families are unsafe until understood.
A1's gate is compared only against pass 3's gate, and A1's ledger only against
the canonical ledger.

For the paper: the Limitations sentence saying the binding constraint is
distillation rather than verification is no longer supported for the best
student available. It passes every scored ledger cell and the bound refuses
two of three. The constraint has moved to the bound's looseness.

<a id="2f918d5"></a>
## 2026-09-05 `2f918d5` V2: the paper's 0.98 ft student drives fog at 1.42 ft, twelve times out of twelve

Author: Zach Asher. Full hash: `2f918d5da65b3acbe8857863e098239dc1b84820`.

Through closed_loop_ledger -- the instrument that writes the study's scored
ledger -- the student lands on 1.42 ft in all twelve laps, to two decimal
places, and clears pass 3's 1.095 ft margin ZERO times. Through evaluate.py,
the driver the original claim came from, it ranges 0.97-1.34 and clears the
margin 3 of 6.

Either way 0.98 ft is the favourable end of a distribution, not a property of
the student, and the draft should not rest a Limitations sentence on it.
E4-F1's "the first student in this study to clear pass 3's margin gate on fog"
does not survive the scored instrument at all.

P2 held in an extreme form: twelve laps, ONE distinct value. The shipped
student's fog cell gave six distinct values over 24 laps (V1). So
multimodality is a property of the particular policy rather than of the
harness -- more evidence the harness is not what makes cells void.

OPEN ITEM, recorded rather than guessed at: the two committed drivers disagree
systematically on the same checkpoint, same GPU, same night, by about 0.4 ft.
Ruled out by measurement -- scoring scope (both exclude bridged steps; the
ledger's 1274-row trace is 1179 non-bridged + 95 bridged, and evaluate.py's
"1179/1280" is exactly that non-bridged count), route and spawn (identical
teleport + warmup), and a bridged peak (the ledger's peak is at s = 206.7 m,
far from either span). A departure-threshold difference exists (4.0 m vs
6.0 m) and cannot explain a peak-CTE gap. The cause is a real trajectory
difference and is not yet identified.

It matters because the study's two number families come from these two
drivers: the scored ledger and the paper's agreement figure from one, and
E4/Q1/Q2's gate/Q4/pass 3 from the other. Every comparison made so far was
driver-consistent within itself, so nothing is invalidated -- but a sweep
number and a ledger number are not interchangeable, and the paper's 0.98 ft
sits in a Limitations paragraph otherwise discussing ledger results.

<a id="3f6da90"></a>
## 2026-09-05 `3f6da90` V1: the VOID cell's excursion has a location, and the lap that voided it was measured on different hardware

Author: Zach Asher. Full hash: `3f6da904ed6768f4a8501548bcba718f07d7aa57`.

24 laps of the canonical checkpoint under fog: min 1.19, median 1.19, max
1.66 ft against a 2.19 ft budget. 0/24 over budget, 0 departed, SIX distinct
values with fourteen laps landing on exactly 1.19 ft. E1b's discreteness
signature, reproduced on the cell that matters.

P1 and P2 held. P3 and P4 failed, and they are the informative ones.

P3 predicted 10-50% of laps over budget because one canonical lap in three
was. Measured 0/24, Wilson 95% upper bound 13.8%. P4 predicted the canonical
laps fall inside V1's clusters: 1.33 and 1.47 do, 5.25 does not -- it is 3.2x
V1's worst lap and was not sampled in 24 tries.

The prereg said a P4 failure is a harness question that takes priority, so the
harness was checked and the 5.25 lap's own provenance is CLEAN: per_run
granularity, independent runs, deterministic control on, frozen rules intact,
correct server flags, git clean. Not a violation, not a dependent chain, not a
degraded server.

What differs is the MACHINE. Pass 1 was driven 2026-09-03 00:27, pass 2 at
12:49, and the RTX 5090 landed at 22:56 the same day. The migration
re-verified the certificate (offline, all six verdicts) and the oracle
(bit-identical CSVs) and explicitly did not re-drive the closed loop. So the
paper's "reproduced by an independent second pass" is a WITHIN-hardware
reproduction, and V1 is the first closed-loop cell ever driven on this GPU.

That matters because E1b's mechanism is renderer-driven: ~30 differing pixels
per frame select among discrete basins. A different GPU changes that input,
and photometry agreeing to 0.003% is not bit-exactness.

The excursion also has a location, the same one every time -- s = 50.8-55.3 m,
step 22-26, inside the route's FIRST curve (2.81 deg/vertex, second-sharpest
of seven spans on a lap that is 83% straight), met immediately after the
student takes over from pure-pursuit with no straight section to settle on.
That is the cause standing rule 3 asks for, measured on this cell.

This does NOT clear the cell and V1 wrote nothing to the committed ledger.
Rule 3 forbids converting a void cell into a rate. What it licenses is a
better sentence than "VOID", and a larger question: if basin selection is
hardware-conditioned, every closed-loop number in the study is conditioned on
a GPU the lab no longer has while every certificate number is not. V3 is
already running to test exactly that.

<a id="d8d9feb"></a>
## 2026-09-05 `d8d9feb` Q8b: integration validated, both undecided cells still undecided, reasons measured

Author: Zach Asher. Full hash: `d8d9febcec4bf8a667b6382a4c08a40f81139ee4`.

INCOMPLETE, and under its own pre-registered rules it is not allowed to be
otherwise: the prereg requires the loop to reproduce FALSIFIED on the
witness-carrying cells BEFORE any result on the undecided ones, and says that
if it does not, no such result is reported. It does not yet, so none is.

  Q8b-P1  shipped cells time out          CONFIRMED, more strongly -- CUDA OOM
  Q8b-P2  small nets decide in budget     SPLIT: yes per sub-problem, no per cell
  Q8b-P3  a decided cell is CERTIFIED     NOT REACHED

What works, validated end to end at 12,736 ReLU: export, the A-1 fidelity gate
(6.3e-07 to 7.5e-07 against a 1e-5 threshold), and beta-CROWN returning unsat
in 5.0 s. The strongest evidence the exported graph is the study's network is
not the replay but the bound: abcrown's own CROWN result agrees with the
study's Bounder to SIX DECIMALS on both students, across two torch versions
and two numpy majors.

Four findings.

1. The clamp is provably inactive and was blocking branch-and-bound entirely.
   Clamp01 exports as a subtraction and abcrown raises
   NotImplementedError(BoundSub) when branching through it -- bound
   propagation works, complete verification cannot run at all. It need not:
   the image is a convex combination of two real captures, both in [0,1], so
   over t in [-1,1] the exact elementwise range is [0.0243, 0.5808] and the
   clamp cannot fire. The builder computes that range and REFUSES to drop the
   clamp if it leaves [0,1]. With it gone the graph still matches the study's
   CLAMPED forward pass to 6.26e-07.

2. The shipped cells do not time out, they do not run. patches mode asserts
   image.ndim == 4 -- it assumes a 4-D root and ours is the ONE-DIMENSIONAL
   disturbance parameter -- and matrix mode OOMs at 7.17 GiB on top of 25.30
   on a 31.35 GiB card. The reparameterisation that makes this study's
   property cheap to STATE is what puts it on the unoptimised path.

3. Even 12,736 ReLU is intractable per CELL: 133 poses x 16 sub-intervals =
   2,128 sub-problems, ~3 h for one threshold pass against a declared 2 h
   budget, and exact per-pose bounds need bisection on top. Separability makes
   the decomposition exact, not cheap.

4. The counterexample path is blocked by plumbing, not scale. On a provably
   falsifiable instance BaB exhausts the space ("all nodes are split", 58
   domains, 5.6 s) but reports timeout rather than sat, because witnesses come
   from the PGD attack, which needs a batch -- and the graph's static reshape
   is batch-1. Exporting with -1 was tried and is worse: it emits a dynamic
   Shape/Split subgraph auto_LiRPA cannot bound. An ONNX reshape with a
   leading 0 would be static AND batch-preserving; that is the next step.

Canonical certificate, both ledgers and the witness exhibit untouched. Study
venv verified unmodified at torch 2.13.0+cu130 / numpy 1.26.4.

<a id="d7f40e1"></a>
## 2026-09-05 `d7f40e1` Q8b machinery: export a sub-problem, and PROVE the exported graph

Author: Zach Asher. Full hash: `d7f40e15a1bc042ce4ddeb197e2b0725fb6199ff`.

The verifier runs out of process (amendment A-1), so the two sides meet at
ONNX. An export is a re-implementation of the network by a translator, and a
verdict about a mistranslated graph is sound and about the wrong network --
the same shape as A-3's mis-rigged camera, correct downstream of a wrong
artifact. So the gate comes before any verdict, not after.

GATE CLOSED on the first sub-problem: max |study - onnx| = 7.45e-07 over 1000
inputs, against the 1e-5 declared in A-1.

The split across environments is the design, not a workaround, and it makes
the check STRONGER. torch.onnx.export needs `onnx` and the replay needs
`onnxruntime`; neither is in the study venv and neither may be added, because
pulling them risks moving numpy off 1.26.4. So the study side emits the
problem (W, b) and its own forward pass, and the graph is built AND checked
inside .venv-abcrown. The agreement therefore spans the translation and the
torch 2.13 -> 2.11 / numpy 1.26 -> 2.4 gap together, which is exactly what a
verdict computed in that environment depends on.

.venv-abcrown imports THIS repo's student.py and verifiable_disturbance.py --
opencv-python-headless was added there to make that possible -- so the
architecture and the disturbance head are never written down twice. A
duplicated model definition is how the exported graph and the certified graph
drift apart while both look right.

Two things recorded per sub-problem so any verifier answer can be bracketed:
the 1000-point grid extremes (values actually ATTAINED, so a sound bound
cannot be tighter) and plain CROWN's bound from the study's own Bounder (a
sound upper bound, so an exact answer cannot exceed it).

On the first fog sub-problem those bracket tightly: grid [-0.18331, -0.15801],
CROWN [-0.18492, -0.15690]. The upper slack is 0.0011, about 9% of tolerance
-- independent corroboration of Q8a's finding that fog's bound is nearly tight
and its excess is largely real rather than relaxation.

LinearDisturbance.forward does .view(1,3,h,w), so the head is batch-1 by
construction; both sides feed it one input at a time.

<a id="0832810"></a>
## 2026-09-05 `0832810` Q8a: alpha-CROWN resolves neither undecided cell, and the slack is not where I predicted it was

Author: Zach Asher. Full hash: `0832810e6508a0804663a2cb078c85e142494f9f`.

  cell      plain CROWN   alpha-CROWN   tightening   verdict
  fog          +1.2400       +1.1983        3.4%     NOT_CERTIFIED
  night        +2.8361       +1.5581       45.1%     NOT_CERTIFIED
  low_sun      +0.2991       +0.2909        2.7%     CERTIFIED

P1 HELD: neither cell resolves, so the cheap route to closing the question
fails. That is the result Q8a existed to get -- it had to be tried before
beta-CROWN could be justified.

P1's arithmetic was wrong even though its conclusion was right. It projected a
uniform 6% gain from the Methodology note and predicted fog -> 1.166, night ->
2.666. The gain is strongly cell-dependent: 3.4% and 45.1%. That 6% came from
one cell of a different sweep and should not be used to budget alpha-CROWN.

P2 FALSIFIED by a factor of thirteen, and backwards. I predicted fog would
tighten MORE, reasoning that a bound near its witness holds less slack.
Measured, night tightened 45% and fog 3.4% -- night's refusal was mostly
relaxation slack, fog's is not. The reasoning conflated two independent
properties: fog sits close to a witness AND is close to tight; night sits far
from its witness AND was mostly loose. Proximity to a witness does not bound
the available slack.

The prereg said what to do if this happened, so Q8b's expectations are
reconsidered before it runs and recorded in the findings: fog is the HARDER
target with only 0.35x of headroom left to its witness, night is now the
better candidate to be resolved, and Q8b-P3 (a decided cell comes back
CERTIFIED) is in doubt for fog specifically. P3 stands as committed -- it is
not being edited after the fact -- with a note that Q8a moved the odds against
it for one of the two cells.

Cost measured rather than quoted: ~17x plain CROWN, not the 78x the Bounder
docstring records. Both the 6% and the 78x come from the same single-cell
measurement and both are wrong here in opposite directions, so the standing
argument for plain CROWN ("78x the cost for 6% tightness") does not hold on
these cells.

Canonical certificate untouched and verified unmodified; both refusal guards
fired when tested. The alpha result is a separate artifact carrying
_meta.method = CROWN-Optimized so it can never be read as plain CROWN.

<a id="f5b4db3"></a>
## 2026-09-05 `f5b4db3` Q4: balancing replicates at twelve seeds, and is the first driving-endpoint win

Author: Zach Asher. Full hash: `f5b4db3e7bd6c8b1d87cb382be0e05d62a56c488`.

48/48 cells, no failures. All four predictions held. Fold-in validated
bit-exactly against E6's checkpoints before use.

  seeds holding fog 3/3   bal 10/12   curv 6/12   raw 5/14
                          bal vs raw Fisher p = 0.0119

This is the first training-side lever in the study to reach significance on a
DRIVING endpoint. Q1's learning rate reached p = 0.0079 on KD error but only
p = 0.0553 on driving; balancing reaches p = 0.0119 on driving itself.

The primary endpoint was pre-registered as the FAILURE COUNT, not the median,
and the measurement vindicates that: the median moves 2.33 -> 1.68 ft at
MW p = 0.0667 (not significant) while the failure count moves 9/14 -> 1/11 at
p = 0.0119. E6-F1's claim -- balancing does not move the typical student, it
removes the failures -- reproduces at twice the seeds. Pre-registering the
median would have reported a null result on a real effect.

P3 held: clear IMPROVES, 0.97 vs 1.19 ft, 10/10 held. The repo's stated reason
for rejecting balancing has now been contradicted by measurement twice and
should be retracted in the code comment, not just unsupported.

The result I did not expect, and the most useful one:

  fog KD p99 median   raw 0.0732   bal 0.0658   curv 0.0544

curv has the BEST distillation error of the three arms and the WORST driving
record (6/12), plus seven VOID cells out of 24 -- five of them in clear, the
condition every other arm holds comfortably. After Q1 made the KD endpoint
look like a cheap proxy for driving (far more sensitive), Q4 shows the proxy
can point the wrong way about which arm to ship. Screen with it, never decide
with it.

Also fixes a scoring bug in my own summariser: P1 required 12 MEASURED cells,
but VOID cells are excluded from the denominator by design, so a VOID was
being scored as a falsification -- penalising the arm for a harness outcome
and making the prediction unfalsifiable in the good direction. The prediction
is a count of holders out of the seeds attempted. Same class as the Q2-P3
ordering bug: the scoring code, not the data.

Provenance recorded rather than hidden: the new cells carry git_dirty=True
because arm_sweep.sh appends to its own TRACKED sweep.log. E6's cells recorded
clean only because that log was untracked when its directory was new. Any
re-run of an existing sweep directory dirties the tree, so re-driving would
not fix it; the delta is 22 log lines, nothing in the driving path, and the
SHA is on every lap. The wart is in the driver and is fixed separately.

<a id="5b99317"></a>
## 2026-09-05 `5b99317` Q3: the certificate is sound, and expensively incomplete on a good policy

Author: Zach Asher. Full hash: `5b993173706bce8a46cc4647e9b13e97c61e178f`.

All four pre-registered predictions held. The tuned student drives every
condition 3/3, worst 1.47 ft against a 2.19 ft budget, and the verifier
refuses two of its three scored cells.

  cell     drive          bound hi      certificate
  fog      PASS 1.19 ft   +4.081 x tol  NOT_CERTIFIED
  night    PASS 1.47 ft   +1.656 x tol  NOT_CERTIFIED
  low_sun  PASS 0.45 ft   +0.240 x tol  CERTIFIED       agreement 1/3

P1 held and it was the one that could have stopped the queue: no cell is
CERTIFIED while driving fails, so section 4.1 stands.

P2 held with two cells rather than one. Neither is marginal driving -- 54% and
67% of budget. That is the measured price of a sound method on this family,
which Limitations has been asserting without evidence.

P4 held: agreement 1/3 against pass 1's 4/5, and the prereg gave the reason in
advance -- pass 1's rate was carried by a policy so bad that refusing it was
easy. That sentence belongs next to the paper's agreement figure: a rate
measured on policies that mostly fail is partly evidence that the method and
the road agree a bad policy is bad.

Unpredicted, and the most interesting number here: on the same captures, same
bound math and the same 101,888 ReLU, the TUNED student's fog bound is 3.3x
WIDER than the shipped student's (+4.081 vs +1.240) while it drives fog
better -- it holds 3/3 where the shipped student's fog cell is VOID. Bound
width and driving quality move in opposite directions between these two
policies, which is not a contradiction (a sound bound may be loose) but does
measure how little bound width says about behaviour here. It also rules out
using bound width to select models: the narrower-bounded of these two is the
one that goes VOID in fog.

Not claimed: this is ONE policy over three cells. 1/3 is not a rate.

<a id="394f5ca"></a>
## 2026-09-05 `394f5ca` Let the ONE ledger driver drive an exploratory student, gated on the tag

Author: Zach Asher. Full hash: `394f5ca54f5b0f45a0c5ed147eefcaa87359f357`.

Q3 needs a blind certificate-then-drive on a tuned student. I first drove it
with a hand-rolled loop calling closed_loop_ledger.py --reps 3, and it aborted
at the first in-run restart with "terminate called ... TimeoutException",
core dumped, twice -- once on clear and once on fog.

That is not a new defect. closed_loop_ledger.py documents it at the argparse
for --only-section: killing the server under a live carla.Client throws from a
context Python cannot catch, "releasing every reference the caller held was
not sufficient; something inside the client library outlives it", and A PROCESS
BOUNDARY PER RUN is "the only version that is certainly correct". The shell
driver exists precisely because the in-process --reps path does not work.

So the hand-rolled command was the mistake, and it is the mistake standing
rule 8 names: committed artifacts come from committed drivers. The fix is to
use the committed driver rather than to write a second one -- two drivers is
how they drift apart, which is the same argument the repo already makes about
two certifiers and about two copies of a path definition.

TOWN06_LEDGER_STUDENTS overrides the student list, in the same format as
certify_town06.py's TOWN06_STUDENTS_OVERRIDE, and is REFUSED unless
TOWN06_LEDGER_TAG is also set. Without that guard a stray export would drive a
different policy into a canonical cell, and since the cell filename encodes
the student it would look like an ordinary result. Requiring the tag means an
overridden run cannot land anywhere PROTOCOL R4 protects. The refusal happens
before students are resolved, not after driving.

An overridden checkpoint is driven exactly rather than passed through
final_student(), which resolves the study's DAgger'd policies and must not
rewrite a name that has no rounds -- the same rule the certifier follows.

The 602 MB core dump the aborts left in /var/crash is what the harness was
reporting as low memory; it is removed.

audit 259 -> 262.

<a id="b59ef91"></a>
## 2026-09-05 `b59ef91` An exploratory blind scope, so Q3 need not choose between two wrong options

Author: Zach Asher. Full hash: `b59ef914e1efb6c796530b1e904e0bab6cc877be`.

Q3 wants the blind protocol -- certify, commit, then drive, checkable against
git -- on a student that is not the shipped one. There was nowhere to put it.
TOWN06_PASS accepts only 1 and 2, and both name directories PROTOCOL R4
requires to stand, so an exploratory blind run had exactly two options: write
its scored cells into pass 1's blind record, or skip the order check that is
the entire reason to run it. The first corrupts the record the study rests on;
the second makes the experiment worthless.

TOWN06_LEDGER_TAG redirects the ledger AND the certificate under
results/town06/<tag>/. Every consumer -- the ledger writer, the order checker,
compare_town06, score_scopes -- already reads both from town06_design, so the
guard and the writer cannot drift apart, which is the property that module's
own comments insist on.

Unset by default: with no tag, not one path changes.

The subtle part is that the tag MOVES paths that other guards compare against.
certify_town06.py's two refusals -- an overridden run may not write the
canonical certificate, and a non-CROWN method may not either -- compared
against OUT, which the tag moves. Left alone they would have refused the very
file an exploratory run is meant to write while leaving the published
certificate unguarded, i.e. the tag would have silently disarmed both. They
now compare against CANONICAL_CERT_ARTIFACT, which no scope moves, and the
audit pins that no refusal compares against the scoped OUT any more.

The tag is charset-validated so it cannot traverse out of results/town06,
refused by name for 'ledger', 'ledger_pass2' and 'captures', and refused
outright alongside TOWN06_PASS != 1 -- two scoping mechanisms at once is how
one of them gets ignored.

Also corrects the module docstring's "alpha-CROWN over the one-parameter
family" to CROWN, matching what the code passes.

tests 84 -> 98, audit 253 -> 259.

<a id="401b809"></a>
## 2026-09-05 `401b809` Q2: pass 3's conclusion survives the tuned recipe, and the confound resolves

Author: Zach Asher. Full hash: `401b809f19ef13467b67f2e29e36780a3f11e562`.

Five candidates, pass 3's own gate unchanged at MARGIN_FRAC=0.5. None passes.

  seed  0   4/12   seed 3   6/12   seed 5  screened out at night (6.34 ft)
  seed  7   9/12   seed 12  3/12

P2 held: no candidate passes 12/12. P1 and P3 falsified, and both failures
say more than the verdicts.

P3 FALSIFIED. Fog is the ONLY condition that fails all four gated candidates
(clear 3/4, fog 4/4, night 0/4, low_sun 2/4). Night -- the study's second-worst
condition -- now stops nobody. That is what pass 3 found across its 16
students, so OVERALL_STATUS 3.3 moves from "confounded" to tested and upheld:
the recipe was changed, the gate was not, and fog still stops everything.

P1 FALSIFIED, and this is the sharper result. It was called close to a sanity
check because seed 0 drove fog at 0.98 ft in E4 and again at 0.98 ft in Q1. In
Q2's gate the BYTE-IDENTICAL checkpoint drove it at 1.34 ft, and the cell went
VOID. The one student this study had that cleared pass 3's fog margin did not
clear it on re-measurement. E4-F1's "first student to clear the margin gate",
repeated in Q1_FINDINGS, is now recorded as a single draw that did not
replicate -- the fifth such claim here. This is exactly the dispersion Q6
characterised, landing in the measurement that decides what ships.

The distinction the write-up has to keep: every gated lap of every gated
candidate was WITHIN the 2.19 ft budget, worst 1.50 ft. These are margin
failures at 50% of budget, not departures. The honest claim is that tuned
students drive Town06 within budget in all four conditions and none has pass
3's required headroom, with fog taking it -- weaker than "the recipe fixed
fog", stronger than the original picture, which contained real departures.

Also fixes a bug in my own summariser before it could mislead. It recorded
"the first failing condition per candidate" over a fixed condition order, so
it reported clear 3 / fog 1 and scored P3 as HELD -- the opposite of the truth
-- purely because clear is listed first. Q2-P3 is precisely the question that
ordering artifact answers backwards. It now counts failures per condition.

Q3's subject follows from the rule declared before Q2 ran: seed 7 at 9/12,
stopped by fog alone, holding the other three 3/3 under the strict margin.

PROMOTE=0 throughout, private pins only; neither shipped .selected moved.

<a id="6feded8"></a>
## 2026-09-05 `6feded8` Q6: there is no cheap variance lever, and the dispersion is intrinsic

Author: Zach Asher. Full hash: `6feded8f543524d2cc11d876ac685fcc88db29ac`.

40/40 cells, no simulator. Three of five predictions falsified, and the
falsifications ARE the result.

Q6a-P1 FALSIFIED. Initialisation does not dominate -- SD(init) 0.0181 against
SD(data) 0.0197, Levene p = 0.991, statistically indistinguishable. Minibatch
ORDER contributes as much as weight initialisation, which removes the lever
the prediction was reaching for: --init-from controls initialisation only and
cannot address half a problem whose halves are equal. Pinning the data order
buys 18% of SD, pinning the init 11%. Neither is worth a code path against a
design needing n = 20-60.

Q6b-P1 FALSIFIED, and the reason matters more than the verdict. CV FELL as the
pool shrank, 28.1% -> 9.4% -> 11.0%, but CV is the wrong statistic: the SD is
flat at 0.013-0.023 across a 4x change in pool size while the median nearly
triples. The CV collapsed because its denominator grew. Removing data makes
every seed uniformly worse, not more alike. So the absolute dispersion does
not respond to pool size at all over this range -- intrinsic to the objective,
not estimation noise -- which is the branch the prereg declared for a P1
failure, and it removes a costed justification from the next capture campaign.

Q6c-P1 FALSIFIED on its second clause. The output ensemble improves
monotonically and saturates at -22%, and at k=8 is still 31% WORSE than simply
having drawn the best seed. Seed selection beats ensembling on this endpoint
and is free -- a mild vindication of pass 3's design, whatever happens to its
attribution. The k-times-ReLU caveat now costs even more than it did.

Q6c-P2 held by a factor of five: weight averaging gives 0.5434 against a worst
single seed of 0.1088 and does not improve with k. No linear mode connectivity
without permutation alignment, now measured rather than argued.

Q6b-P2 is recorded as held per the letter and carries no evidential weight --
it predicted a shallow increase in CV and passed on a decrease.

Amendment A-1 is now a measurement as well as an argument: at tied seeds the
two code paths produce IDENTICAL weights and differ only in the shuffling RNG,
and seed 0 gave 0.0627 un-opted against 0.1064 tied. Pooling Q1's arm into
Q6a would have added a minibatch-stream difference to the experiment whose
purpose is to decompose exactly that.

This also explains Q1's split verdict: fog KD p99 reached p = 0.0079 while
driving reached only p = 0.0553 on the same students. None of the controllable
knobs would have narrowed that -- the variance is in the training, and the
closed loop only adds to it.

<a id="e30c0ed"></a>
## 2026-09-05 `e30c0ed` Q6: separate the init seed from the data seed, opt-in and proved bit-neutral

Author: Zach Asher. Full hash: `e30c0eda4884bef0ac72dba34e97122c71a1f0a4`.

DISTILL_SEED seeds torch, numpy and python once, after which the student's
INITIALISATION and the DataLoader's minibatch ORDER both draw from the same
global torch stream. "The seed" has been two variables wearing one name, which
is why the dispersion this study keeps paying for -- fog p99 CV 42.6%, r ~ 0
between two objectives at the same seed -- has never been attributable to
either of them.

DISTILL_INIT_SEED and DISTILL_DATA_SEED separate them; DISTILL_TRAIN_FRAC
shrinks the training pool for Q6b. All three are OPT-IN, and that is the
design rather than caution: passing generator= to a DataLoader normally
changes which RNG the shuffling draws from, and every checkpoint and every
published number in this repo was distilled on the un-opted path. If that path
moved by one draw, nothing already measured would be comparable to anything
measured later, and nothing in a result would reveal it.

Bit-neutrality is proved, not asserted. Seed 0 re-distilled after the patch at
both learning rates matches the references by SHA-256:

  lr 1e-3  97ed2be397ef5831  ==  S_mixed_taildet_a0p0_s0
  lr 3e-4  d4047b01bc656d20  ==  S_mixed_depth_d3lr3_s0

That costs two full distillations and cannot run in the suite, so the new test
pins the three properties it rests on -- chiefly that generator=None IS the
DataLoader default, the assumption the whole argument hangs on. It also pins
that the opt-in path actually changes something (a knob that silently does
nothing is worse than no knob, because the experiment still produces numbers)
and that TRAIN_FRAC never touches the validation index, which would move the
yardstick with the knob.

TRAIN_FRAC's subset comes from a fixed RNG independent of the seed under
study, so dispersion across seeds is not also dispersion across which frames
were kept.

78 -> 83 tests (+1 skipped, the absent-server path). audit 253 passed.

<a id="5636855"></a>
## 2026-09-05 `5636855` Q1: the learning-rate effect is confirmed on KD error and not on driving

Author: Zach Asher. Full hash: `56368557f2af665b0939b3049f45e9f71c7d2a63`.

36/36 cells, no harness failures. Pre-registration 5614780 preceded the first
scored lap.

  fog median   10.43 -> 2.33 ft   4.49x   Mann-Whitney p = 0.0553
               HL shift +5.96 ft  95% CI [-0.02, +9.57]

F1 held, F2 falsified by 0.0053, F3 falsified, F4 held, F5 held.

The most informative result is a secondary endpoint. On the SAME 15 students
per arm, measured through KD error instead of through driving:

  fog   KD p99  0.1024 -> 0.0732  -28.5%  p = 0.0079
  clear KD p99  0.0667 -> 0.0454  -32.0%  p = 0.00036

The difference between p = 0.008 and p = 0.055 is not about the learning rate,
it is about the measurement: the closed loop adds enough variance to hide an
effect the open loop resolves comfortably. That is a property of this study's
instrument, it applies to every training comparison in the lab, and it makes
Q6 the right next item rather than a nice-to-have.

Two things are reported that a less careful summary would have dropped:

  * F1 holds at 4.49x POOLED but only 1.92x on the nine NEW seeds, which alone
    would have falsified it. The prereg's sensitivity rule is written on
    direction and significance, so by the letter the pooled result stands --
    but the rule did not anticipate an effect-size disagreement and quoting
    only 4.49x would be selective. Both numbers are the finding.
  * F3 is the consequential failure. Exactly ONE student in thirty clears
    pass 3's fog margin gate, and it is seed 0 at 0.98 ft -- the same seed E4
    already had. Nine fresh draws at the tuned recipe produced no second one.
    A recipe that yields one gate-clearing student in fifteen has not fixed
    fog; it has shifted the distribution so the good tail occasionally reaches.

Clear is where the tuned recipe looks best and the median hides it: 14/14 laps
held with a 1.92 ft worst case, against 10/11 with a 5.93 ft clear failure.
VOID cells 6/30 vs 2/30 (Fisher p = 0.254), direction favouring the tuned arm.

pass 3's attribution stays confounded as OVERALL_STATUS 3.3 records it; Q1
does not retract it, Q2 tests it. Q2 has five candidates: seeds 0, 3, 5, 7, 12.

Nothing promoted, no .selected pin moved, ledgers and certificates untouched.

<a id="0e674cc"></a>
## 2026-09-05 `0e674cc` Q8 amendment A-1: Route 1 cannot be installed into .venv, measured

Author: Zach Asher. Full hash: `0e674cc27a6af3b26d2f914891e563042be48744`.

alpha-beta-CROWN at e5c7e17 pins torch==2.11.0, requires numpy>=2.0.0 and
requires-python ~=3.11.0. This repo is torch 2.13.0+cu130, numpy 1.26.4,
Python 3.12.3. The torch pin and the numpy floor cannot both be satisfied.

The pre-registration already declared this branch -- abort rather than move
torch or numpy, and run Q8b in a separate environment -- so it is taken on
measurement, not on caution. torch 2.13.0+cu130 exists here because the RTX
5090 is sm_120 and the previous pin had no kernels for it while
cuda.is_available() said True; downgrading it to run a verifier would
re-derive the study in order to check a bound.

Q8b therefore runs out of process, exporting ONNX + VNNLIB, which is
alpha-beta-CROWN's native format and which this study's one-dimensional
reparameterised spec already fits. That is a better decomposition than
linking the verifier in: it cannot perturb the environment that produced the
checkpoints, and the exported artifact is what someone else can re-verify
with a different tool.

It also creates a new hazard, so the amendment carries its check: an ONNX
export is a re-implementation of the network by a translator, and a verdict
about a mistranslated graph is sound and about the wrong network -- the same
shape as A-3's mis-rigged camera. The export is compared against the study's
own forward pass on >= 1,000 inputs across the certified interval, max abs
difference below 1e-5, before any Q8b verdict is reported.

One decision is deliberately NOT taken here: the separate environment wants
Python 3.11 and only 3.12.3 is installed. Adding an interpreter to a shared
lab machine is Zach's call, not a pre-registration's.

Q8a is unaffected and still runs in .venv.

<a id="ad3dc2f"></a>
## 2026-09-05 `ad3dc2f` Q8 pre-registration: alpha-CROWN then beta-CROWN, Route 1 declared

Author: Zach Asher. Full hash: `ad3dc2fa586daeef7d3b534f14220615673d6c46`.

Route 1 (pin Verified-Intelligence/alpha-beta-CROWN) is chosen over writing
our own branch-and-bound loop: the alternative puts the completeness argument
in our own unvalidated code, in a study whose contribution is that its
verdicts can be trusted.

The two undecided cells are quantified from the committed certificate and
witness exhibit rather than described:

  S_mixed/fog     bound 1.2400 x tol, densest witness 0.8454, no witness
  S_mixed/night   bound 2.8361 x tol, densest witness 0.6552, no witness

which lets Q8a carry a real prediction: the measured alpha-CROWN gain on this
network is 6%, so fog goes 1.2400 -> ~1.166 and night 2.8361 -> ~2.666, and
NEITHER resolves. Night would need a 65% tightening. Q8a is run anyway because
it is cheap and it is the only step that could close the question with no new
tooling -- and being wrong there would mean plain CROWN is refusing a safe
policy, which is a result about the instrument.

Cost is computed, not guessed: 133 poses x nsplit 16 = 2,128 bounds per cell,
at the 47 ms / 3,654 ms per-bound figures measured in Bounder.__init__, so
~2.2 h per cell.

Three commitments made before any number exists:
  * the beta-CROWN loop is validated on the three S_clear cells that already
    carry witnesses BEFORE it is pointed at the undecided ones. If it cannot
    re-find a known counterexample, no Q8b result is reported.
  * a 2 h per-cell timeout, declared now so it cannot be extended after
    watching a run that is nearly done.
  * the new dependency must not move torch or numpy. If it would, the install
    aborts and Q8b runs in a separate environment.

The alpha-CROWN knob is exposed as a committed --method flag defaulting to
CROWN, not edited in place for the run (standing rule 8).

<a id="3dea682"></a>
## 2026-09-04 `3dea682` Overall status: the certification result stands, pass 3's attribution does not

Author: Zach Asher. Full hash: `3dea68297566f8f944d721b3c36455a699d21950`.

Answers the question the follow-on experiments were run to answer. Nothing found
touches the certificate, the ledgers, the agreement figure or the
endpoint-only-unsoundness result. Three things did not survive.

The resolution trend (T06-F48) was single draws and is refuted by E1. The KD figures
quoted beside it do not reproduce as a comparison -- across six seeds fog RMSE beats
night's by 4% in 4 of 6 seeds, not by 22% always, and the paper's night value lies
outside the range of all six. The qualitative claim (fog's tail is catastrophic while
its mean is comparable to a passing condition) is robust and every seed shows it.

The serious one is pass 3. All 16 of its students were distilled at lr=1e-3 and
nothing in the study ever varied it. Changing only that to 3e-4 moves the fog median
from 11.79 to 1.91 ft, takes seeds holding fog from 1/5 to 3/6, and produces the
first student in this study to clear pass 3's own margin gate on fog. Pass 3's
conclusion is true of what it ran and cannot separate "fog defeats this architecture"
from "fog defeats it at this learning rate". Effect is 6x in median, consistent in 5
of 6 seeds, p=0.247 -- large enough to act on, not yet publishable.

Two claims got STRONGER. E4-F2 measures for the first time that the verifier prefers
shallow-and-wide: at matched ReLU count a 5-conv student's bounds are 2.3-3.7x wider
and it fails to certify the one cell the 3-conv student certifies. E1b exonerates the
harness, so every multi-rep number stands.

The sentence that has to change is "no policy good enough to certify exists yet, and
the obstruction is distillation rather than verification". The second half is now
better supported than before. The first half is not safe: a policy driving fog at
0.98 ft appeared within six seeds of changing one hyperparameter.

Lists five experiments still needed, with item 1 -- confirming the learning-rate
effect at n>=15 -- flagged as a blocker for the paper as written.

<a id="621aeb3"></a>
## 2026-09-04 `621aeb3` E4: depth costs verification 2.3-3.7x, does not help driving, and the learning rate dwarfs both

Author: Zach Asher. Full hash: `621aeb35133ec1a636fe08cabc454617fcc94ac9`.

F2 held, measured directly for the first time. At matched ReLU count (101,888 vs
101,892) and matched flatten dimension, on the same captures through the same bound
math, the 5-conv student's certified bounds are 2.30x wider on fog, 3.73x on night
and 3.70x on low sun -- and the one cell the 3-conv student CERTIFIES, the deeper one
does not. Every layer compounds alpha-CROWN's relaxation and the cost is large. This
is the paper's thesis, now with a number on it.

F1 held: depth does not rescue fog. d5 fog median 3.60 ft against d3's 1.91 -- worse
at driving AND worse to verify. The feared tension does not exist in the direction
feared; shallow-and-wide is better on both axes.

F5 held, and it is the biggest result in the queue. Changing ONLY the learning rate,
1e-3 to 3e-4, moved the fog median from 11.79 ft to 1.91 ft on the same architecture,
data, teacher, kernels and seeds. Seeds holding fog went 1/5 to 3/6, fog KD p99
median improved 28%, clear did not regress, and seed 0 drives fog at 0.98 ft -- the
first student in this study to clear pass 3's 1.095 ft margin gate on fog. The
learning-rate effect is 6x the depth effect and points the other way.

Stated honestly: Mann-Whitney p=0.247 at n=6, because one arm carries a 37.65 ft
departure and the dispersion is what E2R-F5 quantified. A 6x median shift consistent
across five of six seeds is strong enough to act on and not strong enough to publish.
It needs more seeds, and that is now the top recommendation.

Two design errors were caught before they became findings and are recorded as
amendments: the first depth arm was matched on neurons alone and carried a 20x
smaller flatten dimension, and the corrected one would not train at the study's fixed
learning rate at all.

Consequence: pass 3 is confounded. Its 16 students were all trained at 1e-3, so it
cannot separate "fog defeats this architecture" from "fog defeats this architecture
at this learning rate".

<a id="62bfdac"></a>
## 2026-09-04 `62bfdac` Headless equals windowed, the launcher can no longer hand you the wrong server, and the study's learning rate does not fit a deeper student

Author: Zach Asher. Full hash: `62bfdacc4e13f300e08f1928592a5f757520fe38`.

Headless verified equivalent, not assumed: photometry 0.257104 against the committed
reference 0.257106 (0.000% off, windowed measured 0.003%), and drive_expert.py
--direction all produced CSVs BIT-IDENTICAL to the committed windowed run on all
three sections. Switching the sweeps to headless.

carla_launch.sh had a real defect found doing that swap. It launches and then waits
for the port to answer, so when something was already listening the wait succeeded
instantly against THAT server while the process just launched died unnoticed. Asking
for headless on a box already running windowed printed "launching CARLA headless ...
ready after 0s" and then ran everything on the windowed server, leaving two CarlaUE4
processes behind. Nothing in a result reveals which server you were on, which is why
R-SIM-1 exists. It now compares the running server's mode against the requested one
and refuses, pointing at carla_restart.sh.

E4 amendment A-2. The corrected depth arm still would not train: best validation at
EPOCH 0, flat at 8.26e-3, while d3 descends 7.49 -> 4.66e-3 in four epochs. That is
an optimisation failure, not a depth result. Sweeping a declared LR grid at seed 0,
selected on validation KD-MSE and never on a driving outcome:

    lr        1e-3      3e-4      1e-4
    d3    2.080e-3  1.183e-3  1.229e-3
    d5    8.259e-3  2.121e-3  1.619e-3

d5 trains fine at 1e-4 and beats d3 at the study's own learning rate. But the second
row matters more: d3 at 3e-4 reaches 1.183e-3 against 2.080e-3 at the shipped 1e-3,
a 43% lower validation KD error ON THE SHIPPED ARCHITECTURE. Every student in this
study, on both maps, was distilled at 1e-3, and nothing has ever varied it.

E4 becomes three arms -- shipped recipe, tuned recipe at the same depth, and depth at
its own best recipe -- so the recipe and the depth are separated. New prediction F5:
the learning rate matters more than the depth.

<a id="801337a"></a>
## 2026-09-04 `801337a` E2 re-run: pinning makes a run repeatable, not the seed a control

Author: Zach Asher. Full hash: `801337a07c2b6cf300c003ccdd8a2593826e3da1`.

Same declared set with DISTILL_DETERMINISTIC=1. D1 predicted the paired design
would separate arms the unpaired one could not; it did the opposite -- Wilcoxon
p=0.562 both arms against Mann-Whitney 0.240 and 0.310 unpinned. Pairing made the
test WEAKER.

The reason is the useful part. Correlation between baseline and treated arm at the
SAME seed is r=+0.115 and r=-0.015. Pairing helps only when the seed is a shared
block effect across arms, and it is not: the seed fixes initialisation, the
trajectories diverge as soon as the loss differs, and two students sharing a seed
but not an objective are no more alike than two sharing neither. That is more
general than E2-F6 and applies to every training-configuration comparison in this
lab.

D4 fired correctly and then cleared the concern: 3 of 6 pinned seeds fall outside
the unpinned range, so it fails as written, but the two distributions are
indistinguishable (Mann-Whitney p=0.937). Pinning did not change what the pipeline
produces, only whether a run repeats. The literal range test was too strict for n=6.

C1 falsified again: fog p99 median +20.7% at alpha 2.0 and +28.5% at alpha 8.0, 2/6
seeds improving in each. Alpha 8.0 seed 1 was an outright training failure -- fog
p99 0.5589 and a drive departing at 35.40 ft. C2 held (1, 2, 1 seeds holding fog).
C3 falsified, C4 held.

E2R-F5 is the conclusion: two independent runs agree there is no measurable benefit,
but at CV 42.6% even n=60 per arm misses a 20% effect three times in ten. E2 is
closed as UNANSWERABLE BY THIS ROUTE rather than answered. What would fix it is a
lower-variance endpoint -- certified bound width, which is why E4's decisive
prediction is about certification -- or asking why a fixed objective on fixed data
has CV 42.6% at all, which nothing in this study has yet asked and which is upstream
of everything left in the queue.

<a id="b6ae99d"></a>
## 2026-09-04 `b6ae99d` E2: the tail loss did nothing measurable, and the reason the noise was that large is fixed

Author: Zach Asher. Full hash: `b6ae99d559bc0a0593554d5c8ce16e4b578453b8`.

3 alphas x 6 seeds on the shipped architecture, 18 distillations and 108 laps.

C1 FALSIFIED. Fog p99 |err| median went from 0.0890 to 0.1180 at alpha 2.0 (WORSE,
p=0.310) and 0.0873 at alpha 8.0 (-1.9%, p=0.699). Not monotonic in alpha, which a
real dose-response would not be. C2 held in its strongest form: seeds holding fog
3/3 went 3 (baseline), 0, 2 -- the treated arms are worse. C3 FALSIFIED: there was
no bulk/tail trade because nothing much happened; alpha 8.0's clear p99 median
actually improved. C4 held: within-alpha seed spread 14.69 ft against a
between-alpha median difference of 5.53 ft.

E2-F5 is the honest headline. Baseline fog p99 has CV 19.9% across seeds, so the
6-vs-6 design detects a 20% shift only 31% of the time and needs ~40% to be
reliable. It found nothing, but a 20% improvement in the fog error tail would be
worth having and this design would have missed it 69% of the time. The hypothesis
is NOT refuted; it is untested at usable power. Claiming otherwise would repeat the
single-draw error of T06-F48.

E2-F6 is the useful output. Amendment A-1 came from re-distilling the baseline at
the SAME seed and getting a different model: three draws of "seed 0" gave fog p99
0.1027 / 0.1427 / 0.1036, a 1.39x spread, as large as the spread across six
different seeds. distill.py seeded python, numpy and torch and its comment claimed
"every existing result reproduces exactly" -- but cuDNN autotunes and several
backward kernels reduce non-deterministically.

DISTILL_DETERMINISTIC=1 fixes it: cudnn.deterministic, benchmark off,
use_deterministic_algorithms and CUBLAS_WORKSPACE_CONFIG give BIT-IDENTICAL weights
across two runs at seed 0, verified tensor by tensor. Off by default so no
committed checkpoint is implicitly redefined. That converts the seed from a label
into a control variable, makes a paired design valid, and means a re-run is a re-run
rather than a new draw.

Next: re-run E2 paired with determinism pinned before spending seeds on it, and
adopt the same discipline for E6 and for any comparison of two training
configurations anywhere in this lab.

Passes 1-3, the certificates and E1 are untouched -- none of them compared two
training configurations, which is the design this confound breaks. E1's "the draw
dominates" is strengthened: part of that variance is now named and removable.

<a id="daec967"></a>
## 2026-09-04 `daec967` E1b: multimodal not bimodal, the harness is exonerated, and E5 is answered

Author: Zach Asher. Full hash: `daec967dda1eacc7784d7234834ca7e950860f8c`.

24 laps of E1's cleanest VOID cell in two arms differing only in whether the
client process persists. Predictions committed at c4d43c7 first; B1 is falsified.

B1 FALSIFIED. Four clusters, not two -- and 24 laps land on just 9 distinct
values, seven of them agreeing to within 0.03 ft. The closed loop is not a
continuum with noise on it; it has a handful of discrete outcomes and each lap
falls into one. Three-lap cells looked bimodal because three draws usually show
two of the four modes.

B2 held: lap index does not predict the branch (corr +0.269 on 12 laps, 2/6 vs 3/6
by half, adjacent-same 6/11 against 5.5 by chance). The eye-catching pairing in
the raw sequence is what a 4-mode distribution looks like in 12 draws.

B3 held, and this is the one that mattered: arm A departed 5/12, arm B 8/12,
Fisher p=0.414, Mann-Whitney on CTE p=0.087. No evidence a persisting client
process changes the measurement, so every multi-rep number in this study stands.
The dramatic median gap (7.53 vs 22.58) is an artifact of a multimodal
distribution whose median sits on a cluster boundary.

E5 is answered as sampling. The screen reports worst-of-1 and the gate
worst-of-3; drawing from the measured pool, P(gate worse) = 0.645 and P(all four
observations in the same direction) = 0.17. Unremarkable. Noted honestly: that
pool is one pathological checkpoint and E5's four cases were four students, so it
is an existence proof that sampling suffices rather than a measurement of those
cells -- B3 is the direct evidence.

The six VOID cells now have their written cause and STAY VOID. Explaining a defect
is not rehabilitating it: a cell landing on four outcomes has no verdict to report,
and averaging would publish a rate for an identified defect. What changes is how to
read a marginal cell -- three laps near the budget is one draw from a multimodal
distribution, not a measurement with error bars. Cells with margin are unaffected;
every non-VOID E1 cell varied 1-3%, the ordinary D-7 floor.

<a id="70c71c5"></a>
## 2026-09-04 `70c71c5` E1: the resolution trend was three unlucky seeds, and fog is unreliable rather than absent

Author: Zach Asher. Full hash: `70c71c57aaf4524b0490fa1f48bae3757b2bdb8c`.

48 cells, 4 input sizes x 6 distillation seeds x {fog, clear} x 3 laps, width held
at w4 so resolution is the only axis that moves. Predictions were committed at
e4bb0ec before the first scored lap; two of the four are falsified and the
document says so.

P1 FALSIFIED. Best-of-6 fog IS ordered by resolution -- 1.22 / 1.47 / 1.56 / 1.57 ft
for 84x28 / 168x28 / 168x56 / 252x84 -- which I predicted would not appear. But the
effect is 1.29x across a 9x range of input pixels while the SEED moves the same
quantity by up to 26.6x within one resolution, and the top three sizes are
separated by 0.09 and 0.01 ft. The ordering is real and it is not the story.

P2 FALSIFIED. 8 of the 20 measured fog cells hold all three laps under budget, at
every input size. Distillation does not reliably lose fog robustness; it loses it
on most draws. This does NOT contradict pass 3: that gate was every lap under
1.095 ft across four conditions, and the best fog cell here is 1.22 ft. The gate
stands and was not relaxed.

The T06-F48 numbers that motivated E1 -- 168x28 fog 6.85 ft, 168x56 fog 11.15 ft --
are unremarkable members of their own seed distributions (1.47-30.48 and
1.56-41.54). The trend was an artifact of single draws. Third time in this study.

The two honest summaries disagree. Best achievable student favours LOW resolution;
reliability of a random draw favours HIGH -- cells holding fog go 2/6, 1/5, 2/5,
3/4 as resolution rises, and 252x84 holds clear 6/6 with no cell over 4 ft. For a
safety argument the second question is the relevant one, which is the opposite of
E1's motivating hypothesis.

P3 held (straights degrade at low resolution, consistent with T06-F11). P4 held
emphatically.

Six cells are VOID under standing rule 3 and stay VOID. They are BIMODAL, not
noisy: in four of six, two laps are bit-identical and the third lands elsewhere,
and 252x84 s1 fog departs at exactly step 304 on two laps and completes the third.
Three of the six span the budget, so the bimodality flips verdicts. Determinism
preflight green, deterministic_control true, step counts full -- not R-SIM-6.
Candidate cause is residual D-7 render noise selecting a bifurcation branch; not
ruled in. Driving one such cell for 10+ reps subsumes E5 and is the sharpest
follow-up available.

Redirects the remaining work: architecture is a weak lever and the draw is a
strong one, so E2 and E6 -- which target the variance rather than the architecture
-- are the right next moves, judged on how many seeds clear the bar rather than on
the best seed.

<a id="6796743"></a>
## 2026-09-03 `6796743` The pinned environment could not run on the new card, and nothing said so

Author: Zach Asher. Full hash: `6796743c7b8a01e0b1aaee58194e219a86e30902`.

Ported the study to the new desktop (Ubuntu + ROS Jazzy, Python 3.12, RTX 5090)
and checked that the frozen result still reproduces there. It does: all six
Town06 verdicts and pose counts, the oracle bit-identical to its committed CSVs
and across fresh servers, the determinism preflight green, and render photometry
0.003% off the committed reference. Six defects were in the way.

M-1. torch 2.5.1+cu121 builds sm_50..sm_90; the 5090 is sm_120. Every kernel dies
while torch.cuda.is_available() returns True and get_device_name() answers
correctly, so certify_town06.py selected CUDA and died mid-run. pipeline/gpu.py
already had the right answer -- require_cuda() proves the device by operating on a
tensor, and catches this -- but only the four driving entry points used it. The
certifiers, the measurement scripts and train/distill now use it too, and the
audit enforces it across 17 files instead of 4.

M-2. requirements.txt documented an environment no published number came from. It
claimed torch 2.5.1+cu121 / numpy 2.2.6 and asserted every result used numpy
2.2.6; that pair appears only in results/calibration/sustained_bound.json, the
superseded era-1 artifact. Every published artifact records torch 2.13.0+cu130 /
numpy 1.26.4 in its own _meta, written from torch.__version__ at run time. The
opencv/numpy conflict that blocked the correct pins is resolved: opencv-python's
numpy>=2 is a declared pin, not an ABI requirement, so it installs --no-deps.

M-3. REPRODUCING.md promised the bounds reproduce "exactly". They do not, and the
cause is now measured rather than guessed. cuDNN's TF32 default explains the clear
student entirely (TF32 off, GPU == CPU to 1e-6). The mixed student drifts up to
3.9e-3 in every configuration including the exact recorded environment, with signs
changing between cells -- alpha-CROWN branch-and-bound taking different splits once
floating point reorders them, growing with network size. Neither numpy nor the
checkpoint explains it. No verdict is threatened: the worst headroom to a flip is
309x. The doc now states the tolerance and what to check.

M-4. ROS Jazzy on PYTHONPATH overrode the venv's include-system-site-packages and
pytest autoloaded ROS's launch_testing plugin, aborting before collecting a single
test. Fixed inside the venv with a .pth file, not a sitecustomize.py -- Ubuntu
ships its own sitecustomize earlier on sys.path and only the first is imported.

M-5. There is no DISPLAY :0 on this machine; the socket is :1. A hardcoded :0 does
not fail loudly, it falls back to headless and nobody is watching the run, against
standing rule 6. carla_launch.sh now probes for a live display.

M-6. certify_town06.py formatted its log line with relative_to(REPO), so --out
outside the repo wrote the certificate and then died with ValueError on the next
statement, exiting nonzero on a good run.

Also: certify_town06.py refuses to overwrite an existing certificate, and refuses
before certifying rather than after spending the run. Its default output path is
results/town06/certificate_town06.json, the pass-1 artifact PROTOCOL R4 requires
to stand -- a bare re-run overwrote it during this check and it was restored from
git. scripts/bootstrap_env.sh builds the environment and refuses to finish unless
a real CUDA kernel runs, cv2 works against the installed numpy, and auto_LiRPA
imports without SDP-CROWN markers.

audit_repo.py 216 -> 249 passed, 0 failed. pytest 78 passed with PYTHONPATH set.
Full account in docs/MIGRATION_2026-09-03.md. AEB and multi-condition carry the
same is_available() idiom and the same ROS exposure; both should take this before
their next measurement run.

<a id="366b1b9"></a>
## 2026-09-03 `366b1b9` Freeze the study for publication, and hand off the follow-on experiments

Author: Zach Asher. Full hash: `366b1b944e9d2b19a65bf5d2f5ad2b1061f78290`.

docs/PAPER_HANDOFF.md is the authority for the arXiv write-up. It states the
frozen result, every number traced to a committed artifact, the four results worth
leading with, the limitation to state plainly, and a list of five claims that were
made during the study and WITHDRAWN on evidence -- so a paper session cannot
resurrect them. It also carries the ISO 34503 ODD framing: Town04 is a highway and
Town06 an urban arterial, which are different ODDs under the taxonomy, so their
agreement figures are not comparable by construction. That also re-justifies A-5's
capped scope as a declared ODD boundary rather than a post-hoc exclusion.

docs/NEXT_EXPERIMENTS.md is for a fresh session on the new machine. Six
experiments in priority order, each with the question, why it is worth running,
the invocation, and what would count as an answer:

  E1 input-resolution ablation on fog -- the only measured trend that tracks the
     Town04/Town06 split, and a tension worth publishing either way, since T06-F11
     measured that this route's straights NEED the resolution fog dislikes
  E2 tail-sensitive distillation loss -- fog's mean error is better than night's,
     which passes, while its p99 is ten times tolerance; MSE is blind to that
  E3 gradient-alignment distillation (KDIGA) -- the literature's specific remedy
     for a robust teacher whose student is not, across differing architectures
  E4 depth at matched ReLU count -- never varied in this study; and if fog needs
     depth then VERIFIABILITY constrained the architecture into the failure
  E5 the screen/gate fog discrepancy -- observed four times, always one direction
  E6 the balancing refutation, re-tested by a method its own argument does not cover

Both documents say the study is frozen and that follow-on work does not edit the
paper's inputs.

NEXT_SESSION.md and TOWN06_STATUS.md described a pipeline "running, from step 0"
with stages 7-11 pending. Both now route to the right document and state the
result. TOWN06_STATUS.md keeps its historical record below the fold.

<a id="d5503e7"></a>
## 2026-09-03 `d5503e7` T06-F57 PASS 3: neither width met the gate, and width is eliminated properly this time

Author: Zach Asher. Full hash: `d5503e78a344604e28388b0f672896a0ff4f967d`.

Two mixed-student widths, eight seeds each in the same order, same teacher and
pools, criterion fixed before the first draw: screen at the full 2.19 ft budget,
gate every lap under 1.096 ft. NEITHER WIDTH PASSED. 0 of 8 at each. Zero harness
aborts, zero unmeasured laps, and all 83 laps carry a provenance block.

P1 held and T06-F48 was wrong on its own terms. Swept properly, w6 is visibly the
BETTER model: three seeds reached the gate against w4's one, and w6_s7 gave the
best non-fog driving in the study -- clear 0.62/0.49/0.78 and low sun
0.64/0.78/0.71, inside a criterion the shipped student fails. "The extra 50,000
ReLU buys nothing here" is false. The true statement is narrower and was never
tested: the extra capacity does not buy FOG.

P2 held. Fog stopped every seed that got past clear, at both widths. No other
condition rejected a single seed.

P3, third branch. Sixteen students, two widths, one criterion, no survivor: fog is
neither a capacity problem nor a draw problem at this input size and pool.

AND A MECHANISM I HAD BACKWARDS. Fog failure is reproducible per checkpoint, not
chaotic: w6_s7 drove fog 12.02, 11.97, 12.09 -- three laps within an inch and a
half -- while driving clear at 0.49-0.78 ft. w4_s5 2.14/1.98/2.26, w6_s5
2.01/2.11/1.86, w6_s4 6.06/7.10/7.02. A policy that fails fog identically every
lap is not being perturbed; it has learned something wrong about fog. This retires
the "fog amplifies the D-7 residual" reading I put in T06-F53 and already withdrew
there on its own control. The erratic cells and these stable ones are one
phenomenon at different severities: where the degradation lands near the budget a
lap verdict flips on render noise, where it lands far past it the laps agree.

Eliminated: width (8 seeds x 2 widths) and the draw (16 draws). Not tested, and
both are where the literature points: input resolution (T06-F48's 168x28 ->
168x56 moved fog the wrong way, 6.85 -> 11.15 ft, and is a single draw owed the
same scrutiny w6 just got), and the steering-label distribution (--balance exists,
is off, no driver passes it; the refutation predates the seed sweep, was measured
on the superseded six-section route, and refutes only downsampling -- not loss
weighting, which leaves the input distribution intact).

The gate is not relaxed and no student is pinned.

<a id="09726f5"></a>
## 2026-09-03 `09726f5` An unmeasured lap is not a failing lap, and my last fix only got half of it

Author: Zach Asher. Full hash: `09726f56ae0eb4316e4430927aa7cbb26614c63c`.

The restart-status fix stopped a lap being DRIVEN on an unverified server. It did
not stop that lap being COUNTED as a failure, and the sweep found the gap within
half an hour: S_mixed_t06lap_168x56_w4_s3 -- the shipped student -- was logged
"rejected at the screen" when one restart failed and its night lap was never
driven at all. Two of its screens read 0.76 and 1.39 ft; the third read

    {"error": true, "restart_failed": true, "tail": ["restart failed; lap not driven"]}

held_under counts laps that are not marked error, and the sweep compares that
count against the EXPECTED lap count -- so an undriven lap subtracts from held and
the seed is rejected. A harness failure wearing the costume of a model verdict,
which is the precise confusion the previous commit set out to end.

Three fixes, one per level.

compare_student_variants.py now uses carla_restart_retry.sh, THE one retry policy
(a6beb75), instead of calling carla_restart.sh directly. A boot that misses its
300 s window is a certainty over a stage of dozens of restarts, not a risk, and
four copies of a retry policy is how they drift. It also counts unmeasured laps
and exits 3 when there are any.

select_student_seed.sh checks that exit code at BOTH the screen and the gate and
ABORTS the sweep rather than rejecting the seed. A sweep that cannot get a server
cannot evaluate anything.

pass3_sweep_widths.sh treats an aborted sweep as an abort, not as "no seed
passed". Recording it as a width result would compare one width scored normally
against another scored through a broken harness.

Only one lap was contaminated -- seeds 0-2 were rejected on genuine driving. That
artifact is deleted so the re-run drives it.

Four new tests. Sweep stopped and to be relaunched from the start.

<a id="26e5d9d"></a>
## 2026-09-03 `26e5d9d` The gate that picks the shipped model recorded nothing about the harness

Author: Zach Asher. Full hash: `26e5d9d779f5d631f808e53db907b8ef541ab9ba`.

S_mixed_t06lap_168x56_w4_s0 scored 11.45 ft on fog on 09-02 and 1.48 ft on fog on
09-03. Same checkpoint file, byte-identical, mtime unchanged. The route file has
not moved since 08-31, config.py did not change between the two measurements, and
the only commit touching any driving-path file added scored_span_m(), which is not
called while driving. Nothing in the repository accounts for it.

It could not be attributed, because the whole artifact behind the rejection was a
max, a step count and a duration. No server command line, no determinism state, no
git SHA, no timestamp. The scored ledger records all of that per run; the SELECTION
gate -- which chose the model the study then certified and drove -- recorded none
of it. D-11 says data collected under a violating harness is not reusable, and
that is only enforceable if the data says which harness it ran under.

Three fixes.

1. restart_carla() reads the exit status and returns a boolean. It called
subprocess.run with no check= and never looked at returncode, so a restart that
printed "FATAL: CARLA did not come up on 3000" and exited non-zero was
indistinguishable from one that worked and the lap was driven anyway. The restart
log carries five such failures, three within the first two launches. A failed
restart now records an unmeasured lap marked restart_failed and drives nothing --
a student must be rejected by its own behaviour, not by the simulator.

2. Every lap carries the ledger's provenance block: run_started, weather, map,
fixed_delta_seconds, git sha and dirty flag, and the determinism harness read from
the RUNNING server -- package version, rules digest, lock problems, server argv,
notexturestreaming, quality level, windowed. Absent server gives None, never False:
"unknown" and "absent" are different facts.

3. OUT_DIR, so a new sweep of an old checkpoint stops overwriting the old sweep's
record. The 11.45 ft screen survived only because it happened to be tracked in git;
the aborted pass-3 run had already replaced it, and s2's and s3's with it. All
restored from git, and pass 3 now writes to results/town06/pass3/.

Unmeasured laps are also named in the summary. A gate compares held against the
EXPECTED count so a dropped lap can never inflate a pass, but a cell measured on
two laps read exactly like one measured on three.

This is A-4 applied as written: where the harness is not enforced, enforce it --
do not average over it.

<a id="4882cb4"></a>
## 2026-09-03 `4882cb4` Pass 3 stages 1-2: a margin gate, and pin namespaces that cannot clobber pass 1/2

Author: Zach Asher. Full hash: `4882cb45f372b516ba5f3382a293e6a0db50cb60`.

select_student_seed.sh gains MARGIN_FRAC (gate laps must stay under this fraction
of budget), SCREEN_FRAC, PIN_CK and PROMOTE. Every default reproduces the old
behaviour exactly, so passes 1 and 2 remain reproducible.

The gate counted `passed`, i.e. "under budget". A sweep that stops at the first
draw meeting that cannot select for headroom, because it stops at the first
student that has none -- which is how the shipped student came to clear fog at
1.78 ft of a 2.19 ft budget and then go VOID under fog in two independent passes.

PIN_CK and PROMOTE exist for a specific hazard. Pass 3 re-sweeps the SAME sweep
base for w4 so it can reuse w4_s0..s3 rather than re-distilling, and without a
separate pin namespace the winner would overwrite
S_mixed_t06lap_168x56_w4.selected -- the pin passes 1 and 2 resolve through --
silently changing which model those committed results refer to. Pass 3 pins under
<base>p3 and never promotes over the shipped .pth.

config.TOWN06_PASS3_WIDTHS declares both widths and their separate pins;
TOWN06_PASS3_GATE_MARGIN = 0.50 is the pre-registered criterion, read from config
by the driver so it cannot drift from the document.

pass3_sweep_widths.sh sweeps BOTH widths with the same seeds in the same order and
does not stop when one succeeds -- stopping early would answer a different question
and would answer it in whichever order the widths happen to be listed. "Neither
width passes" is handled as the pre-registered outcome it is, exiting 0 with a
note that relaxing the gate and re-running is the one move the pre-registration
forbids.

Four new tests, including one that checks the criterion against the shipped
student's own committed gate artifacts: it must REJECT it (6/12). If that test
ever passes trivially, the gate no longer does what the pre-registration says.

<a id="b86d4d8"></a>
## 2026-09-03 `b86d4d8` Pass 3 pre-registration: the wider student, and a gate that selects for margin

Author: Zach Asher. Full hash: `b86d4d8e2f77d242ef1aa32be1e040dbab72f4a7`.

Committed before any distillation, sweep or drive.

Two changes, both declared: a w6 mixed student -- (48,96,96)/fc192, 152,832
ReLUs, exactly 3.0x the clear student's 50,944 and so the Town04 ratio -- and a
selection criterion that requires headroom rather than a pass, applied identically
to both widths.

The criterion is fixed here: screen 1 lap x 4 conditions at budget, then gate
3 laps x 4 conditions at 50% of budget (1.096 ft). 50% is the midpoint and is well
clear of the D-7 residual, which T06-F53 measured moving a fog lap by 0.7 m against
a 0.334 m half-budget. It is not tuned to any student's observed value, and the
shipped w4_s3 FAILS it on two conditions -- fog 1.78 ft and low sun 1.26 ft --
which is stated now so the criterion cannot later be said to have been chosen to
admit a favoured model.

P3 is the question and all three outcomes are pre-committed: w6 succeeds where w4
fails (width was the lever); both succeed (the CRITERION was the lever, and Town06's
student was marginal because it was selected to be); neither succeeds (fog is
neither capacity nor seed at this input size and pool, and the study reports the
mixed student as fog-limited rather than shipping another 19%-margin model).

I decline to predict which. T06-F55 shows the only prior evidence -- one draw per
width -- cannot separate them, and inventing a prediction where the evidence is
absent is the error that finding documents.

Also corrected in the document rather than quietly: I estimated w6 at ~229k ReLUs
in conversation. It is 152,832.

Stage 3 closes a residual I had wrong at first and checked: the seed sweep DOES
distil on the student-DAgger pool, so the pinned student is trained on on-policy
data -- but on states collected by earlier students in the r01..r05 lineage, never
its own. Stage 3 collects from the pinned student's own trajectories and re-gates,
for both widths or neither.

<a id="99a08b4"></a>
## 2026-09-03 `99a08b4` The audit drove CARLA, and standing rule 1 was never checked for Town06

Author: Zach Asher. Full hash: `99a08b4cc6c1eb08b2f2f04d3d1c1a03e2d8b3ad`.

Three defects, all pre-existing, all found by running audit_repo.py after the
pass-2 ledger rather than before it.

1. THE AUDIT RESTARTED CARLA AND DROVE LAPS. capture_gate_drives.py had no
argparse at all, so `--help` was ignored and fell through into its body -- which
restarts the server and drives one lap per student per section. audit_repo.py
probes every entry point with `--help` to prove it imports cleanly. So running
the audit while a server happened to be up made the audit itself restart the
simulator and begin driving, violating R-SIM-3 from inside the tool whose job is
to check the repo is sound. It passed for months because the audit was normally
run with no server listening: the port guard returned 2 and the check went green.
The audit's behaviour depended on whether CARLA happened to be running.

2. STANDING RULE 1 WAS NEVER VERIFIED FOR TOWN06 BY THE CHECK THE RULE NAMES.
check_blind_order.py pointed town06 at results/town06/certificate/
sustained_bound.json, which has NO commit anywhere in this repository's history.
Every run reported "8 closed-loop cell(s) recorded with NO certificate -- order
unverifiable". Confirmed pre-existing by running the checker as it stood at
8d0de25^: identical output. The protocol itself held throughout, because
check_order_town06.py is correct and the ledger calls it before writing a cell --
what failed is the generic check standing rule 1 actually names.

3. AND THE AUDIT HID IT. It printed splitlines()[0] of the checker's output. Line
one was the town04_v2 warning; line two was the town06 error. The error was
invisible in every audit ever run, behind an unrelated warning that was surfaced.

Fixed: a real argparse; the correct certificate path plus both A-5 pass-2 scopes;
every checker line reported. Standing rule 1 now verifies for Town06 pass 1 and
for both pass-2 scopes:

    OK  town06: certificate precedes all 8 closed-loop cells
    OK  town06_pass2: certificate precedes all 8 closed-loop cells
    OK  town06_pass2_capped: certificate precedes all 8 closed-loop cells

audit_repo.py: 216 passed, 0 failed -- green for the first time.

tests/test_entrypoints_help.py covers all 11 entry points: --help must return in
60 s and print usage. A script that starts driving cannot answer in 60 s.

<a id="c2a8bfd"></a>
## 2026-09-03 `c2a8bfd` Exhibit the witness: three NOT_CERTIFIED cells are genuine falsifications

Author: Zach Asher. Full hash: `c2a8bfd3643ef56b8b0297f6123471a7be12043c`.

certify_sustained_bound.py's own docstring says NOT_CERTIFIED overstates what is
known, that a sound over-approximation can certify but cannot falsify, and that
"turning one into a genuine falsification means exhibiting a witness s* whose
sampled lap-mean deviation exceeds tolerance, which this repo can do cheaply and
does not yet do. Two independent reviewers raised this; see F45."

This does it, in about a minute on one GPU, offline, on the certificate's own
frames. Results identical under both scopes:

    student      cond      s=1     worst-s   s*     witness  certificate
    S_clear/fog          -0.69x    -1.01x  0.414    YES      NOT_CERTIFIED
    S_clear/night        -2.29x    -2.88x  0.767    YES      NOT_CERTIFIED
    S_clear/low_sun      -0.37x    -1.87x  0.605    YES      NOT_CERTIFIED
    S_mixed/fog          +0.04x    +0.85x  0.697    no       NOT_CERTIFIED
    S_mixed/night        +0.25x    -0.66x  0.678    no       NOT_CERTIFIED
    S_mixed/low_sun      +0.08x    +0.08x  1.000    no       CERTIFIED

Two consequences.

The three clear-only cells now carry an exhibited witness, so their verdicts are
falsifications rather than "the bound did not decide".

The two S_mixed NOT_CERTIFIED cells have NO witness at any single global
intensity. Their verdicts rest entirely on the certifier's pose-wise-varying-s
relaxation -- sound, deliberate, documented, and quantifying over a strictly
larger set than any rendered condition. That is the disposition for
night/S_mixed's DISAGREE: the certificate and the ledger are not in conflict,
they answer different questions.

AND THE RESULT THAT ARGUES THE STUDY'S THESIS. fog/S_clear and low_sun/S_clear
sit INSIDE the corridor at the driven intensity -- 0.69x and 0.37x of tolerance
-- yet drive FAIL 3/3, 22.6 m and 6.3 m off the road. Their witnesses are
interior, at s=0.41 and s=0.60. A certificate computed only at the rendered
condition would have issued a sound-looking certificate on both. Quantifying over
the family is what prevents that, demonstrated with no rendering, no shadows and
no exposure decision -- which is what T06-F51 and T06-F52 were reaching for and
could not isolate.

The tool cannot certify and carries no truth table: dense sampling is a lower
bound, so finding nothing means "no witness found", never "safe". R2 untouched.

<a id="c294c1c"></a>
## 2026-09-03 `c294c1c` Town06 pass 2: 24 laps, both scopes, and the arc-parameterisation bug found scoring them

Author: Zach Asher. Full hash: `c294c1cdee950a1663b14bff6c859246ec32a0da`.

THE RESULT. Agreement 4/5 under BOTH scopes, identical verdicts, and all eight
pass-1 verdicts reproduce -- including fog/S_mixed VOID, which the
pre-registration declined to predict.

    cell               FULL scope            CAPPED scope
    clear/S_clear      PASS  0.417 m +37.5%  PASS  0.417 m +37.5%
    clear/S_mixed      PASS  0.227 m +66.0%  PASS  0.227 m +66.0%
    fog/S_clear        FAIL 22.570 m         FAIL 22.570 m
    fog/S_mixed        VOID  1.000 m         VOID  1.000 m
    low_sun/S_clear    FAIL  6.324 m         FAIL  6.324 m
    low_sun/S_mixed    PASS  0.454 m +32.1%  PASS  0.217 m +67.5%
    night/S_clear      FAIL  7.783 m         FAIL  7.783 m
    night/S_mixed      PASS  0.295 m +55.8%  PASS  0.185 m +72.2%

P2 holds: 0 of 8 cells change verdict with the scope. Only two margins move, and
they are the two the pre-registration named.

TWO PARAMETERISATIONS OF "WHERE AM I", and the first version of this scoring
mixed them. The driver records here_m = route_index * step_m, the NOMINAL 2.0 m.
BRIDGE_SPANS in the route metadata and scored_scope's spans are TRUE arc, cumsum
of the actual spacing, which averages 1.9974 m. Over 1,147 vertices they drift up
to 6.8 m and end 3.0 m apart. Scored against here_m, low_sun/S_mixed's peak at
true arc 2284.9 m reads 2288.0 and falls outside the 2249.2-2287.0 exclusion, so
the capped scope excluded nothing and printed margins identical to the full scope
-- which is precisely what a correct comparison of two identical scopes looks
like, and would have been reported as "the scope makes no difference".

The same mismatch is PRE-EXISTING in closed_loop_ledger.py's bridge test.
Measured from the 24 traces: 286 mis-assigned steps, ~13-15 per lap, and ZERO
laps whose max |CTE| changes -- the affected steps sit at bridge edges on
dead-straight grade-separated merge road. Real defect, no verdict or margin
affected. Recorded rather than quietly corrected.

Also: the derived cells now carry `runs` as well as `laps_detail`. Without it
compare_town06.py counted zero laps and printed "PASS 0/0 [0,100]%" -- a verdict
with no visible evidence, which reads as a cell nobody drove.

<a id="9bb70a3"></a>
## 2026-09-03 `9bb70a3` T06-F51/F52: the interior is not closed-loop testable as the family is defined

Author: Zach Asher. Full hash: `9bb70a30d1b9c521732e4dcf04014ffcde6324d7`.

Two attempts to drive an interior point of the night family, and both fail a control. Both
are recorded because the controls are the result.

F51, PHYSICAL sweep (sun altitude, daylight exposure throughout):

    45 deg  2.85 ft FAIL      5 deg (low sun)  1.34 ft PASS  <- endpoint
    20 deg  2.90 ft FAIL      0 deg           62.74 ft  black frame, 98.5% dark
    10 deg  2.18 ft PASS 99%  -25 (night)     65.36 ft  wrong exposure

45 and 20 degrees fail at ~130% of budget on entirely normal images while BOTH endpoints
pass, so the physical lighting axis is not monotone and endpoint-only testing declares this
policy safe when it is not. But the failing band is where the sun casts DIRECTIONAL SHADOWS,
which T06-F35 classes as a different disturbance from the modelled uniform darkening -- so
it is a real observation about physical dusk and not evidence about this bound. Below the
horizon the axis cannot be swept at all: exposure is declared per NAMED condition, 800
blacks out the bottom of the range and 200 overexposes the top, and the sweep proves it on
itself by failing the night endpoint at 65 ft that the ledger passes 3/3.

F52, SYNTHETIC injection (Zach's suggestion: perturb the image between camera and network):

    s=0.00  1.69 ft PASS      s=0.75   7.03 ft FAIL
    s=0.25  5.65 ft FAIL      s=1.00  29.07 ft FAIL  <- should reproduce night

s=1 is the night endpoint and the ledger drives it PASS 0/3 at about 1.0 ft, so the
stand-in does not reproduce its own endpoint and the interior numbers are not evidence.

The reason is structural. captured_night[k] - captured_clear[k] is exact only AT pose k,
and a closed loop never stays there: cross-track error misaligns the injected difference,
which corrupts the input, which grows the error. At s=1 that ran 84.9% of the lap over
budget.

So PROTOCOL section 3's frozen family is defined POINTWISE on the captured poses. That is
sound for the certificate, which is computed offline on exactly those frames, and it means
there is no function to inject into a live loop. An interior claim about this family is not
closed-loop testable as the family is currently defined -- by open-loop pose-matched
evaluation, by certifying a pose-independent model instead, or by a simulator that can
render intermediates. Worth stating in the paper rather than letting a reader assume the
endpoint drive covers the interior.

Nothing here undermines the certificate. It bounds what it bounds, on frames that passed
the A-3 capture gate at 0.0148.

<a id="3a9da5d"></a>
## 2026-09-03 `3a9da5d` The comparison re-derived a verdict the ledger had already decided, and lost a VOID

Author: Zach Asher. Full hash: `3a9da5dcf69addf9f9dadc1eb78db76faeeef397`.

fog/S_mixed_t06 failed 1 of its 3 laps. The ledger correctly marked the cell VOID under
PROTOCOL A-4 -- "if the three laps disagree, that is a BUG until proven otherwise ... a
cell whose laps disagree is void, not uncertain" -- and compare_town06.py printed

    fog  S_mixed_t06  PASS 1/3  NOT_CERTIFIED  DISAGREE

because it recomputed the driving verdict by MAJORITY VOTE over the runs instead of
reading the cell's own verdict field. So a void cell became a pass, that pass was counted
as a disagreement with the certificate, and the headline agreement rate was 4/6 built on
a number nobody can defend.

A majority vote over three laps is precisely the "estimate a rate from a small sample"
reading A-4 exists to forbid. The aggregator had already applied the rule; the
comparison's job is to report it.

Now: the cell verdict is read, not derived; a VOID cell agrees with nothing (it is a
measurement of the harness, not of the policy) and is excluded from the rate with its own
line saying so; and the agreement is 4/5 with the void cell named.

The result, for the record:

    clear    S_clear  PASS 0/3   CERTIFIED       vacuous
    clear    S_mixed  PASS 0/3   CERTIFIED       vacuous
    fog      S_clear  FAIL 3/3   NOT_CERTIFIED   agree      CONTRADICTS D-14
    fog      S_mixed  VOID 1/3   NOT_CERTIFIED   n/a
    low sun  S_clear  FAIL 3/3   NOT_CERTIFIED   agree
    low sun  S_mixed  PASS 0/3   CERTIFIED       agree
    night    S_clear  FAIL 3/3   NOT_CERTIFIED   agree
    night    S_mixed  PASS 0/3   NOT_CERTIFIED   DISAGREE

PROTOCOL section 4.2's declared risk did NOT materialise: the certificate discriminates
between the two students and between conditions within the mixed student, rather than
returning one verdict pair everywhere.

<a id="f6e921c"></a>
## 2026-09-02 `f6e921c` T06-F49: repeating a lap is not data; T06-F48's remedy is withdrawn

Author: Zach Asher. Full hash: `f6e921c03c54d3486906b0f72ddf5496c44b4926`.

T06-F48 raised the base sets from three laps per condition to six, on the measurement that
Town06's students train on a third of Town04's data. The extra laps carry no new
information:

    steer labels, all 1,274 steps, every condition:   max |difference| = 0.00e+00
    rendered frames:                                   every sampled pair differs

The trajectory is bit-identical and only the pixels move, by the D-7 render floor. That is
the determinism campaign working as designed -- and it means a second lap of a fixed route
driven by a deterministic expert visits the same states with the same labels. It is a
reproducibility check, which is what A-4 says three laps are for, not a sample.

What the extra laps did do is halve the DAgger share of the distillation pool, 49% -> 33%,
by doubling the base alone. Same architecture, same teacher, same DAgger set:

    condition   3-lap base       6-lap base
    clear       0.83 ft PASS     0.78 ft PASS
    fog        11.15 ft FAIL    10.90 ft FAIL  (over-budget 24.6% -> 8.7-16.2%)
    night       0.68 ft PASS     9.83 ft FAIL

Fog improved slightly and night was destroyed. Diluting recovery data with repeated nominal
data is a bad trade, and that is all "collect more laps" amounts to on this route.

Town04's larger dataset IS larger because it collects two laps in TWO DIRECTIONS, and the
opposing carriageway is different road from the camera's point of view. Town06's lap is
one-way. T06-F48 compared frame counts correctly and drew the wrong inference from them.

Base sets restored to three laps per condition, which is what Zach specified before F48
argued otherwise. The remaining lever for fog is the DAgger pool -- 14,921 frames against
Town04's 61,175 -- which is the part of Town04's advantage that is real.

<a id="364e623"></a>
## 2026-09-02 `364e623` T06-F48: the Town06 students train on a third of Town04's data

Author: Zach Asher. Full hash: `364e62396b9f9f93d826868d46ec928aa6e0fa5d`.

Zach, after the mixed student failed fog at every width and resolution tried: "I would
just look at the data used to train town04 models."

                      base     DAgger              total   base per condition
    Town04 mixed    27,112   61,175 (5 rounds)    88,287       ~6,778
    Town06 mixed    15,288   14,921 (4 rounds)    30,209       ~3,822
    Town04 clear         -   23,084 (7 rounds)    23,084            -
    Town06 clear     3,823    4,967 (5 rounds)     8,790        3,823

34% of the data for the mixed student, 38% for the clear one. Two causes compound. Town04
collects two laps in TWO DIRECTIONS per condition -- four traversals -- so "three laps per
condition" on a one-way route sounds like more than Town04's two and is 56% of it. And each
Town04 DAgger round yields about 12,235 frames against Town06's 3,730, because its scored
road is 5,722 m against 2,289 m.

This explains what architecture could not. Fog failed at 168x28 w4 (6.85 ft), 168x56 w4
(11.15) and 168x56 w6 (11.64) while the same w4 student held clear 0.83, night 0.68 and low
sun 0.70. The KD split shows distillation is not failing on fog either: its RMSE 0.0272
beats night's 0.0333, which passes. What distinguishes fog is its tail, p99 error 0.121 --
ten times the steering tolerance. A heavy tail on a condition whose mean error is
unremarkable is what too little data looks like.

So is the student-DAgger collapse, now measured rather than described: after ONE
re-distillation the student's output magnitude fell from 0.0591 to 0.0143 against a teacher
at 0.0615. It stopped steering. distill.py's own comment predicts exactly that on a route
where 83.8% of the lap needs |steer| <= 0.01 and a student without enough signal learns to
emit zero with a small offset.

Base sets go to six laps per condition, matching Town04's per-condition VOLUME rather than
its lap count -- the lap is a different length, so copying the count copies the wrong thing.
This supersedes "three laps per condition", which was set before these numbers existed.

<a id="35b32cd"></a>
## 2026-09-02 `35b32cd` T06-F46: a windowed server sometimes renders 14% darker; back to headless

Author: Zach Asher. Full hash: `35b32cd7844724042bff3c502948a8f15e82a03f`.

Zach asked for a watchable window (standing rule 6) and windowed CARLA now starts -- the
SDL failure in T06-F42 was a property of the session, not the machine. The first windowed
launch passed the photometry gate at 0.002% off reference. The second, three minutes later,
same script, same flags, same map, came up at

    photometry Town06/clear: 0.220557 vs reference 0.257106 (14.215% off)

0.220557 / 0.257106 = 0.858. T06-F42's contamination ratio was 0.846. Same defect, caught
in the act for the first time.

It is a property of the SERVER INSTANCE, not the frame: five consecutive measurements
against that one live server gave 0.220562 / 0.220565 / 0.220566 / 0.220566 / 0.220566, a
spread of 4e-6. A server comes up either right or 14% dark, stays that way for its whole
life, and answers every RPC identically either way -- which is exactly the shape T06-F42
saw across DAgger rounds, each round internally consistent and the set split in two.

Not explained by headless-vs-windowed as such (a windowed lap and a headless lap agreed to
4e-5), not by the launch flags (/proc argv identical on a passing and a failing windowed
launch, determinism preflight green on both), not by map, weather, camera or exposure. The
trigger is still unidentified; what is established is that it is decided at LAUNCH and
survives for the life of the server.

The campaign therefore runs HEADLESS, and the runs are not watchable. That is a deliberate
deviation from standing rule 6 with a measurement behind it: every headless launch today
has passed the gate, a windowed one has now failed it by 14%, and a window that changes the
image the network sees by 14% is a second copy of the defect that cost this study two
rebuilds.

This is also what the photometry gate was written for, and it has now stopped that defect
at server launch, before any frame reached a dataset.

<a id="bdfd186"></a>
## 2026-09-02 `bdfd186` T06-F43: every collected lap ended with a garbage expert LABEL

Author: Zach Asher. Full hash: `bdfd186e4255b7c4fc7f6b7bd072606e47dbd940`.

collect_data.py reported the mixed set's steering range as [-0.754, 0.079] where clear's
was [-0.086, 0.079]. The expert is pure pursuit driving from ground-truth pose and never
reads the camera, so a label that depends on the weather is impossible by construction.

Every outlier is in the last three steps of a lap, at the route's end point, with |CTE|
of 0.001 m -- the car perfectly on the line and the label meaningless. 13 frames of
15,360.

Every driving loop ends a lap by "leave the start, then come back to it". ON AN OPEN
ROUTE THAT CAN NEVER FIRE: the Town06 lap's start and end are 174 m apart, so the loop
runs to its step budget, drives past the last vertex, and pure pursuit's lookahead is
clamped onto that vertex (correctly -- _step_idx clamps rather than wraps on an open
route) and the commanded steering degenerates. Whether a lap reaches that vertex within
its budget depends on millimetres of accumulated pose, which is why the clear laps
escaped and it looked like a weather effect.

gate_teacher_lap.py already stopped at `hint >= n_route - 2` and its comment says exactly
why. The fix had been applied to the loop that MEASURES a policy and not to the three that
BUILD one -- the same shape as the bridging omission, where evaluate.py and the ledger
bridged the intersections and dagger.py did not.

0.08% of frames is worth a rebuild here: they are behaviour-cloning LABELS, they are all
at ONE place, and that place is the end of the scored road. A policy trained on them
learns to jerk in the last few metres of every lap, and would then be diagnosed as a
teacher that cannot hold the lap end.

  - route.lap_finished(), one definition, true only on an OPEN route so Town04's closed
    loop is untouched. Called by all three collectors BEFORE the frame is written, so the
    bad frame is never recorded rather than recorded and filtered.
  - audit_training_data.py flags any expert label above 0.25 (pure pursuit commands ~0.09
    on these routes at 20 mph), checked on the DATA rather than the source.
  - tests/test_open_route_end.py pins the helper, and that the stop precedes the write.

It was never lap-specific: the same signature is in the SIX-SECTION datasets at each
section's end (max |steer| 0.337). It predates the lap, survived A-2's full recollection,
and was invisible because nothing looked at the labels.

Invalidates clear_t06lap, mixed_t06lap, dagger_clear_t06lap and the clear teacher trained
on them -- all collected earlier today, all archived rather than deleted. No certificate
exists and no cell has been scored.

<a id="bc1819c"></a>
## 2026-09-02 `bc1819c` The loose gate's FAILURE was outranking the strict gate's PASS

Author: Zach Asher. Full hash: `bc1819cea278f517ef5f0ea0b228d61175730d8b`.

teacher_clear_t06lap_dagger_r03 passed the strict lap gate 3/3 at 44-56% of budget, the
driver logged "clear teacher PASSED", and run_town06_pipeline.sh then declared

    FATAL: dagger_clear_t06lap exhausted its rounds WITHOUT the teacher meeting budget.
           Refusing to distil.

dagger.py's one-rep internal gate is a progress signal -- it runs with --external-gate,
each invocation gets --rounds 1, and it scores the PREVIOUS round's policy -- so it prints
"Exhausted N rounds without passing" on every round. Four such lines sat in the log
alongside one "*** LAP GATE PASSED", and teacher_gate() grepped for the failure first.

Commit dd631a4 fixed exactly this precedence for the PASS marker ("the loose gate was
overriding the strict one by sharing its marker") and left the FAIL marker pointing the
other way. The strict marker now decides, and it is checked first.

Left unblocked this would have looped: the watchdog restarts the pipeline, the DAgger
stage is skipped because the marker is present, and teacher_gate FATALs again on the same
four lines, forever.

The two audit checks around this were grepping PROSE, and both demonstrated it:

  * "teacher_gate requires positive evidence" tested for the literal "PASSED at round",
    a string that existed only inside an explanatory comment about dagger.py's internal
    gate. Rewriting that comment broke the check while the property it named got stronger.
  * The new precedence check compared raw string offsets in the function body and failed
    on its own comment, which names the loose gate's message before the code tests the
    strict one.

Both now assert the code with comments stripped: the gate cannot report success before it
has tested for the strict marker, and the marker's absence is an explicit refusal.

<a id="f39aeb7"></a>
## 2026-09-02 `f39aeb7` The lap capture would have certified 170 m of intersection nobody drives

Author: Zach Asher. Full hash: `f39aeb7fa58db21d7f3ded856eb2eb49c064c118`.

Found by reading forward through the stages the rebuild has not reached yet, not by
running them.

The Town06 lap's route geometry is 2,289 m and its SCORED road is 2,119 m: the two
intersections are driven by pure pursuit and excluded from every CTE, because the lane
centreline is undefined through them and a lane-follower asked to drive one is being
scored outside its domain. Six drivers already knew that (BRIDGE_SPANS); the capture rig
and the certifier did not.

So the capture sampled poses uniformly over the ROUTE, and the certificate would have
bounded 170 m of road that no closed-loop cell scores -- the same error as Town04's 181 m
ODD-boundary tail, in the same direction, on the other map. Standing rule 7 is two-sided
and this is the "more" half.

  - config.scored_len_m() and config.bridge_spans_for() are the one definition. The
    capture rig samples over the scored length and the certifier checks coverage against
    it; with only one of them changed the certifier refuses a correct capture, and with
    only the other it certifies road nothing drives.
  - capture_offset_yaw.py samples uniformly over SCORED arc-length, maps each sample back
    through the bridges, masks bridged points out of the candidate set (a nearest-point
    snap lands inside a bridge otherwise) and REFUSES if any pose still falls in one.

A second defect surfaced on the way, and this one would have wasted a capture run:

  capture_offset_yaw.py computed route arc-length with
  np.linalg.norm(np.diff(xy), axis=1) where xy was the WHOLE route array. Town04's
  routes are (N, 2); the Town06 lap's route is (N, 3) and the third column is YAW IN
  DEGREES. Including it makes the lap 5,299 m instead of 2,289 m, so every
  metres-along-the-route lookup landed at ~40% of the distance it named. The capture
  would have covered the first ~920 m of a 2,119 m scored road. The certifier's coverage
  floor would have caught it -- after a full capture run, and only because
  route_span_m is computed from x and y alone and so disagreed.

tests/test_capture_scope.py pins both offline, without CARLA. tests/test_scope_guards.py
stopped hardcoding the lap's length: its own comment said the value should come from the
route rather than being typed in, and then typed in 2289.0 -- the geometry -- so it was
asserting that a capture of 170 m of unscored road must be ACCEPTED. It now asks the
study, and gains a case for a capture that spans the bridges.

<a id="4a2cff6"></a>
## 2026-09-02 `4a2cff6` T06-F42: the server rendered 15% darker for half a day, and both teachers trained on it

Author: Zach Asher. Full hash: `4a2cff6fddc2a8006600d37fbcf70bdbaaab0ebb`.

The mixed teacher would not converge on the lap -- night 0/29 gate laps, fog 3/29 -- and
T06-F41 concluded the lap route renders darker than the six-section route the conditions
were calibrated on, so the frozen condition constants had to be re-derived. That is wrong,
and it is withdrawn before it was acted on.

pipeline/data/dagger_clear_t06lap holds TWO renderings of the same road under the same
declared condition: rounds 00-05 average 0.2508-0.2537 on the network's input, rounds 06-14
average 0.2140. dagger_mixed_t06lap is interleaved rather than split. Both BC sets, which
seed both teachers, are on the dark side. A collection run today with unchanged code gives
0.2526. At matched poses 0.5 m apart the frames are the same picture at a different
exposure -- per-pixel ratio 0.830, median 0.831, flat across the tonal range, identical
geometry and content.

So every lap teacher trained on frames systematically darker than the frames it is scored
on, and DAgger aggregated both renderings into one set. It predicts the failure pattern
exactly: clear has the most headroom and passed throughout, night and low sun are where a
15% gain bites, and the gate reached 6/12 at rounds 10-13 -- precisely the four consecutive
bright rounds. Round 13 passed every lap it was given and was stopped by infrastructure.

T06-F41 compared the six-section dataset's frame means against the lap dataset's. The
first was collected 08-28 (bright), the second 09-01 (dark). It measured the drift and
named it the route. Driving one instrument over the lap does not reproduce it: a
pure-pursuit lap of the LAP route matches the SIX-SECTION dataset to within 0.4%.

The conditions HOLD. Measured on the student's view -- the view condition_signature's
thresholds were derived on -- low sun is 5.0% from A-2's re-derivation against the 9%
T06-F20 accepted, the night/low-sun axis stays ordered, and all four classify as themselves
with margin on every discriminator. No frozen constant moves and PROTOCOL.lock is untouched.

Nothing caught this because nothing looked at brightness: the determinism preflight checks
the launch argv, verify_condition() reads the weather struct back, and identify() only asks
which condition it is. A uniform gain passes all three, and nothing downstream of the frames
can reveal it.

  - scripts/check_render_photometry.py, run from carla_launch.sh on every fresh server.
    Fixed camera transform at the study spawn, no vehicle, ~2 s. Reproducible across fresh
    servers to 0.001%; headless against windowed on a full driven lap is 4e-5. The 1% gate
    is 250x the noise floor and 15x below the drift it catches. A map with no reference
    prints "photometry NOT CHECKED" rather than passing quietly.
  - scripts/measure_lap_condition.py, ONE instrument for the rendered outcome, recording
    both the teacher's and the student's view. Three mutually inconsistent brightness
    tables had accumulated here because each was computed from whatever frames were on
    disk, and one of them is in a comment that decided a condition's name.
  - carla_restart.sh no longer kills its own caller. It stopped clients with
    `pkill -f collect_data.py`, which matches any ancestor naming the script; the bracket
    trick only protects against pkill's own pattern argument. That is the previous
    session's "restart failed before gate lap N" with a healthy server in the log, which
    discarded a 12-lap gate that was passing.

Every Town06 lap artifact produced by driving is archived to the drive and recollected,
under A-2's own reasoning. No lap certificate exists and no lap cell has been scored, so
nothing downstream is contaminated.

<a id="d370c31"></a>
## 2026-09-01 `d370c31` The condition is low_sun; "shadows" was always a bug, and the protocol already said so

Author: Zach Asher. Full hash: `d370c315a9524a52fde39e7ee970cac773b4a7e7`.

PROTOCOL.md's FROZEN section -- the part that wins over every other file in this repo --
has read "clear, fog, night, low sun" the whole time. The code key said "shadows". By the
protocol's own first rule that makes the code wrong and the protocol right, so this is a
bug fix, not an amendment, and PROTOCOL.lock is untouched (verified: it still passes).

The name also described something that does not happen. "shadows" implies the road is
partly occluded, and the Town04 rationale was exactly that -- terrain shadows the road at
15 degrees. Town06's terrain does not, which is why its angle is 5 degrees, and at 5
degrees the scene is uniformly dark rather than shadowed. Measured on the Town06 lap
training frames, mean brightness of the network's input:

    clear 0.1371    fog 0.3319    night 0.0897    low sun 0.0401

Low sun renders DARKER THAN NIGHT on this route. Calling it "shadows" both describes an
occlusion that is not there and hides that the lighting axis is not ordered the way the
name implies.

low_sun is canonical. canonical_condition() accepts "shadows" on READ so existing
artifacts stay readable; nothing new is written under the old name.

TOWN04 KEEPS THE OLD KEY, and this is not a half measure. Its certificate is
pre-registered under standing rule 1 and its four cell keys carry the name. Renaming
inside it would rewrite a pre-registered artifact and place its commit after the drives it
predicted -- check_blind_order.py would fail it, correctly. Frozen evidence keeps the name
it was collected under; the reader maps it.

scripts/migrate_shadows_to_low_sun.py migrates Town06's not-yet-reported data: 9
directories and 7 manifests (10,356 of 34,226 rows), verifying afterwards that no manifest
row points at a missing frame. It is a DRY RUN by default and must be run at a stage
boundary -- dagger.py builds round subdirectories from the weather name, so renaming under
a live collector would split a round across two names. The mixed teacher is mid-flight, so
it has not been applied yet.

<a id="b364a2c"></a>
## 2026-09-01 `b364a2c` A clean server before every lap, and cells that record the harness they ran under

Author: Zach Asher. Full hash: `b364a2c06ca038fbaaff0015e8ab4388cb9ec9ab`.

DETERMINISTIC CONTROL ON TOWN04. Already true and now verified rather than assumed: True
under (defaults), STUDY_MAP=Town04, STUDY_MAP=Town04 TOWN04_REDO=1 and STUDY_MAP=Town06,
and forced off nowhere. The completed Town04 redo drives were collected under it.

RESTARTS BETWEEN LAPS. The ledger already restarted before every run, and the run is the
lap. The teacher gate did not: it restarted once per lap INDEX and then drove all four
conditions on that one server -- 3 restarts for 12 laps. A-4's three laps are defensible
only while "a clean server restart before every run" holds, and four laps sharing an
ageing server is exactly the coupling the per-run restart exists to break. The restart is
now inside the per-condition loop: one lap, one clean server, 12 restarts for 12 laps.

Audited positionally, because a carla_restart call being present in the file says nothing
about which loop it sits in. The first version of that check matched line 57's
`carla_up 12 || carla_restart || exit 1` startup fallback and failed a ledger that was
correct -- the check being wrong, not the script.

CELLS RECORD THEIR HARNESS. D-11 makes data from a violating harness unusable, which is
enforceable only if the data says which harness it ran under. Cells recorded the timestep
and substepping but not whether deterministic control was on, what flags the server
carried, or whether the frozen rules were intact -- so "was this collected correctly?" had
to be answered from today's config rather than from the artifact, which is backwards.

Every cell now carries deterministic_control, the package version, the RULES digest,
check_lock() output, and the server's ACTUAL command line read from the running process
(-notexturestreaming is D-3 and the 168x term; a flag we meant to pass but did not looks
identical in a log to one we did).

An uninspectable server records notexturestreaming as null, never false. The first version
wrote false when the lookup returned nothing, which describes a D-3 violation that did not
happen and would later be read as evidence that one did. Unknown and absent are different
facts and the artifact must not collapse them.

<a id="25f64e3"></a>
## 2026-09-01 `25f64e3` Archive the superseded eras to the drive, and stop gating checkpoints a round did not train

Author: Zach Asher. Full hash: `25f64e3c4ea29324bbe46be65ff42830ad1b7031`.

Two things, both about an artifact being read as though the current step produced it.

ARCHIVE. The 2,861 m Town04 captures and the six-section Town06 results are on the
portable drive, sha256-verified, and out of the repo. Both are answers to questions the
study no longer asks, and both were read as current during the rebuild -- a watchdog
exited on the six-section certificate and a pipeline stage skipped a teacher on its log.
docs/ARCHIVE_2026-09-01.md says where they went; the drive carries the full manifest.

STALE CHECKPOINTS. run_dagger_rounds.sh took `ls -t | head -1` as "the checkpoint this
round trained". Today four consecutive attempts were killed (rc=143) having trained
nothing, and the driver gated teacher_mixed_t06lap_dagger_r00 -- from before the stage
began -- three times, logging a lap count against it each time as though a round had run.
A fifth exited rc=0 after collecting data but never training, and gated r00 again at
"3/12 laps passed". None of those five numbers measured what the log says they measured.

It now requires two independent facts before gating: the checkpoint is newer than the
round started, AND this round's own log segment says it trained that exact checkpoint.
Either alone has already been wrong -- mtime trusts the filesystem, the marker alone
trusts a log another process also writes to.

That also makes rc != 0 survivable for the right reason. The observed rc=134 is a
carla::client::TimeoutException thrown in the client destructor AFTER
"aggregating ... -> <ck>" is written, so the round's work is done and the abort is
teardown. rc=143 never reaches that path: a killed round trains nothing, so there is no
new checkpoint and no marker.

SPECTATOR. gate_teacher_lap.py drove the entire teacher gate with a stationary spectator
-- every other driving loop calls update_spectator and this one, which I wrote, did not.
Zach watches these run, so the window showed empty road while the gate was working
correctly. Audited across all five driving loops now.

320 audit checks pass.

<a id="46f69a2"></a>
## 2026-09-01 `46f69a2` Restore the blind-order check the prune deleted, which then caught me

Author: Zach Asher. Full hash: `46f69a2c77354c467cf0f1779170effbee8ddc13`.

Standing rule 1 says to check verdict-before-run ordering with
`python -m study.ledger --check-order`. That module was removed from this repo by 9cbc61a
"Prune to a minimal public artifact repo", along with the rest of the research record.
From that commit until now the check the rule depends on could not be run here at all --
through the entire Town04 redo and the Town06 rebuild. Both sibling repos still carry it.
Nobody noticed because the rule names a command, and a command that does not exist fails
the way a passing check looks: silently.

scripts/check_blind_order.py restores the ordering logic and only that, against the layout
the study has now (one certificate covering many cells, not one verdict file per cell).
It checks four things: certificate committed after a result, both in the same commit,
certificate committed after a run STARTED per provenance.run_started, and the certificate
modified once outcomes were known.

The first thing it caught was my own commit. 25c75fe used `git add -A` and swept in a
modified sustained_bound.json -- an accidental certifier re-run that had been sitting in
the working tree. Verdicts were unchanged, but a certificate rewritten after the drives is
indistinguishable from laundering a bound to fit them, and "the verdicts didn't change"
is exactly what someone laundering one would say.

The pre-registered certificate is restored byte-for-byte. The re-run is kept, clearly not
as the certificate, in calibration/reproduction/, because it answers something the study
otherwise could not: 12/12 verdicts identical, largest bound difference 2.62e-03 (21.8% of
tolerance) on a cell falsified by 284%, while the tightest cell (36.0% margin) reproduces
to 1.8% of tolerance. No verdict here rests on bound noise.

The check distinguishes a restoration from a rewrite by comparing content against the
pre-run version, so putting the file back is not itself flagged as a second violation.

Also three stale audit checks that were failing correct artifacts: capture scope re-derived
from published constants instead of the capture's own length_m_requested (calling eight
correct 2,988 m redo captures over-coverage -- the audit committing the very error it
exists to catch), "per_run_process" not accepted as the stronger form of "per_run", and
the DAgger gate flags asserted against the orchestrator after they moved into
run_dagger_rounds.sh. 202 passed/11 failed -> 309 passed/1 failed, the one being a real
gap: this certificate predates lap_end_m in _meta. Both certifiers write it now, so the
Town06 certificate will carry it.

<a id="b98f8d1"></a>
## 2026-08-29 `b98f8d1` T06-F31: deployment test result 4/6, and 3/3 on the genuinely blind cells

Author: Zach Asher. Full hash: `b98f8d1519739bbba44b147dde8c170ebc084866`.

Certificate committed before every drive (9e22253, R1 verified). Ledger 12 runs/cell.

  fog     S_clear FAIL 10/12  NOT_CERTIFIED  AGREE
  night   S_clear FAIL 12/12  NOT_CERTIFIED  AGREE
  low sun S_clear FAIL 12/12  NOT_CERTIFIED  AGREE
  fog     S_mixed PASS  0/12  NOT_CERTIFIED  disagree
  night   S_mixed PASS  0/12  NOT_CERTIFIED  disagree
  low sun S_mixed PASS  0/12  CERTIFIED      AGREE

4/6 mixes two kinds of cell and must not be quoted alone. Audited: the clear student was
never driven under any disturbance before the certificate, and the captures hold the
brake rather than driving it -- so its three cells are genuinely blind and agree 3/3. The
mixed student WAS driven under all conditions at 21:34 and 21:58, before the 23:16
certificate, so its three cells are not blind and agree 1/3. certify_town06.py had no
access to those results, but the choice to certify this checkpoint at w3 used them.

Found a logical gap in the comparison. The certificate runs alpha-CROWN over the whole
one-parameter family, so NOT_CERTIFIED means 'there exists an s whose bound exceeds
tolerance'. The ledger drives ONE point, the preset. A passing preset drive therefore
does not contradict NOT_CERTIFIED, and the agreement column treats the verdict as a
stronger claim than it makes. Irrelevant for the clear student, which failed at the
preset; the whole story for the mixed student.

Three dispositions written (D-T06-4/5/6). D-T06-4 is the favourable one: the certificate
beat the human prior on a blind cell, since the pre-registration carried Town04's D-14
'clear-only student is robust in fog' and it did not transfer.

Robustness check: re-scored against worst-SECTION instead of route-mean, no verdict
changes, and the one CERTIFIED cell survives at 0.69x. The averaging limitation is real
in principle and has no effect here.

<a id="d2292f5"></a>
## 2026-08-28 `d2292f5` Reproducibility RESOLVED: apply_control raced the tick, and textures streamed

Author: Zach Asher. Full hash: `d2292f5facdf962c62f2e3c90bc3ed8af6e5b580`.

Answers T06-F21. Synchronous mode with a fixed timestep synchronises the TICK, not
the command queue feeding it, so the study's protections were all real and all aimed
at the wrong layer.

Diagnosed OPEN LOOP, which is why it was findable at all: a closed-loop probe measures
physics, rendering and feedback amplification at once and every cause looks the same.
With the feedback cut and the commands a pure function of the step index, pose / raw
frame hash / steering-computed-but-not-applied separate cleanly.

Cause 1, FIXED. vehicle.apply_control() is fire-and-forget; whether the server registers
it before it processes world.tick() is a wall-clock race. Invisible while a command is
unchanged, because a late arrival re-applies the same value -- so it bites only on a
step where the command CHANGES, which in closed loop is every step. Up to 60 m apart
over 200 identical scripted steps; the applied-control readback differed between reps.
Acknowledged batch commands make pose, velocity, gear and readback bit-identical.
One choke point, env.apply_control(), gated on config.DETERMINISTIC_CONTROL.

Cause 2, FIXED. UE4 streams texture mips asynchronously, so mip residency depends on
load timing, not world state. -notexturestreaming: injected steering noise 3.9e-3 ->
2.4e-5 (168x), and the cold-server first-run outlier disappears.

Rejected by measurement, each a plausible fix: postprocess off is 2000x WORSE (manual
exposure lives inside the postprocess chain); quality High is catastrophic; motion blur,
bloom, lens flare and the spectator camera are all immaterial.

Residual is irreducible and now bounded: a frozen scene renders ~30 differing pixels of
307,200 across reps, generated per frame, not converged by a longer settle. In closed
loop a 2.6e-6 steering perturbation grows to 4-8 ft of CTE over 349 steps. Standing
rule 3 therefore STANDS, now justified by measurement -- but the amplification is a
property of the policy, not the simulator, so run-to-run spread reads as a stability
margin and the Town06 capacity decision is still open.

TOWN04 IS UNTOUCHED. DETERMINISTIC_CONTROL defaults off there, -notexturestreaming is
applied only for STUDY_MAP=Town06, and the preflight runs on the Town06 path only.

Also: determinism_probe.py reported the opposite and was believed. Its defect was not
in-place CSV overwriting but an UNCHECKED subprocess return code -- a crashed rep left
the previous rep's file on disk and it compared that with itself. Now guarded three ways.

Rules written up as a hash-locked lab standard, CARLA_DETERMINISM.md, enforced by
scripts/check_carla_determinism.py, which reads the server's real argv from /proc
because the launch flags that matter are invisible over RPC.

<a id="72dd65f"></a>
## 2026-08-27 `72dd65f` T06-F20: low sun is defined by rendered outcome; Town06 moves to 5 deg

Author: Zach Asher. Full hash: `72dd65f2cae9332f3fc0f43b7cc73663fb2b3103`.

Checked against the published artifact rather than anyone's memory.

v1.0.0 (Town04) has low sun 15 deg, night -25 deg, and night at 4x daylight exposure.
So the night exposure was NOT introduced for Town06 -- Zach believed Town04 used none,
and it did. Stating that plainly because the rest of his recollection was correct.

Measured brightness of the network's input, from lap captures:

                     Town04      T06 @15deg   T06 @5deg
    clear             0.2411       0.2963        --
    night             0.2075       0.2058        --
    low sun           0.1117       0.1841      0.1215
    night - low sun   0.0958       0.0217      0.0843

Night IS brighter than low sun on both maps -- correct, since night has headlights and 4x
exposure. But at 15 deg Town06's low sun is 65% brighter than Town04's and sits only
0.022 below night, collapsing an axis the study depends on being ordered.

The cause is TERRAIN, as Zach guessed: identical angle, exposure and code, but Town04's
terrain shadows the whole road at 15 deg and Town06's does not. The paper's own
justification -- 'the whole road is in shadow at that elevation' -- is a statement about
Town04's terrain, not about the number 15.

5 deg validated on all six sections: route mean 0.1215 vs Town04's 0.1117 (within 9%),
worst pose CV 6.81% -> 3.29%. Headlights key off angle < 0, so it stays lights-off.

The angle is MAP-SPECIFIC and the CONDITION is held fixed. Town04 keeps 15 deg exactly:
the constant is shared, and changing it globally would have silently altered the
published study while every file still looked right.

Invalidates every Town06 low-sun frame collected so far. Teachers and students need
rebuilding, which was already required.

<a id="d974c45"></a>
## 2026-08-27 `d974c45` T06-F19: harness overshoot bug; all closed-loop numbers re-measured and superseded

Author: Zach Asher. Full hash: `d974c45a310eeed04ce0ae26f6e238312b84037c`.

steps_for() capped STEPS, not distance. The vehicle runs slightly hot, so runs overshot
each section's clean window and the excursion found in excluded road was recorded as that
section's max |CTE|. Found by asking WHERE failures peaked: fog s02 at 101-102% through,
night at 94-101% on four sections.

Re-measured on the fixed harness, 12 runs per condition:

  teacher      0/12  2/12  2/12  0/12  =  4/48   (was 2/48)
  320x64 w3    0/12  3/12  1/12  0/12  =  4/48   (was 5-6/48)
  168x28 w2    0/12  6/12  4/12  0/12  = 10/48   (was 14/48)
  224x64 w2    2/12  2/12  6/12  3/12  = 13/48   (was 15/48)

SURVIVES: 320x64 w3 reaches teacher parity at 4/48 and beats its teacher at night. But
night improved 4/12 -> 1/12, not 8/12 -> 1/12 -- half the baseline's night failures were
the harness.

DOES NOT SURVIVE: three teacher ceilings reported in one session (0/24, 2/48, 4/48), each
as settled. Any 'the teacher is perfect' claim is void. The 14/48 'floor' behind the
covariate-shift hypothesis was 10/48.

RETRACTED: 'roughly 90% of that fog failure was the harness', concluded from ONE run.
Aggregate fog barely moved, 5/12 -> 6/12. Extrapolation from n=1.

Bigger input is NOT monotone: 224x64 w2 is worse than the 168x28 baseline on 4x the
pixels, so the night result cannot be attributed to input size alone -- 320x64 w3 differs
in width AND channels and that is unresolved.

For the revised narrative: under the ledger rule the 320x64 student now PASSES all four
ODD conditions, which is the precondition for verifying the continuum. But that rule
marks 3/12 -- 25% failures -- as PASS, and Town04's cells were 0/10 or 10/10 so it was
never stressed. Flagged for Zach, not resolved here: changing a scoring rule after seeing
the scores is not a call to make unilaterally.

<a id="a3f94a5"></a>
## 2026-08-27 `a3f94a5` explore phase 2: 320x64 w3 breaks the floor at 5/48; my floor hypothesis was wrong

Author: Zach Asher. Full hash: `a3f94a5062e91bce55f5161c91456f55842e8c26`.

Scored 12 runs per condition:

  config       ReLU    clear  fog  night  shadows  total
  168x28 w2  21,408      0     5     8      1      14/48
  168x28 w3  32,112      2     4     5      4      15/48
  224x64 w2  79,904      2     1     6      6      15/48
  320x64 w3 172,848      0     4     1      0       5/48   <-- night 8/12 -> 1/12

I had concluded from the first three that 14/48 was a distillation floor -- covariate
shift from behaviour-cloning teacher-visited states -- that architecture could not break.
The next architecture broke it to 5/48. Three points looked like a floor and were not,
and the on-policy explanation was premature. Zach's read was right: night needed a bigger
input in BOTH dimensions.

It sits well inside the verification envelope, which was the only hard constraint:
172,848 ReLU, ~0.85h to certify, 3.5 GB, bound width 0.2x tolerance, against a measured
ceiling near 325k where MEMORY, not time and not looseness, is what stops us.

Two rungs prove nothing and are marked as such. 448x64 w3 failed to train outright --
val MSE flat at 4.80e-3 from epoch 1 to 20, the network collapsed to a constant, and it
then failed clear 12/12. That is an optimisation failure at that size and LR, not
evidence about size. It is also a live instance of the competence-gate rationale: a
constant-output model certifies perfectly and drives off the road.

Round 2 isolates the confound, since 224x64 w2 -> 320x64 w3 changed input width AND
channels together:
  320x64 w2  115,232 ReLU  490k params  -> input width alone
  224x64 w3  119,856 ReLU  770k params  -> channels alone
Near-identical ReLU counts, so it is close to cost-matched.

Also queued: the TEACHER's failure rate at 12 runs per condition. Its 0/24 is a
single-pass number, and every 'the gap is all distillation' claim rests on it. Three
conclusions tonight were built on single-pass evidence and had to be withdrawn.

<a id="1b7ad5b"></a>
## 2026-08-26 `1b7ad5b` T06-F14: student DAgger is harmful at 168x28, w2 beats w3; F13 corrected

Author: Zach Asher. Full hash: `1b7ad5bf478ccd4ae18569de3818835749395a7e`.

Six checkpoints, one CARLA session, 3 reps each, clear weather, a section held only if
it holds on every rep.

  clear w2 base    4/6      mixed w2 base  6/6      mixed w3 base          4/6
  clear w2 +DAgger 4/6      mixed w2 +DAg  3/6      clear w2 (sweep seed)  6/6

Three results, two of which overturn decisions I took earlier tonight:

1. Student DAgger is harmful. Both paired comparisons hold architecture fixed and vary
   only procedure: mixed 6/6 -> 3/6; clear stays 4/6 but its worst section goes 1/3 at
   3.45 ft to 0/3 at 11.97 ft. No comparison shows it helping. This inverts Town04, and
   the reason is legible: there the distilled student held 1/6 at 16.50 ft, so DAgger was
   rescuing an incompetent policy. At 168x28 distillation alone is already competent, and
   DAgger's off-nominal states cost the marginal capability -- the sub-pixel straight-line
   cue from F11.

2. w3 is worse than w2 for mixed, 4/6 vs 6/6, with 50% more ReLU. The F13 widening is
   withdrawn: w2 is cheaper AND better.

3. Two clear students, same architecture, same data, same epochs, differ 4/6 vs 6/6 on
   seed alone. It is seed-marginal because it trains on 21,923 frames against the mixed
   student's 143,425.

F13's conclusion is marked corrected in place. Its diagnosis rested on single-pass
drives; its ruled-out list still stands, but the control it leaned on -- clear-only
DAgger 'improving' the clear student -- does not survive repetitions, and the
weather-dilution explanation goes with it.

Not done deliberately: shipping the sweep-seed checkpoint because it passes. It differs
only by seed, and picking the seed that clears a gate turns a precondition into a
selection step. Collecting more clear laps instead.

Also T06-F15: collect_data.py restarted lap indices at 0 while the manifest appended, so
re-collecting a weather rewrote its earlier laps' images while the old rows still pointed
at them. Caught before running it. Lap indices now continue past what is on disk.

<a id="9bb6e50"></a>
## 2026-08-26 `9bb6e50` Size each student to its own task, and put the sizes in ONE registry

Author: Zach Asher. Full hash: `9bb6e505c5eacc82e7551de8d59f41be1e87efa8`.

Zach asked whether the two students should be the same size. This lab already
answered that: 2b955e7 explicitly DROPPED the identical-architecture rule, because
the study's claim is WITHIN-model -- each policy against its own closed-loop
behaviour -- so architecture is irrelevant to the comparison, and "a tool that only
works when two models share an architecture is not a tool". Equal size would only
matter for a model-vs-model claim this study deliberately does not make.

So: sized to task, not matched. Town06 needs more width than Town04 at BOTH ends.
Town04's w1/w3 pair passed student-DAgger at round 0, comfortably inside budget
(0.53-1.61 ft). The same pair on Town06 plateaued ON the budget after ten rounds
each, with the SAME weights scoring 5/6, 6/6, 5/6 on consecutive gate runs -- the
verdict was noise, not progress. The straight sections punish residual steering bias,
which is what makes this route harder at a given capacity.

    S_clear_t06  w1 ->  w2   (16,32,32)/64    5,152 -> 10,304 ReLU
    S_mixed_t06  w3 ->  w4   (32,64,64)/128  15,456 -> 20,608 ReLU

Widening is close to free for verifiability here: F12 (693facb) measured 0.78 %
UNKNOWN at 5,152 and 2.5 % at 15,456 against ~11 % where certification stops being
useful, because what binds is input dimension and ours is one-dimensional. The
certificate now records ReLU count per student, as 2b955e7 requires, so bound
looseness from a larger model stays visible.

config.TOWN06_STUDENTS is now the single definition, read by the pipeline, the
student loop, the competence gate, the certifier and the ledger. Those five named
checkpoints independently before, which is how all four ended up pointing at the
distilled base while student-DAgger was writing <base>_dagger_rNN.

relu_count() reproduces the published 5,152 and 15,456 exactly, so the arithmetic is
checked against the paper rather than asserted.

<a id="6c706ac"></a>
## 2026-08-25 `6c706ac` Ledger v2: two tiers, three instruments, and a hardened order check (D-14)

Author: Zach Asher. Full hash: `6c706ac452571c5ba1efa264fd1e6e4a982f737d`.

The audit showed the smell test was red in steady state (so a new violation was
invisible), covered 20 of ~90 result files (so the paper's own instrument had no
column, per D-12), silently skipped pairs with a missing verdict, and checked only
the FIRST add of a verify file (so the 682b0eb verdict rewrites passed clean).

study/ledger.py rewritten:
- Two tiers: contradictions carrying a `disposition` key that names a real section
  of docs/DISPOSITIONS.md print as warnings and exit 0; anything unexplained exits 1.
  Nothing is silenced -- dispositioned rows stay visible, marked <d>.
- Three instruments: the era-1 canonical table (historical record, unchanged on
  disk), the FINAL open-road campaign (design.FINAL_CLOSED_LOOP -> the ___trunc_
  cells plus rain), and the sustained-bias certificate (sustained_bound.json
  in-sample + heldout_rain_verdicts.json blind). Prints the certificate/driving
  agreement the paper reports: 8/8.
- check-order hardened: fails on a closed loop with NO committed verdict; flags any
  commit that MODIFIES a verify file after the run was recorded; flags same-commit
  pairs; orders by git ancestry with timestamps as fallback (committer dates are
  forgeable, rebases rewrite them); checks the blind rain file precedes the rain
  drives; and reads provenance.run_started when present so future verdicts must
  precede the RUN, not merely the result commit.
- Coverage: unknown files in results/ledger are reported; untracked result files
  (no git anchor) are errors; the certificate artifacts must exist and be committed.

D-14 (docs/DISPOSITIONS.md) is the written bridge between the eras: every era-1 fog
"failure" originated inside the western intersection (max-CTE at steps 1695-1706,
1.2% of frames over budget) -- the D-09 junction ODD boundary, not fog -- and the F28
lap-scope amendment (open road, 0-2861 m) is the divide. The fog/S_clear expectation
is superseded by measurement, same shape as D-13; the expectation itself is not
edited. D-12 gains an addendum recording that the era-1 S_mixed verify cells were
never blind, which the order check now reports as a dispositioned warning instead of
un-actionable red.

Disposition keys added to the ten cells covered by written dispositions
(D-01/D-05/D-12/D-13/D-14). STUDY.md's verdict-rule table updated to the amended
a112d3a rule it had silently drifted from (design.verify_verdict is authoritative).
FINDINGS F21 fog rows marked superseded-in-part by D-14.

Conformance (25 passed):
- trap 6: the dead test imported a module (verify_v2) that never existed and skipped
  forever; now statically pins certify_cell's corridor to (cs - tol, cs + tol).
- trap 8: the numpy-identity tautology now tests the pipeline's actual Clamp01 and
  that verifiable_disturbance uses it.
- new scans: no world.get_weather() outside carla_env (the fog_isolation bug class);
  no hand-rolled synchronous_mode (under-provisioned substepping class); every CARLA
  entry point takes carla_lock; queue scan broadened to .get(timeout=...).
- trap 19: headlights_on() extracted as a pure function and tested against the
  presets and swept angles.
- the 20-cell expectation table is pinned as a golden constant, so a retro-edit of
  design.expected() fails the suite; FINAL_CLOSED_LOOP must cover the design exactly.

<a id="fa7f127"></a>
## 2026-08-15 `fa7f127` F47/D-13: held-out rain drives FAIL 10/10 -- the blind certificate scored 4/4

Author: Zach Asher. Full hash: `fa7f127d647f0d8ef5a9e5b3957d0d122ecf43b6`.

The driving is in, and the verdicts were committed before it (16abbcb).

    dir        model     bound (x tol)     verdict         driving      result
    westbound  S_clear   [-6.45,  +2.66]   NOT CERTIFIED   FAIL 10/10   agree
    westbound  S_mixed   [-1.98, +11.33]   NOT CERTIFIED   FAIL 10/10   agree
    eastbound  S_clear   [-5.26,  +2.83]   NOT CERTIFIED   FAIL 10/10   agree
    eastbound  S_mixed   [-2.00,  +9.31]   NOT CERTIFIED   FAIL 10/10   agree

    4/4, every run departed, both students, both directions

Every prior blind test in this project regressed to chance -- 14/14 -> 2/6,
7/8 -> 3/7, 8/8 -> 6/10, 10/10 -> 2/4. This is the first that did not, and it is
the held-out canonical condition both reviewers said the paper lacked.

It is not the criterion echoing our expectations, because it contradicted them.
STUDY.md pre-registered rain as S_mixed PASS / CERTIFIED. The certificate said NOT
CERTIFIED at +11.33x and the car departed on all ten runs. The certificate was right
and the design was wrong: S_mixed never saw rain, and "mixed-conditions training
generalises to unseen photometric conditions" was an assumption, not a measurement.
D-13 disposes of the resulting ledger contradiction as a finding rather than a bug,
because two instruments agree against the expectation and one committed first.

The failure is sustained -- 57.8% and 82.3% of the lap over budget, comparable to
night's 67.2% -- so it sits squarely inside the scope the certificate claims and says
nothing about the localized mode.

WHAT 4/4 DOES NOT SHOW, stated in both records: all four cells carry the same verdict
and all four drove the same way, so a criterion answering NOT CERTIFIED to everything
would also score 4/4. This tests sensitivity, not specificity; rain contains no
passing cell to false-alarm on. The next experiment is a rain intensity mild enough
for S_mixed to survive, swept the way fog density was, held out and committed the
same way.

<a id="fd83345"></a>
## 2026-08-15 `fd83345` F46: run the Koschmieder test on our own family -- it passes, and fog is non-monotonic

Author: Zach Asher. Full hash: `fd833457f5b012eddb15d0bab10f376057d88a3a`.

Both blind reviewers made the same objection independently: the study invented a
behavioural fidelity test, used it to kill the analytic Koschmieder model (image
R^2 0.848, drove the policy 23.8x harder than real fog), and never ran it on the
replacement. The interior of x(s) is a pixel chord; only s=0 and s=1 are rendered.

Ran it. Fog at densities 17.5/35/52.5 against the canonical 70, 200 poses over the
full lap, every capture carrying its own clear. Each render projected onto the
chord, then the policy evaluated at both points.

    THE CHORD PASSES. Where the render has a measurable effect it drives the
    policy 1.06-1.64x as hard, against Koschmieder's 23.8x, and the absolute error
    a verdict would inherit never exceeds 0.22x tolerance -- against a worst
    certified margin of 0.76x. The coverage claim survives with an error bar
    instead of an unquantified caveat.

    THE FOG AXIS IS NOT MONOTONIC, and that is new. Signed effect on the road
    region by density: +0.0115 at 17.5, -0.0133 at 35, -0.0464 at 52.5, -0.0342 at
    70. It brightens at low density and darkens above, and both sign and magnitude
    turn over between 52.5 and 70. So s is not a monotone reparameterisation of
    density: it runs roughly linearly to d=52.5 (s* = 0.15, 0.56, 1.00) then
    saturates, and the WORST real fog on this axis sits at s ~ 1 rather than beyond
    it. The certificate covers the chord, not "all densities up to 70" -- those
    coincide here by luck rather than design, and any future interpolated family
    should check monotonicity before assuming otherwise.

A control fell out for free: the four captures ran against one CARLA session and
their four independent clear captures agree to 3e-4 per pixel. F44's +0.048 regime
offset is confirmed from the other side as strictly BETWEEN-session.

Also adds scripts/tolerance_sensitivity.py, which makes F45's sweep runnable rather
than asserted, and two conformance tests: one replacing a test that passed while
its property did not hold (it checked that "0.012" was absent from a line, while
the value was laundered through a sqrt one line above), and one guarding that
T_CLOSED_LOOP_S stays labelled CALIBRATED. 17 -> 18 passing.

<a id="ea38e2d"></a>
## 2026-08-15 `ea38e2d` Prune to the published result: 48 scripts -> 13, and make the repo runnable elsewhere

Author: Zach Asher. Full hash: `ea38e2d54ab268ace3182254bc28c9a3bf76f3af`.

Acting on an independent senior-engineer review of the repo, verified rather than
taken on trust. The goal is a repo an outside researcher can read.

STRUCTURE. 35 scripts move to archive/ behind a README that names, for each one,
the measurement that retired it. Nothing is deleted: the paper makes NEGATIVE
claims, and a negative claim whose code is gone cannot be checked. Three groups --
trajectory/tube propagation (seven scripts, all of which diverged), the seven
retired pointwise criteria (F22 measured r = -0.053 against ground truth), and the
retired 12-frame-median instrument that wrote the ledger's verify cells (D-12).
The sun-elevation expansion moves there too; it is now owned by
lab--future-plans--docs/localized-sun-elevation-failures.md.

Before moving anything I rebuilt the reference map myself, because reference count
alone is misleading here: capture_offset_yaw.py, measure_night_gain.py and
measure_shadow_mask.py have zero importers but produce artifacts the certificate
loads, and the review's delete list contained four files that looked imported by
certify_cell.py but were only named in its prose.

README. It described milestone M0 -- "no pipeline code yet, deliberately" -- across
152 commits and a finished result, and routed newcomers at the M0 design docs while
never mentioning STATE_OF_PLAY.md, the only file that says what is currently true.
Rewritten around the result, its three scope limits, and why `python -m study.ledger`
exits 1 on purpose (a reader's first command reporting failure, with the explanation
buried at line 895 of a 950-line file, is the worst possible first impression).

RUNNABILITY. requirements.txt pinned numpy<2.0 while every result in this repo was
produced under numpy 2.2.6 -- installing it gave you a different environment from
the one that ran. Now pinned to the versions read off that environment. Absolute
paths from this machine are gone from everything outside archive/: five shell
scripts hardcoded an interpreter living in a *different, superseded* sub-repo, two
wrote logs to agent scratch directories, and CARLA_ROOT and the lock directory had
no env override.

The two student checkpoints the certificate actually loads are now tracked. They
are 403 KB; they were excluded by a blanket checkpoints/ rule aimed at large
weights, so a clone contained sustained_bound.json -- the answer -- and nothing
that produced it.

TESTS. conformance/ tested process discipline well and the verification argument
not at all. Added test_bound_soundness.py: sample inside each branch-and-bound
sub-interval and assert every sampled output lies within the returned bound. That
is the property that makes a certificate a certificate, it runs in 6 s with no
CARLA and no checkpoint, and it deliberately uses a LOOSER 4-way split than
production so the test is harder than the thing it guards. Two companions check
that splitting never loosens the enclosure and that a zero-width disturbance
collapses onto the true output. 14 passed -> 17 passed.

HEADLINE SCRIPT. certify_sustained_bound.py now takes argparse rather than an
undocumented positional, refuses to run on missing captures instead of printing a
clean 6/6 indistinguishable from 12/12, and records provenance -- nsplit, stride,
tolerance, cells expected vs scored, git commit, torch and numpy versions -- into
sustained_bound.json, which previously carried bounds with no way to tie them to a
paper table. Its docstring now states plainly that FALSIFIED overstates what a
sound over-approximation can know; the honest reading is NOT CERTIFIED.

<a id="e76f3b1"></a>
## 2026-08-15 `e76f3b1` F45: the tolerance horizon is fitted, and at its a-priori value the certificate is unsound

Author: Zach Asher. Full hash: `e76f3b16fb4625c8c9b7890ce6c48afdf09645de`.

Two expert reviewers, reading the paper blind and independently of each other,
raised the same objection and derived the same numbers. It reproduces exactly
against sustained_bound.json, so it goes in the findings log rather than into an
argument.

T_CLOSED_LOOP_S = 1.85 is commented "[MEASURED, back-solved from the observed
cliff]" -- the cliff being the closed-loop departures the certificate is then
validated against. The paper claims "no fitted parameter" three times.

Sweeping T over the twelve committed cells:

    T=1.00  tol 0.04111  10/12   BOTH shadows cells certified, both depart 10/10
    T=1.23  tol 0.02717  11/12   west shadows still certified
    T=1.50  tol 0.01827  12/12
    T=1.85  tol 0.01201  12/12   <- in use
    T=2.13  tol 0.00906  11/12   east S_mixed night false alarm
    admissible window: T in (1.231, 2.128) s

T=1.00 is not an arbitrary probe: it is the one-second reaction horizon the paper
introduces two sentences before back-solving 1.85, and where STEER_CORRIDOR_RAD
already sits. At that value the criterion issues UNSOUND CERTIFICATES on two cells
that leave the lane on every run -- the worst failure this project can produce,
one parameter away from the published result.

What it does not undermine: the 3.0x gap is a ratio, invariant to T, and the cell
ordering is correct at every T. What T does is place the threshold inside the gap,
and T was picked by looking at where the gap is.

The repair is cheap and the result survives it. T=1.5 s, a standard human-factors
reaction time obtainable without looking at our data, scores 12/12 with the
threshold comfortably inside the gap. So the fix costs one sentence: take T from
the literature, report the admissible window as a sensitivity result, and drop
"no fitted parameter". Recommended but NOT done -- it changes a published claim.

Also recorded: a sound over-approximation can certify but cannot falsify. The
FALSIFIED verdict this repo emits should be NOT CERTIFIED unless we produce a
witness s*, which we can do cheaply since we already sample the family. Under the
strict reading the headline is 8 sound certificates plus 4 uninformative unknowns
that happen to coincide with failure.

<a id="6e1fa73"></a>
## 2026-08-15 `6e1fa73` Re-certify all twelve with paired baselines: 12/12, ten cells bit-for-bit

Author: Zach Asher. Full hash: `6e1fa73643f66654a0cdf31c5923076640fd9a33`.

Full re-run of certify_sustained_bound.py with the F43 fix. This is also the
answer to whether the committed 12/12 was stale: it was not.

    ten of twelve cells reproduce to within 2e-7 of tolerance  (GPU float noise)
    two cells changed, both eastbound fog, both now baseline=paired
    every verdict identical -- 12/12 stands

    east S_clear fog   [-0.82,+0.29] -> [-0.45,+0.39]   CERTIFIED both
    east S_mixed fog   [-0.22,+0.43] -> [-0.17,+0.26]   CERTIFIED both

The correction improves the margin rather than eroding it. The worst certified
cell was eastbound S_clear fog at 0.82x; it is now eastbound S_mixed night at
0.76x, which was always there and was simply not the worst. Against a
least-escaping falsified cell of 2.26x, the separation goes from 2.76x to 2.99x,
so the "3x gap" the study has been claiming is now nearly exact instead of a
generous rounding.

sustained_bound.json now records which baseline each cell used, so "foreign"
is visible in the artefact rather than implicit in the filenames.

D-12 additionally disposes of the two standing ledger `verify` contradictions,
which had sat red with no written cause while D-01 and D-05 covered the
closed-loop pair. All six non-vacuous verify cells were written by the retired
12-frame-median instrument, which F33 showed measures provability rather than
severity and which therefore falsifies the wider, safer model -- exactly the two
cells the ledger flags. The real gap it exposes is that the sustained-bias
certificate, the instrument behind the paper's result, has no ledger cell type
at all: its twelve results live in sustained_bound.json, which study.ledger never
reads. That is why the ledger could not have caught F43. The cells were NOT
overwritten with the current verdicts -- doing so would place a verification
verdict in git after the driving it is supposed to have predicted, which is what
--check-order exists to detect.

<a id="a9d040e"></a>
## 2026-08-15 `a9d040e` F43/F44: the eastbound fog cell was certified against another session's baseline

Author: Zach Asher. Full hash: `a9d040e7ed4d4c150c90bff3506ed31a2b46a817`.

Checking whether the committed 12/12 reproduces turned up a defect the ledger
cannot see, because it is an INPUT to the certificate rather than one of its
verdicts.

The certificate interpolates x(s) = x_clear + s (x_cond - x_clear), so the
clear endpoint defines the disturbance as much as the condition endpoint does.
certify_sustained_bound.py took the two from different files -- lap_{dir}_clear
and lap_{dir}_{cond} -- which are separate CARLA sessions recorded hours apart,
and nothing required them to agree.

lap_eastbound_fog.npz is the one capture that recorded its own clear frames, so
it is the only cell where this could be measured rather than argued. Against the
clear capture the certifier actually used, at pose-identical frames (max |dx| =
|dy| = 0.0), the two clear captures differ by a uniform +0.049 per pixel -- 83%
of the fog disturbance being certified, and enough to invert its sign. Fog reads
-0.0348 westbound and +0.0149 eastbound, which is not something one fog preset
can do; re-paired against its own clear, eastbound fog reads -0.0341.

Effect, measured before anything was changed:

    S_clear  foreign [-0.82,+0.29] -> paired [-0.45,+0.39]   CERTIFIED both
    S_mixed  foreign [-0.22,+0.43] -> paired [-0.17,+0.26]   CERTIFIED both

No verdict moves. The count stays 12/12 and every westbound number is
unchanged. The corrected bound is TIGHTER, so this widens the gap between
certified and falsified cells rather than closing it -- had it gone the other
way this would have been a retraction, and the disposition says so.

F44 then settles why the two captures differ at all, because the two available
explanations had opposite consequences. If the capture protocol contaminated one
condition slot (the CARLA next-tick trap: the first condition rendering under the
previous weather), the internal clear would be the WRONG one and the fix would be
backwards. Three 40-pose captures on a fresh simulator: clear captured first,
alone, and last agree with each other to 1e-4, and all three sit +0.048 above the
archive. Slot order is not the mechanism -- the level is a session property. The
disturbance itself survives both regimes: four measurements of westbound fog
across three sessions agree within 8%.

So the fix is to pair within the session, applied to every cell identically,
including the eleven where it changes nothing; which baseline was used is now
printed and stored in sustained_bound.json rather than chosen silently.

Explicitly NOT done: re-capturing the study on today's simulator. That would move
all twelve cells into the new regime while the closed-loop runs they are compared
against were driven in the old one, and gate A was measured there too. That is a
decision about the whole study's data and needs the driving re-run with it.

The leading suspect for the regime shift is the render path -- this machine can no
longer open a CARLA window (Vulkan surface creation fails; only -RenderOffScreen
starts), so today's frames are offscreen and the archive was captured windowed.
Recorded as a suspect; nothing here tests it.

<a id="b9ad55b"></a>
## 2026-08-11 `b9ad55b` S_clear verify cells (night FALSIFIED, shadows CERTIFIED), and fog model fails D3

Author: Zach Asher. Full hash: `b9ad55b54ee16d3c2d4df34c56d3fcd1c450dcfa`.

Three S_clear verify cells, all committed BEFORE their closed-loop counterparts
exist, which is what makes them predictions:

  clear    CERTIFIED (vacuous, zero-width box)
  night    FALSIFIED  100% of the axis, 1 bound per frame -- as pre-registered
  shadows  CERTIFIED  median 100% -- CONTRADICTS the pre-registered FALSIFIED

Shadows survives the better mask: the pooled-mask run and the per-frame-mask run
both return CERTIFIED, so the contradiction is not a mask artefact. Kept the
pooled run under results/diagnostic/ rather than discarding it.

THE FOG MODEL DOES NOT DESCRIBE CARLA'S FOG. Fitting pose-paired frames, plain
Koschmieder fails D3(a) outright: CARLA darkens the road ROI by -0.031 while the
model brightens it by +0.015, opposite signs, ROI R^2 -0.030. The full-frame rmse
looks fine (0.053) only because the sky dominates -- exactly the pooled-statistics
trap D3(d) exists to catch.

This is the SAME train/verify family mismatch CLAUDE.md names as one of the two
unruled-out causes of the previous study's disaster. Our students train on
CARLA-rendered fog and were about to be verified against a model that moves the
road the wrong way.

Cause is physical: fog also attenuates the sunlight reaching the road surface,
which fixed-radiance Koschmieder omits. Adding it, x' = A(1-t) + t*k*x0, fixes
every computable D3 check (a,b,f: 0/8 -> 8/8, ROI R^2 -0.03 -> +0.87) and moves
the operating point from MOR 250 m to MOR 61 m -- the severe end of the axis, not
the mild end. Airlight measured at ~[0.47 0.44 0.43], not the assumed 0.78 (D4).

Also fixed a broadcast bug in the airlight solve that summed the denominator over
(H,1) and the numerator over (H,W), inflating A by ~W (first run reported A=657).

<a id="f71efdc"></a>
## 2026-08-11 `f71efdc` Spectator: restore one-tick extrapolation, now backed by measurement

Author: Zach Asher. Full hash: `f71efdc8d6d67ee2ab8a5f50db5f36b380931b80`.

Zach reported the view still jumping forward and back. I had guessed at this
twice and been wrong twice, so this time I measured it against a live run --
sampling the spectator-to-vehicle offset at 50 Hz while the car drove:

  mean  -7.81 m   against a nominal placement of -6.00 m
  values alternate cleanly between -7.80 m and -9.60 m, a 1.80 m swing

1.80 m is exactly one tick of travel at 20 mph and dt=0.2 s. So the camera sits a
systematic ONE tick behind and intermittently TWO, which is the visible snap.

Cause confirmed: the transform is set before world.tick() and CARLA applies it ON
that tick -- the same tick that moves the car -- so the camera always lands where
the car was.

I REVERTED THIS EXACT FIX EARLIER FOR THE WRONG REASON. I pulled the extrapolation
when Zach said jumping persisted, reasoning it might be causing an overshoot. The
persistence was actually two other bugs, both since fixed: warmup_to_speed froze
the spectator for up to 95 ticks per lap, and closed_loop_ledger.py never updated
it at all. The extrapolation was right; my inference from the symptom was not.

Honest limit, recorded in the docstring: this cancels the systematic 1.8 m lag,
NOT the occasional second tick. That is RPC timing jitter -- whether
set_transform reaches the server before it processes the tick -- and a client not
synchronised to the render cannot control it. Expect a correctly centred view
that still twitches sometimes.

Measurement caveat also worth stating: the sample reads vehicle and spectator
transforms in two separate non-atomic RPC calls, so some apparent lag could be
the read race rather than the render. The magnitude matching one tick of travel
exactly, and the mean sitting exactly 1.8 m beyond nominal, is what makes the
render explanation the credible one.

<a id="99df778"></a>
## 2026-08-11 `99df778` F11: width is the capacity lever; resolution loses on both axes

Author: Zach Asher. Full hash: `99df778212e7845c451690728d4ce4e2b7a41e0d`.

Distilled from teacher_mixed_dagger_r07 over 102,938 frames, four conditions:

  1x width 84x28    5,152 ReLU   KD RMSE 0.0263
  2x width 84x28   10,304        0.0227
  3x width 84x28   15,456        0.0201   <- best
  4x width 84x28   20,608        0.0215
  2x width 112x38  21,504        0.0319   <- worst

Width knees at 3x: 4x costs 33% more neurons and is worse on the offline metric,
so there is no case for paying that bound-looseness at M6.

Resolution loses on BOTH axes simultaneously. 112x38 needs more neurons than any
width config -- 21,504 against 3x width's 15,456 -- for the worst KD RMSE in the
sweep. More of exactly what verification pays for, less of what we want.

I HAD REOPENED THIS QUESTION AND WAS WRONG TO. CONSTRAINTS item 8 argued
resolution was viable again because the verifier's input is the physical
parameter rather than the image, so resolution no longer inflates the
PERTURBATION dimension. That reasoning is correct and still stands -- it is just
not the binding cost. Resolution scales ReLU count as k^2 where width scales it
as k, and ReLU count is what drives bound looseness. Same conclusion the frozen
repo reached, for a different reason than it recorded.

140x47 dropped rather than run: strictly further along the same losing trend at
roughly 33,000 ReLU, and unattended time is scarce with the machine reaping
background jobs every ~15 minutes (four times now, consistent with Zach's read
that another CARLA session loading large maps triggers the OOM killer).

KD RMSE stays a screen, not a decision. Closed loop picks the config; this bounds
the search to 1x-3x width at 84x28.

<a id="11bbb4f"></a>
## 2026-08-11 `11bbb4f` M2.5 COMPLETE: mixed teacher passes all four conditions, both directions

Author: Zach Asher. Full hash: `11bbb4f27410f11e8484fa085ceb098bba38cec3`.

teacher_mixed_dagger_r07, converged at round 8, 0% over budget on every leg
against a 1.75 ft gate and a 2.19 ft budget:

  clear     0.35 / 0.29 ft
  fog       0.58 / 1.09 ft
  night     0.44 / 0.39 ft
  shadows   0.55 / 0.35 ft

Extending past the original 6 rounds was the right call. night/eastbound had sat
at 2.53-2.55 ft for three consecutive rounds while everything else converged, and
looked like a hard spot rather than something more rounds would fix -- the
earlier diagnostic put night failures at the east-end curve, which is the
headlight-geometry story. It dropped to 0.44 ft at round 8. Accepting the round-6
teacher would have propagated a marginal policy into both students.

Both teachers now in hand: teacher_clear_dagger_r03, teacher_mixed_dagger_r07.

CARLA released for Zach's other project -- 0 processes, GPU at 400 MiB. Nothing
in M3's distillation stage needs the simulator.

scripts/batch_distill.sh runs the whole capacity sweep in one go so the CARLA
handover can be long rather than alternating: S_clear at baseline width, then
S_mixed across four widths and two higher resolutions. The objective is minimum
ReLU COUNT that drives all four conditions, since ReLU count is what drives bound
looseness -- not "enough width". Width scales ReLU by ~k, resolution by ~k^2, and
resolution is only on the table at all because the verifier's input is the
physical parameter rather than the image.

KD RMSE is used as a screen, not a decision: measured today, 4x width barely
moved it (0.0338 -> 0.0314) while flipping a closed-loop direction from fail to
pass. Closed loop decides; this batch only narrows what one CARLA session has to
test.

<a id="9763e82"></a>
## 2026-08-11 `9763e82` F10: retract the d=2 result -- my BaB search order was wrong

Author: Zach Asher. Full hash: `9763e82c9cd64d155e2568f1e5cc0019d1a4b97b`.

I reported night at d=2 as "dramatically worse" than fog and called it the k^d
cost appearing for the first time. That was my bug.

The BaB loop used stack.pop() -- LIFO, so it always popped the box it had just
pushed, the SMALLEST one, burrowing into an ever-shrinking corner while large
undecided siblings sat untouched on the stack.

The data said so and I nearly filed it as a finding. Raising the budget from 48
to 400 cells changed the resolved volume by NOTHING: 33.2%, 81.6%, 4.2% UNKNOWN,
identical to three significant figures. Eight times the work for zero progress is
a broken search, not a cost curve. bound_box was verified sound in isolation
first (width 0.153 -> 0.087 -> 0.041 -> 0.0073 -> 0.0014 as the box shrinks),
which localized the fault to the search order rather than the verifier.

Fixed to largest-volume-first via a heap. Same frames:

  frame      LIFO @ 400      largest-first @ 120
  +0.0040    33.2% unknown   13.3%
  -0.0241    81.6% unknown   46.9%
  +0.0062     4.2% unknown    0.0%, fully certified

Less than a third of the budget, UNKNOWN roughly halved, one frame fully
resolved, and it is converging where before it was not.

What can honestly be said now: d=2 does cost more than d=1 -- fog resolves at a
median of 15 bounds with 0.78% UNKNOWN, night at 120 bounds still sits at 13.3%
median. Whether that ratio matches k^d needs night run to convergence with the
bounds counted, which is now running at a 500-cell budget.

The withdrawn claim is kept visible in FINDINGS rather than edited away.

<a id="d08408e"></a>
## 2026-08-11 `d08408e` Spectator: revert my extrapolation, fix the real cause (frozen during warmup)

Author: Zach Asher. Full hash: `d08408eac23d6382692e42092b6ca9df6f960a19`.

Zach reported the render still skipping after the earlier "fix", so I stopped
guessing and read the tick loops instead.

THE REAL CAUSE. warmup_to_speed ticks up to 95 times per lap -- 15 settle plus up
to 80 acceleration -- and NEVER touches the spectator. So at the start of every
lap the camera froze at the old pose while the car accelerated away, then the
drive loop's first update_spectator snapped it forward. Sixteen laps per DAgger
round. The recovery-reset path in dagger.py and dagger_student.py had the same
hole: six bare world.tick() calls with no spectator update, followed by another
warmup. Both now update the spectator inside their tick loops.

REVERTED my velocity extrapolation. It was built on an unverified premise about
when CARLA applies a spectator set_transform, it did not fix the reported
symptom, and if the transform actually applies immediately then it CAUSES an
overshoot -- camera leaps ahead, car catches up -- which is precisely the
"forward and back" artefact it was meant to remove. A constant one-step trail is
harmless; an overshoot is not. Place the camera from the pose we have and do not
predict.

Residual 5 Hz stepping is inherent and unchanged: FIXED_DT is the control rate
the study is defined at, so motion really is five discrete 1.79 m steps per
second.

CONFORMANCE CAUGHT TWO REAL GAPS when perturbations/verifiable_disturbance/
disturbance_models were transplanted -- two tests went from skip to live and
failed immediately:

  - verifiable_disturbance had no PROBE_DELTA constant; the probe step lived in a
    default argument where trap 12 could not assert on it. Now declared at 0.1,
    which clears uint8 quantisation by 25x, and used as the default.
  - the trap-9 test assumed an apply(cond, theta) dispatcher that does not exist.
    Rewritten against the real per-condition API (apply_fog/apply_rain/
    apply_night), asserting each returns full sensor resolution.

14 passed, 1 skipped.

Takes effect at the next process launch; stage 4 has these modules already
imported.

<a id="4f034ec"></a>
## 2026-08-11 `4f034ec` F9: verification is decisive on this disturbance family -- UNKNOWN under 2.5%

Author: Zach Asher. Full hash: `4f034ecaf13181121818e50a74ac30434531026b`.

20 clear frames, adaptive bisection over MOR 2000-60 m at depth 7, corridor
centred on clear-weather steering, per-row transmission per F8. 322 bound
computations total.

  certified fraction   median 98.0%, mean 84.6%, range 5.5-100%
  UNKNOWN              median 0.78%, max 2.34%
  bounds per frame     median 15, max 33
  fully certified      6/20 frames over the whole axis
  under 50% certified  3/20

The UNKNOWN rate is the result and it is the one number here that does not
depend on the calibration constants being right. The previous generation
reported 11.5% UNKNOWN for its disturbance-trained student, meaning the verifier
frequently could not decide. Under 2.5% worst-case says the physical
parameterization plus alpha-CROWN plus input-space bisection returns a decisive
verdict nearly everywhere -- which is the core feasibility claim of the approach.

FLAGGED, NOT EXPLAINED: certificates are non-monotone in visibility on some
frames. Frame 3 certifies [75,121] U [393,2000]; frame 5 certifies [60,105] U
[1348,2000] -- certified in dense fog AND near-clear, falsified in between. A
physical story exists (as MOR -> 0 the image saturates toward uniform airlight and
the output may drift back toward its clear value) but it is equally consistent
with the uncalibrated A=0.78 producing an artifact. Recheck when the airlight is
measured.

ALSO RECORDED: do not oversell efficiency from this. Verification returns a
per-frame certified interval in ~16 bounds; closed loop returns pass/fail per
lap. Different granularities, so 322-bounds-vs-N-laps is not like-for-like. That
claim needs the M6 blind protocol.

Inputs remain provisional: student distilled from pre-fix data, airlight
uncalibrated, flat-road row depth.

<a id="4d7bebd"></a>
## 2026-08-11 `4d7bebd` DENSE: record availability uncertainty and a fallback that may be better

Author: Zach Asher. Full hash: `4d7bebd0de6807e97a582f45c9b914b9e0dd1a9a`.

Status after Zach submitted the registration form: on-screen German confirmation
received, no email. Checked rather than assumed --

  gruberto/PixelAccurateDepthBenchmark README download link  ->  404, dead
  the Ulm registration form page                             ->  live, accepts
  that repo's issue #1 "Unable to download dataset"          ->  May 2020,
                                                                 closed, no
                                                                 visible reply

Nothing proves the data is gone, but the DENSE project has ended, maintainers are
split between Ulm and Daimler, the repo's own link has rotted and the one public
access issue went unanswered. Treat delivery as uncertain rather than delayed:
check spam, email the three maintainers directly naming PADB and its fog-chamber
subset, give it about a week.

FALLBACK, and possibly the better instrument: Cerema's PAVIN Fog and Rain
platform records CONTINUOUS fog dissipation from 10 m to 100 m with a reference
visibility meter measuring throughout -- a continuous MOR sweep rather than 17
discrete steps, and denser fog than PADB reaches. The REHEARSE dataset (ROADVIEW,
January 2025) includes PAVIN chamber data and is recent enough to be actively
maintained, which DENSE is not.

Shared limitation now stated explicitly: PADB covers 20-100 m and PAVIN 10-100 m
against our declared 2000-60 m fog axis, so only the severe end can ever be
externally validated. No chamber produces 2 km visibility. That is inherent and
belongs in the paper regardless of which dataset lands.

Licence question RESOLVED (Zach): paper only. DENSE/PADB stays inside the
academic work and the funding demo is built entirely on CARLA results, which
carry no such restriction. Recorded so the boundary is not blurred later.

<a id="a531a64"></a>
## 2026-08-11 `a531a64` M6 machinery: adaptive BaB over the fog axis produces ODD sub-ranges

Author: Zach Asher. Full hash: `a531a64c9704984841d85af14e2702fdda9d6174`.

scripts/certify_fog.py is the M6 machinery in miniature -- one condition, one
frame at a time -- and it runs end to end without CARLA.

Corridor centred on CLEAR-weather steering per trap 6, not on the disturbed
midpoint: centring on the midpoint certifies only insensitivity to the parameter
while permitting an arbitrary offset from what clear weather would produce, which
is the hazard, and is the bug that once made night read 100% certified while
failing 85% of closed-loop frames.

Transmission per-row, never banded (F8).

Provisional output on S_clear_84x28:

  frame 0   13 bounds   98.4% certified   -> certified above 90 m MOR
  frame 1   13 bounds   95.3% certified   -> certified above 151 m MOR
                         3.1% falsified
  frame 2    1 bound    100%  certified

Mean 9 bound computations per frame to resolve the whole visibility axis into
certified and falsified sub-ranges. Each is seconds. That is the deliverable
shape the study promises -- a bounded region of the ODD rather than a single
verdict -- and the sampling-cost comparison is now measurable rather than
asserted.

NOT RECORDED AS LEDGER CELLS, deliberately:

  - S_clear_84x28 was distilled from the pre-fix contaminated data
  - the airlight is still A=0.78, the UNIDENTIFIED constant from the previous
    generation; the certified boundary moves with it (F22)
  - flat-road row depth, not the measured depth map (D4)
  - it says S_clear is CERTIFIED in fog while the ledger pre-registers
    S_clear/fog as FALSIFIED

That last one is a contradiction under our own rule and is flagged rather than
dismissed. It is premature to hunt it while none of the inputs are final, but it
is exactly the check the ledger exists to force, and it must be resolved once the
students and the calibrated model land.

<a id="d412ca8"></a>
## 2026-08-11 `d412ca8` F8: the 6-band depth discretization was the binding constraint, not the physics

Author: Zach Asher. Full hash: `d412ca888ac565bec2407d2c22c928cc3f4e2628`.

Measured without CARLA, on S_clear_84x28 through upstream alpha-CROWN.

Fog is driven by ONE scalar. The inherited machinery hands the verifier a box
over six per-band transmissions, where banded_transmission_box takes min/max over
the ROWS INSIDE each band. That conflates variation from the MOR interval, which
we are bounding, with variation from depth, which is fixed per pixel and not free
at all. So the perturbation never shrinks as the interval shrinks: at a
1-METRE-WIDE interval [60,61] the banded model still had |W|max = 0.242, barely
changed from the full [60,2000] range.

Bound width against the 0.0120 closed-loop tolerance:

  MOR interval    banded box   banded rank-1   per-row rank-1
  [60, 2000]        9.488          1.218           0.198
  [60, 150]           -            0.628           0.0507
  [60, 80]            -            0.276           0.0370
  [60, 61]            -            0.191 (floor)   0.00129  -> CERTIFIED

Removing the banding removes the floor: |W|max falls 0.301 -> 0.0024 as the
interval narrows, and the bound CONVERGES TO THE CONCRETE RANGE (0.0507 vs 0.0506
concrete at [60,150]; 0.0370 vs 0.0370 at [60,80]). alpha-CROWN is essentially
exact on this family once the parameterization is right, and branch-and-bound
does work -- the earlier "splitting does not help" reading was the discretization,
not the problem.

TWO CORRECTIONS TO MY OWN CLAIMS, kept visible rather than quietly fixed:

1. linearity_probe.py reported every condition "EXACT" at ~1e-6. That is close to
   tautological -- each model is parameterized BY CONSTRUCTION in a quantity it is
   linear in. The probe measured the wrong thing; conservatism decides
   certifiability, not linearity residual.
2. My first box-vs-rank1 run showed a floor at 0.19 and I came close to reporting
   it as a limit of the approach. It was my own harness inheriting the banding.
   The anomaly that caught it: a bound should collapse at a 1 m interval and did
   not.

Consequence for M5, now written into docs/DISTURBANCE_MATH.md: do not band. Use
per-pixel transmission from the measured depth map with one scalar driving all of
it. Band count is not a hyperparameter; banding is the error.

Open and now the real question: at [60,2000] the CONCRETE output range is 0.0494,
already 4.1x the tolerance, so no verifier can certify that interval -- the
network genuinely varies that much. Certification comes from BaB over
sub-intervals and the result is a SET OF MOR SUB-RANGES, which is exactly the
"bounded region of the ODD" the study claims to deliver. Cell count is the next
measurement.

<a id="de4e93a"></a>
## 2026-08-11 `de4e93a` DENSE: we were pointing at the wrong dataset; request PADB, not Seeing Through Fog

Author: Zach Asher. Full hash: `de4e93a207016a24843348140566d218275d28e2`.

Verified against the sources rather than recalled. The inherited notes recorded
"DENSE / Seeing Through Fog: 17 measured fog visibility levels, 12-bit RGB, lidar
depth". Those properties belong to a DIFFERENT dataset in the same family.

  Seeing Through Fog        ~3 chamber visibility levels (30/40/50 m), 12,000
                            annotated road samples we have no use for, one very
                            large split archive
  Pixel Accurate Depth      17 levels, 20-100 m in 5 m steps, plus clear/light
  Benchmark (PADB)          rain/heavy rain, day and night, 1,600 samples,
                            12-bit stereo RGB, and depth from a Leica
                            ScanStation P30 survey scanner rather than lidar

Requesting STF would have meant a very large download dominated by data this
study cannot use, at three visibility levels instead of seventeen.

PADB also fixes the previous generation's actual blocker rather than merely
supplying real imagery: the vehicle is static while 50x50 cm diffusive Zenith
Polymer reflectance targets are moved to known distances. Known reflectance at
known depth at measured MOR makes the Koschmieder pair (beta, A) MEASURABLE
instead of fitted -- which is precisely the identifiability failure that made the
fog certificate an artifact of an unidentifiable airlight.

Caveat now recorded in both STUDY.md and METHODOLOGY.md: the chamber covers
20-100 m while our declared fog axis runs 2000-60 m, so only the severe end can
be externally validated. A chamber cannot produce 2 km visibility.

docs/DENSE_ACCESS.md has the registration URL, every form field, the licence
terms, and the dataset contacts.

FLAGGED FOR A DECISION BEFORE THE DATA IS USED: the licence is royalty-free for
"own research and teaching" and PROHIBITS COMMERCIAL USE. The paper is fine. An
investor-facing demo built on this data is not obviously covered, and this
project has an explicit commercial goal. Either keep DENSE strictly inside the
academic work and build the demo on CARLA results, or ask the contacts about
terms -- but decide first.

<a id="65ec8ae"></a>
## 2026-08-11 `65ec8ae` Stand up the verification stack on upstream auto_LiRPA; all cross-checks pass

Author: Zach Asher. Full hash: `65ec8aef12e36fb7c108b49ddd25b6a141c12e5f`.

Done during the CARLA handover. auto_LiRPA had never actually been installed in
this repo -- the previous generation used its VENDORED SDP-CROWN fork via a
repo-root path, which constraint 2 forbids carrying forward.

FIRST: I BROKE THE SHARED VENV AND FIXED IT. `pip install auto_LiRPA` pulls PyPI's
0.3, which is years stale, DOWNGRADED torch 2.5.1+cu121 to 1.12.1 and killed CUDA
in an environment the frozen repo also uses. Restored to torch 2.5.1+cu121 /
torchvision 0.20.1+cu121, CUDA verified working, carla/cv2/numpy verified
importing. requirements.txt now documents all three traps so nobody repeats it:
PyPI is stale and rewrites torch, --no-deps is mandatory, and upstream's
requires-python ~=3.11 has to be overridden because the CARLA client wheel pins
us to 3.10.

That last one is an override, not an assumption, so it is verified rather than
trusted: scripts/verify_smoke.py computes real bounds on a real StudentNet and
asserts the installed package carries no SDP-CROWN markers.

ALL THREE MANDATORY CROSS-CHECKS PASS on S_clear_84x28, 5,152 ReLU:

  zero perturbation -> [+0.069682, +0.069682], collapses to nominal exactly
  soundness         -> bound [-0.119838, +0.301609] contains concrete
                       [+0.059238, +0.078655]
  tightness         -> IBP 9.358629 >= CROWN 0.421448 >= alpha-CROWN 0.381512

BONUS RESULT, and it is a paper figure. A pixel-space L-inf ball at eps=1/255
over 7,056 input dims gives an alpha-CROWN width of 0.381512 against a
closed-loop tolerance of 0.0120 -- 31.8x too loose to certify anything, at a
perturbation of literally one grey level. That independently reproduces the
previous generation's "full-dimensional pixel ball is vacuous" finding on a fresh
network with upstream tooling, and it is the baseline the physical
parameterization has to beat.

<a id="c2ebb33"></a>
## 2026-08-11 `c2ebb33` Close trap 2 properly: frame-id matched capture everywhere, one implementation

Author: Zach Asher. Full hash: `c2ebb33e84f4a15db8b67be77bf89ed44cb16702`.

Done during the CARLA handover -- pure code, no simulator needed.

Every drive loop consumed frames with a bare queue.get() wrapped in
try/except: continue. That is correct while it works and silently wrong the
moment it does not: one timeout leaves that tick's frame queued, the loop ticks
again, and every subsequent get() returns the PREVIOUS frame -- pairing
image[t-1] with pose[t] for the rest of the lap, 1.79 m of error at 20 mph, with
nothing logged and every frame looking plausible.

No evidence it ever fired. The queue accounting is balanced (warmup drains one
image per warmup tick) and >3,000 frame-id-matched grabs across the exposure, fog
isolation, dynamic range and night verification sweeps never once raised. But
nothing would have told us if it had, which is the problem.

env.grab_frame() matches on the id world.tick() returns: older frames are
discarded, a newer frame or a timeout raises FrameDesync rather than being
swallowed. Wired into collect_data, dagger, dagger_student, evaluate and
closed_loop_ledger. drive_expert uses the new env.drain_frame() instead, since
the oracle never looks at the image and there is no pairing to get wrong --
stated explicitly rather than left as a bare get that reads like a bug.

calibrate_exposure.grab() WAS a second implementation of frame matching and now
delegates to carla_env. Two copies of one piece of logic is exactly how trap 13
happened; there is now one.

Conformance test asserts no module outside carla_env calls *_queue.get(), so this
cannot come back. 12 passed, 3 skipped.

CLAUDE.md gains the generalised rule rather than a fourth separate lesson:
a read or a placement issued next to a write does not see that write. Four
instances so far -- sensor queue, weather presets, spectator, queue desync -- all
silent, all the same next-tick semantics.

<a id="3e413c6"></a>
## 2026-08-11 `3e413c6` STUDY M7: add combined disturbances to the stretch goals

Author: Zach Asher. Full hash: `3e413c6b8673c355af7373cace23ffeea6bf4a29`.

Zach's idea, 2026-08-11: fog+night, rain+fog, rain+fog+night. Recorded alongside
the night-vs-dusk interpolation probe, gated on M5 and M6 landing first.

It may be the better probe of the two. Train on single conditions, verify over
the JOINT box, and ask where the combination fails -- nobody's intuition is
reliable about fog-at-night, so a correct prediction there is a real prediction
in a way "it fails at dusk" is not. A joint certificate is also literally the
form an ODD is written in ("visibility > X AND illuminance > Y").

It also stress-tests the paper's central technical claim for the first time. The
tractability argument is that theta is low-dimensional so BaB costs k^d rather
than 2^thousands, and at d=1 that is never actually tested.

Two things recorded as NOT free, because "just compose them" is the tempting
reading:

1. Composition is BILINEAR, not affine. fog then night gives
   x'' = (g*t)*x0 + (g*A*(1-t) + c*H) -- the gain is a product of the two
   conditions' parameters, so the composed map loses the exactly-affine property
   each has alone. BaB absorbs it (on a cell with t pinned narrow, g*t is affine
   in g with a quadratically shrinking residual) but cells go k -> k^d.

2. The easy composition is PHYSICALLY WRONG. Naive fog-then-dim holds the
   airlight fixed, but at night the airlight is headlight backscatter
   concentrated in the near field, not skylight. Real fog at night is a bright
   wall in front of the car. fog+night needs A(lux), a modelling extension rather
   than a composition. Same for rain+fog, where streak brightness should itself
   be fog-attenuated by each drop's depth.

Also noted: shadows are largely exclusive with the others since they need direct
sun, but thin fog WITH sun is physically real and fog washing out shadow contrast
is a genuine interaction worth one experiment.

<a id="993e3ad"></a>
## 2026-08-11 `993e3ad` Fix preset read-after-write race: night was running at fog_density 70

Author: Zach Asher. Full hash: `993e3adc1979b422d982e37bc5a587e4ab5608eb`.

Caught by Zach watching the render -- he said the night driving had fog in it.
Verified live: sun_altitude_angle -25 WITH fog_density 70.

ROOT CAUSE. `world.set_weather()` is applied by the simulator on the NEXT TICK,
so a `world.get_weather()` issued immediately after returns the PREVIOUS
condition's values. Presets were built read-modify-write: set_clear_weather()
cleared fog, the read-back returned the stale still-foggy parameters, the sun
angle was set on that object and pushed -- reinstating fog. Nothing errored and
the frames looked plausible. Same shape as trap 2, where CARLA's sensor queue
runs a frame behind.

This was introduced by MY preset-isolation edit. The original presets set every
confounding field explicitly in each branch, so they were self-contained despite
the read-back; rewriting them to lean on set_clear_weather plus a read-back is
what created the race.

FIX. Presets are now CONSTRUCTED, never read-modify-written: a fresh
carla.WeatherParameters with every field set from CLEAR_BASELINE plus a
single-axis delta. No live state is read, so order-independence is structural.

Verified live, cycling fog -> night -> shadows -> night:
  after fog      sun  90.0  fog 70.0
  after night    sun -25.0  fog  0.0
  after shadows  sun  15.0  fog  0.0
  after night    sun -25.0  fog  0.0

Two new conformance tests, both would have caught this:
  - each condition moves exactly one axis (no other condition's axis active)
  - weather_params is independent of call order
Conformance now 11 passed, 3 skipped.

DATA IMPACT. The race only fires when a condition follows another in the same
process. data/clear was clear-only and the clear branch never read back;
data/night was a night-only process off a fresh world. data/mixed shadows
followed night which followed fog, so it carried fog; data/mixed fog took the
map default as its base rather than our baseline. Rather than spend longer
proving which frames survive than recollecting takes, everything is retired to
data/_retired_presetrace/ (reversible) and all four conditions are being
recollected into a single order-independent dataset.

<a id="a1dea9f"></a>
## 2026-08-11 `a1dea9f` Fix two bugs in dagger_student: missing exposure switch and no beta-mixing

Author: Zach Asher. Full hash: `a1dea9f9070565d29e7dc1528b3f8484ecf79686`.

Killed the student-DAgger run after round 0 rather than burn 80 more minutes on
a configuration that could not have worked.

BUG 1, and it was mine. dagger_student used env.set_weather, not
env.set_condition, so it captured every condition through the PREVIOUS
condition's exposure -- night through the daylight setting. When per-condition
exposure was added I converted collect_data, dagger and evaluate and missed this
file. That is trap 13's own lesson (grep every call site when fixing a bug like
this) applied to a different bug, one commit after writing it down.

BUG 2. dagger_student had no beta-mixing, no recovery reset and no
abort_on_departure -- its drive_collect was a plain loop where dagger.py had all
three. Trap 15 exactly. Measured at round 0: night aborted at step 32 and step
30, so four rounds would have contributed ~120 night frames against 83,000.
Student-DAgger could not have fixed night no matter how many rounds it ran.
Ported dagger.py's mixing and recovery logic, plus the two-pass split where
evaluation runs under pure policy control and collection runs with expert
assistance, since a weak policy cannot serve both in one lap.

Both are now conformance tests rather than things to remember:

- no pipeline module may call env.set_weather directly (carla_env excepted)
- distill.KDDataset preload must be parallel

The second caught a live instance while being written: SteeringDataset was
parallelised and KDDataset was not, so the original trap-17 test passed while the
real bottleneck sat in a second class -- single-threaded decode of 83,567 frames
on every distill run this session. Same two-implementations shape as trap 13.
Now parallelised.

Conformance 9 passed, 3 skipped. Restarted with --beta0 0.6.

<a id="e93e261"></a>
## 2026-08-11 `e93e261` Width sweep: S_mixed is NOT capacity-bound; expose distill's warm-start on the CLI

Author: Zach Asher. Full hash: `e93e261520336f8d06b67580f9447a8efed0a7c1`.

Sweep at 84x28, distilled from teacher_mixed_dagger_r04 over 83,567 frames:

  width   ReLU     params    KD val RMSE
    1x    5,152     ~10k       0.0338
    2x   10,304    39,809      0.0372
    3x   15,456    88,513      0.0327
    4x   20,608   156,417      0.0314

Quadrupling the neurons buys 7%, non-monotone through 2x. That is a plateau, not
a capacity ceiling -- a capacity-starved model improves steadily as capacity is
added. CORRECTING MY EARLIER CALL: I said "5,152 ReLU holds one condition and not
four" on the strength of the S_clear control alone. The control does establish
that S_mixed is worse than S_clear at matched architecture; it does not establish
why, and width was the cheap way to find out.

The real signature was in the training curves and I read past it: every S_mixed
run scored best at a low epoch and then degraded, which is optimization, not
capacity.

distill_student() has had an `init_from` parameter all along, documented as
stabilizing multi-condition re-distill -- the same lesson as trap 14, where
multi-condition DAgger diverges without warm start and needs fine-tuning at
reduced lr. It was never wired to the CLI, so the documented fix for exactly this
failure was unreachable from the command line. Now exposed along with --lr and
--patience.

Testing warm-start from S_clear_84x28 at lr 5e-4, 1x width. If it works we keep
the 5,152-neuron student, which matters at M6: 4x width means 4x the ReLU
relaxations and looser bounds, and bound looseness is one of the two candidate
causes of the previous generation's unresolved anomaly.

<a id="a86f47e"></a>
## 2026-08-11 `a86f47e` Exposure becomes a declared function of condition; retire old night data

Author: Zach Asher. Full hash: `a86f47e6c62e9a18af15cf50289c427256263cc5`.

Decision (Zach): condition-dependent exposure. The alternative readings -- reduce
night severity, accept night as an ODD boundary, or run more DAgger rounds --
were weighed against the measurement below.

WHY IT WAS FORCED. The mixed teacher failed night in all 6 DAgger rounds while
passing fog and shadows and holding clear. Night's over-budget fraction did
improve (56% -> 0.9%) but max|CTE| never did (30 -> 22 -> 27 -> 44 ft), and the
failures cluster at ONE place: round 6 westbound is over budget only at
x 386-388, y -173..-149, the curve at the east end of the loop. That is headlight
geometry -- on a curve the beams point straight while the road turns away, so the
lane is unlit exactly where steering input matters most.

But that was measured through a camera clipping 50.6% of the night road ROI to
zero. scripts/exposure_dynamic_range.py shows no single exposure serves both
ends: clearing the clipping bound needs shutter=25, which puts the clear road at
mu=0.938 -- back in the washed-out regime that made the fog airlight
unidentifiable. Calling night uncertifiable from that rig would have repeated the
headlights-off error: an artefact of the setup reported as a property of the
model.

MEASURED at the new declared exposures, 15 poses:

  clear  shutter 800  mu 0.290  sigma 0.0858  clip_lo  3.4%  clip_hi 0.0%
  night  shutter 200  mu 0.200  sigma 0.1520  clip_lo 12.6%  clip_hi 0.0%

Night stays DARKER than clear, so it remains a dimming disturbance rather than an
auto-exposure-style normalization; contrast recovers 2.6x; clipping falls from
50.6% to 12.6%, the remainder being the genuinely unlit far field beyond the
headlight throw that no exposure recovers; no highlights blown.

WHAT IT COSTS, and the paper must say so: the certificate now reads "certified at
X lux WITH THE CAMERA EXPOSING AS DECLARED". The night disturbance's gain carries
the exposure ratio (x4.0) as a known factor alongside the illuminance ratio. Both
are known because we set them, so identifiability -- the entire reason for
pinning exposure -- is preserved. A declared function is not auto-exposure: an
auto-exposure loop is opaque and destroys the mapping.

Exposure is a blueprint attribute and cannot be changed on a live sensor, so
env.set_condition() respawns the camera with the condition's declared exposure.
All three condition-switching call sites (collect_data, dagger, evaluate) now use
it; using set_weather alone would capture the new condition through the previous
condition's exposure.

Old-exposure night data moved to data/_retired_oldexposure/ (reversible, not
deleted): 6,785 night frames plus the 7 dagger_mixed rounds that contain them.
The mixed manifest is rewritten to fog 6,782 + shadows 6,781.

<a id="5e2f6ae"></a>
## 2026-08-11 `5e2f6ae` M2: mixed teacher trained; fix single-base DAgger/distill and trap 13's second site

Author: Zach Asher. Full hash: `5e2f6ae8a207580fa4ab03c5d3a0518228df9895`.

Collected 20,348 frames across fog/night/shadows (13m49s). Mixed BC teacher on
all four conditions: val RMSE 0.0044 over 27,127 frames, against the clear-only
teacher's 0.0042 -- it learned night about as well as clear, which is the first
evidence the dark night data is usable.

TWO BUGS CAUGHT BEFORE THEY COST A RUN.

1. dagger.py and distill.py both took a SINGLE base dataset name. A mixed-
   condition run started from --base clear would have retrained on the clear base
   plus DAgger rounds and silently discarded all 20,348 fog/night/shadows frames,
   producing something called a mixed teacher that had barely seen the
   conditions. Caught by reading the manifest assembly before letting a 90-minute
   run proceed. Both now take a comma-separated list and fail loudly on a missing
   manifest.

2. distill.py carried a SECOND COPY of the legacy-row condition filter -- the
   exact duplication that trap 13 documents, where the previous generation's fix
   landed in train.py and missed distill.py. Both now call
   dataset.filter_conditions, which is the only implementation.

FINDINGS F4 update: night has 50.5% of its road ROI clipped to exactly 0 at the
chosen exposure. scripts/exposure_dynamic_range.py measures whether any single
exposure avoids this and the answer is no -- clearing the clipping bound needs
shutter=25, which puts the clear road at mu=0.938, back in the washed-out regime
that made the fog airlight unidentifiable. The two requirements are incompatible.

Correcting my own overstatement: half the night ROI being black is PARTLY
PHYSICAL. Beyond the headlight throw there is no light, and a real night camera
sees that too. p99=54 against asphalt near 10 is about 5x contrast in the lit
region, which is usable -- and the BC result above suggests it is. The clamp also
does not break the model: clamp01 is exact as two ReLUs, so the night disturbance
stays soundly representable. What it costs is bound TIGHTNESS, since CROWN's ReLU
relaxation loosens with the fraction of pixels near the clamp. That is an M5
concern, not a model-form one.

<a id="2dd919f"></a>
## 2026-08-10 `2dd919f` M1 transplant + D1 measured: auto-exposure confirmed, fog preset confounded

Author: Zach Asher. Full hash: `2dd919ff9002542952d2da16d7bd0a4ee72d143f`.

Transplants the 12 M1 files plus build_routes (1,508 lines, clean import
closure -- only config, imaging and third-party). Conformance: 7 passed,
3 skipped (those need M4/M5 modules).

D1 MEASURED, and it splits.

E7 CONFIRMED. Night's contrast ratio versus clear goes 1.45x under CARLA's
default histogram auto-exposure to 0.68x under manual exposure. Contrast rising
as a scene darkens was never physical; it was the auto-exposure loop
re-normalizing each frame after the weather was rendered -- the same defect that
disqualified ACDC, sitting in the instrument and never checked. This is why the
night model failed the fidelity gate "inverted". Manual exposure is now pinned in
config (shutter 800, f/2.8, ISO 100), putting the clear road ROI at mu=0.290
against a real road's ~0.31, versus 0.703 auto-exposed.

E9 NOT ANSWERED, because the inherited presets could not answer it. set_weather
moved three fields at once: fog changed cloudiness 80->90 and sun_altitude 90->45
alongside fog_density, and rain did the same. Every clear-vs-fog measurement in
the previous generation therefore conflated fog scattering with a lower sun. At
fog_density=70 the old preset moves the road mean by -0.060; with illumination
held fixed it moves by -0.024. Over half the darkening was the sun angle.

Presets now restore the full clear baseline and move exactly ONE axis, which is
what the design rule in CLAUDE.md already required. A shadows preset is added on
the solar-elevation axis.

With fog isolated, the road BRIGHTENS at low density (+0.024 at density 25,
consistent with airlight on a dark road) and then turns around and darkens. That
is the signature of a renderer that both adds airlight and attenuates the
illumination reaching the ground -- which would mean A is not constant across
severities, the assumption Koschmieder makes, and would explain directly why A
was unidentifiable. Not concluded: pooled ROI statistics are exactly what hid the
previous identifiability failure, so this needs the depth-resolved fit (D4, the
pre-registered E8 test) before anything is fitted.

Also here: depth camera and CARLA depth decoding wired into carla_env at the
identical transform as RGB; CLOSED_LOOP_TOLERANCE derived from primitives via a
measured bias horizon rather than hardcoded, reproducing 0.0120; condition
filtering centralized into dataset.filter_conditions as the ONLY filter site,
which is the structural form of trap 13 (a fix landed in one of two sites and
missed the other).

Open design question in FINDINGS.md F2: night and shadows are the same physical
knob at different ranges. One condition or two is not decided.

<a id="0c1feff"></a>
## 2026-08-10 `0c1feff` M0: study design, executable ledger, conformance suite

Author: Zach Asher. Full hash: `0c1feff023dc2a02bb4d8f99807300247d2e2f5a`.

Clean history. No pipeline code yet, deliberately -- the design is the first
artifact and nothing is transplanted until the ledger prints.

The study in four steps: train a clear-weather expert and a mixed-condition
expert in CARLA, distill both into verifiable ReLU-only students, closed-loop
test both under disturbances, then verify both and get the same answer without
simulating. Step 4 is the contribution; steps 1-3 are infrastructure.

The demo form is blind: two students handed over as A and B, verification emits
per-condition verdicts, verdicts are committed, only then does closed loop run.
study/ledger.py --check-order enforces that ordering against git history, so
prediction cannot silently become postdiction.

study/ledger.py is the anti-drift mechanism. The previous study measured a
disturbance-trained student certifying WORSE than the clear-only student at
every visibility below 1000 m -- the exact inverse of the design -- and wrote it
up as a finding instead of hunting the bug. Two causes were never ruled out
(train/verify family mismatch, and 2x width loosening the bounds). The ledger
makes that check a command that exits nonzero rather than something a session
has to remember. See docs/PRIOR_STUDY.md.

Also resolved here:

- D1. The previous study's washed-out road baseline traces to sensor.camera.rgb
  being configured with only image_size and fov, leaving CARLA's default
  per-frame histogram auto-exposure active -- the same defect that disqualified
  ACDC for photometry. Fix the camera, not the weather preset. Unverified until
  M1 measures it.
- Conditions and axes declared before training, so training points, closed-loop
  test points and verified intervals share one axis per condition.
- docs/DISTURBANCE_MATH.md: the derivation template that keeps theta
  low-dimensional through to bound propagation, worked per condition. Night is
  k=2 with zero residual; fog is k=1 per BaB branch via a rank-1 transmission
  model whose residual shrinks quadratically with splitting; shadows are
  verifiable only in the fixed-mask form; rain has no known low-rank form.

Snow is out of scope -- CARLA renders none.


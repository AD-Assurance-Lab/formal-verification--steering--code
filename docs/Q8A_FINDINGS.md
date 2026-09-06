# Q8a — α-CROWN on the undecided cells: findings

**Run 2026-09-05, 18:47–19:5x.** Pre-registration `docs/Q8_PREREGISTRATION.md` (with
amendment A-1), committed `f1dbf22` before any bound was computed. Driver
`scripts/certify_town06.py --method CROWN-Optimized`, a committed flag rather than a local
edit. Artifact `results/town06/beta/cert_alpha.json`, which records `_meta.method =
"CROWN-Optimized"` so it can never be read as a plain-CROWN result. **No simulator.**

```
cell        plain CROWN   alpha-CROWN   tightening   densest witness   witness?   verdict
fog            +1.2400       +1.1983        3.4%          +0.8454         no      NOT_CERTIFIED
night          +2.8361       +1.5581       45.1%          -0.6552         no      NOT_CERTIFIED
low_sun        +0.2991       +0.2909        2.7%          +0.0831         no      CERTIFIED
                                                            (bounds in units of tolerance)
```

## Q8a-P1 — HELD. Neither undecided cell is resolved

Predicted: α-CROWN resolves neither cell. **Neither is resolved.** Both stay
`NOT_CERTIFIED`; `low_sun` was already `CERTIFIED` and remains so.

The cheap route to closing the question fails, exactly as pre-registered, and that is the
result Q8a was run to get: it is the only step that could have closed the question with no
new tooling, so it had to be tried before β-CROWN was justified.

**The prediction's arithmetic was wrong even though its conclusion was right.** It projected
a uniform 6% gain from the §Methodology measurement, giving fog → ~1.166 and night → ~2.666.
Measured: fog tightened **3.4%** and night **45.1%**. The 6% figure was taken from one cell
of a different sweep and does not generalise — the gain is strongly cell-dependent, which is
itself worth knowing before anyone budgets α-CROWN by that number again.

## Q8a-P2 — FALSIFIED, decisively, and in the opposite direction

Predicted: *"the gain is larger on fog than on night, because fog's bound is nearer the
witness and therefore contains proportionally less slack to remove."*

Measured the reverse, by a factor of thirteen:

```
  fog     3.4% tightening      night   45.1% tightening
```

**Night's refusal was mostly relaxation slack. Fog's is not.**

The reasoning behind P2 was not merely unlucky, it was backwards. It assumed proximity to
the witness bounds the available slack. What the measurement says is that the *gap* between
bound and witness is not a measure of slack at all:

```
  cell     bound   witness   gap      slack actually removed by alpha-CROWN
  fog      1.2400  0.8454    0.3946   0.0417   (11% of the gap)
  night    2.8361 -0.6552    2.1809   1.2780   (59% of the gap)
```

Fog's bound sits close to a witness *and* is close to tight. Night's sits far from its
witness *and* was mostly loose. Those are independent properties, and P2 conflated them.

## What this means for Q8b, recorded before it runs

The pre-registration said what to do if this happened: *"If night tightens more than fog,
the slack is not where this reasoning assumes and the Q8b branching heuristic should be
reconsidered before it is written."* Reconsidered, in three points:

1. **Fog is the harder target, not the easier one.** After α-CROWN it sits at 1.198x
   tolerance with only 0.35x of headroom between it and its densest witness. Complete
   verification is more likely to confirm fog's refusal — or find a witness the dense 1-D
   search missed — than to certify it.
2. **Night is now the better candidate to be resolved.** It fell 45% under α-CROWN alone and
   still has 1.56x to shed. Branch-and-bound removes relaxation slack, which is demonstrably
   what night's excess is largely made of.
3. **Q8b-P3 is in doubt for fog specifically.** It predicted that a decided cell would come
   back `CERTIFIED` rather than `FALSIFIED`, reasoning that the dense 1-D search is thorough
   enough that a missed counterexample is unlikely. That reasoning is unaffected for night,
   but fog's near-tight bound makes `FALSIFIED` a live outcome there. **Q8b-P3 stands as
   written** — it was committed before this run and is not being edited — and this note
   records that Q8a moved the odds against it for one of the two cells.

## The α-CROWN cost, measured rather than quoted

Three cells in roughly 50 minutes against plain CROWN's ~100 s per cell — about **17x**, not
the 78x the `Bounder` docstring records from a single interpolation cell. Like the 6%
tightening figure, the 78x cost figure is cell-dependent and should not be used as a planning
constant. Both numbers come from the same one-cell measurement and both are wrong here, in
opposite directions: α-CROWN is **cheaper and less effective** on these cells than the
methodology note implies.

That combination is worth stating plainly, because it inverts the standing argument for
using plain CROWN everywhere. The argument was "78x the cost for 6% tightness". On these
cells it is "17x the cost for 3% tightness on the cell that matters, and 45% on one that is
nowhere near the corridor either way".

## What was NOT done

The canonical certificate is untouched and verified unmodified. `certify_town06.py` refuses
a non-CROWN method on the canonical path *before* the run, and refuses `--out` to that path
under an override — both guards were exercised and both fired. The α-CROWN result is a
**separate artifact** carrying its own `_meta.method`, reported alongside the committed
plain-CROWN certificate and never as a replacement for it.

No driving, no promotion, no `.selected` pin, nothing written to either ledger.

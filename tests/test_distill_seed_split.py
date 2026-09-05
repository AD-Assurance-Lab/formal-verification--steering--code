"""Q6's seed split must be OPT-IN, and the un-opted path must be bit-identical.

WHY THIS EXISTS. `DISTILL_SEED` seeds torch, numpy and python once, after which the
student's INITIALISATION and the DataLoader's minibatch ORDER both draw from the same
global torch stream. That makes "the seed" two variables wearing one name, and it is why
the dispersion this study keeps paying for -- fog p99 CV 42.6%, r ~ 0 between two
objectives at the same seed -- cannot be attributed to either of them.

Q6 separates them with `DISTILL_INIT_SEED` and `DISTILL_DATA_SEED`. The hazard is that
separating them at all could change the default path: passing a `generator=` to a
DataLoader normally changes which RNG the shuffling draws from. Every checkpoint in this
repo, and every published number, was distilled on the un-opted path -- so if that path
moves by one draw, nothing already measured is comparable to anything measured later, and
NOTHING IN A RESULT WOULD REVEAL IT.

The change was verified end-to-end by SHA-256: seed 0 re-distilled after the patch at both
learning rates matched `S_mixed_taildet_a0p0_s0` and `S_mixed_depth_d3lr3_s0` bit-exactly.
That check costs two full distillations and cannot run in the suite, so this file pins the
three properties that make it true, cheaply enough to run every time.

No CARLA and no GPU.
"""
import ast
import os
import pathlib
import sys

import pytest
import torch
from torch.utils.data import DataLoader

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = (REPO / "pipeline" / "distill.py").read_text()


def test_generator_none_is_the_dataloader_default():
    """The load-bearing assumption: `generator=None` == omitting the argument.

    The whole bit-neutrality argument rests on this. If a torch upgrade ever made
    `generator=None` mean something other than "use the global RNG", the un-opted path
    would silently start drawing a different minibatch order.
    """
    data = list(range(64))

    def order(**kw):
        torch.manual_seed(1234)
        return [int(b[0]) for b in DataLoader(data, batch_size=1, shuffle=True, **kw)]

    assert order() == order(generator=None)


def test_an_explicit_generator_actually_changes_the_order():
    """The opt-in path must DO something -- a knob that silently does nothing is worse
    than no knob, because the experiment still produces numbers."""
    data = list(range(64))

    def order(seed):
        # A FRESH generator per call. torch.Generator is stateful, so iterating a
        # DataLoader advances it -- which is what makes successive epochs differ, and
        # what makes reusing one generator across two runs NOT reproduce. distill.py
        # constructs it once per run, which is the correct scope.
        gen = torch.Generator()
        gen.manual_seed(seed)
        torch.manual_seed(1234)
        return [int(b[0]) for b in
                DataLoader(data, batch_size=1, shuffle=True, generator=gen)]

    assert order(1) != order(2)
    assert order(1) == order(1)            # and it is reproducible


def test_reseeding_before_construction_changes_the_weights():
    """The other half of the split: INIT_SEED must control the initialisation."""
    sys.path.insert(0, str(REPO / "pipeline"))
    from student import StudentNet

    def weights(seed):
        torch.manual_seed(seed)
        return StudentNet(56, 168, channels=(4, 8, 8), fc=16).conv[0].weight.clone()

    assert not torch.equal(weights(1), weights(2))
    assert torch.equal(weights(1), weights(1))


def test_the_knobs_are_opt_in_and_off_by_default():
    """With nothing set, the module must report the un-opted path."""
    for var in ("DISTILL_INIT_SEED", "DISTILL_DATA_SEED", "DISTILL_TRAIN_FRAC"):
        assert var not in os.environ or os.environ[var] == "", (
            f"{var} is set in this environment; the default path cannot be checked")
    assert os.environ.get("DISTILL_INIT_SEED") is None
    assert os.environ.get("DISTILL_DATA_SEED") is None
    # Read from source rather than importing distill (which pulls in torch, cv2, config
    # and the dataset layer): the defaults are what is being pinned, not the import.
    tree = ast.parse(SRC)
    assigns = {t.id: n.value for n in tree.body if isinstance(n, ast.Assign)
               for t in n.targets if isinstance(t, ast.Name)}
    assert "SPLIT_SEEDS" in assigns, "SPLIT_SEEDS must be a module-level knob"
    assert "TRAIN_FRAC" in assigns, "TRAIN_FRAC must be a module-level knob"
    # SPLIT_SEEDS is a disjunction of two `is not None` tests -- i.e. it is False unless
    # one of the variables is explicitly set.
    assert isinstance(assigns["SPLIT_SEEDS"], ast.BoolOp)
    assert isinstance(assigns["SPLIT_SEEDS"].op, ast.Or)


def test_the_default_path_is_guarded_in_source():
    """Both new behaviours must sit behind the opt-in flag, not run unconditionally."""
    assert "generator=_gen" in SRC, "the DataLoader must take the (possibly None) generator"
    assert "_gen = None" in SRC, "the generator must default to None, not to a seeded one"
    # The reseed before StudentNet must be conditional.
    i_guard = SRC.index("if SPLIT_SEEDS:\n        torch.manual_seed(")
    i_student = SRC.index("student = StudentNet(")
    assert i_guard < i_student, "the init reseed must precede the student's construction"


def test_train_frac_never_touches_validation():
    """Subsampling val too would move the yardstick with the knob, which is exactly the
    mistake the augment path was already written to avoid."""
    i = SRC.index("if TRAIN_FRAC < 1.0:")
    block = SRC[i:SRC.index("tr = KDDataset(", i)]
    assert "tr_idx" in block
    assert "va_idx" not in block, "TRAIN_FRAC must not touch the validation index"
    assert "RandomState(TRAIN_FRAC_RNG_SEED)" in block, (
        "the subset must come from a FIXED rng, independent of the seed under study -- "
        "otherwise dispersion across seeds is also dispersion across which frames were kept")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))

"""The checkpoint that IS the student is a recorded decision, not the newest file.

Four separate times this study has read a stale artifact as though the current step
produced it. The most expensive: a student-DAgger run resumed from an r03 left behind by
an abandoned run and destroyed a policy that had just passed all four conditions, because
"newest <base>_dagger_rNN" was an inference from mtimes rather than a record of what a
gate accepted.
"""
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "pipeline"))


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    os.environ["STUDY_MAP"] = "Town06"
    sys.modules.pop("config", None)
    import config as C
    monkeypatch.setattr(C, "CHECKPOINT_DIR", str(tmp_path))
    monkeypatch.setattr(C, "STUDENT_DAGGER", True)
    return C


def _touch(d, name):
    open(os.path.join(d, f"{name}.pth"), "wb").write(b"x")


def test_pin_wins_over_a_newer_round(cfg, tmp_path):
    for r in range(4):
        _touch(tmp_path, f"S_x_dagger_r{r:02d}")
    assert cfg.final_student("S_x") == "S_x_dagger_r03"      # without a pin, newest
    (tmp_path / "S_x.selected").write_text("S_x_dagger_r01\n")
    assert cfg.final_student("S_x") == "S_x_dagger_r01"      # with one, the pin


def test_a_pin_pointing_at_nothing_raises(cfg, tmp_path):
    _touch(tmp_path, "S_x_dagger_r00")
    (tmp_path / "S_x.selected").write_text("S_x_dagger_r99\n")
    with pytest.raises(RuntimeError, match="not in"):
        cfg.final_student("S_x")


def test_no_pin_keeps_the_old_behaviour(cfg, tmp_path):
    _touch(tmp_path, "S_x_dagger_r00")
    _touch(tmp_path, "S_x_dagger_r05")
    assert cfg.final_student("S_x") == "S_x_dagger_r05"

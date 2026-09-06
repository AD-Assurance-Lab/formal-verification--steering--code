"""TOWN06_LEDGER_TAG must give an exploratory blind run its own scope, and must never
be able to reach the protected ones.

WHY THIS EXISTS. Q3 wants the blind protocol -- certify, commit, then drive, checkable
against git -- on a student that is NOT the shipped one. Before the tag there was
nowhere to put it. `TOWN06_PASS` accepts only 1 and 2, and both name directories
PROTOCOL R4 requires to stand, so an exploratory blind run had two options:

  * write its scored cells into results/town06/ledger (pass 1's blind record), or
  * skip the order check, which is the entire reason to run the experiment.

The first corrupts the record the study rests on; the second makes the experiment
worthless. So the tag exists -- and because it MOVES the paths that other guards compare
against, it is exactly the kind of mechanism that can quietly disable a guard.

Two properties are pinned here:

  1. With no tag set, every path is byte-identical to what it was.
  2. With a tag set, nothing resolves into a protected directory, and the CANONICAL
     certificate path does not move -- because certify_town06.py's refusals compare
     against it, and a guard whose target moves with the scope guards nothing.

No CARLA, no GPU.
"""
import importlib
import os
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent

PROTECTED_LEDGERS = ("results/town06/ledger", "results/town06/ledger_pass2")
CANONICAL_CERT = "results/town06/certificate_town06.json"


def design(**env):
    """Reload the design module under a given environment."""
    saved = {k: os.environ.get(k) for k in
             ("TOWN06_LEDGER_TAG", "TOWN06_PASS", "STUDY_MAP")}
    try:
        for k in saved:
            os.environ.pop(k, None)
        os.environ.update({k: v for k, v in env.items() if v is not None})
        from steering.study import town06_design as D
        return importlib.reload(D)
    finally:
        for k, v in saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def test_no_tag_leaves_every_path_unchanged():
    D = design()
    assert D.LEDGER_SUBDIR == os.path.join("results", "town06", "ledger")
    assert D.CERT_ARTIFACT == os.path.join("results", "town06",
                                           "certificate_town06.json")
    assert D.CERT_ARTIFACTS == [D.CERT_ARTIFACT]
    assert D.CANONICAL_CERT_ARTIFACT == D.CERT_ARTIFACT


def test_pass_2_still_scopes_its_own_ledger():
    D = design(TOWN06_PASS="2")
    assert D.LEDGER_SUBDIR == os.path.join("results", "town06", "ledger_pass2")
    # pass 2 scores both scopes and must predict with both certificates
    assert len(D.CERT_ARTIFACTS) == 2


def test_a_tag_moves_the_ledger_and_certificate_together():
    D = design(TOWN06_LEDGER_TAG="q3_tuned")
    assert D.LEDGER_SUBDIR == os.path.join("results", "town06", "q3_tuned", "ledger")
    assert D.CERT_ARTIFACT == os.path.join("results", "town06", "q3_tuned",
                                           "certificate.json")
    assert D.CERT_ARTIFACTS == [D.CERT_ARTIFACT]


def test_a_tag_never_resolves_into_a_protected_directory():
    D = design(TOWN06_LEDGER_TAG="q3_tuned")
    assert D.LEDGER_SUBDIR.replace(os.sep, "/") not in PROTECTED_LEDGERS
    assert D.CERT_ARTIFACT.replace(os.sep, "/") != CANONICAL_CERT


def test_the_canonical_certificate_path_does_not_move_with_the_scope():
    """certify_town06.py's two refusals compare against CANONICAL_CERT_ARTIFACT. If a
    tag moved it, both guards would protect the exploratory file and leave the
    published one open."""
    for env in ({}, {"TOWN06_LEDGER_TAG": "q3_tuned"}, {"TOWN06_PASS": "2"}):
        D = design(**env)
        assert D.CANONICAL_CERT_ARTIFACT.replace(os.sep, "/") == CANONICAL_CERT


@pytest.mark.parametrize("tag", ["ledger", "ledger_pass2", "captures"])
def test_tags_that_would_alias_a_protected_directory_are_refused(tag):
    with pytest.raises(SystemExit):
        design(TOWN06_LEDGER_TAG=tag)


@pytest.mark.parametrize("tag", ["../ledger", "a/b", "_leading", "UPPER", "x" * 33, "."])
def test_malformed_tags_are_refused(tag):
    with pytest.raises(SystemExit):
        design(TOWN06_LEDGER_TAG=tag)


def test_a_tag_cannot_be_combined_with_a_deployment_pass():
    """Two scoping mechanisms at once is how one of them gets ignored."""
    with pytest.raises(SystemExit):
        design(TOWN06_LEDGER_TAG="q3_tuned", TOWN06_PASS="2")


def teardown_module(_):
    design()          # leave the module in its default state for other tests




def test_an_unknown_student_gets_no_defaulted_expectation():
    """study.expected() is keyed on the student for every branch but the vacuous one, so
    a name it has never heard of used to fall through to the LAST line -- the clear-only
    student's row -- and be scored against it. Q3 drove an exploratory tuned student and
    got three CONTRADICTS that meant only "this table has no row for me".

    Standing rule 2 makes that expensive: a contradiction is a BUG until a written
    disposition rules out the candidate causes, so a defaulted expectation manufactures
    an investigation with no subject."""
    D = design()
    with pytest.raises(SystemExit):
        D.expected("S_tuned", "fog")
    # the shipped students still resolve exactly as before
    assert D.expected("S_clear_t06", "night") == ("FAIL", "NOT_CERTIFIED")
    assert D.expected("S_mixed_t06", "fog") == ("PASS", "CERTIFIED")
    assert D.expected("S_clear_t06", "fog") == ("PASS", "CERTIFIED")      # D-14


def test_an_exploratory_student_reports_no_expectation_rather_than_inventing_one():
    D = design(TOWN06_LEDGER_TAG="q3_tuned")
    assert D.expected("S_tuned", "fog") == (None, None)
    assert D.expected("S_tuned", "night") == (None, None)
    # a vacuous cell does not depend on the student and must not fall into that branch
    assert D.expected("S_tuned", "clear") == ("PASS", "CERTIFIED")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))

"""The fetcher's digest table must describe the captures the certifier actually reads.

`scripts/fetch_captures.py` is the only route from the published dataset back into this
repository, and its table of digests is the only thing standing between a reader and a
bound computed from the wrong frames. That is not a transport concern. A capture is the
certifier's entire input, so the wrong one produces a sound bound about a different
experiment, complete with a verdict and a margin, and nothing downstream says otherwise.

So the table is checked here rather than trusted: it must be well formed, it must land
files where the certifier looks, and on a machine that has the captures it must match
them byte for byte.
"""
import hashlib
import importlib.util
import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fetcher():
    spec = importlib.util.spec_from_file_location(
        "_fetch", os.path.join(REPO, "scripts", "fetch_captures.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


FETCH = _fetcher()

# Where the two certifiers look. Anything the fetcher places outside these is a file
# nothing reads, and anything they need that it omits is a reader stuck at level 1.
CERTIFIER_DIRS = ("results/town06/captures", "results/town04_v2/calibration")


def test_the_table_is_well_formed():
    assert FETCH.FILES, "the fetcher has no files to fetch"
    for name, rel, digest in FETCH.FILES:
        assert re.fullmatch(r"[0-9a-f]{64}", digest), f"{rel}: not a sha256 digest"
        assert not rel.startswith("/") and ".." not in rel, f"{rel}: escapes the repo"


def test_every_file_lands_where_a_certifier_reads():
    for _, rel, _ in FETCH.FILES:
        assert any(rel.startswith(d) for d in CERTIFIER_DIRS), \
            f"{rel} is fetched into a directory no certifier reads"


def test_both_studies_are_covered():
    """Twelve captures: one per condition on the arterial lap, and two directions by
    four conditions on the highway. A table that quietly lost one would leave a reader
    with a certificate over a subset and no sign of it."""
    npz = [rel for _, rel, _ in FETCH.FILES if rel.endswith(".npz")]
    t06 = [r for r in npz if "town06" in r]
    t04 = [r for r in npz if "town04_v2" in r]
    assert len(t06) == 4, f"expected 4 arterial captures, table has {len(t06)}"
    assert len(t04) == 8, f"expected 8 highway captures, table has {len(t04)}"


def test_no_duplicate_destinations():
    dests = [rel for _, rel, _ in FETCH.FILES]
    assert len(dests) == len(set(dests)), "two entries write to the same path"


def test_the_digests_match_the_captures_on_this_machine():
    """Skipped where the captures are absent, which is most machines. Where they are
    present -- the lab machine, and anyone who has run the fetcher -- this is the check
    that the published table describes the files the paper's numbers came from."""
    checked = 0
    for _, rel, want in FETCH.FILES:
        path = os.path.join(REPO, rel)
        if not os.path.exists(path):
            continue
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        assert h.hexdigest() == want, (
            f"{rel} on disk does not match the digest in fetch_captures.py. Either the "
            f"file changed or the table did; certifying against it would bound a "
            f"different experiment")
        checked += 1
    if checked == 0:
        pytest.skip("no captures on this machine; run scripts/fetch_captures.py")

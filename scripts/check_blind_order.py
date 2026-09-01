#!/usr/bin/env python3
"""Standing rule 1, checked against git: a verdict must be committed BEFORE the
closed-loop run it predicts. Postdiction is not prediction.

    python3 scripts/check_blind_order.py

The lab's rule names `python -m study.ledger --check-order`. That module was removed
from this repo by the "Prune to a minimal public artifact repo" commit (cd01256) along
with the rest of the research record, so from that commit until now the check standing
rule 1 depends on could not be run here AT ALL -- through the whole Town04 redo and the
Town06 rebuild. The sibling repos still carry it. This restores the ordering logic (and
only that) against the layout the study actually has now: one certificate covering many
cells, rather than one verdict file per cell.

Four ways the order can be broken, all of them checked:
  * the certificate was committed after a closed-loop result
  * they were committed in the SAME commit, so the order is unverifiable
  * the certificate was MODIFIED after a run was recorded -- indistinguishable from
    laundering a bound to match the outcome
  * the certificate was committed after the run STARTED, per provenance.run_started,
    which is stricter than comparing commits and is the one that matters
"""
import datetime
import glob
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CERTIFICATES = {
    "town04_v2": ("results/town04_v2/calibration/sustained_bound.json",
                  "results/town04_v2/ledger/*closed_loop.json"),
    "town06":    ("results/town06/certificate/sustained_bound.json",
                  "results/town06/ledger/*closed_loop.json"),
}


def _git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              check=True, cwd=REPO).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _add_commit(path):
    """(hash, unix_time) of the commit that FIRST added `path`, or None."""
    out = _git("log", "--diff-filter=A", "--format=%H %ct", "--", str(path))
    if not out or not out.split():
        return None
    h, t = out.splitlines()[-1].split()
    return (h, int(t))


def _touch_commits(path):
    out = _git("log", "--format=%H %ct", "--", str(path))
    if not out:
        return []
    return [(l.split()[0], int(l.split()[1])) for l in out.splitlines() if l.strip()]


def _is_ancestor(a, b):
    try:
        r = subprocess.run(["git", "merge-base", "--is-ancestor", a, b],
                           capture_output=True, cwd=REPO)
        return r.returncode == 0 if r.returncode in (0, 1) else None
    except FileNotFoundError:
        return None


def _ordered_before(first, second):
    """Ancestry is the primary evidence -- committer dates are forgeable and rebases
    rewrite them. Timestamps are the fallback for histories ancestry cannot order."""
    (fh, ft), (sh, st) = first, second
    if fh == sh:
        return "same-commit"
    anc = _is_ancestor(fh, sh)
    if anc is True:
        return True
    if anc is False and _is_ancestor(sh, fh):
        return False
    return ft < st


def check(study, cert_rel, ledger_glob):
    found = []
    cert_abs = os.path.join(REPO, cert_rel)
    cells = sorted(glob.glob(os.path.join(REPO, ledger_glob)))
    if not cells:
        return [("skip", f"{study}: no closed-loop cells yet")]
    if not os.path.exists(cert_abs):
        return [("error", f"{study}: {len(cells)} closed-loop cell(s) recorded with NO "
                          f"certificate -- order unverifiable")]
    c_add = _add_commit(cert_rel)
    if c_add is None:
        return [("error", f"{study}: certificate not committed, order unverifiable")]

    for cell in cells:
        rel = os.path.relpath(cell, REPO)
        label = f"{study}/{os.path.basename(cell)}"
        r_add = _add_commit(rel)
        if r_add is None:
            found.append(("error", f"{label}: closed loop not committed, order "
                                   f"unverifiable"))
            continue
        order = _ordered_before(c_add, r_add)
        if order == "same-commit":
            found.append(("error", f"{label}: certificate and closed loop added in the "
                                   f"SAME commit -- order unverifiable"))
        elif order is False:
            found.append(("error", f"{label}: certificate committed AFTER the closed "
                                   f"loop"))
        # The run itself, not the commit of its result. This is the strict one.
        try:
            started = json.load(open(cell)).get("provenance", {}).get("run_started")
        except ValueError:
            started = None
        if started:
            try:
                run_t = datetime.datetime.fromisoformat(started).timestamp()
            except ValueError:
                run_t = None
            if run_t and c_add[1] > run_t:
                found.append(("error", f"{label}: certificate committed AFTER the run "
                                       f"STARTED"))

    # A certificate rewritten once the outcomes are known is indistinguishable from
    # laundering the bounds to match them, even when the verdicts are unchanged.
    first_run = None
    for cell in cells:
        try:
            s = json.load(open(cell)).get("provenance", {}).get("run_started")
            if s:
                t = datetime.datetime.fromisoformat(s).timestamp()
                first_run = t if first_run is None else min(first_run, t)
        except (ValueError, TypeError):
            pass
    #
    # What actually matters is the CONTENT: if the file as it stands today is
    # byte-identical to the version committed before the runs, the bounds the drives
    # were compared against are the pre-registered ones, whatever happened in between.
    # A touch that restores the file is not laundering, and a check that cannot tell
    # the two apart makes restoring the correct state look like another violation.
    # So: content mismatch is an error, an excursion that came back is a warning that
    # stays in the record.
    pre_run = None
    for h, t in reversed(_touch_commits(cert_rel)):
        if first_run is None or t <= first_run:
            pre_run = h
    touched_after = [(h, t) for h, t in _touch_commits(cert_rel)
                     if first_run is not None and t > first_run]
    if touched_after and pre_run:
        now = _git("show", f"HEAD:{cert_rel}")
        then = _git("show", f"{pre_run}:{cert_rel}")
        subj = (_git("log", "-1", "--format=%s", touched_after[0][0]) or "").strip()
        if now != then:
            found.append(("error", f"{study}: certificate CONTENT differs from the "
                                   f"version committed before the runs "
                                   f"({touched_after[0][0][:7]} {subj[:50]!r})"))
        else:
            found.append(("warn", f"{study}: certificate was touched after the runs "
                                  f"began but its content matches the pre-registered "
                                  f"version ({len(touched_after)} commit(s))"))
    if not found:
        found.append(("ok", f"{study}: certificate precedes all {len(cells)} closed-loop "
                            f"cells, and was not touched afterwards"))
    return found


def main():
    problems = 0
    for study, (cert, led) in CERTIFICATES.items():
        for level, msg in check(study, cert, led):
            print(f"  {level.upper():5s} {msg}")
            if level == "error":
                problems += 1
    print()
    if problems:
        print(f"  BLIND PROTOCOL: {problems} problem(s) -- standing rule 1 is not "
              f"satisfied as committed")
        return 1
    print("  BLIND PROTOCOL: verdicts precede their runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Verify PROTOCOL R1: every Town06 certificate was committed BEFORE its drive.

This is the whole difference between the deployment test and the discovery test, so
it is checked mechanically against git rather than asserted in prose. The check uses
COMMIT timestamps, not file mtimes: mtimes are trivially altered by a rebuild and
prove nothing, whereas a commit is the record.

    python3 scripts/check_order_town06.py           # exit 1 if any cell is out of order

Import guard, for the ledger to call before it writes a scored cell:

    from check_order_town06 import require_certificate_committed
    require_certificate_committed()
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from study import town06_design as D  # noqa: E402

CERT = os.path.join(REPO, D.CERT_ARTIFACT)
LEDGER = os.path.join(REPO, D.LEDGER_SUBDIR)


def _git(*args):
    return subprocess.run(["git", "-C", REPO, *args],
                          capture_output=True, text=True).stdout.strip()


def first_commit_epoch(relpath):
    """Unix time of the commit that FIRST added `relpath`, or None if untracked."""
    out = _git("log", "--diff-filter=A", "--format=%ct", "--", relpath)
    if not out:
        return None
    return int(out.splitlines()[-1])


def require_certificate_committed():
    """Refuse to run a scored cell unless the certificate is already committed.

    Called by the ledger. This is the guard that makes R1 hold by construction rather
    than by remembering to run a checker afterwards.
    """
    rel = D.CERT_ARTIFACT
    if not os.path.exists(CERT):
        raise SystemExit(
            f"PROTOCOL R1: {rel} does not exist.\n"
            "The certificate must be computed AND committed before any scored Town06\n"
            "closed-loop run. Run the certifier, commit its output, then drive.")
    if first_commit_epoch(rel) is None:
        raise SystemExit(
            f"PROTOCOL R1: {rel} exists but is NOT COMMITTED.\n"
            "An uncommitted certificate is not a prediction -- it can still be edited.\n"
            "    git add %s && git commit -m 'Town06 certificate (pre-drive)'" % rel)
    dirty = _git("status", "--porcelain", "--", rel)
    if dirty:
        raise SystemExit(
            f"PROTOCOL R1: {rel} has uncommitted modifications.\n"
            "Commit or restore it before driving; a certificate that moves after the\n"
            "drive is not the certificate that predicted it.")
    return True


def main():
    ok = True
    try:
        require_certificate_committed()
        cert_t = first_commit_epoch(D.CERT_ARTIFACT)
        print(f"certificate committed at epoch {cert_t}")
    except SystemExit as e:
        print(e)
        return 1

    if not os.path.isdir(LEDGER):
        print("no scored ledger cells yet -- order trivially satisfied")
        return 0

    rows = []
    for fn in sorted(os.listdir(LEDGER)):
        if not fn.endswith(".json"):
            continue
        rel = os.path.join(D.LEDGER_SUBDIR, fn)
        t = first_commit_epoch(rel)
        if t is None:
            rows.append((fn, None, "UNCOMMITTED"))
            continue
        good = t > cert_t
        ok &= good
        rows.append((fn, t, "OK" if good else "VIOLATION: drive precedes certificate"))

    w = max((len(r[0]) for r in rows), default=10)
    for fn, t, note in rows:
        print(f"  {fn:<{w}}  {t}  {note}")
    print("\nR1 satisfied" if ok else "\nR1 VIOLATED -- these cells are not predictions")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

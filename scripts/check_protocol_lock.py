#!/usr/bin/env python3
"""Verify PROTOCOL.md's frozen section against PROTOCOL.lock.

The Town06 deployment test is only a test if its constants were fixed before the
results existed. This makes silent drift detectable: any edit to the frozen section
changes the hash, and every entry point that writes a Town06 result refuses to run
until the lock is deliberately regenerated through the amendment procedure.

    python3 scripts/check_protocol_lock.py            # verify, exit 1 on mismatch
    python3 scripts/check_protocol_lock.py --write    # (re)generate the lock

Import guard for use inside pipeline scripts:

    from check_protocol_lock import require_locked
    require_locked()
"""
import argparse
import hashlib
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTOCOL = os.path.join(REPO, "PROTOCOL.md")
LOCK = os.path.join(REPO, "PROTOCOL.lock")

# The frozen region: section 3 up to (not including) section 4.
START = re.compile(r"^## 3\. Frozen constants\s*$", re.M)
END = re.compile(r"^## 4\. ", re.M)


def frozen_text():
    src = open(PROTOCOL, encoding="utf-8").read()
    m0 = START.search(src)
    if not m0:
        raise SystemExit("PROTOCOL.md: section 3 header not found")
    m1 = END.search(src, m0.end())
    if not m1:
        raise SystemExit("PROTOCOL.md: section 4 header not found")
    # Normalise trailing whitespace so a stray space cannot break the lock.
    body = src[m0.start():m1.start()]
    return "\n".join(line.rstrip() for line in body.strip().splitlines()) + "\n"


def digest():
    return hashlib.sha256(frozen_text().encode("utf-8")).hexdigest()


def require_locked():
    """Raise unless PROTOCOL.md's frozen section matches the committed lock."""
    if not os.path.exists(LOCK):
        raise SystemExit("PROTOCOL.lock missing -- run check_protocol_lock.py --write")
    want = open(LOCK, encoding="utf-8").read().split()[0].strip()
    got = digest()
    if got != want:
        raise SystemExit(
            "PROTOCOL.md frozen section has changed.\n"
            f"  locked : {want}\n  current: {got}\n"
            "This is not a thing to fix by regenerating the lock. Follow the amendment\n"
            "procedure in PROTOCOL.md section 9, or restore the frozen section.")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="(re)generate PROTOCOL.lock")
    args = ap.parse_args()
    d = digest()
    if args.write:
        with open(LOCK, "w", encoding="utf-8") as f:
            f.write(d + "  PROTOCOL.md#frozen-constants\n")
        print(f"wrote PROTOCOL.lock\n  {d}")
        return 0
    require_locked()
    print(f"PROTOCOL.lock OK\n  {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

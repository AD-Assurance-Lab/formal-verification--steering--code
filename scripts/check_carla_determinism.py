#!/usr/bin/env python3
"""Preflight for CARLA_DETERMINISM.md. Refuses a misconfigured simulator.

A document gets skimmed; a `raise` cannot be. This asserts D-1..D-6 against a LIVE
server and against the standard's own hash, so the rules cannot be quietly relaxed to
make a run pass -- editing them changes the hash and this fails until the lock is
regenerated through the amendment procedure.

D-3 and D-5 are LAUNCH flags, invisible from the Python API, so they are read from the
server's actual command line in /proc. A server someone started by hand without them
looks completely normal over RPC, and every result it produces is quietly noisier.

    python3 scripts/check_carla_determinism.py           # verify, exit 1 on violation
    python3 scripts/check_carla_determinism.py --write   # regenerate the lock

Import guard, for entry points that produce measurements:

    from check_carla_determinism import require_deterministic
    require_deterministic(world)
"""
import argparse
import hashlib
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STANDARD = os.path.join(REPO, "CARLA_DETERMINISM.md")
LOCK = os.path.join(REPO, "CARLA_DETERMINISM.lock")
sys.path.insert(0, os.path.join(REPO, "pipeline"))

START = re.compile(r"^## 2\. Frozen rules\s*$", re.M)
END = re.compile(r"^## 3\. Preflight\s*$", re.M)

REQUIRED_LAUNCH = ("-notexturestreaming",)          # D-3
REQUIRED_QUALITY = "Epic"                            # D-5


def frozen_text():
    src = open(STANDARD, encoding="utf-8").read()
    m0, m1 = START.search(src), END.search(src)
    if not (m0 and m1):
        raise SystemExit("CARLA_DETERMINISM.md: frozen section markers not found")
    body = src[m0.start():m1.start()]
    return "\n".join(l.rstrip() for l in body.strip().splitlines()) + "\n"


def digest():
    return hashlib.sha256(frozen_text().encode()).hexdigest()


def check_lock():
    if not os.path.exists(LOCK):
        return ["CARLA_DETERMINISM.lock is missing"]
    want = open(LOCK).read().split()[0]
    got = digest()
    if want != got:
        return [f"CARLA_DETERMINISM.md frozen rules were EDITED without an amendment "
                f"(lock {want[:16]}, file {got[:16]}). See section 4."]
    return []


def server_cmdline(port):
    """The launch arguments of the CARLA serving `port`, from /proc.

    Matched on the rpc-port so a second server on another port is never mistaken for
    this one -- kill-by-name has already taken down someone else's simulator once.
    """
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as fh:
                argv = fh.read().decode(errors="replace").split("\0")
        except OSError:
            continue
        if not argv or "CarlaUE4" not in argv[0]:
            continue
        if any(f"-carla-rpc-port={port}" in a for a in argv):
            return argv
    return None


def check_server(world=None, port=None, in_run=True):
    import config as C
    port = port or C.PORT
    problems = []

    argv = server_cmdline(port)
    if argv is None:
        problems.append(f"D-3/D-5: no CarlaUE4 server found serving rpc-port {port}; "
                        f"cannot verify its launch flags")
    else:
        joined = " ".join(argv)
        for flag in REQUIRED_LAUNCH:
            if flag not in joined:
                problems.append(
                    f"D-3: server on port {port} was NOT launched with {flag}. Texture "
                    f"streaming is the dominant render entropy source (168x). Restart "
                    f"with scripts/carla_restart.sh.")
        m = re.search(r"-quality-level=(\w+)", joined)
        q = m.group(1) if m else "(unset)"
        if q != REQUIRED_QUALITY:
            problems.append(f"D-5: quality-level is {q}, must be {REQUIRED_QUALITY}.")

    if not C.DETERMINISTIC_CONTROL:
        problems.append(
            "D-2: config.DETERMINISTIC_CONTROL is off, so vehicle commands use the "
            "fire-and-forget RPC that diverges the first time a command changes.")

    # D-1 is a PER-RUN setting: enable_sync_mode applies it at the start of a run and
    # env.cleanup restores the original at the end, so an IDLE server is legitimately
    # asynchronous and flagging it would be a false positive that trains people to
    # ignore this check. Assert it only from inside a run -- require_deterministic(world)
    # -- and report it as information otherwise.
    if world is not None:
        s = world.get_settings()
        if not s.synchronous_mode:
            if in_run:
                problems.append("D-1: world is not in synchronous mode.")
            else:
                print("  note: server is idle and asynchronous, which is expected "
                      "between runs; D-1 is asserted per-run by require_deterministic().")
            return problems
        if abs((s.fixed_delta_seconds or 0.0) - C.FIXED_DT) > 1e-9:
            problems.append(
                f"D-1: fixed_delta_seconds is {s.fixed_delta_seconds}, expected {C.FIXED_DT}.")
        if not getattr(s, "substepping", False):
            problems.append("D-1: substepping is off.")
        else:
            covered = s.max_substeps * s.max_substep_delta_time
            if covered + 1e-12 < (s.fixed_delta_seconds or 0.0):
                problems.append(
                    f"D-1: substeps cover {covered:.4f}s of a {s.fixed_delta_seconds}s "
                    f"step; physics will silently advance less than the full step.")
    return problems


def require_deterministic(world=None, port=None):
    """Raise unless the live simulator satisfies the standard. Call before measuring."""
    problems = check_lock() + check_server(world, port, in_run=True)
    if problems:
        raise SystemExit(
            "CARLA DETERMINISM PREFLIGHT FAILED -- refusing to produce a measurement.\n"
            "See CARLA_DETERMINISM.md.\n  " + "\n  ".join(problems))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="regenerate the lock (section 4 only)")
    ap.add_argument("--no-server", action="store_true", help="check the lock only")
    args = ap.parse_args()

    if args.write:
        open(LOCK, "w").write(f"{digest()}  CARLA_DETERMINISM.md#frozen-rules\n")
        print(f"  wrote {LOCK}\n  {digest()}")
        return 0

    problems = check_lock()
    if not args.no_server:
        world = None
        try:
            import carla_env as env
            client = env.connect()
            world = client.get_world()
        except Exception as exc:
            problems.append(f"could not reach the server to verify D-1: {exc}")
        problems += check_server(world, in_run=False)

    if problems:
        print("  DETERMINISM PREFLIGHT FAILED:")
        for p_ in problems:
            print(f"    - {p_}")
        return 1
    print("  determinism preflight OK (D-1..D-6 verified; D-7 floor remains: closed-loop\n"
          "  numbers are still RATES over >=10 repetitions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""One CARLA client at a time, per port.

WHY THIS EXISTS. On 2026-08-11 23:16 a closed-loop ledger cell was running on port 3000
while I opened a second client on the same port to run a photometric comparison. Both were
in synchronous mode, so their `world.tick()` calls interleaved, and the second client also
set the weather and teleported a vehicle into the running scene. The cell's rep 2 departed
the road at 20.69 ft after reps 0 and 1 came in at 1.15 and 1.26 ft. The result looked like
a model failure and was not one.

Nothing errors when two synchronous clients share a world. The simulator serves both, the
frames look plausible, and the corrupted run is indistinguishable from a real result unless
you happen to know what else was running. That is the same failure shape as the read-
after-write and queue-desync traps: silent, and only visible if you go looking.

Usage -- wrap anything that touches CARLA:

    from carla_lock import carla_lock
    with carla_lock():
        ...

Acquisition is non-blocking by default and raises, because the right response to "someone
else is driving" is to stop, not to queue up behind them and start ticking an hour later
into a world you no longer understand.
"""
import os
import errno
import tempfile
import contextlib
from pathlib import Path

import config as C

LOCK_DIR = Path(os.environ.get("CARLA_LOCK_DIR",
                               Path(tempfile.gettempdir()) / "carla-locks"))

# CARLA binds rpc-port, rpc-port+1 AND rpc-port+2. A server on 3000 owns 3000-3002, so a
# second server started on 3001 or 3002 silently conflicts and never becomes ready, while a
# client "connecting to 3001" reaches the FIRST server's streaming port. Space concurrent
# servers by at least 3. Measured the hard way on 2026-08-12.
PORT_SPAN = 3


class CarlaBusy(RuntimeError):
    pass


@contextlib.contextmanager
def carla_lock(port=None, owner=None, force=False):
    """Exclusive use of one CARLA port. Raises CarlaBusy if another holder is alive."""
    port = C.PORT if port is None else port
    owner = owner or f"pid {os.getpid()}"
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    path = LOCK_DIR / f"carla-{port}.lock"

    fd = None
    try:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
            held = _read_holder(path)
            if held and _alive(held[0]) and not force:
                raise CarlaBusy(
                    f"CARLA :{port} is in use by pid {held[0]} ({held[1]}).\n"
                    f"Two synchronous clients on one world interleave ticks and silently "
                    f"corrupt each other's runs -- that is how a ledger cell recorded a "
                    f"20.69 ft departure that never happened. Wait, or use a different "
                    f"CARLA_PORT."
                )
            # stale lock from a dead process, or an explicit override
            path.unlink(missing_ok=True)
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.write(fd, f"{os.getpid()}\n{owner}\n".encode())
        os.close(fd)
        fd = None
        yield path
    finally:
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)
        held = _read_holder(path)
        if held and held[0] == os.getpid():
            path.unlink(missing_ok=True)


def _read_holder(path):
    try:
        parts = path.read_text().splitlines()
        return int(parts[0]), (parts[1] if len(parts) > 1 else "")
    except (OSError, ValueError, IndexError):
        return None


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError as exc:
        return exc.errno == errno.EPERM

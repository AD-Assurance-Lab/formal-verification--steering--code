"""Wait for the GPU rather than silently falling back to the CPU.

`torch.cuda.is_available()` returns False while CARLA is still initialising on the same
device, and it returns False QUIETLY. Every measurement script here was written as

    device = "cuda" if torch.cuda.is_available() else "cpu"

which reads like a portability convenience and is actually a silent-failure switch: the
run continues on the CPU, produces numbers, and nothing says so. Caught on Town06 when a
policy drive printed "CUDA unknown error ... setting the available devices to be zero"
and then drove the whole lap anyway.

It became likely rather than rare when R-SIM-1 moved to a restart before EVERY run: that
turned one startup race per cell into one per run.

    device = require_cuda()          # waits, then insists
    device = require_cuda(allow_cpu=True)   # for tools that genuinely do not need it
"""
import time

import torch


def require_cuda(tries=12, wait_s=10.0, allow_cpu=False, verbose=True):
    """Return "cuda" once the device is actually usable, or raise.

    Allocates a tensor rather than trusting is_available(): the flag can be True while
    the context still fails, which is the same class of lie in the other direction.
    """
    last = None
    for i in range(tries):
        try:
            if torch.cuda.is_available():
                torch.zeros(8, device="cuda") + 1.0     # prove it, do not assume it
                return "cuda"
            last = "torch.cuda.is_available() is False"
        except Exception as exc:                        # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
        if verbose:
            print(f"  GPU not ready ({last}); CARLA is probably still starting "
                  f"-- retry {i+1}/{tries} in {wait_s:.0f} s", flush=True)
        time.sleep(wait_s)
    if allow_cpu:
        print("  WARNING: falling back to CPU deliberately (allow_cpu=True)", flush=True)
        return "cpu"
    raise RuntimeError(
        f"GPU never became available after {tries} tries ({last}).\n"
        "  Refusing to fall back to the CPU silently: a measurement that quietly runs "
        "on a different device is a measurement of something else.")

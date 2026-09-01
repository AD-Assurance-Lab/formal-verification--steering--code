#!/usr/bin/env python3
"""Refuse to launch if the GPU is present but CUDA cannot initialise.

nvidia-smi can report a perfectly healthy card while CUDA context creation fails:
nvidia_uvm wedges after many rapid GPU-heavy process restarts, which is exactly what
R-SIM-1 does now that it restarts before EVERY run. Measured 2026-09-01 after a few
hundred restarts -- card healthy, torch.cuda.is_available() False.

Catching it at launch turns "discover it 40 minutes into a training run" into "refuse to
start". The fix needs root and cannot be automated:

    sudo modprobe -r nvidia_uvm && sudo modprobe nvidia_uvm
"""
import sys

try:
    import torch
    torch.zeros(8, device="cuda")
except Exception as exc:                                       # noqa: BLE001
    print(f"FATAL: the GPU is present but CUDA cannot initialise "
          f"({type(exc).__name__}: {exc}).", file=sys.stderr)
    print("  nvidia_uvm is probably wedged after repeated restarts. In a terminal:\n"
          "      sudo modprobe -r nvidia_uvm && sudo modprobe nvidia_uvm", file=sys.stderr)
    sys.exit(1)

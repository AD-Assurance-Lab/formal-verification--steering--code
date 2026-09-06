#!/usr/bin/env python3
"""Q8b: build the ONNX for one sub-problem and close the A-1 export gate.

    .venv-abcrown/bin/python scripts/q8b_build_onnx.py results/town06/beta/specs/<stem>.json

RUN WITH .venv-abcrown/bin/python, never the study venv.

Why here and not on the study side: torch.onnx.export needs the `onnx` package and the
fidelity replay needs `onnxruntime`; neither is in the study venv and neither may be added
to it, because pulling them risks moving numpy off 1.26.4 and every checkpoint and
published number in this repo is tied to that pin (docs/Q8_PREREGISTRATION.md A-1).

This imports THIS REPO's pipeline/student.py and pipeline/verifiable_disturbance.py, so
the architecture and the disturbance head are never written down a second time -- a
duplicated model definition is how the exported graph and the certified graph drift apart
while both look right.

The A-1 gate: the graph, built and executed HERE under torch 2.11 / numpy 2.x, must agree
with the study's own forward pass (torch 2.13 / numpy 1.26.4) to < 1e-5 over the recorded
inputs. That is a stronger check than an in-process one -- it covers the translation AND
the version gap, which is exactly what a verdict computed in this environment depends on.
Exits non-zero on failure; no Q8b verdict may be reported from a graph that fails it.
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))

from student import StudentNet            # noqa: E402  -- the study's own definition
from verifiable_disturbance import LinearDisturbance   # noqa: E402


def build(meta):
    ch = tuple(int(x) for x in meta["channels"].split(","))
    h, w = int(meta["in_h"]), int(meta["in_w"])
    net_s = StudentNet(h, w, channels=ch, fc=int(meta["fc"]))
    ckpt = REPO / "pipeline" / "checkpoints" / f"{meta['student']}.pth"
    net_s.load_state_dict(torch.load(ckpt, map_location="cpu", weights_only=True))
    net_s.eval()
    prob = np.load(REPO / meta["problem"])
    head = LinearDisturbance(prob["W"], prob["bias"], (1, 3, h, w))
    return torch.nn.Sequential(head, net_s).eval()


def main(meta_path):
    meta = json.loads(Path(meta_path).read_text())
    for k in ("problem", "reference", "export_check_tol", "onnx"):
        if k not in meta:
            sys.exit(f"{meta_path}: no '{k}' -- rerun q8b_export.py with --check")

    net = build(meta)
    onnx_path = REPO / meta["onnx"]
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(net, torch.zeros(1, 1), str(onnx_path),
                      input_names=["X_0"], output_names=["Y_0"],
                      opset_version=17, dynamo=False)

    ref = np.load(REPO / meta["reference"])
    ts, want = ref["inputs"], ref["outputs"].reshape(-1)

    import onnxruntime as ort
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    name = sess.get_inputs()[0].name
    # Batch-1, matching the head's .view(1, 3, h, w) -- see q8b_export.py.
    got = np.array([float(sess.run(None, {name: t.reshape(1, 1)})[0].reshape(-1)[0])
                    for t in ts], dtype=np.float32)

    diff = float(np.abs(want - got).max())
    tol = float(meta["export_check_tol"])
    ok = diff < tol
    meta.update(export_max_abs_diff=diff, export_ok=bool(ok),
                export_checked_by="q8b_build_onnx.py (.venv-abcrown)",
                onnx_grid_max=float(got.max()), onnx_grid_min=float(got.min()))
    Path(meta_path).write_text(json.dumps(meta, indent=2))

    print(f"{onnx_path.name}")
    print(f"  inputs compared     {len(ts)}")
    print(f"  max |study - onnx|  {diff:.3e}   (tol {tol:g})")
    print(f"  study grid max/min  {want.max():+.6f} / {want.min():+.6f}")
    print(f"  onnx  grid max/min  {got.max():+.6f} / {got.min():+.6f}")
    if "crown_ub" in meta:
        print(f"  plain CROWN bound   [{meta['crown_lb']:+.6f}, {meta['crown_ub']:+.6f}]")
    print(f"  {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    all_ok = True
    for p in sys.argv[1:]:
        all_ok &= main(p)
    if not all_ok:
        sys.exit("REFUSING: an exported graph is not the study's network. "
                 "No Q8b verdict may be reported from it (amendment A-1).")

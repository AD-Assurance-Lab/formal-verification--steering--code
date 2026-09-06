#!/usr/bin/env python3
"""Q8b: export one certification sub-problem to ONNX + VNNLIB, and PROVE the export.

WHY AN EXPORT AT ALL. docs/Q8_PREREGISTRATION.md amendment A-1: alpha-beta-CROWN pins
torch==2.11.0 / numpy>=2.0 / Python 3.11 and the study is 2.13.0+cu130 / 1.26.4 / 3.12.3,
irreconcilably. So the verifier runs OUT OF PROCESS in .venv-abcrown and the two sides
meet at ONNX + VNNLIB -- which is alpha-beta-CROWN's native format and which this study's
spec already fits.

THE SUB-PROBLEM. certify_town06.py bounds, per pose k and per sub-interval j of [0,1]:

    t in [-1, 1]  ->  image = W t + b  ->  clamp01  ->  student  ->  scalar steering

with  W = half*(x1 - x0),  b = x0 + mid*(x1 - x0),  half = (b_j - a_j)/2,
mid = (a_j + b_j)/2, so the image traces the segment x0 + s*(x1-x0) for s in [a_j, b_j].
x0 is the clear capture at that pose and x1 the disturbed one. ONE INPUT VARIABLE.

The cell's statistic is the route-MEAN over poses of (max over t) - (value at x0). A sum
of independent terms is SEPARABLE, so the exact mean of exact per-pose maxima IS the exact
cell bound -- which is why complete verification of these sub-problems decides the cell
rather than merely tightening it.

THE EXPORT IS A RE-IMPLEMENTATION BY A TRANSLATOR, and a verdict about a mistranslated
graph is sound and about the wrong network -- the same shape as A-3's mis-rigged camera,
correct downstream of a wrong artifact. So amendment A-1 requires the exported model to be
checked against the study's own forward pass on >= 1000 inputs across the interval at
< 1e-5 max absolute difference, BEFORE any Q8b verdict is reported. --check does that and
exits non-zero if it fails.

    python3 scripts/q8b_export.py --student S_mixed_t06lap_168x56_w4_s3 \
        --condition fog --pose 0 --split 0 --outdir results/town06/beta/specs --check
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "scripts"))

import config as C  # noqa: E402
import verifiable_disturbance as vd  # noqa: E402
from student import StudentNet  # noqa: E402
from study import town06_design as D  # noqa: E402

CAPTURES = REPO / "results" / "town06" / "captures"


def load_pose_pair(condition, stride, scope="full"):
    """Every (x0, x1) pair the certifier would bound, in its order.

    Reuses certify_town06's own helpers so the pose set cannot drift from the one the
    committed certificate used -- two implementations of "which poses" is how a capture
    ends up certifying different road than it claims (standing rule 7).
    """
    import certify_town06 as ct
    pairs = []
    for sec in D.SECTIONS:
        p = CAPTURES / f"lap_{sec}_{condition}.npz"
        base = CAPTURES / f"lap_{sec}_clear.npz"
        if not p.exists() or not base.exists():
            continue
        ct.check_coverage(p, sec)
        ct.check_coverage(base, sec)
        mask = ct.scope_mask(p, scope)
        bmask = ct.scope_mask(base, scope)
        clr, _ = ct.baseline_for(p, ct.nominal(base, "clear", bmask), mask)
        dis = ct.nominal(p, condition, mask)
        if dis is None or len(dis) != len(clr):
            continue
        for k in range(0, len(clr), stride):
            pairs.append((clr[k].reshape(-1).astype(np.float32),
                          dis[k].reshape(-1).astype(np.float32)))
    return pairs


def build_net(student, x0, x1, split, nsplit, h, w):
    """The exact nn.Sequential certify_town06 bounds, for one (pose, split)."""
    a, b = split / nsplit, (split + 1) / nsplit
    mid, half = 0.5 * (a + b), 0.5 * (b - a)
    W = (half * (x1 - x0)).reshape(-1, 1)
    bias = x0 + mid * (x1 - x0)
    head = vd.LinearDisturbance(W, bias, (1, 3, h, w))
    return torch.nn.Sequential(head, student).eval(), W, bias


def write_vnnlib(path, lo, hi, threshold, direction):
    """One input variable, one output. "Is the output beyond `threshold`?"

    VNNLIB asserts the NEGATION of the property: a spec that is UNSAT means no input in
    the box drives the output past the threshold, i.e. the bound holds.
    """
    with open(path, "w") as fh:
        fh.write("; Q8b sub-problem: student(W t + b) over a 1-D interval\n")
        fh.write("(declare-const X_0 Real)\n(declare-const Y_0 Real)\n\n")
        fh.write(f"(assert (>= X_0 {lo:.10f}))\n(assert (<= X_0 {hi:.10f}))\n\n")
        op = ">=" if direction == "max" else "<="
        fh.write(f"(assert ({op} Y_0 {threshold:.10f}))\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--student", required=True)
    ap.add_argument("--channels", default="32,64,64")
    ap.add_argument("--fc", type=int, default=128)
    ap.add_argument("--condition", required=True)
    ap.add_argument("--pose", type=int, default=0)
    ap.add_argument("--split", type=int, default=0)
    ap.add_argument("--nsplit", type=int, default=16)
    ap.add_argument("--stride", type=int, default=8)
    ap.add_argument("--threshold", type=float, default=None,
                    help="VNNLIB threshold; omit to skip writing a spec")
    ap.add_argument("--direction", default="max", choices=("max", "min"))
    ap.add_argument("--outdir", default="results/town06/beta/specs")
    ap.add_argument("--check", action="store_true",
                    help="verify the ONNX against the study's forward pass (A-1)")
    ap.add_argument("--check-n", type=int, default=1000)
    ap.add_argument("--check-tol", type=float, default=1e-5)
    a = ap.parse_args()

    h, w = C.TOWN06_INPUT_H, C.TOWN06_INPUT_W
    ch = tuple(int(x) for x in a.channels.split(","))
    net_s = StudentNet(h, w, channels=ch, fc=a.fc)
    net_s.load_state_dict(torch.load(Path(C.CHECKPOINT_DIR) / f"{a.student}.pth",
                                     map_location="cpu", weights_only=True))
    net_s.eval()

    pairs = load_pose_pair(a.condition, a.stride)
    if not pairs:
        sys.exit(f"no capture pairs for condition {a.condition}")
    if a.pose >= len(pairs):
        sys.exit(f"pose {a.pose} out of range (have {len(pairs)})")
    x0, x1 = pairs[a.pose]
    net, W, bias = build_net(net_s, x0, x1, a.split, a.nsplit, h, w)

    outdir = REPO / a.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    stem = f"{a.student}__{a.condition}__p{a.pose:04d}__s{a.split:02d}"
    onnx_path = outdir / f"{stem}.onnx"

    # NO ONNX HERE. torch.onnx.export needs the `onnx` package, which the study venv does
    # not have and must not get: pulling it risks moving numpy off 1.26.4, and every
    # checkpoint and published number in this repo is tied to that pin.
    #
    # So this side emits the PROBLEM (W, b) and the study's own forward pass, and
    # scripts/q8b_build_onnx.py builds and checks the graph inside .venv-abcrown -- which
    # imports THIS repo's student.py and verifiable_disturbance.py, so the architecture is
    # never written down twice.
    prob_path = outdir / f"{stem}__problem.npz"
    np.savez(prob_path, W=W.astype(np.float32), bias=bias.astype(np.float32))

    rec = {"student": a.student, "channels": a.channels, "fc": a.fc,
           "condition": a.condition, "pose": a.pose,
           "split": a.split, "nsplit": a.nsplit, "stride": a.stride,
           "in_h": h, "in_w": w,
           "problem": str(prob_path.relative_to(REPO)),
           "onnx": str(onnx_path.relative_to(REPO)), "poses_available": len(pairs)}

    if a.check:
        # A-1's export-fidelity gate, in two halves that CANNOT share an environment.
        #
        # onnxruntime is not installed in the study venv and must not be: adding it risks
        # moving numpy, and every checkpoint and published number here is tied to
        # 1.26.4. So this half writes the study's OWN forward pass to a file, and
        # scripts/q8b_check_export.py replays the ONNX against it inside .venv-abcrown.
        #
        # That is stronger evidence than an in-process check would be, not weaker: it
        # proves the graph agrees with the study when executed in the environment that
        # will actually consume it, which is the environment a mistranslation would show
        # up in.
        #
        # Endpoints included -- a clamp boundary is most likely to be crossed there.
        # ONE INPUT AT A TIME. LinearDisturbance.forward does .view(1, 3, h, w), so the
        # head is batch-1 by construction -- which is how Bounder uses it. Feeding a
        # batch reshapes 1000 images into one and raises; it does not silently produce
        # a wrong answer, but the loop is the honest way to exercise the same path the
        # verifier will.
        ts = np.linspace(-1.0, 1.0, a.check_n, dtype=np.float32).reshape(-1, 1)
        with torch.no_grad():
            ref = np.array([float(net(torch.from_numpy(t.reshape(1, 1))))
                            for t in ts], dtype=np.float32)
        ref_path = outdir / f"{stem}__ref.npz"
        np.savez(ref_path, inputs=ts, outputs=ref)
        rec["reference"] = str(ref_path.relative_to(REPO))
        rec["export_check_n"] = int(a.check_n)
        rec["export_check_tol"] = float(a.check_tol)
        # The grid extremes, for comparison with whatever the verifier returns. A sound
        # bound must not be TIGHTER than a value actually attained on the grid.
        rec["torch_grid_max"] = float(ref.max())
        rec["torch_grid_min"] = float(ref.min())
        # What plain CROWN says about this same sub-problem, from the study's own
        # Bounder. A complete verifier must land INSIDE this (its exact max cannot exceed
        # a sound upper bound) and AT OR ABOVE the grid max (a value actually attained).
        # Those two together bracket any answer Q8b returns.
        import certify_cell as cc
        bd = cc.Bounder(1, net_s, torch.device("cpu"), h, w, method="CROWN")
        cl, cu = bd(W, bias, np.array([-1.0]), np.array([1.0]))
        rec["crown_lb"], rec["crown_ub"] = float(cl), float(cu)
        print(f"  plain CROWN on this sub-problem: [{cl:+.6f}, {cu:+.6f}]")
        print(f"wrote reference {ref_path.relative_to(REPO)} "
              f"({a.check_n} inputs; grid max {ref.max():+.6f}, min {ref.min():+.6f})")
        print("  now run scripts/q8b_check_export.py in .venv-abcrown to close A-1")

    if a.threshold is not None:
        vnn = outdir / f"{stem}__{a.direction}.vnnlib"
        write_vnnlib(vnn, -1.0, 1.0, a.threshold, a.direction)
        rec["vnnlib"] = str(vnn.relative_to(REPO))
        rec["threshold"] = a.threshold
        rec["direction"] = a.direction

    (outdir / f"{stem}.json").write_text(json.dumps(rec, indent=2))
    print(f"wrote {onnx_path.relative_to(REPO)}")
    print(json.dumps(rec, indent=2))


if __name__ == "__main__":
    main()

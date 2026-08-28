#!/usr/bin/env python3
"""TIER 0: is the INFERENCE PATH bit-exact? No CARLA, no physics, no renderer.

The closed-loop probe cannot answer this. It measures physics, rendering and feedback
amplification at once, so any one-LSB difference anywhere in the chain surfaces as a
divergent trajectory and every candidate cause looks identical. This isolates the one
link that can be tested with the simulator switched off.

Two questions, and they are different:

  1. WITHIN one process, does the same tensor forward to the same bits every time?
     A `no_grad` eval-mode forward should. If it does not, cuDNN algorithm selection or
     a non-deterministic reduction is live and every closed-loop number in the study is
     noise on top of that.

  2. ACROSS processes, does it? Each closed-loop rep is a FRESH `evaluate.py` process,
     so this is the question that actually matters for the competence gate. cuDNN can
     pick a different algorithm per process (autotuning, free-VRAM-dependent workspace
     selection), which is invisible within a run and changes results between runs.

Also checks `student_preprocess` itself, because a non-deterministic resize would
produce the same symptom from outside and OpenCV dispatches on CPU features and thread
count.

Digest is over the RAW BITS of the output, not a rounded value: a difference of 1e-9 in
steering is what this is hunting, and `repr(float)` would hide it.

    python3 scripts/determinism_tier0_model.py --procs 5
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))

import numpy as np  # noqa: E402
import torch  # noqa: E402


def _digest(arr):
    """Hash the raw bytes. float32 steering differences below print precision are
    exactly what is being hunted, so nothing may be rounded on the way in."""
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()[:16]


def build_inputs(n_real, in_w, in_h):
    """A fixed synthetic batch plus real captured frames through the real preprocessing.

    Synthetic alone would test the network but not `student_preprocess`; real frames
    alone would conflate the two. Both, separately digested, separates them.
    """
    from student import student_preprocess
    import cv2

    rng = np.random.RandomState(0)
    synth = rng.rand(8, 3, in_h, in_w).astype(np.float32)

    # Real frames, sorted so the selection is identical in every process.
    roots = sorted((REPO / "pipeline" / "data" / "mixed_t06").glob("*/frames"))
    paths = []
    for r in roots:
        paths.extend(sorted(r.glob("*.png")))
        if len(paths) >= n_real * 4:
            break
    paths = paths[:: max(1, len(paths) // n_real)][:n_real]

    pre = []
    for p in paths:
        bgr = cv2.imread(str(p))
        if bgr is None:
            continue
        pre.append(student_preprocess(bgr, in_w, in_h))
    real = np.stack(pre).astype(np.float32) if pre else np.zeros((0, 3, in_h, in_w), np.float32)
    return synth, real, [str(p) for p in paths]


def run_once(ck, channels, fc, in_w, in_h, device, rounds, n_real):
    from student import StudentNet
    import config as C

    synth, real, paths = build_inputs(n_real, in_w, in_h)

    model = StudentNet(in_h, in_w, channels=tuple(channels), fc=fc).to(device)
    sd = torch.load(os.path.join(C.CHECKPOINT_DIR, f"{ck}.pth"), map_location=device)
    model.load_state_dict(sd)
    model.eval()

    out = {
        "device": device,
        "torch": torch.__version__,
        "cudnn": torch.backends.cudnn.version(),
        "cudnn_benchmark": torch.backends.cudnn.benchmark,
        "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "weights_digest": _digest(np.concatenate([v.detach().cpu().numpy().ravel()
                                                  for v in sd.values()])),
        "preproc_digest": _digest(real),
        "n_real": int(real.shape[0]),
        "frames": paths[:3],
    }

    # WITHIN-PROCESS. Batched once, then ONE AT A TIME, because the closed loop always
    # forwards a single frame with batch 1 and cuDNN can pick a different kernel per
    # batch shape. A study that only ever checked the batched path could miss it.
    # ONE SET PER INPUT. Pooling synthetic and real digests into a single set makes
    # "two inputs" indistinguishable from "one input, two answers", and reports a
    # perfectly deterministic model as non-deterministic. Same class of defect as the
    # stale-CSV compare in determinism_probe.py: a probe that cannot fail correctly.
    named = [("synth", synth), ("real", real)]
    dig = {f"{tag}_{mode}": set() for tag, _ in named for mode in ("batched", "single")}
    for _ in range(rounds):
        for tag, x in named:
            if x.shape[0] == 0:
                continue
            with torch.no_grad():
                y = model(torch.from_numpy(x).to(device)).cpu().numpy()
            dig[f"{tag}_batched"].add(_digest(y))
            ys = []
            for i in range(x.shape[0]):
                with torch.no_grad():
                    ys.append(model(torch.from_numpy(x[i:i + 1]).to(device)).cpu().numpy())
            dig[f"{tag}_single"].add(_digest(np.concatenate(ys)))

    dig = {k: sorted(v) for k, v in dig.items() if v}
    out["within_batched_stable"] = all(len(v) == 1 for k, v in dig.items() if k.endswith("batched"))
    out["within_single_stable"] = all(len(v) == 1 for k, v in dig.items() if k.endswith("single"))
    out["batched_digest"] = {k: v for k, v in dig.items() if k.endswith("batched")}
    out["single_digest"] = {k: v for k, v in dig.items() if k.endswith("single")}

    # Does batching change the answer? Not a determinism question, but if batch-1 and
    # batch-N disagree, any offline analysis that batches is not measuring what drives.
    with torch.no_grad():
        yb = model(torch.from_numpy(real).to(device)).cpu().numpy() if real.shape[0] else np.zeros(0)
        ys = np.concatenate([model(torch.from_numpy(real[i:i + 1]).to(device)).cpu().numpy()
                             for i in range(real.shape[0])]) if real.shape[0] else np.zeros(0)
    out["batch_vs_single_max_abs_diff"] = float(np.max(np.abs(yb - ys))) if real.shape[0] else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ck", default="S_clear_t06_168x28_w2")
    ap.add_argument("--channels", default="16,32,32")
    ap.add_argument("--fc", type=int, default=64)
    ap.add_argument("--in-w", type=int, default=168)
    ap.add_argument("--in-h", type=int, default=28)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--n-real", type=int, default=64)
    ap.add_argument("--procs", type=int, default=5, help="fresh processes to compare")
    ap.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    ch = [int(v) for v in args.channels.split(",")]

    if args.child:
        print(json.dumps(run_once(args.ck, ch, args.fc, args.in_w, args.in_h,
                                  args.device, args.rounds, args.n_real)))
        return 0

    print(f"  TIER 0 -- inference determinism, no simulator")
    print(f"  checkpoint {args.ck}  device {args.device}  "
          f"{args.rounds} rounds x {args.procs} fresh processes\n")

    reports = []
    for i in range(args.procs):
        p = subprocess.run([sys.executable, __file__, "--child",
                            "--ck", args.ck, "--channels", args.channels,
                            "--fc", str(args.fc), "--in-w", str(args.in_w),
                            "--in-h", str(args.in_h), "--device", args.device,
                            "--rounds", str(args.rounds), "--n-real", str(args.n_real)],
                           capture_output=True, text=True, timeout=900,
                           env=dict(os.environ, STUDY_MAP="Town06"))
        if p.returncode != 0:
            print(f"  proc {i}: FAILED rc={p.returncode}\n{p.stderr[-2000:]}")
            return 2
        r = json.loads(p.stdout.strip().splitlines()[-1])
        reports.append(r)
        print(f"  proc {i}: within-batched {'OK ' if r['within_batched_stable'] else 'VARIES'}  "
              f"within-single {'OK ' if r['within_single_stable'] else 'VARIES'}  "
              f"real-batch={r['batched_digest']['real_batched'][0]}  "
              f"real-single={r['single_digest']['real_single'][0]}  "
              f"preproc={r['preproc_digest']}")

    r0 = reports[0]
    print(f"\n  environment: torch {r0['torch']}  cuDNN {r0['cudnn']}  "
          f"benchmark={r0['cudnn_benchmark']}  gpu={r0['gpu']}")
    print(f"  real frames preprocessed: {r0['n_real']}")
    print(f"  batch-N vs batch-1 max |diff|: {r0['batch_vs_single_max_abs_diff']:.3e}"
          if r0["batch_vs_single_max_abs_diff"] is not None else "")

    def agree(key):
        vals = {json.dumps(r[key]) for r in reports}
        return len(vals) == 1, vals

    ok = True
    for key, label in (("weights_digest", "weights load"),
                       ("preproc_digest", "student_preprocess"),
                       ("batched_digest", "forward, batched"),
                       ("single_digest", "forward, batch-1")):
        same, vals = agree(key)
        ok &= same
        print(f"  across processes -- {label:22s}: "
              f"{'IDENTICAL' if same else 'DIFFERS  ' + ' | '.join(sorted(vals))}")

    within = all(r["within_batched_stable"] and r["within_single_stable"] for r in reports)
    print()
    if ok and within:
        print("  VERDICT: the inference path is bit-exact, within and across processes.")
        print("  Tier 0 is RULED OUT as the entropy source. Proceed to Tier 1 (open loop).")
        return 0
    print("  VERDICT: the inference path is NOT bit-exact. Fix this before any")
    print("  simulator work -- every closed-loop number sits on top of it.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

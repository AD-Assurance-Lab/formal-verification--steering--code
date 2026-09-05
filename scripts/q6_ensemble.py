#!/usr/bin/env python3
"""Q6c -- does combining seeds beat the median seed?

Two ways of combining the `both` arm's students, on the SAME fog p99 endpoint every other
Q6 arm uses:

  output    average the predicted steering of k students
  weights   average the k parameter vectors, then predict once

They are not one option, and docs/Q6_PREREGISTRATION.md predicts they behave oppositely:
the output ensemble should reduce the tail, the weight average should fail badly, because
independently initialised networks are not linearly mode-connected without permutation
alignment and nothing here aligns them.

THE CAVEAT IS PART OF THE RESULT. An output ensemble of k students is k TIMES THE ReLU
COUNT TO CERTIFY, and this study's thesis is that bound width is what constrains the
architecture -- E4-F2 measured depth alone costing 2.3-3.7x. So a win here is a result
about the pipeline's noise floor, NOT a proposed shipping architecture, unless the bound
on the combined network is separately measured. That measurement is out of Q6's scope.

No CARLA. Reads cached teacher targets, exactly as kd_error_by_condition.py does.

    python3 scripts/q6_ensemble.py --arm both --seeds 0-7
"""
import argparse
import itertools
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np
import torch
import cv2

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))

from gpu import require_cuda  # noqa: E402
import config as C  # noqa: E402
from distill import aggregated_manifests  # noqa: E402
from dataset import load_manifests  # noqa: E402
from student import StudentNet, student_preprocess  # noqa: E402

TEACHER = "teacher_mixed_t06lap_dagger_r03"
BASE = "mixed_t06lap"
DAGGER = ["dagger_mixed_t06lap", "dagger_student_S_mixed_t06_t06lap"]
CH, FC = (32, 64, 64), 128
CONDS = ["clear", "fog", "night", "low_sun"]
CAP = 3000


def load_frames(dev):
    """Per condition: the preprocessed frames and the teacher's targets for them."""
    _, rows = load_manifests(aggregated_manifests(base=BASE, dagger_dirs=DAGGER))
    z = np.load(Path(C.DATASET_DIR) / f"teacher_targets_{TEACHER}.npz", allow_pickle=True)
    tgt = {str(p): float(s) for p, s in zip(z["paths"], z["steer"])}
    w, h = C.TOWN06_INPUT_W, C.TOWN06_INPUT_H
    out = {}
    for cond in CONDS:
        sub = [r for r in rows if r.get("weather") == cond and r["image"] in tgt]
        if not sub:
            continue
        if len(sub) > CAP:
            sub = [sub[i] for i in np.linspace(0, len(sub) - 1, CAP).astype(int)]
        xs, ts = [], []
        for r in sub:
            im = cv2.imread(r["image"])
            if im is None:
                continue
            xs.append(student_preprocess(im, w, h))
            ts.append(tgt[r["image"]])
        out[cond] = (torch.from_numpy(np.stack(xs)), np.array(ts, np.float32))
        print(f"  {cond:8s} {len(ts):,} frames", flush=True)
    return out


def net_for(ck, dev):
    n = StudentNet(C.TOWN06_INPUT_H, C.TOWN06_INPUT_W, channels=CH, fc=FC).to(dev)
    n.load_state_dict(torch.load(Path(C.CHECKPOINT_DIR) / f"{ck}.pth",
                                 map_location=dev, weights_only=True))
    return n.eval()


def predict(net, x, dev):
    out = []
    with torch.no_grad():
        for i in range(0, len(x), 256):
            out.append(net(x[i:i + 256].to(dev)).cpu().numpy().reshape(-1))
    return np.concatenate(out)


def p99(pred, t):
    return float(np.percentile(np.abs(pred - t), 99))


def weight_average(cks, dev):
    sds = [torch.load(Path(C.CHECKPOINT_DIR) / f"{c}.pth", map_location=dev,
                      weights_only=True) for c in cks]
    avg = {k: sum(sd[k].float() for sd in sds) / len(sds) for k in sds[0]}
    n = StudentNet(C.TOWN06_INPUT_H, C.TOWN06_INPUT_W, channels=CH, fc=FC).to(dev)
    n.load_state_dict(avg)
    return n.eval()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="both")
    ap.add_argument("--seeds", default="0-7")
    ap.add_argument("--out", default="results/town06/variance/q6c_ensemble.json")
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.seeds.split("-"))
    seeds = list(range(lo, hi + 1))
    dev = require_cuda(tries=1, wait_s=0)

    cks = [f"S_q6_{a.arm}_s{s}" for s in seeds]
    missing = [c for c in cks if not (Path(C.CHECKPOINT_DIR) / f"{c}.pth").exists()]
    if missing:
        sys.exit(f"missing checkpoints: {', '.join(missing)}")

    print("loading frames")
    data = load_frames(dev)
    print("\nsingle-seed predictions")
    nets = {c: net_for(c, dev) for c in cks}
    preds = {cond: {c: predict(nets[c], x, dev) for c in cks}
             for cond, (x, _) in data.items()}

    rec = {"arm": a.arm, "seeds": seeds, "singles": {}, "output": {}, "weights": {}}
    for cond, (_, t) in data.items():
        singles = [p99(preds[cond][c], t) for c in cks]
        rec["singles"][cond] = {"per_seed": singles, "median": st.median(singles),
                                "best": min(singles), "worst": max(singles)}
        print(f"  {cond:8s} p99 median {st.median(singles):.4f}  "
              f"best {min(singles):.4f}  worst {max(singles):.4f}")

    # Output ensemble: every DISJOINT subset at each k, so no student is counted twice
    # inside one estimate and the k values are comparable to each other.
    print("\noutput ensembles (disjoint subsets)")
    for k in (2, 4, 8):
        if k > len(cks):
            continue
        groups = [cks[i:i + k] for i in range(0, len(cks) - k + 1, k)]
        for cond, (_, t) in data.items():
            vals = [p99(np.mean([preds[cond][c] for c in g], axis=0), t) for g in groups]
            rec["output"].setdefault(cond, {})[str(k)] = {
                "per_group": vals, "median": st.median(vals), "groups": len(groups)}
        f = rec["output"]["fog"][str(k)]
        print(f"  k={k}  fog p99 median {f['median']:.4f}  over {f['groups']} group(s)")

    print("\nweight averages (disjoint subsets)")
    for k in (2, 4, 8):
        if k > len(cks):
            continue
        groups = [cks[i:i + k] for i in range(0, len(cks) - k + 1, k)]
        for cond, (x, t) in data.items():
            vals = []
            for g in groups:
                vals.append(p99(predict(weight_average(g, dev), x, dev), t))
            rec["weights"].setdefault(cond, {})[str(k)] = {
                "per_group": vals, "median": st.median(vals), "groups": len(groups)}
        f = rec["weights"]["fog"][str(k)]
        print(f"  k={k}  fog p99 median {f['median']:.4f}  over {f['groups']} group(s)")

    rec["caveat"] = ("An output ensemble of k students is k times the ReLU count to "
                     "certify. This is a result about the pipeline's noise floor, not a "
                     "proposed shipping architecture, unless the bound on the combined "
                     "network is separately measured.")
    p = REPO / a.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, indent=2))
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()

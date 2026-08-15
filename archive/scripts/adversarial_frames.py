#!/usr/bin/env python3
"""Is the disturbance model wrong, or did verification just look at the wrong frames?

Zach's challenge: if the disturbance model does not predict closed-loop performance, in
what sense is it correct? Fair. "Reproduces CARLA's images" (shadows: ROI R^2 0.996) is
necessary but not sufficient, and the fix to the aggregation rule only converts bad
CERTIFIED verdicts into UNKNOWN -- which stops verification being wrong without making it
predict anything.

This separates the two possibilities directly. We know empirically which frames matter:
for a pose-matched (clear, condition) pair, forward-evaluate the student on each and keep
the frames where the steering ALREADY deviates by more than the corridor. Those frames are
where closed loop goes wrong. Then run the SAME verification, with the SAME disturbance
model, on exactly those frames instead of an even sample.

    verification FALSIFIES them  -> the model is fine; the 12-frame even sample simply
                                    never contained them. Coverage problem.
    verification CERTIFIES them  -> the model genuinely fails to represent whatever breaks
                                    the policy. Zach is right and the model needs work.

No CARLA required.
"""
import argparse, sys
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402
import verifiable_disturbance as vd  # noqa: E402
from student import StudentNet  # noqa: E402
from scripts.certify_cell import (paired_frames, fog_map_illum, night_map, shadow_map,
                                  Bounder, sweep, clear_steer)  # noqa: E402
import json  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--student", default="S_clear_84x28")
    ap.add_argument("--condition", default="shadows", choices=["fog", "night", "shadows"])
    ap.add_argument("--channels", default="8,16,16")
    ap.add_argument("--fc", type=int, default=32)
    ap.add_argument("--pool", type=int, default=120, help="frames to screen")
    ap.add_argument("--take", type=int, default=6, help="worst frames to verify")
    ap.add_argument("--budget", type=int, default=96)
    a = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = StudentNet(28, 84, channels=tuple(int(v) for v in a.channels.split(",")), fc=a.fc).to(dev)
    m.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{a.student}.pth", map_location=dev)); m.eval()
    tol = C.CLOSED_LOOP_TOLERANCE

    def steer(img):
        xf = img.astype(np.float32) / 255.0
        with torch.no_grad():
            return float(m(torch.from_numpy(vd._project(xf, 84, 28).reshape(1, 3, 28, 84)
                                            .astype(np.float32)).to(dev)).item())

    pairs = paired_frames(a.pool, a.condition)
    dev_list = [(abs(steer(o) - steer(c)), i) for i, (c, o, _) in enumerate(pairs)]
    dev_list.sort(reverse=True)
    worst = dev_list[:a.take]
    print(f"{a.condition} / {a.student}: screened {len(pairs)} pose-matched frames, "
          f"tolerance {tol:.4f}")
    print(f"  frames exceeding tolerance empirically: "
          f"{sum(1 for d,_ in dev_list if d > tol)}/{len(dev_list)}")
    print(f"  verifying the {a.take} WORST (empirical deviation shown)\n")

    fog_A, fog_k = (0.445, 0.416, 0.412), (0.637, 1.255)
    rows = []
    for rank, (d_emp, idx) in enumerate(worst):
        cimg, oimg, _ = pairs[idx]
        xf = cimg.astype(np.float32) / 255.0
        if a.condition == "fog":
            build, lo, hi = fog_map_illum(xf, 84, 28, fog_A, fog_k)
        elif a.condition == "night":
            build, lo, hi = night_map(xf, 84, 28)
        else:
            sf = oimg.astype(np.float32) / 255.0
            mask = np.clip(1.0 - np.divide(sf, xf, out=np.ones_like(sf), where=xf > 0.04), 0, 1)
            build, lo, hi = shadow_map(xf, 84, 28, mask)
        cs = clear_steer(m, xf, dev, 84, 28)
        corridor = (cs - tol, cs + tol)
        b = Bounder(build(lo, hi)[0].shape[1], m, dev, 28, 84)
        frac, n, _ = sweep(build, lo, hi, b, corridor, a.budget)
        rows.append(frac)
        print(f"  frame {rank}: empirical dev {d_emp:.4f} ({d_emp/tol:.0f}x tol) -> "
              f"cert {frac['CERTIFIED']:5.1%}  fals {frac['FALSIFIED']:5.1%}  "
              f"unk {frac['UNKNOWN']:5.1%}")

    anyf = sum(1 for f in rows if f["FALSIFIED"] > 0)
    print(f"\n  frames with a falsified region: {anyf}/{len(rows)}")
    print("  -> COVERAGE problem (model fine)" if anyf > len(rows)//2
          else "  -> the model does NOT capture what breaks the policy")
    json.dump({"condition": a.condition, "student": a.student,
               "n_falsified": anyf, "n": len(rows), "per_frame": rows},
              open(REPO/"results"/"diagnostic"/f"adversarial_{a.condition}_{a.student}.json","w"),
              indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Assemble the low-sun azimuth sweep and name the azimuth that matches the target."""
import glob
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(REPO, "results/town06/low_sun_calibration")
TARGET = 0.410      # T06-F20's Town06 target (Town04 measured 0.463)


def main():
    files = sorted(glob.glob(os.path.join(D, "*.json")))
    if not files:
        print("  no calibration runs yet")
        return 1
    runs = [json.load(open(f)) for f in files]
    ref = next((r for r in runs if r["condition"] == "clear"), None)
    if ref is None:
        print("  no clear reference lap; ratios cannot be computed")
        return 1
    print(f"\n  clear reference: mean {ref['mean']:.4f} (n={ref['samples']})")
    print(f"  target low sun/clear = {TARGET:.3f}  (T06-F20; Town04 measured 0.463)\n")
    print("  %8s %9s %9s %10s %12s %9s" %
          ("azimuth", "mean", "ratio", "blown", "sun-in-FOV", "|d-target|"))
    rows = []
    for r in sorted((x for x in runs if x["condition"] != "clear"),
                    key=lambda x: x["sun_azimuth"]):
        ratio = r["mean"] / ref["mean"]
        d = abs(ratio - TARGET)
        rows.append((d, r["sun_azimuth"], ratio))
        print("  %8.0f %9.4f %9.3f %10.4f %11.1f%% %9.3f" %
              (r["sun_azimuth"], r["mean"], ratio, r["blown_frac"],
               100 * r["sun_in_fov_frac"], d))
    if rows:
        rows.sort()
        print(f"\n  closest to target: azimuth {rows[0][1]:.0f} at ratio {rows[0][2]:.3f}")
        print("  NOT applied. Declaring a condition parameter is Zach's call, and it makes")
        print("  the existing Town06 training data unusable (A-2/D-11).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

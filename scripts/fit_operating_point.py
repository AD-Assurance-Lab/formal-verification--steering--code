#!/usr/bin/env python3
"""Locate each CARLA preset ON its physical axis, by fitting the disturbance model to
pose-paired frames. No CARLA, no GPU.

WHAT THIS IS FOR
----------------
Closed loop drives ONE point on an axis (the CARLA preset). Verification covers an
INTERVAL. Until the preset's location on the axis is known, the two instruments are not
being asked the same question, and the ledger comparison rests on an unstated assumption.
`STUDY.md` records this as the thing M5 still owes.

Shadows already has it for free: with S measured as the raw dimming, s = 1 reproduces the
observed shadows frame by construction. Fog and night do not, and this script supplies it.

HOW
---
Pose-paired (clear, condition) frames -- see docs and `certify_cell.paired_frames` for why
CARLA supports this and ACDC does not. For each pair, fit the model's parameters by least
squares and report the distribution over frames.

    fog    x' = A + t(row; MOR) * (x - A)
           MOR enters nonlinearly through t = exp(-ln(20)*d(row)/MOR), but it is ONE
           scalar, so: grid over MOR, and at each MOR solve for the airlight A in closed
           form (the model is linear in A given t). This also IDENTIFIES A, which the
           previous generation assumed at 0.78 and never measured -- D4.

    night  x' = x * (1 - g*(1 - L)) + a_r * retro
           linear in (g, a_r), so a single least-squares solve per frame.

The RESIDUAL, plus D3 checks (a),(b),(c),(f) on the road ROI, says how well the analytic model reproduces what
CARLA actually rendered. A model that cannot reproduce the simulator's own frame should not
be used to certify behaviour in it, and a large residual here is a real negative result
worth reporting rather than tuning away. This is NOT the full D3 gate: (d) needs
ground-truth depth bands and (e) is behavioural. Both are still owed.

    python scripts/fit_operating_point.py --condition fog
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
import disturbance_models as dm  # noqa: E402
from scripts.certify_cell import paired_frames  # noqa: E402

OUT = REPO / "results" / "calibration"


def fit_fog(clear, obs, mor_grid):
    """Return (MOR, A[3], rmse) minimising ||A + t(MOR)*(x-A) - obs||."""
    H = clear.shape[0]
    best = None
    for mor in mor_grid:
        t = dm.transmission(H, mor, dm.CARLA_GEOM).astype(np.float32).reshape(-1, 1, 1)
        # obs = t*clear + A*(1-t)  ->  per channel, least squares in A.
        # u must be BROADCAST to the full frame before the sums: t is per-row, shape
        # (H,1,1), so summing u**2 over (H,1) while summing u*r over (H,W) divides by a
        # denominator W times too small and inflates A by ~W.
        u = np.broadcast_to(1.0 - t, clear.shape)
        r = obs - t * clear
        A = np.array([float((u[..., c] * r[..., c]).sum()
                            / max((u[..., c] ** 2).sum(), 1e-9))
                      for c in range(3)], np.float32)
        pred = t * clear + A.reshape(1, 1, 3) * (1.0 - t)
        rmse = float(np.sqrt(((pred - obs) ** 2).mean()))
        if best is None or rmse < best[2]:
            best = (float(mor), A, rmse, pred)
    return best


def fit_fog_illum(clear, obs, mor_grid):
    """Koschmieder PLUS surface-illumination attenuation.

        x' = A*(1 - t) + t * k * x0

    WHY THE EXTRA TERM. Plain Koschmieder holds the scene radiance x0 fixed and veils it
    toward the airlight, so it can only move the road ROI TOWARD A. Measured on pose-paired
    CARLA frames, fog brightens the sky by +0.42 and DARKENS the road by -0.03 at the same
    time, which no single global A can reproduce. The physical omission is that fog also
    attenuates the sunlight reaching the road surface, so the surface radiance itself drops;
    `k` is that attenuation.

    STILL VERIFIABLE. Reparameterize as u1 = t (per row) and u2 = t*k. Then

        x' = A*(1 - u1) + u2 * x0

    is linear in (u1, u2), so a sub-interval is rank-2 rather than rank-1 -- d = 2 instead
    of d = 1, the same cost night already pays.
    """
    H = clear.shape[0]
    best = None
    for mor in mor_grid:
        t = dm.transmission(H, mor, dm.CARLA_GEOM).astype(np.float32).reshape(-1, 1, 1)
        u = np.broadcast_to(1.0 - t, clear.shape)
        tx = np.broadcast_to(t, clear.shape) * clear
        A = np.zeros(3, np.float32)
        k = np.zeros(3, np.float32)
        for c in range(3):
            M = np.stack([u[..., c].reshape(-1), tx[..., c].reshape(-1)], 1)
            sol, *_ = np.linalg.lstsq(M, obs[..., c].reshape(-1), rcond=None)
            A[c], k[c] = float(sol[0]), float(sol[1])
        pred = A.reshape(1, 1, 3) * (1.0 - t) + t * k.reshape(1, 1, 3) * clear
        rmse = float(np.sqrt(((pred - obs) ** 2).mean()))
        if best is None or rmse < best[3]:
            best = (float(mor), A, k, rmse, pred)
    return best


def d3_partial(clear, obs, pred, roi):
    """D3 checks (a), (b), (c), (f) on the road ROI. NOT the full gate.

    D3 is a six-part conjunction. (d) needs per-pixel ground-truth depth from a depth
    camera at the identical transform, and (e) is behavioural over >= 2 students, so
    neither can be evaluated here. Reporting these four as "D3" would be exactly the
    behaviour-only gate that let the previous study's fog model through while it moved the
    road mean by 0.003 against the renderer's 0.248.
    """
    c = clear[roi].reshape(-1, 3)
    o = obs[roi].reshape(-1, 3)
    p = pred[roi].reshape(-1, 3)

    dmu_r = float((o - c).mean())            # rendered mean shift
    dmu_m = float((p - c).mean())            # modelled mean shift
    a_ok = (dmu_r == 0 and dmu_m == 0) or (np.sign(dmu_r) == np.sign(dmu_m))
    ratio_mu = dmu_m / dmu_r if abs(dmu_r) > 1e-9 else float("inf")
    b_ok = 0.75 <= ratio_mu <= 1.25

    ds_r, ds_m = float(o.std()), float(p.std())
    ratio_sig = ds_m / ds_r if ds_r > 1e-9 else float("inf")
    c_ok = 0.7 <= ratio_sig <= 1.4

    ss_res = float(((o - p) ** 2).sum())
    ss_tot = float(((o - o.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-9 else float("nan")
    f_ok = r2 >= 0.5

    return {"dmu_rendered": dmu_r, "dmu_model": dmu_m, "ratio_mu": ratio_mu,
            "ratio_sigma": ratio_sig, "roi_r2": r2,
            "a_sign": bool(a_ok), "b_magnitude": bool(b_ok),
            "c_sigma": bool(c_ok), "f_r2": bool(f_ok)}


def fit_night(clear, obs):
    """Return (g, a_retro, rmse). Linear in both, so one solve."""
    H, W = clear.shape[:2]
    L = dm.headlight_field(H, W)[..., None].astype(np.float32)
    t_road = float(np.percentile(clear[dm.ROAD_TOP:dm.ROAD_BOT], 75))
    retro = (L * np.maximum(clear - t_road, 0.0)).astype(np.float32)

    # obs = clear - g*clear*(1-L) + a_r*retro
    b1 = (-clear * (1.0 - L)).reshape(-1)
    b2 = retro.reshape(-1)
    y = (obs - clear).reshape(-1)
    M = np.stack([b1, b2], 1)
    sol, *_ = np.linalg.lstsq(M, y, rcond=None)
    g, a_r = float(sol[0]), float(sol[1])
    pred = clear + g * (-clear * (1.0 - L)) + a_r * retro
    return g, a_r, float(np.sqrt(((pred - obs) ** 2).mean())), pred


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--condition", required=True, choices=["fog", "night"])
    ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--model", choices=["illum", "koschmieder"], default="illum",
                    help="fog only; 'koschmieder' is the D3-failing diagnostic (F14)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    pairs = paired_frames(args.frames, args.condition)
    if not pairs:
        print("no pose-matched pairs")
        return 2
    print(f"{args.condition}: {len(pairs)} pose-matched pairs, "
          f"median pose err {np.median([p[2] for p in pairs]):.3f} m\n")

    roi = slice(*C.ROAD_ROI_ROWS)
    # coarse-to-fine so the grid does not decide the answer
    mor_grid = np.concatenate([np.arange(10, 200, 2.0), np.arange(200, 2100, 25.0)])

    rows = []
    for i, (cimg, oimg, perr) in enumerate(pairs):
        clear = cimg.astype(np.float32) / 255.0
        obs = oimg.astype(np.float32) / 255.0
        if args.condition == "fog":
            if args.model == "illum":
                mor, A, kv, rmse, pred = fit_fog_illum(clear, obs, mor_grid)
            else:
                mor, A, rmse, pred = fit_fog(clear, obs, mor_grid)
                kv = np.ones(3, np.float32)
            d3 = d3_partial(clear, obs, pred, roi)
            rows.append({"frame": i, "pose_err_m": perr, "mor_m": mor,
                         "airlight": A.tolist(), "k": kv.tolist(),
                         "rmse": rmse, "d3_partial": d3})
            print(f"  {i:3d}  MOR {mor:7.1f} m   A = [{A[0]:.3f} {A[1]:.3f} {A[2]:.3f}]"
                  f"   k = {float(np.mean(kv)):.3f}   rmse {rmse:.4f}")
        else:
            g, a_r, rmse, pred = fit_night(clear, obs)
            d3 = d3_partial(clear, obs, pred, roi)
            ambient = 1.0 / g - 1.0 if g > 0 else float("nan")
            rows.append({"frame": i, "pose_err_m": perr, "g": g, "ambient": ambient,
                         "a_retro": a_r, "rmse": rmse, "d3_partial": d3})
            print(f"  {i:3d}  g {g:6.3f}  (ambient {ambient:6.3f})  "
                  f"a_retro {a_r:+7.3f}   rmse {rmse:.4f}")

    print("\n" + "=" * 62)
    rmse = np.array([r["rmse"] for r in rows])
    if args.condition == "fog":
        mor = np.array([r["mor_m"] for r in rows])
        A = np.array([r["airlight"] for r in rows])
        print(f"  MOR      median {np.median(mor):.1f} m   "
              f"IQR [{np.percentile(mor,25):.1f}, {np.percentile(mor,75):.1f}]")
        print(f"  airlight median [{np.median(A[:,0]):.3f} {np.median(A[:,1]):.3f} "
              f"{np.median(A[:,2]):.3f}]   (0.78 was ASSUMED, never measured)")
        K = np.array([r["k"] for r in rows])
        print(f"  k        median [{np.median(K[:,0]):.3f} {np.median(K[:,1]):.3f} "
              f"{np.median(K[:,2]):.3f}]   (surface illumination attenuation)")
        summary = {"condition": "fog", "model": args.model,
                   "mor_median_m": float(np.median(mor)),
                   "mor_iqr": [float(np.percentile(mor, 25)), float(np.percentile(mor, 75))],
                   "airlight_median": [float(np.median(A[:, c])) for c in range(3)],
                   "k_median": [float(np.median(K[:, c])) for c in range(3)]}
        axis_note = (f"CARLA fog_density=70 sits at MOR ~ {np.median(mor):.0f} m on the "
                     f"declared 2000 -> 60 m axis.")
    else:
        g = np.array([r["g"] for r in rows])
        amb = np.array([r["ambient"] for r in rows])
        ar = np.array([r["a_retro"] for r in rows])
        print(f"  g        median {np.median(g):.4f}   "
              f"IQR [{np.percentile(g,25):.4f}, {np.percentile(g,75):.4f}]")
        print(f"  ambient  median {np.median(amb):.4f}   (declared axis 0.02 - 0.50)")
        print(f"  a_retro  median {np.median(ar):+.3f}   (declared axis 0.0 - 3.0)")
        summary = {"condition": "night", "g_median": float(np.median(g)),
                   "ambient_median": float(np.median(amb)),
                   "a_retro_median": float(np.median(ar))}
        axis_note = (f"CARLA sun_altitude=-25 sits at g ~ {np.median(g):.3f} "
                     f"(ambient ~ {np.median(amb):.3f}), a_retro ~ {np.median(ar):.2f}.")
    print(f"  rmse     median {np.median(rmse):.4f}   max {rmse.max():.4f}")
    print()
    print("  D3 PARTIAL on the road ROI -- checks (a),(b),(c),(f) only. (d) needs")
    print("  ground-truth depth bands and (e) is behavioural, so this is NOT the gate.")
    for k, label in (("a_sign", "(a) dmu sign agrees"),
                     ("b_magnitude", "(b) dmu magnitude within 0.25x"),
                     ("c_sigma", "(c) dsigma ratio in [0.7,1.4]"),
                     ("f_r2", "(f) ROI R^2 >= 0.5")):
        n = sum(1 for r in rows if r["d3_partial"][k])
        print(f"    {label:<34s} {n}/{len(rows)} frames")
    print(f"    median ROI R^2 {np.median([r['d3_partial']['roi_r2'] for r in rows]):+.3f}"
          f"   median dmu rendered "
          f"{np.median([r['d3_partial']['dmu_rendered'] for r in rows]):+.4f}"
          f"   model "
          f"{np.median([r['d3_partial']['dmu_model'] for r in rows]):+.4f}")
    print(f"\n  {axis_note}")
    print("=" * 62)

    summary.update({"pairs": len(rows), "rmse_median": float(np.median(rmse)),
                    "rmse_max": float(rmse.max()), "axis_note": axis_note,
                    "per_frame": rows})
    path = OUT / f"operating_point_{args.condition}.json"
    with open(path, "w") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

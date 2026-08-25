#!/usr/bin/env python3
"""Capture the SAME poses at many fog densities, to calibrate MOR(fog_density) and k(MOR).

WHY. Fitting the fog model against pose-paired frames gave, at CARLA's fog_density=70:
MOR ~ 61 m, airlight ~ 0.45, and a surface-illumination attenuation k ~ 0.70. Plain
Koschmieder without k fails D3(a) outright -- it brightens the road ROI while CARLA darkens
it. Adding k fixes all four computable D3 checks (ROI R^2 -0.03 -> +0.87).

But k was fitted at ONE density, so k(MOR) is an assumed functional form with one fitted
number. Certifying an interval on the strength of a curve measured at a single point is the
kind of thing that looks fine until a reviewer asks. This script measures it.

CHEAP BY CONSTRUCTION. No driving: park at N poses, and at each pose cycle the fog density.
Nothing depends on closed-loop behaviour, so this costs minutes, not laps.

THE CARLA RULE THAT HAS BITTEN FOUR TIMES. A read or a placement issued next to a write does
not see that write. So: weather is CONSTRUCTED, never read-modify-written; the vehicle is
placed and then ticked before any capture; and every frame is matched on the id
`world.tick()` returns via `env.grab_frame`, which raises rather than swallowing a timeout.

    python scripts/fog_density_sweep.py --poses 12
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import carla  # noqa: E402
import config as C  # noqa: E402
import carla_env as env  # noqa: E402
import disturbance_models as dm  # noqa: E402
from imaging import raw_to_bgr  # noqa: E402

OUT = REPO / "results" / "calibration"
DENSITIES = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 0.0]
WARMUP_TICKS = 20     # camera settling before ANY capture
SETTLE_TICKS = 8      # after a weather write, before capture


def fit_at(clear, obs, mor_grid):
    """(MOR, A[3], k[3], rmse) for the illumination-attenuated Koschmieder model."""
    H = clear.shape[0]
    best = None
    for mor in mor_grid:
        t = dm.transmission(H, mor, dm.CARLA_GEOM).astype(np.float32).reshape(-1, 1, 1)
        u = np.broadcast_to(1.0 - t, clear.shape)
        tx = np.broadcast_to(t, clear.shape) * clear
        A = np.zeros(3, np.float32); k = np.zeros(3, np.float32)
        for c in range(3):
            M = np.stack([u[..., c].reshape(-1), tx[..., c].reshape(-1)], 1)
            sol, *_ = np.linalg.lstsq(M, obs[..., c].reshape(-1), rcond=None)
            A[c], k[c] = float(sol[0]), float(sol[1])
        pred = A.reshape(1, 1, 3) * (1.0 - t) + t * k.reshape(1, 1, 3) * clear
        rmse = float(np.sqrt(((pred - obs) ** 2).mean()))
        if best is None or rmse < best[3]:
            best = (float(mor), A, k, rmse)
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--poses", type=int, default=12)
    ap.add_argument("--tag", default="", help="suffix for the output file")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    client = carla.Client(C.HOST, C.PORT)
    client.set_timeout(C.CLIENT_TIMEOUT_S)
    # LOAD THE CONFIGURED MAP. `get_world()` returns whatever happens to be loaded; a
    # freshly launched CARLA serves Town10, and this sweep would then capture Town10 at
    # Town04 coordinates (capture_offset_yaw.py documents the incident).
    world = env.load_town04(client, fresh=False)
    # enable_sync_mode also provisions bounded substepping. Hand-rolled settings here
    # left CARLA's defaults (0.01 x 10 = 0.1 s of physics per 0.2 s tick), so the
    # settle loop below ran under different physics than the driving pipeline.
    original = env.enable_sync_mode(world)

    vehicle = camera = None
    captures = {}
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
        vehicle.set_autopilot(False)
        vehicle.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))

        # SETTLE, THEN FREEZE PHYSICS.
        #
        # Measured: teleporting to the spawn z and capturing 2 ticks later leaves the car
        # 0.2943 m above its settled height, and it then oscillates (-0.19, -0.22, -0.17)
        # rather than converging. Camera height enters the depth model directly as
        # d(row) = h*f/(row - horizon), so a 0.28 m error rescales every depth by ~23% and
        # biases the (MOR, k) fit -- which is very likely why this sweep disagreed with the
        # route frames on k. The start-vs-end drift check could not catch it because both
        # clear passes carried the identical error.
        #
        # A static photometric capture does not need physics, so settle once, read the
        # settled height, and freeze. Teleports are then exact and reproducible.
        for _ in range(40):
            world.tick()
        z_settled = vehicle.get_transform().location.z
        vehicle.set_simulate_physics(False)
        print(f"  settled ride height z = {z_settled:.4f} (physics now frozen)")

        # Spawn the camera ONCE, up front, and warm it up.
        #
        # The first version spawned it inside the density loop, so the clear baseline --
        # which every other density is measured against -- came from the camera's very
        # first frames. That biased the baseline dark and made fog look relatively
        # brighter, which is very likely why the sweep fitted k ~ 1.18 while the route
        # frames fit k ~ 0.70 with a sharp rmse minimum. A corrupted denominator does not
        # announce itself; it just returns a plausible wrong number.
        camera, img_queue = env.spawn_camera(world, vehicle, condition="fog")
        for _ in range(WARMUP_TICKS):
            fid = world.tick()
            try:
                env.grab_frame(img_queue, fid)
            except Exception:
                pass

        offsets = np.linspace(0.0, 220.0, args.poses)
        for di, density in enumerate(DENSITIES):
            # CONSTRUCT the weather; never read-modify-write.
            w = env.weather_params("clear" if density == 0.0 else "fog")
            w.fog_density = float(density)
            if density == 0.0:
                w.fog_distance = 0.0
            world.set_weather(w)
            # the write lands on the NEXT tick, and volumetric fog needs a few more to
            # settle; measured by re-capturing the clear baseline at the end of the sweep.
            for _ in range(SETTLE_TICKS):
                world.tick()

            frames = []
            for oi, off in enumerate(offsets):
                pose = dict(C.SPAWN_EASTBOUND)
                pose["x"] += float(off)
                pose["z"] = z_settled
                vehicle.set_transform(env.make_transform(pose))
                world.tick()      # placement lands next tick
                fid = world.tick()
                frames.append(raw_to_bgr(env.grab_frame(img_queue, fid)).copy())
            key = density if density not in captures else "0_end"
            captures[key] = frames
            print(f"  density {density:5.1f}: {len(frames)} poses captured"
                  f"{' (end-of-sweep drift check)' if key == '0_end' else ''}")
    finally:
        for label, fn in (("camera", lambda: camera and camera.destroy()),
                          ("vehicle", lambda: vehicle and vehicle.destroy()),
                          ("settings", lambda: world.apply_settings(original))):
            try:
                fn()
            except Exception as exc:
                print(f"  cleanup: {label} failed ({type(exc).__name__}); continuing")

    if 0.0 not in captures:
        print("no clear baseline captured")
        return 2

    # Baseline drift check: the clear capture repeated at the end must match the first.
    if "0_end" in captures:
        d = [float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean() / 255.0)
             for a, b in zip(captures[0.0], captures["0_end"])]
        print(f"\n  clear baseline drift, start vs end: mean |diff| {np.mean(d):.4f} "
              f"(max {np.max(d):.4f}) -- large means the scene was still settling")
        captures.pop("0_end")

    mor_grid = np.concatenate([np.arange(6, 200, 2.0), np.arange(200, 3000, 25.0)])
    rows = []
    print(f"\n  {'density':>8s} {'MOR (m)':>10s} {'k (mean)':>9s} {'A (mean)':>9s} "
          f"{'rmse':>7s}")
    print("  " + "-" * 48)
    for density, frames in sorted(captures.items()):
        if density == 0.0:
            continue
        fits = []
        for clear_img, obs_img in zip(captures[0.0], frames):
            cf = clear_img.astype(np.float32) / 255.0
            of = obs_img.astype(np.float32) / 255.0
            fits.append(fit_at(cf, of, mor_grid))
        mor = float(np.median([f[0] for f in fits]))
        A = [float(np.median([f[1][c] for f in fits])) for c in range(3)]
        k = [float(np.median([f[2][c] for f in fits])) for c in range(3)]
        rmse = float(np.median([f[3] for f in fits]))
        rows.append({"fog_density": density, "mor_m": mor, "airlight": A,
                     "k": k, "rmse": rmse, "poses": len(fits)})
        print(f"  {density:8.1f} {mor:10.1f} {np.mean(k):9.3f} {np.mean(A):9.3f} "
              f"{rmse:7.4f}")

    # k(MOR) = exp(-ln(20) * d_sun / MOR): does one effective sun path fit them all?
    m = np.array([r["mor_m"] for r in rows])
    kk = np.array([float(np.mean(r["k"])) for r in rows])
    good = (kk > 0) & (kk < 1) & (m > 0)
    d_sun = float(np.median(-np.log(kk[good]) * m[good] / np.log(20.0))) if good.any() \
        else float("nan")
    pred_k = np.exp(-np.log(20.0) * d_sun / m)
    resid = float(np.abs(pred_k - kk).max()) if good.any() else float("nan")
    print("\n" + "=" * 52)
    print(f"  k(MOR) = exp(-ln20 * d_sun / MOR),  d_sun = {d_sun:.2f} m")
    print(f"  max |k_pred - k_measured| over the sweep = {resid:.4f}")
    print("  A one-parameter law fitting the whole sweep is evidence the form is right;")
    print("  a large residual means k must be bounded per sub-interval instead (d = 2).")
    print("=" * 52)

    path = OUT / f"fog_density_sweep{args.tag}.json"
    json.dump({"densities": rows, "d_sun_m": d_sun, "k_law_max_resid": resid,
               "poses": args.poses}, open(path, "w"), indent=2)
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    # One CARLA client per port. Two synchronous clients on one world interleave ticks
    # and silently corrupt each other -- see pipeline/carla_lock.py for the run this cost.
    from carla_lock import carla_lock, CarlaBusy
    try:
        with carla_lock(owner=" ".join(sys.argv[:3])):
            sys.exit(main())
    except CarlaBusy as exc:
        print(exc)
        sys.exit(4)

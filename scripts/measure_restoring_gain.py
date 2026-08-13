#!/usr/bin/env python3
"""Does the policy still steer back toward the lane when it is off-centre, under disturbance?

WHY THIS AND NOT ANOTHER PER-FRAME CRITERION. F21 showed closed-loop failure here is feedback
divergence, not bias accumulation on the nominal path: at fog densities 25-55 the real
per-frame biases reverse sign every 8-16 frames while the vehicle departs on every run, and
a parameter-free accumulation model explains only 1 of 4 failures. The frames that cause a
departure are off-centre views that appear nowhere on the nominal trajectory, so no amount
of bounding the nominal frames can see them.

The simplest measurable form of the missing quantity is the RESTORING GAIN: place the
vehicle at a known lateral offset and ask which way the policy steers. A stable policy
steers back, so d(steer)/d(offset) has a consistent restoring sign and adequate magnitude. A
policy whose restoring gain collapses or inverts under a disturbance will walk out of the
lane regardless of how small its nominal-path bias looks -- which is exactly the S_clear
pattern.

This is the vehicle-dynamics extension in its cheapest form: one scalar per (policy,
condition) that speaks to closed-loop stability rather than open-loop error.

Static placement is trustworthy here: at a manifest pose it reproduces the driven frame to
0.0099 on the road ROI. Physics is frozen at the settled ride height and the camera warmed
up, both of which have bitten before.
"""
import sys, csv, math
from pathlib import Path
import numpy as np
import torch
import carla

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402
import carla_env as env  # noqa: E402
import verifiable_disturbance as vd  # noqa: E402
from imaging import raw_to_bgr  # noqa: E402
from student import StudentNet  # noqa: E402
from carla_lock import carla_lock  # noqa: E402

OFFSETS = np.array([-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0])
CONDS = ["clear", "fog", "night", "shadows"]
N_POSE = 8


def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    nets = {}
    for nm, ck, ch, fc in (("S_clear", "S_clear_84x28", (8, 16, 16), 32),
                           ("S_mixed", "S_mixed_84x28_w3", (24, 48, 48), 96)):
        m = StudentNet(28, 84, channels=ch, fc=fc).to(dev)
        m.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev))
        m.eval(); nets[nm] = m

    def steer(m, bgr):
        with torch.no_grad():
            return float(m(torch.from_numpy(
                vd._project(bgr.astype(np.float32) / 255.0, 84, 28)
                .reshape(1, 3, 28, 84).astype(np.float32)).to(dev)).item())

    base = REPO / "pipeline" / "data" / "live_pairs"
    with open(base / "manifest.csv") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r["weather"] == "clear" and r["direction"] == "westbound"]
    poses = rows[200:: max(1, (len(rows) - 300) // N_POSE)][:N_POSE]

    data = {(nm, c): {o: [] for o in OFFSETS} for nm in nets for c in CONDS}
    with carla_lock(owner="restoring gain"):
        cl = carla.Client(C.HOST, C.PORT); cl.set_timeout(120.0)
        world = cl.get_world()
        orig = world.get_settings(); s = world.get_settings()
        s.synchronous_mode = True; s.fixed_delta_seconds = C.FIXED_DT
        world.apply_settings(s)
        v = cam = None
        try:
            v = env.spawn_vehicle(world, C.SPAWN_WESTBOUND)
            v.apply_control(carla.VehicleControl(brake=1.0))
            for _ in range(40):
                world.tick()
            z = v.get_transform().location.z
            v.set_simulate_physics(False)
            for cond in CONDS:
                if cam is not None:
                    cam.destroy()
                cam, q = env.set_condition(world, v, cond)
                for _ in range(25):
                    f = world.tick()
                    try: env.grab_frame(q, f)
                    except Exception: pass
                for r in poses:
                    yaw = float(r["yaw"])
                    nx = -math.sin(math.radians(yaw)); ny = math.cos(math.radians(yaw))
                    for off in OFFSETS:
                        v.set_transform(env.make_transform(
                            dict(x=float(r["x"]) + nx * off, y=float(r["y"]) + ny * off,
                                 z=z, yaw=yaw)))
                        for _ in range(4):
                            world.tick()
                        while True:
                            fid = world.tick()
                            try:
                                img = raw_to_bgr(env.grab_frame(q, fid)); break
                            except Exception: pass
                        for nm, m in nets.items():
                            data[(nm, cond)][off].append(steer(m, img))
        finally:
            try:
                if cam: cam.destroy()
                if v: v.destroy()
            except Exception: pass
            world.apply_settings(orig)

    print(f"\nRESTORING GAIN  d(steer)/d(lateral offset), {N_POSE} poses, westbound")
    print("a stable policy has a consistent restoring sign; collapse or inversion means "
          "it will not return to the lane\n")
    print(f"  {'model':9s} {'region':>12s} " + " ".join(f"{c:>10s}" for c in CONDS))
    for nm in nets:
        for label, sel in (("near |o|<=0.5", np.abs(OFFSETS) <= 0.5),
                           ("far |o|>=1.0", np.abs(OFFSETS) >= 1.0)):
            cells = []
            for cond in CONDS:
                x = OFFSETS[sel]
                y = np.array([np.mean(data[(nm, cond)][o]) for o in OFFSETS[sel]])
                cells.append(f"{float(np.polyfit(x, y, 1)[0]):+10.4f}")
            print(f"  {nm:9s} {label:>12s} " + " ".join(cells))
    print()
    for nm in nets:
        for cond in CONDS:
            y = np.array([np.mean(data[(nm, cond)][o]) for o in OFFSETS])
            print(f"  {nm:9s} {cond:8s} steer by offset: " +
                  " ".join(f"{o:+.1f}:{v:+.3f}" for o, v in zip(OFFSETS, y)))
    print("\n  (sign relative to clear is what matters: same sign = still correcting)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

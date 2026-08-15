#!/usr/bin/env python3
"""Measure each policy's steering response to lateral offset, at controlled offsets.

WHY. The signed steering bias under a disturbance separates the two policies by 30-70x
(F21), so it is the statistic verification should bound. To turn it into a threshold rather
than a number read off the data, we need the loop's disturbance rejection: a sustained bias
`d` settles at CTE = d / k, where k is the policy's steering response per metre of lateral
offset. Departure when d/k exceeds the CTE budget, so |d|_max = k * budget.

Regressing steering against the EXPERT's logged CTE does not measure k -- the expert holds
|CTE| < 0.1 m, so the fit is dominated by road curvature, and it returned |k| ~ 1.9 steer/m,
implying a tolerable bias beyond full steering lock. That is obviously wrong given the
policies crash.

So place the vehicle at CONTROLLED lateral offsets on a straight, capture, and read the
response directly. Physics frozen at the settled ride height (a car 0.29 m high biases
depth-per-row); camera warmed up.
"""
import sys, math
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
from route import load_route  # noqa: E402
from carla_lock import carla_lock  # noqa: E402

OFFSETS = np.arange(-0.6, 0.61, 0.15)     # metres, within and beyond the CTE budget
N_POSE = 6


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

    route = load_route("eastbound")
    with carla_lock(owner="cte gain"):
        cl = carla.Client(C.HOST, C.PORT); cl.set_timeout(120.0)
        world = cl.get_world()
        orig = world.get_settings(); s = world.get_settings()
        s.synchronous_mode = True; s.fixed_delta_seconds = C.FIXED_DT
        world.apply_settings(s)
        v = cam = None
        try:
            world.set_weather(env.weather_params("clear"))
            v = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
            v.apply_control(carla.VehicleControl(brake=1.0))
            for _ in range(40):
                world.tick()
            z = v.get_transform().location.z
            v.set_simulate_physics(False)
            cam, q = env.spawn_camera(world, v, condition="clear")
            for _ in range(25):
                f = world.tick()
                try: env.grab_frame(q, f)
                except Exception: pass

            # straight stretch, spaced along the route
            idx = np.linspace(60, 60 + 40 * N_POSE, N_POSE).astype(int)
            data = {nm: {o: [] for o in OFFSETS} for nm in nets}
            for i in idx:
                p0 = route[i % len(route)]; p1 = route[(i + 3) % len(route)]
                yaw = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
                nx, ny = -math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
                for off in OFFSETS:
                    tf = env.make_transform(dict(x=float(p0[0] + nx * off),
                                                 y=float(p0[1] + ny * off),
                                                 z=z, yaw=yaw))
                    v.set_transform(tf)
                    for _ in range(4):
                        world.tick()
                    while True:
                        fid = world.tick()
                        try:
                            img = raw_to_bgr(env.grab_frame(q, fid)); break
                        except Exception: pass
                    for nm, m in nets.items():
                        data[nm][off].append(steer(m, img))
        finally:
            try:
                if cam: cam.destroy()
                if v: v.destroy()
            except Exception: pass
            world.apply_settings(orig)

    print(f"CTE budget {C.CTE_BUDGET_M:.3f} m; steering is normalised to [-1, 1]\n")
    print(f"  {'offset m':>9s} " + " ".join(f"{nm:>10s}" for nm in nets))
    for off in OFFSETS:
        print(f"  {off:9.2f} " + " ".join(f"{np.mean(data[nm][off]):10.4f}" for nm in nets))
    print()
    for nm in nets:
        x = np.array(OFFSETS, float)
        y = np.array([np.mean(data[nm][o]) for o in OFFSETS])
        k = float(np.polyfit(x, y, 1)[0])
        thr = abs(k) * C.CTE_BUDGET_M
        print(f"  {nm:9s} k = {k:+.4f} steer/m   max sustained bias |d| = {thr:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

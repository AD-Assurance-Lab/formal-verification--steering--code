#!/usr/bin/env python3
"""Are the ledger's repetitions INDEPENDENT, or does each run inherit the last one's state?

The clear/S_clear_t06 cell drove 1/12, and the failing run is reproducible across two
independent rebuilds: s00 peaks at 0.50 ft on rep0 and 2.77 ft on rep1, at the SAME step
(498) and the same place. Every other section is stable between reps.

The asymmetry has an obvious candidate. closed_loop_ledger.py spawns the vehicle ONCE and
reuses it for all twelve runs, so in rep0 s00 follows the spawn and in rep1 it follows s05.
Every other section is preceded by another run in both reps -- which is exactly the set
that is stable.

If that is the cause, the twelve runs are not twelve independent trials, and a failure
RATE over them is not a rate over independent trials, which is what the Wilson interval
assumes (standing rule 3).

    A: s00, s00, s00        same section three times, nothing else between
    B: s05 -> s00           the rep1 ordering
    C: respawn -> s00       a genuinely fresh vehicle

If A is tight and B reproduces ~2.8 ft, run order is the cause. If C matches A, respawning
per run is the fix.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/probe_run_independence.py
"""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.environ.setdefault("CARLA_PORT", "3000")
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "scripts"))

import torch                                                     # noqa: E402
import carla_env as env                                          # noqa: E402
import config as C                                               # noqa: E402
from student import StudentNet                                   # noqa: E402
from closed_loop_ledger import drive_once                        # noqa: E402

SEC = "s00"
COND = "clear"


def load_student():
    nm, ck_base, ch, fc = C.TOWN06_STUDENTS[0]
    ck = C.final_student(ck_base)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = StudentNet(C.TOWN06_INPUT_H, C.TOWN06_INPUT_W, channels=ch, fc=fc).to(dev)
    net.load_state_dict(torch.load(f"{C.CHECKPOINT_DIR}/{ck}.pth", map_location=dev,
                                   weights_only=True))
    net.eval()
    return ck, net, dev


def main():
    ck, net, dev = load_student()
    print(f"\nRUN-INDEPENDENCE PROBE -- {ck}, '{COND}', budget {C.CTE_BUDGET_FT:.2f} ft")
    client = env.connect()
    world = env.load_town04(client)
    original = env.enable_sync_mode(world)
    vehicle = camera = None
    try:
        vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
        camera, q = env.set_condition(world, vehicle, COND)

        print("\n  A: the same section three times, nothing between")
        for i in range(3):
            mx, frac, dep, _, _ = drive_once(world, vehicle, q, net, dev, SEC,
                                          C.steps_for(SEC))
            print(f"     {SEC} #{i}   max|CTE| {mx * C.M_TO_FT:5.2f} ft", flush=True)

        print("\n  B: s05 first, then s00 -- the rep1 ordering")
        mx, _, _, _, _ = drive_once(world, vehicle, q, net, dev, "s05", C.steps_for("s05"))
        print(f"     s05      max|CTE| {mx * C.M_TO_FT:5.2f} ft", flush=True)
        mx, _, _, _, _ = drive_once(world, vehicle, q, net, dev, SEC, C.steps_for(SEC))
        print(f"     {SEC}      max|CTE| {mx * C.M_TO_FT:5.2f} ft   <-- rep1 position",
              flush=True)

        print("\n  C: a genuinely fresh vehicle, then s00")
        camera.destroy(); vehicle.destroy(); world.tick()
        vehicle = env.spawn_vehicle(world, C.SPAWN_EASTBOUND)
        camera, q = env.set_condition(world, vehicle, COND)
        mx, _, _, _, _ = drive_once(world, vehicle, q, net, dev, SEC, C.steps_for(SEC))
        print(f"     {SEC}      max|CTE| {mx * C.M_TO_FT:5.2f} ft   <-- respawned",
              flush=True)
    finally:
        try:
            if camera:
                camera.destroy()
            if vehicle:
                vehicle.destroy()
        except Exception:
            pass
        world.apply_settings(original)
    return 0


if __name__ == "__main__":
    sys.exit(main())

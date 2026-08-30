#!/usr/bin/env python3
"""Drive each student once per section so the CAPTURE GATE has something to compare against.

The gate (scripts/capture_driven_gate.py) asks whether the frames a certificate was
computed on reproduce what the vehicle actually commanded. That needs the driven steering
PER POSE, and the closed-loop ledger keeps only per-run summaries -- max |CTE|, the
position it occurred at, a verdict. Correct for a failure rate, useless for the gate.

evaluate.py already writes the full per-step trace (x, y, nn_steer) via save_and_report.
This is the committed driver that invokes it with the right architecture for each student
on each map, so the gate's inputs are reproducible from the repo rather than from whatever
was typed that day -- which is exactly how the 160 m capture defect got in.

One clear-weather pass per student per section. No repetitions: the gate is a check on the
capture rig, not a failure rate, and rule 3 does not apply to it.

    STUDY_MAP=Town06 python3 scripts/capture_gate_drives.py
    STUDY_MAP=Town04 TOWN04_REDO=1 python3 scripts/capture_gate_drives.py
"""
import os, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C                                              # noqa: E402


def main():
    students = C.TOWN06_STUDENTS if C.STUDY_MAP == "Town06" else C.STUDENTS
    in_w, in_h = ((C.TOWN06_INPUT_W, C.TOWN06_INPUT_H) if C.STUDY_MAP == "Town06"
                  else (84, 28))

    # R-SIM-1: a degraded server reports plausible velocities and stops advancing physics.
    print("restarting CARLA before the run (R-SIM-1)", flush=True)
    subprocess.run(["bash", str(REPO / "scripts" / "carla_restart.sh")],
                   stdout=open("/tmp/gate_drive_restart.log", "w"),
                   stderr=subprocess.STDOUT, check=False)

    rc_all = 0
    for nm, ck_base, ch, fc in students:
        ck = C.final_student(ck_base)
        if not (Path(C.CHECKPOINT_DIR) / f"{ck}.pth").exists():
            print(f"  {nm}: MISSING checkpoint {ck}.pth -- cannot drive", flush=True)
            rc_all = 1
            continue
        cmd = [sys.executable, str(REPO / "pipeline" / "evaluate.py"),
               "--model", ck, "--student",
               "--channels", ",".join(str(c) for c in ch), "--fc", str(fc),
               "--in-w", str(in_w), "--in-h", str(in_h),
               "--weather", "clear", "--direction", "all"]
        print(f"\n=== {nm} ({ck}) ===\n  {' '.join(cmd)}", flush=True)
        rc = subprocess.run(cmd, cwd=str(REPO)).returncode
        print(f"  rc={rc}", flush=True)
        rc_all = rc_all or rc
    return rc_all


if __name__ == "__main__":
    sys.exit(main())

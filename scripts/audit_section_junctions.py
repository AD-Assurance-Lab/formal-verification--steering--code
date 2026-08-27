#!/usr/bin/env python3
"""How much JUNCTION is inside each scored section?

build_town06_sections.clean_mask filters on lane markings, lane width and distance from
traffic-control points. It never checks wp.is_junction. Only the SEEDS avoid junctions
(`if not w.is_junction`); the run grown from a seed can cross one, provided the junction
has painted markings and standard lane width.

Zach, watching a run, saw the vehicle spawn on the far side of an intersection and drive
straight through it. The policies are lane-keepers and were never trained for junctions,
so a junction inside a scored window contributes frames the model cannot be expected to
handle -- and max|CTE| is a MAXIMUM, so one such frame sets the section's score.

Reports, per section: the fraction of the scored window that is junction, where those
stretches begin and end, and what a scored-window trim would have to remove.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/audit_section_junctions.py
"""
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402


def main():
    import carla
    import carla_env as env
    from route import load_route

    client = env.connect()
    world = env.load_town04(client, fresh=False)
    wmap = world.get_map()

    print(f"{'section':8s} {'scored_m':>9s} {'junction_m':>11s} {'%':>6s} "
          f"{'stretches (m along scored window)'}")
    worst_tail = 0.0
    for sec in C.SECTIONS:
        rt = np.asarray(load_route(sec), dtype=float)
        seg = np.linalg.norm(np.diff(rt, axis=0), axis=1)
        arc = np.concatenate([[0.0], np.cumsum(seg)])
        scored = C.SECTION_LEN_M[sec]
        idx = np.where(arc <= scored)[0]
        isj = []
        for i in idx:
            wp = wmap.get_waypoint(carla.Location(x=float(rt[i, 0]), y=float(rt[i, 1]), z=0.5),
                                   project_to_road=True, lane_type=carla.LaneType.Driving)
            isj.append(bool(wp.is_junction))
        isj = np.array(isj)
        # contiguous junction stretches
        spans, s0 = [], None
        for i, v in enumerate(isj):
            if v and s0 is None:
                s0 = i
            elif not v and s0 is not None:
                spans.append((arc[idx[s0]], arc[idx[i - 1]]))
                s0 = None
        if s0 is not None:
            spans.append((arc[idx[s0]], arc[idx[-1]]))
        jm = float(sum(b - a for a, b in spans))
        txt = ", ".join(f"{a:.0f}-{b:.0f}" for a, b in spans) if spans else "none"
        print(f"{sec:8s} {scored:9.0f} {jm:11.1f} {100*jm/scored:5.1f}% {txt}")
        if spans:
            # how much would have to come off the END to clear the last junction
            worst_tail = max(worst_tail, scored - spans[0][0] if spans else 0.0)

    print(f"\nThe scored window is the CLEAN RUN as clean_mask defined it. Any junction "
          f"listed above\nsits inside a window the study treats as clean lane-keeping road.")


if __name__ == "__main__":
    sys.exit(main())

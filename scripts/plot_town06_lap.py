#!/usr/bin/env python3
"""Plot the Town06 lap over the map: which road the POLICY drives, which PPC bridges.

A route is a design decision, and a design decision that can only be checked by reading
coordinates will not get checked. This draws it.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/plot_town06_lap.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
import numpy as np                                            # noqa: E402
import matplotlib                                             # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                               # noqa: E402
import carla                                                  # noqa: E402
import config as C                                            # noqa: E402

ROUTES = REPO / "pipeline" / "data" / "routes_town06"
OUT = REPO / "docs" / "design" / "town06_lap_control.png"


def main():
    lap = np.load(ROUTES / "lap.npy")
    meta = json.loads((ROUTES / "lap_meta.json").read_text())
    step = meta.get("step_m", 2.0)
    arc = np.arange(len(lap)) * step

    client = carla.Client("127.0.0.1", int(C.PORT)); client.set_timeout(60.0)
    m = client.get_world().get_map()
    road = np.array([[w.transform.location.x, w.transform.location.y]
                     for w in m.generate_waypoints(4.0)
                     if w.lane_type == carla.LaneType.Driving])

    fig, ax = plt.subplots(figsize=(16, 8))
    ax.scatter(road[:, 0], road[:, 1], s=0.6, c="0.85", linewidths=0, label="Town06 roads")

    is_bridge = np.zeros(len(lap), bool)
    for a, b in meta["bridges"]:
        is_bridge |= (arc >= a) & (arc <= b)

    # draw as contiguous runs so the legend has one entry per control mode
    def runs(mask):
        out, i = [], 0
        while i < len(mask):
            if mask[i]:
                j = i
                while j < len(mask) and mask[j]:
                    j += 1
                out.append((i, j)); i = j
            else:
                i += 1
        return out

    for k, (i, j) in enumerate(runs(~is_bridge)):
        ax.plot(lap[i:j, 0], lap[i:j, 1], lw=3.2, c="#1a7f37",
                label="policy drives (scored)" if k == 0 else None, solid_capstyle="round")
    for k, (i, j) in enumerate(runs(is_bridge)):
        ax.plot(lap[i:j, 0], lap[i:j, 1], lw=3.2, c="#d1242f",
                label="pure pursuit bridges (not scored)" if k == 0 else None,
                solid_capstyle="round")
        ax.annotate(f"{meta['bridges'][k][1]-meta['bridges'][k][0]:.0f} m",
                    (lap[(i+j)//2, 0], lap[(i+j)//2, 1]), color="#d1242f",
                    fontsize=9, weight="bold",
                    xytext=(0, 12), textcoords="offset points", ha="center")

    ax.scatter(*lap[0, :2], s=140, marker="o", c="#1a7f37", zorder=5, edgecolor="k")
    ax.annotate("START", lap[0, :2], xytext=(10, 10), textcoords="offset points",
                weight="bold")
    ax.scatter(*lap[-1, :2], s=140, marker="s", c="k", zorder=5)
    ax.annotate("END", lap[-1, :2], xytext=(10, -16), textcoords="offset points",
                weight="bold")

    ax.set_title(f"Town06 lap — {meta['length_m']:.0f} m total, "
                 f"{meta['scored_m']:.0f} m scored ({100*meta['scored_m']/meta['length_m']:.0f}%), "
                 f"{len(meta['bridges'])} PPC bridges")
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    ax.set_aspect("equal"); ax.legend(loc="upper right"); ax.grid(alpha=0.25)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(OUT, dpi=130)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

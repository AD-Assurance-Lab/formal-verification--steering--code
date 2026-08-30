#!/usr/bin/env python3
"""One-time: trace and cache the eastbound/westbound reference centerlines."""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config as C
import carla_env as env
from route import build_route, save_route, ROUTES_DIR

# Sections, not a hardcoded pair (Town06 has six; Town04 has its two directions).
SPAWNS = C.SPAWNS


def main():
    client = env.connect()
    world = env.load_town04(client)
    world_map = world.get_map()

    fig, ax = plt.subplots(figsize=(7, 7))
    for d, spawn in SPAWNS.items():
        route = build_route(world_map, spawn)
        length = sum(math.hypot(*(route[i + 1] - route[i])) for i in range(len(route) - 1))
        save_route(d, route)
        print(f"{d}: {len(route)} pts, {length:.0f} m -> {os.path.join(ROUTES_DIR, d+'.npy')}")
        ax.plot(route[:, 0], route[:, 1], label=d, lw=1.5)
        ax.scatter([spawn["x"]], [spawn["y"]], marker="*", s=120)
    ax.axis("equal"); ax.legend(); ax.set_title("Reference routes (intended centerlines)")
    os.makedirs(C.RESULTS_DIR, exist_ok=True)
    fig.savefig(os.path.join(C.RESULTS_DIR, "reference_routes.png"), dpi=110)
    print("saved reference_routes.png")


if __name__ == "__main__":
    main()

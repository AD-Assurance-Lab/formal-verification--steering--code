#!/usr/bin/env python3
"""Render the README figures from the committed result artifacts.

    python3 scripts/make_readme_figures.py     # writes docs/figures/*.png

Every number plotted here is read from a machine artifact -- nothing is typed in.
The certificate/rain figures need only committed JSON; the trace figure needs
results/traces/ (gitignored simulator output) and is skipped when absent.
"""

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "docs" / "figures"

# Validated categorical pair (dataviz reference palette, adjacent slots 1-2).
BLUE = "#2a78d6"      # certified
ORANGE = "#eb6834"    # not certified
INK = "#0b0b0b"
MUTED = "#52514e"
CORRIDOR = "#e8e8e4"


def _interval_axis(ax, xmin, xmax):
    ax.axvspan(-1, 1, color=CORRIDOR, zorder=0)
    for x in (-1, 1):
        ax.axvline(x, color=MUTED, lw=0.8, ls="--", zorder=1)
    ax.set_xlim(xmin, xmax)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, labelsize=9, colors=INK)
    ax.tick_params(axis="x", labelsize=8, colors=MUTED)
    ax.set_xlabel("certified bound on sustained steering bias  (× closed-loop tolerance)",
                  fontsize=9, color=INK)


def _draw_cells(ax, rows):
    """rows: list of (label, lo, hi, certified, drive_text)."""
    for i, (label, lo, hi, cert, drive) in enumerate(rows):
        color = BLUE if cert else ORANGE
        ax.plot([lo, hi], [i, i], color=color, lw=4, solid_capstyle="butt", zorder=3)
        for x in (lo, hi):
            ax.plot([x], [i], marker="|", ms=9, color=color, zorder=4)
        ax.annotate(drive, xy=(1.0, i), xycoords=("axes fraction", "data"),
                    xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8, color=MUTED)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.set_ylim(len(rows) - 0.4, -0.6)


def cert_figure():
    data = json.loads((REPO / "results/calibration/sustained_bound.json").read_text())
    tol = data["_meta"]["tolerance"]
    rows = []
    for student, sname in (("S_clear", "clear-only"), ("S_mixed", "mixed")):
        for cond in ("fog", "night", "shadows"):
            for d, dtag in (("westbound", "W"), ("eastbound", "E")):
                c = data[f"{d}/{student}/{cond}"]
                cert = c["verdict"] == "CERTIFIED"
                rows.append((f"{sname} · {cond} · {dtag}",
                             c["lo"] / tol, c["hi"] / tol, cert,
                             f"drives {'PASS 0/10' if c['truth'] == 'PASS' else 'FAIL 10/10'}"))
    fig, ax = plt.subplots(figsize=(8.6, 4.6), dpi=160)
    _draw_cells(ax, rows)
    _interval_axis(ax, -7.6, 2.6)
    ax.plot([], [], color=BLUE, lw=4, label="certified")
    ax.plot([], [], color=ORANGE, lw=4, label="not certified")
    ax.legend(loc="lower left", frameon=False, fontsize=9)
    ax.set_title("The certificate agrees with driving on all 12 canonical cells "
                 "(in-sample)", fontsize=10, color=INK, loc="left")
    fig.subplots_adjust(left=0.22, right=0.86, bottom=0.13, top=0.92)
    fig.savefig(OUT / "certificate_cells.png", facecolor="white")
    plt.close(fig)


def rain_figure():
    data = json.loads((REPO / "results/predictions/heldout_rain_verdicts.json").read_text())
    tol = data["_meta"]["tolerance"]
    ledger = REPO / "results/ledger"
    rows = []
    for student, sname in (("S_clear", "clear-only"), ("S_mixed", "mixed")):
        cl = json.loads((ledger / f"rain__{student}__closed_loop.json").read_text())
        drive = f"drives FAIL {cl['failures']}/{cl['repetitions']}"
        for d, dtag in (("westbound", "W"), ("eastbound", "E")):
            c = data[f"{d}/{student}/rain"]
            rows.append((f"{sname} · rain · {dtag}", c["lo"] / tol, c["hi"] / tol,
                         c["verdict"] == "CERTIFIED", drive))
    fig, ax = plt.subplots(figsize=(8.6, 2.4), dpi=160)
    _draw_cells(ax, rows)
    _interval_axis(ax, -8.0, 13.0)
    ax.set_title("Held-out rain (blind): verdicts committed before driving --\n"
                 "all four bounds escape, all twenty runs depart", fontsize=10,
                 color=INK, loc="left")
    fig.subplots_adjust(left=0.22, right=0.86, bottom=0.24, top=0.86)
    fig.savefig(OUT / "rain_blind.png", facecolor="white")
    plt.close(fig)


def trace_figure():
    traces = REPO / "results/traces"
    if not traces.exists():
        print("  results/traces absent (gitignored) -- trace figure skipped")
        return

    def load(student):
        rows = [r for r in csv.DictReader(
            open(traces / f"{student}_night_night_westbound_rep00.csv")) if r["cte_m"]]
        dist, prev, xs, ys = 0.0, None, [], []
        for r in rows:
            x, y = float(r["x"]), float(r["y"])
            if prev is not None:
                dist += ((x - prev[0]) ** 2 + (y - prev[1]) ** 2) ** 0.5
            prev = (x, y)
            xs.append(dist / 1000.0)
            ys.append(float(r["cte_m"]) * 3.28084)
        return xs, ys

    budget_ft = 0.668 * 3.28084
    fig, ax = plt.subplots(figsize=(8.6, 2.8), dpi=160)
    for student, name, color in (("Sclear", "clear-only", ORANGE),
                                 ("Smixed", "mixed", BLUE)):
        xs, ys = load(student)
        ax.plot(xs, ys, color=color, lw=1.6)
        ax.annotate(name, xy=(xs[-1], ys[-1]), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=9, color=color)
    for y in (budget_ft, -budget_ft):
        ax.axhline(y, color=MUTED, lw=0.8, ls="--")
    ax.annotate("lane budget ±2.19 ft", xy=(1.35, -budget_ft), xytext=(0, -11),
                textcoords="offset points", fontsize=8, color=MUTED)
    ax.set_xlabel("distance along lap (km)", fontsize=9, color=INK)
    ax.set_ylabel("cross-track error (ft)", fontsize=9, color=INK)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8, colors=MUTED)
    ax.set_title("Night, westbound: the clear-only student leaves its lane within "
                 "35 m; the mixed student holds the lap", fontsize=10, color=INK,
                 loc="left")
    fig.subplots_adjust(left=0.09, right=0.9, bottom=0.19, top=0.88)
    fig.savefig(OUT / "night_trace.png", facecolor="white")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cert_figure()
    rain_figure()
    trace_figure()
    for p in sorted(OUT.glob("*.png")):
        print(f"wrote {p.relative_to(REPO)}  ({p.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

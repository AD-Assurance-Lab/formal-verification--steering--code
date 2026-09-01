#!/usr/bin/env python3
"""Rename the `shadows` condition to `low_sun` in Town06's collected data.

    python3 scripts/migrate_shadows_to_low_sun.py            # dry run, prints the plan
    python3 scripts/migrate_shadows_to_low_sun.py --apply

PROTOCOL.md's frozen section has always said "clear, fog, night, low sun". The code key
said "shadows", and by the protocol's first rule that makes the code wrong. The name also
described something that does not happen: it implies the road is partly occluded, and at
Town06's 5 degrees the whole scene is uniformly dark. Measured on the lap training frames,
mean brightness of the network's input is clear 0.1371, fog 0.3319, night 0.0897,
low sun 0.0401 -- low sun renders DARKER THAN NIGHT here.

WHAT THIS DOES NOT TOUCH. Town04's artifacts keep the old key: its certificate is
pre-registered under standing rule 1, and rewriting a key inside it would place its commit
after the drives it predicted. `carla_env.canonical_condition` reads both names, so those
artifacts stay readable forever. Only Town06's not-yet-reported data is migrated.

RUN IT AT A STAGE BOUNDARY, never mid-round: dagger.py builds round subdirectories from
the weather name, so renaming under a live collector splits a round across two names.
"""
import argparse
import csv
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "pipeline" / "data"
OLD, NEW = "shadows", "low_sun"


def plan():
    dirs, manifests = [], []
    for base in sorted(DATA.glob("*t06lap*")):
        if not base.is_dir():
            continue
        for d in sorted(base.rglob(f"{OLD}*")):
            if d.is_dir():
                dirs.append(d)
        for m in sorted(base.rglob("manifest.csv")):
            try:
                rows = list(csv.DictReader(m.open()))
            except Exception:
                continue
            n = sum(1 for r in rows if r.get("weather") == OLD or
                    str(r.get("image", "")).startswith(f"{OLD}"))
            if n:
                manifests.append((m, n, len(rows)))
    return dirs, manifests


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    dirs, manifests = plan()
    print(f"  directories to rename ({len(dirs)}):")
    for d in dirs:
        print(f"    {d.relative_to(REPO)}  ->  {d.name.replace(OLD, NEW, 1)}")
    print(f"  manifests to rewrite ({len(manifests)}):")
    for m, n, tot in manifests:
        print(f"    {m.relative_to(REPO)}  {n}/{tot} rows")
    if not args.apply:
        print("\n  DRY RUN. Re-run with --apply at a stage boundary, not mid-round.")
        return 0

    # Deepest first, so renaming a parent never invalidates a child's path.
    for d in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        tgt = d.with_name(d.name.replace(OLD, NEW, 1))
        if tgt.exists():
            print(f"  REFUSING: {tgt} already exists"); return 1
        d.rename(tgt)
    for m, _, _ in manifests:
        rows = list(csv.DictReader(m.open()))
        fields = rows[0].keys() if rows else []
        for r in rows:
            if r.get("weather") == OLD:
                r["weather"] = NEW
            if str(r.get("image", "")).startswith(f"{OLD}"):
                r["image"] = r["image"].replace(OLD, NEW, 1)
        tmp = m.with_suffix(".csv.tmp")
        with tmp.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(fields))
            w.writeheader()
            w.writerows(rows)
        tmp.replace(m)

    # Verify: no frame the manifest names is missing after the rename.
    missing = 0
    for m, _, _ in manifests:
        base = m.parent
        for r in csv.DictReader(m.open()):
            if not (base / r["image"]).exists():
                missing += 1
    print(f"  migrated. manifest rows pointing at a missing frame: {missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())

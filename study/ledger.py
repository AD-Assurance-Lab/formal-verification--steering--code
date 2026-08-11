"""The executable smell test.

    python -m study.ledger                 print the ledger, exit nonzero on contradiction
    python -m study.ledger --check-order   verify verdicts were committed before their
                                           closed-loop counterparts (the blind protocol)

A result that contradicts a pre-registered cell is a bug until proven otherwise. This
module makes that checkable instead of remembered.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from study.design import (
    AGREES,
    CONDITIONS,
    INSTRUMENTS,
    MIN_CLOSED_LOOP_REPS,
    STUDENTS,
    VERDICTS,
    cells,
    expected,
)

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "ledger"


def cell_path(condition, student, instrument):
    return RESULTS_DIR / f"{condition}__{student}__{instrument}.json"


def load(condition, student, instrument):
    """Load a recorded result, or None if the cell is still pending."""
    path = cell_path(condition, student, instrument)
    if not path.exists():
        return None
    with open(path) as fh:
        return json.load(fh)


def problems_with(result, condition, student, instrument):
    """Everything wrong with one recorded cell. Empty list means the cell is sound."""
    found = []
    verdict = result.get("verdict")

    if verdict not in VERDICTS[instrument]:
        found.append(f"verdict {verdict!r} is not one of {VERDICTS[instrument]}")
        return found

    want = expected(student, condition, instrument)
    if verdict != want and verdict != "UNKNOWN":
        found.append(f"CONTRADICTS pre-registered {want}")

    if instrument == "closed_loop":
        reps = result.get("repetitions", 0)
        if reps < MIN_CLOSED_LOOP_REPS:
            found.append(f"only {reps} repetitions, need >= {MIN_CLOSED_LOOP_REPS}")

    # A contradiction may be accepted only once its causes have been ruled out in writing.
    if any(p.startswith("CONTRADICTS") for p in found) and result.get("disposition"):
        found = [p for p in found if not p.startswith("CONTRADICTS")]
        found.append("contradiction, DISPOSITIONED")

    return found


def unsound_cells(rows):
    """Cells where verification called something safe that closed loop then failed.

    This is the one failure mode that invalidates the tool rather than the experiment,
    so it is checked across instruments rather than per cell.
    """
    out = []
    for cond in CONDITIONS:
        for student in STUDENTS:
            cl = load(cond.name, student, "closed_loop")
            ve = load(cond.name, student, "verify")
            if not cl or not ve:
                continue
            if ve.get("verdict") == "CERTIFIED" and cl.get("verdict") == "FAIL":
                out.append(f"{cond.name}/{student}: certified safe, closed loop FAILED")
    return out


def check_order():
    """The blind protocol: a verification verdict must be committed to git before the
    closed-loop result for the same cell exists. Postdiction is not prediction."""
    violations = []
    for cond in CONDITIONS:
        for student in STUDENTS:
            v_path = cell_path(cond.name, student, "verify")
            c_path = cell_path(cond.name, student, "closed_loop")
            if not (v_path.exists() and c_path.exists()):
                continue
            v_time = _added_at(v_path)
            c_time = _added_at(c_path)
            if v_time is None or c_time is None:
                violations.append(f"{cond.name}/{student}: not committed, order unverifiable")
            elif v_time > c_time:
                violations.append(
                    f"{cond.name}/{student}: verification committed AFTER closed loop"
                )
    return violations


def _added_at(path):
    """Unix timestamp of the commit that added `path`, or None if uncommitted."""
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%ct", "--", str(path)],
            capture_output=True, text=True, check=True, cwd=path.parent,
        ).stdout.split()
        return int(out[-1]) if out else None
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None


def render():
    """Print the ledger. Returns the list of problems found."""
    all_problems = []
    width = max(len(c.name) for c in CONDITIONS)

    header = f"{'condition':<{width}}  "
    for student in STUDENTS:
        for instrument in INSTRUMENTS:
            header += f"{student + '/' + instrument:<26}"
    print(header)
    print("-" * len(header))

    for cond in CONDITIONS:
        line = f"{cond.name:<{width}}  "
        for student in STUDENTS:
            for instrument in INSTRUMENTS:
                result = load(cond.name, student, instrument)
                if result is None:
                    line += f"{'PENDING':<26}"
                    continue
                found = problems_with(result, cond.name, student, instrument)
                mark = result["verdict"] if not found else f"{result['verdict']} <!>"
                line += f"{mark:<26}"
                all_problems += [f"{cond.name}/{student}/{instrument}: {p}" for p in found]
        if cond.status != "active":
            line += f"  ({cond.status})"
        print(line)

    all_problems += unsound_cells(None)
    return all_problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-order", action="store_true",
                        help="verify verdicts preceded their closed-loop counterparts")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print()
    problems = render()
    print()

    total = sum(1 for _ in cells())
    filled = sum(1 for c, s, i in cells() if load(c, s, i) is not None)
    print(f"{filled}/{total} cells recorded")

    if args.check_order:
        problems += check_order()

    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        print("\nA result that contradicts a ledger cell is a bug until proven otherwise.")
        print("Do not write it up as a finding. See CLAUDE.md.")
        return 1

    print("no contradictions")
    return 0


if __name__ == "__main__":
    sys.exit(main())

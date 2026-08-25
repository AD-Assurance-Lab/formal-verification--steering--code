"""The executable smell test.

    python -m study.ledger                 print the ledger, exit nonzero on NEW problems
    python -m study.ledger --check-order   also verify verdicts were committed before their
                                           closed-loop counterparts (the blind protocol)

A result that contradicts a pre-registered cell is a bug until proven otherwise. This
module makes that checkable instead of remembered.

Two tiers, so a new violation is never one more line in a wall of familiar red:

  PROBLEMS   exit 1. Anything unexplained: a fresh contradiction, a missing or
             uncommitted artifact, an order violation, an unsound certificate.
  DISPOSITIONED  exit 0, printed as warnings. A contradiction whose cell carries a
             `disposition` key naming a section that actually exists in
             docs/DISPOSITIONS.md. The disposition is written by a person, after the
             candidate causes have been ruled out in writing -- adding the key without
             the write-up defeats the tool and shows up in review.

The ledger covers THREE instruments (D-12 closed the gap where the paper's own
instrument had no column):

  era-1 canonical cells   results/ledger/{cond}__{student}__{closed_loop,verify}.json
                          The 2026-08-11/12 full-lap campaign and the retired
                          per-frame-median verifier. Historical record; never edited.
  final campaign          design.FINAL_CLOSED_LOOP -> the open-road (0-2861 m)
                          closed-loop cells the paper reports (F28/D-14 amendment).
  sustained certificate   results/calibration/sustained_bound.json, the F34-F37
                          instrument (in-sample: computed after the driving).
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from study.design import (
    CERT_DISPOSITIONS,
    CONDITIONS,
    FINAL_CLOSED_LOOP,
    INSTRUMENTS,
    MIN_CLOSED_LOOP_REPS,
    STUDENTS,
    SUSTAINED_BOUND_REL,
    SUSTAINED_CONDITIONS,
    VERDICTS,
    cells,
    expected,
)

REPO = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO / "results" / "ledger"
DISPOSITIONS_MD = REPO / "docs" / "DISPOSITIONS.md"


# ── artifact access ──────────────────────────────────────────────────────────

def cell_path(condition, student, instrument):
    return RESULTS_DIR / f"{condition}__{student}__{instrument}.json"


def load(condition, student, instrument):
    """Load a recorded canonical cell, or None if the cell is still pending."""
    return _load_json(cell_path(condition, student, instrument))


def load_final(condition, student):
    """Load the FINAL-campaign closed-loop cell for a pair, or None."""
    stem = FINAL_CLOSED_LOOP.get((condition, student))
    if stem is None:
        return None
    return _load_json(RESULTS_DIR / f"{stem}__closed_loop.json")


def _load_json(path):
    if not path.exists():
        return None
    with open(path) as fh:
        return json.load(fh)


def known_dispositions():
    """The D-numbers that actually have a written record."""
    if not DISPOSITIONS_MD.exists():
        return set()
    return set(re.findall(r"^## (D-\d+)", DISPOSITIONS_MD.read_text(), re.MULTILINE))


# ── per-cell checks ──────────────────────────────────────────────────────────

def problems_with(result, condition, student, instrument, dispositions=None):
    """Everything wrong with one recorded cell, as (level, message) pairs.

    level is "error" (new problem, fails the run) or "warn" (dispositioned)."""
    dispositions = known_dispositions() if dispositions is None else dispositions
    found = []
    verdict = result.get("verdict")

    if verdict not in VERDICTS[instrument]:
        found.append(("error", f"verdict {verdict!r} is not one of {VERDICTS[instrument]}"))
        return found

    want = expected(student, condition, instrument)
    if verdict != want and verdict != "UNKNOWN":
        tag = result.get("disposition")
        if tag and tag in dispositions:
            found.append(("warn", f"contradicts pre-registered {want}; dispositioned {tag}"))
        elif tag:
            found.append(("error",
                          f"CONTRADICTS pre-registered {want}, and disposition {tag!r} "
                          f"names no section of docs/DISPOSITIONS.md"))
        else:
            found.append(("error", f"CONTRADICTS pre-registered {want}"))

    if instrument == "closed_loop":
        reps = result.get("repetitions", 0)
        if reps < MIN_CLOSED_LOOP_REPS:
            found.append(("error",
                          f"only {reps} repetitions, need >= {MIN_CLOSED_LOOP_REPS}"))

    return found


def unsound_cells():
    """Era-1 cells where verification called something safe that closed loop failed."""
    out = []
    for cond in CONDITIONS:
        for student in STUDENTS:
            cl = load(cond.name, student, "closed_loop")
            ve = load(cond.name, student, "verify")
            if not cl or not ve:
                continue
            if ve.get("verdict") == "CERTIFIED" and cl.get("verdict") == "FAIL":
                if ve.get("vacuous"):
                    # A vacuous cell makes NO safety claim: the clear disturbance box
                    # has zero width, so CERTIFIED means only "the network agrees with
                    # itself at the nominal frame". The closed-loop contradiction is
                    # reported by problems_with; this is not a soundness violation.
                    out.append(("warn",
                                f"{cond.name}/{student}: closed loop FAILED and the "
                                f"verify cell is VACUOUS (asserts nothing; see the "
                                f"closed-loop cell's own entry)"))
                    continue
                out.append(("error",
                            f"{cond.name}/{student}: certified safe, closed loop FAILED"))
    return out


# ── the sustained-bias certificate (third instrument) ────────────────────────

def sustained_certificates():
    """Per (condition, student): the collapsed certificate verdict and its directions.

    NOT CERTIFIED (certify_heldout's vocabulary: it loads no truth table, so it
    cannot claim FALSIFIED against a known outcome) maps to FALSIFIED for
    agreement purposes."""
    certs = {}
    data = _load_json(REPO / SUSTAINED_BOUND_REL)
    for key, cell in (data or {}).items():
        if key.startswith("_"):
            continue
        direction, student, condition = key.split("/")
        entry = certs.setdefault((condition, student),
                                 dict(dirs={}, source=SUSTAINED_BOUND_REL))
        entry["dirs"][direction] = cell["verdict"]
    for entry in certs.values():
        vs = {("FALSIFIED" if v == "NOT CERTIFIED" else v) for v in entry["dirs"].values()}
        if "FALSIFIED" in vs:
            entry["verdict"] = "FALSIFIED"
        elif vs == {"CERTIFIED"} and len(entry["dirs"]) == 2:
            entry["verdict"] = "CERTIFIED"
        else:
            entry["verdict"] = "UNKNOWN"
    return certs


def final_campaign_problems(dispositions):
    """Check the final campaign: cells present, expectations, certificate soundness."""
    found = []
    certs = sustained_certificates()
    for cond in CONDITIONS:
        for student in STUDENTS:
            where = f"final {cond.name}/{student}"
            cl = load_final(cond.name, student)
            if cl is None:
                found.append(("error", f"{where}: closed-loop cell "
                              f"{FINAL_CLOSED_LOOP.get((cond.name, student))!r} missing"))
                continue
            for level, msg in problems_with(cl, cond.name, student, "closed_loop",
                                            dispositions):
                found.append((level, f"{where}/closed_loop: {msg}"))

            cert = certs.get((cond.name, student))
            if cond.name == "clear":
                continue          # no certificate cell: clear is the vacuous nominal
            if cert is None:
                found.append(("error", f"{where}: no sustained-certificate cell"))
                continue
            want = expected(student, cond.name, "verify")
            if cert["verdict"] != want and cert["verdict"] != "UNKNOWN":
                tag = CERT_DISPOSITIONS.get((cond.name, student))
                if tag and tag in dispositions:
                    found.append(("warn", f"{where}/certificate: contradicts "
                                  f"pre-registered {want}; dispositioned {tag}"))
                else:
                    found.append(("error", f"{where}/certificate: CONTRADICTS "
                                  f"pre-registered {want}"))
            # The alarm that matters most: certified safe, then failed the drive.
            if cert["verdict"] == "CERTIFIED" and cl.get("verdict") == "FAIL":
                found.append(("error", f"{where}: CERTIFIED by the sustained "
                              f"certificate, closed loop FAILED (unsound)"))
    return found


# ── git plumbing for the order check ─────────────────────────────────────────

def _git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              check=True, cwd=REPO).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _add_commit(path):
    """(hash, unix_time) of the commit that FIRST added `path`, or None."""
    out = _git("log", "--diff-filter=A", "--format=%H %ct", "--", str(path))
    if not out or not out.split():
        return None
    h, t = out.splitlines()[-1].split()
    return (h, int(t))


def _touch_commits(path):
    """All commits touching `path`, newest first, as (hash, unix_time)."""
    out = _git("log", "--format=%H %ct", "--", str(path))
    if not out:
        return []
    return [(l.split()[0], int(l.split()[1])) for l in out.splitlines() if l.strip()]


def _is_ancestor(a, b):
    """True if commit a is an ancestor of commit b, None if git cannot say."""
    try:
        r = subprocess.run(["git", "merge-base", "--is-ancestor", a, b],
                           capture_output=True, cwd=REPO)
        return r.returncode == 0 if r.returncode in (0, 1) else None
    except FileNotFoundError:
        return None


def _ordered_before(first, second):
    """Is add-commit `first` ordered strictly before add-commit `second`?

    Ancestry is the primary evidence (committer dates are forgeable and rebases
    rewrite them); timestamps are the fallback for histories ancestry cannot order."""
    (fh, ft), (sh, st) = first, second
    if fh == sh:
        return "same-commit"
    anc = _is_ancestor(fh, sh)
    if anc is True:
        return True
    if anc is False and _is_ancestor(sh, fh):
        return False
    return ft < st


def check_order(dispositions=None):
    """The blind protocol, checked against git, as (level, message) pairs.

    A verdict must be committed before the corresponding closed-loop result exists.
    Postdiction is not prediction. Beyond the original ordering test this also fails
    on the holes an adversarial audit walked through: a closed loop with NO committed
    verdict (silently skipped before), a verdict file REWRITTEN after the run (only
    the first add was checked before), verdict and result in the SAME commit, and
    result files with no git anchor at all."""
    dispositions = known_dispositions() if dispositions is None else dispositions
    found = []

    def _order_pair(label, v_path, c_path):
        v_add, c_add = _add_commit(v_path), _add_commit(c_path)
        if v_add is None or c_add is None:
            found.append(("error", f"{label}: not committed, order unverifiable"))
            return
        # An order violation with a written disposition stays visible as a warning:
        # e.g. the era-1 S_mixed verify cells were never blind (D-12 addendum) and the
        # record says so rather than pretending otherwise.
        cell_tag = (_load_json(v_path) or {}).get("disposition")
        v_level = "warn" if cell_tag and cell_tag in dispositions else "error"
        v_suffix = f"; dispositioned {cell_tag}" if v_level == "warn" else ""
        order = _ordered_before(v_add, c_add)
        if order == "same-commit":
            found.append((v_level, f"{label}: verdict and closed loop added in the "
                          f"SAME commit -- order unverifiable{v_suffix}"))
        elif order is False:
            found.append((v_level, f"{label}: verification committed AFTER closed "
                          f"loop{v_suffix}"))
        # A verdict rewritten after the outcome was known is indistinguishable from
        # verdict laundering unless a person has dispositioned it.
        touches = _touch_commits(v_path)
        rewrites = [h for (h, t) in touches
                    if h != v_add[0] and _ordered_before(c_add, (h, t)) in (True,)]
        if rewrites:
            cell = _load_json(v_path) or {}
            tag = cell.get("disposition")
            level = "warn" if tag and tag in dispositions else "error"
            found.append((level, f"{label}: verdict file modified after the closed-loop "
                          f"run was recorded ({len(rewrites)} commit(s))"
                          + (f"; dispositioned {tag}" if level == "warn" else "")))

    # Era-1 canonical pairs.
    for cond in CONDITIONS:
        for student in STUDENTS:
            v_path = cell_path(cond.name, student, "verify")
            c_path = cell_path(cond.name, student, "closed_loop")
            if not c_path.exists():
                continue
            if not v_path.exists():
                found.append(("error", f"{cond.name}/{student}: closed loop recorded "
                              f"with NO committed verdict -- order unverifiable"))
                continue
            _order_pair(f"{cond.name}/{student}", v_path, c_path)

    # Provenance timestamps (recorded by closed_loop_ledger going forward): the verdict
    # commit must precede the RUN, not merely the result commit.
    for cond in CONDITIONS:
        for student in STUDENTS:
            cl = load_final(cond.name, student)
            started = (cl or {}).get("provenance", {}).get("run_started")
            v_add = _add_commit(cell_path(cond.name, student, "verify"))
            if started and v_add:
                import datetime
                run_t = datetime.datetime.fromisoformat(started).timestamp()
                if v_add[1] > run_t:
                    found.append(("error", f"{cond.name}/{student}: verdict committed "
                                  f"after the closed-loop run STARTED"))
    return found


def coverage_problems():
    """Result files the ledger would otherwise never look at.

    V1 of the audit: ~60 artifacts, including the headline results, lived outside the
    20 canonical filenames and were invisible to this tool. Every file in
    results/ledger must now be canonical, a registered final-campaign cell, or a
    variant/diagnostic cell (the `___token` convention); anything untracked has no
    git anchor and is reported until committed."""
    found = []
    canonical = {cell_path(c, s, i).name for c, s, i in cells()}
    final = {f"{stem}__closed_loop.json" for stem in FINAL_CLOSED_LOOP.values()}
    variant = re.compile(r"^[a-z]+___[A-Za-z0-9_.-]+__(closed_loop|verify)\.json$")

    n_variant = 0
    for path in sorted(RESULTS_DIR.glob("*.json")):
        if path.name in canonical or path.name in final:
            continue
        if variant.match(path.name):
            n_variant += 1
            continue
        found.append(("warn", f"unrecognised file in results/ledger: {path.name}"))

    status = _git("status", "--porcelain", "--", str(RESULTS_DIR))
    for line in (status or "").splitlines():
        if line.startswith("??"):
            found.append(("error", f"UNTRACKED result file (no git anchor): "
                          f"{line[3:].strip()}"))

    p = REPO / SUSTAINED_BOUND_REL
    if not p.exists():
        found.append(("error", f"certificate artifact missing: {SUSTAINED_BOUND_REL}"))
    elif _add_commit(p) is None:
        found.append(("error", f"certificate artifact not committed: {SUSTAINED_BOUND_REL}"))
    return found


# ── rendering ────────────────────────────────────────────────────────────────

def render(dispositions):
    """Print both ledgers. Returns the list of (level, message) problems found."""
    all_problems = []
    width = max(len(c.name) for c in CONDITIONS)

    print("ERA-1 CANONICAL (full-lap protocol, 2026-08-11/12; historical record)")
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
                found = problems_with(result, cond.name, student, instrument,
                                      dispositions)
                mark = result["verdict"]
                if any(l == "error" for l, _ in found):
                    mark += " <!>"
                elif found:
                    mark += " <d>"       # dispositioned
                line += f"{mark:<26}"
                all_problems += [(l, f"{cond.name}/{student}/{instrument}: {m}")
                                 for l, m in found]
        if cond.status != "active":
            line += f"  ({cond.status})"
        print(line)
    all_problems += unsound_cells()

    print("\nFINAL CAMPAIGN (open road 0-2861 m, F28/D-14) x SUSTAINED CERTIFICATE")
    header = (f"{'condition':<{width}}  "
              + "".join(f"{s + '/cert':<17}{s + '/drive':<15}" for s in STUDENTS))
    print(header)
    print("-" * len(header))
    certs = sustained_certificates()
    agree = total = 0
    for cond in CONDITIONS:
        line = f"{cond.name:<{width}}  "
        for student in STUDENTS:
            cert = certs.get((cond.name, student))
            cl = load_final(cond.name, student)
            cv = "--" if cond.name == "clear" else (cert["verdict"] if cert else "PENDING")
            dv = cl["verdict"] if cl else "PENDING"
            if cert and cl and cond.name != "clear":
                total += 1
                ok = ((cert["verdict"], cl["verdict"]) in
                      {("CERTIFIED", "PASS"), ("FALSIFIED", "FAIL")})
                agree += ok
                dv += "  ok" if ok else "  MISMATCH"
            line += f"{cv:<17}{dv:<15}"
        print(line)
    if total:
        print(f"\ncertificate/driving agreement: {agree}/{total} "
              f"(in-sample, sustained-failure scope only -- see STATE_OF_PLAY 0b)")
    all_problems += final_campaign_problems(dispositions)
    return all_problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-order", action="store_true",
                        help="verify verdicts preceded their closed-loop counterparts")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    dispositions = known_dispositions()

    print()
    problems = render(dispositions)
    print()

    total = sum(1 for _ in cells())
    filled = sum(1 for c, s, i in cells() if load(c, s, i) is not None)
    print(f"{filled}/{total} era-1 cells recorded")

    problems += coverage_problems()
    if args.check_order:
        problems += check_order(dispositions)

    errors = [m for l, m in problems if l == "error"]
    warns = [m for l, m in problems if l == "warn"]

    if warns:
        print(f"\nDISPOSITIONED ({len(warns)}) -- explained in docs/DISPOSITIONS.md, "
              f"kept visible, not fatal:")
        for m in warns:
            print(f"  ~ {m}")
    if errors:
        print(f"\nPROBLEMS ({len(errors)}):")
        for m in errors:
            print(f"  - {m}")
        print("\nA result that contradicts a ledger cell is a bug until proven otherwise.")
        print("Do not write it up as a finding. See CLAUDE.md.")
        return 1

    print("\nno new problems" + (" (dispositioned warnings above)" if warns else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

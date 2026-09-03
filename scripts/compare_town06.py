#!/usr/bin/env python3
"""Compare the Town06 certificate against the closed-loop ledger. Run LAST.

This is the only tool in the deployment test allowed to see both sides. It refuses to
run unless PROTOCOL R1 holds, because an agreement number computed from a certificate
that was written after the drive is not a prediction and must not be printed as one.

It also refuses to report a bare agreement fraction when every scored cell shares a
verdict. That case measures sensitivity and not specificity -- the withdrawn rain
condition scored 4/4 that way -- and PROTOCOL section 4.2 requires it be said out loud
rather than rounded up into a clean score.

    STUDY_MAP=Town06 python3 scripts/compare_town06.py
"""
import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "scripts"))

from check_order_town06 import require_certificate_committed, first_commit_epoch  # noqa: E402
from study import town06_design as D  # noqa: E402

CERT = REPO / D.CERT_ARTIFACT
LEDGER = REPO / D.LEDGER_SUBDIR

# A-5: a pass-2 comparison runs once per SCOPE, against that scope's own certificate and
# that scope's own re-scoring of the same drives. The scope ledgers are DERIVED from the
# committed traces by score_scopes.py, so R1 is still checked against the drives
# themselves (D.LEDGER_SUBDIR, which TOWN06_PASS scopes) and never against a derived
# artifact whose commit time says nothing about when the vehicle moved.
SCOPE_ARTIFACTS = {
    "full":   (D.CERT_ARTIFACT,
               os.path.join(D.LEDGER_SUBDIR, "scored_full")),
    "capped": (getattr(D, "CAPPED_CERT_ARTIFACT",
                       os.path.join(D.RESULTS_SUBDIR, "certificate_town06_capped.json")),
               os.path.join(D.LEDGER_SUBDIR, "scored_capped")),
}

# Ledger student name -> design student name
# Built from the REGISTRY, not hardcoded. This was a literal map of the 84x28
# checkpoint names; once the students moved to 168x28 nothing matched, every cell
# reported its certificate as MISSING, and the summary announced "agreement 0/6" with
# six CONTRADICTS -- a broken join wearing the costume of a catastrophic result.
import config as C  # noqa: E402
STU = {}
for _nm, _ck, _, _ in C.TOWN06_STUDENTS:
    STU[_ck] = _nm
    STU[C.final_student(_ck)] = _nm
COND_LABEL = {"shadows": "low sun", "low_sun": "low sun"}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return ((c - h) / d, (c + h) / d)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scope", default=None, choices=sorted(SCOPE_ARTIFACTS),
                    help="compare one A-5 scope's ledger against that scope's "
                         "certificate. Omit for the pass-1 comparison, unchanged.")
    args = ap.parse_args()

    global CERT, LEDGER
    cert_rel = D.CERT_ARTIFACT
    if args.scope:
        cert_rel, ledger_rel = SCOPE_ARTIFACTS[args.scope]
        CERT, LEDGER = REPO / cert_rel, REPO / ledger_rel
        if not CERT.exists():
            sys.exit(f"no certificate for scope '{args.scope}' at {cert_rel}")
        if not LEDGER.is_dir():
            sys.exit(f"no '{args.scope}' ledger at {ledger_rel} -- run "
                     f"scripts/score_scopes.py --write first")

    require_certificate_committed()
    cert = json.loads(CERT.read_text())
    cert_t = first_commit_epoch(cert_rel)

    if not LEDGER.is_dir():
        sys.exit("no ledger cells yet -- run scripts/run_town06_ledger.sh")

    rows, violations = [], []
    for fn in sorted(os.listdir(LEDGER)):
        if not fn.endswith("__closed_loop.json"):
            continue
        cond, stu_ck, _ = fn.split("__")
        stu = STU.get(stu_ck, stu_ck)
        d = json.loads((LEDGER / fn).read_text())

        t = first_commit_epoch(os.path.join(D.LEDGER_SUBDIR, fn))
        if t is not None and t <= cert_t:
            violations.append(fn)

        runs = d.get("runs", [])
        n = len(runs)
        fails = sum(1 for r in runs if not r.get("pass", r.get("passed", False)))

        # READ THE CELL'S OWN VERDICT. This recomputed one by majority vote, which turns a
        # VOID cell into a PASS: fog/S_mixed_t06 failed 1 of 3 laps, the ledger correctly
        # marked it VOID under PROTOCOL A-4 -- "if the three laps disagree, that is a BUG
        # until proven otherwise ... a cell whose laps disagree is void, not uncertain" --
        # and this printed "PASS 1/3" and counted it toward the agreement rate.
        #
        # A majority vote over three laps is exactly the "estimate a rate from a small
        # sample" reading A-4 exists to forbid. The aggregator already applied the rule;
        # the comparison's job is to report it, not to re-derive it more loosely.
        drive = d.get("verdict")
        if drive not in ("PASS", "FAIL", "VOID"):
            sys.exit(f"FATAL: {fn} has verdict {drive!r}; expected PASS, FAIL or VOID.")
        lo, hi = wilson(fails, n)

        # The certificate is ONE bound per (student, condition), pooled across the six
        # sections, so its keys are "<student>/<condition>". They used to be
        # "<direction>/<student>/<condition>" and this read k.split("/")[2], which now
        # raises IndexError rather than reporting a mismatch.
        key = f"{stu}/{cond}"
        if cond in D.VACUOUS_CELLS:
            cert_v, note = "CERTIFIED", "vacuous"
        elif key not in cert:
            # A missing entry means the join is broken, not that the prediction was
            # wrong. Reporting it as a disagreement invents a finding out of a bug.
            sys.exit(f"FATAL: no certificate entry for '{key}'.\n"
                     f"  certificate has: {sorted(k for k in cert if not k.startswith('_'))}\n"
                     f"  ledger file gave student '{stu_ck}' -> '{stu}'\n"
                     f"  This is a key mismatch between the certificate and the ledger, "
                     f"not a disagreement between prediction and outcome.")
        else:
            cert_v, note = cert[key]["verdict"], ""
        # A VOID cell agrees with nothing: it is not a measurement of the policy, it is a
        # measurement that the harness produced laps that disagree. Counting it either way
        # would put a number nobody can defend into the agreement rate.
        agree = None if drive == "VOID" else (drive, cert_v) in D.AGREES
        exp_drive, exp_cert = D.expected(stu, cond)
        rows.append(dict(cond=cond, stu=stu, drive=drive, fails=fails, n=n,
                         lo=lo, hi=hi, cert=cert_v, agree=agree, note=note,
                         as_expected=(drive == exp_drive and cert_v == exp_cert)))

    if violations:
        print("PROTOCOL R1 VIOLATED -- these cells were committed at or before the")
        print("certificate, so they are not predictions:")
        for v in violations:
            print(f"    {v}")
        return 1

    print(f"\nTOWN06 DEPLOYMENT TEST -- certificate vs closed loop")
    print(f"  certificate committed before every drive (R1 satisfied)\n")
    hdr = f"  {'condition':10s} {'student':13s} {'driving':16s} {'certificate':15s} {'':6s} pre-reg"
    print(hdr); print("  " + "-" * (len(hdr) - 2))
    scored = [r for r in rows if r["cond"] not in D.VACUOUS_CELLS
              and r["drive"] != "VOID"]
    voided = [r for r in rows if r["drive"] == "VOID"]
    for r in rows:
        lab = COND_LABEL.get(r["cond"], r["cond"])
        rate = f"{r['drive']} {r['fails']}/{r['n']}"
        ci = f"[{r['lo']*100:.0f},{r['hi']*100:.0f}]%"
        # A VOID cell neither agrees nor disagrees: there is no driving verdict to
        # compare against. Printing DISAGREE there would read as evidence against the
        # certificate when it is evidence about the harness.
        mark = "n/a" if r["agree"] is None else ("agree" if r["agree"] else "DISAGREE")
        if r["cond"] in D.VACUOUS_CELLS:
            mark = "vacuous"
        print(f"  {lab:10s} {r['stu']:13s} {rate:9s}{ci:8s} {r['cert']:15s} "
              f"{mark:9s} {'ok' if r['as_expected'] else 'CONTRADICTS'}")

    n_ok = sum(1 for r in scored if r["agree"])
    n = len(scored)
    uniform = len({(r["drive"], r["cert"]) for r in scored}) <= 1

    print(f"\n  agreement on scored cells: {n_ok}/{n}"
          f"   (clear excluded: vacuous by construction"
          + (f"; {len(voided)} VOID cell(s) excluded" if voided else "") + ")")
    for r in voided:
        print(f"    VOID: {r['cond']}/{r['stu']} -- {r['fails']} of {r['n']} laps failed, "
              f"so the laps disagree. Under A-4 that is a BUG until the cause is found "
              f"and written down, not a rate. It is excluded from the agreement, and the "
              f"study is not complete while it stands.")

    if uniform and n:
        print("\n  *** EVERY SCORED CELL SHARES ONE VERDICT PAIR. ***")
        print("  " + D.DEGENERATE_IF_ALL_AGREE)
        print("  Report this as sensitivity, NOT as a discriminating result.")

    contradictions = [r for r in scored if not r["as_expected"]]
    if contradictions:
        print(f"\n  {len(contradictions)} cell(s) contradict the pre-registered "
              f"expectation. Standing rule 2:")
        print("  each is a BUG until a written disposition rules out the candidate "
              "causes.")
        for r in contradictions:
            print(f"    {COND_LABEL.get(r['cond'], r['cond'])}/{r['stu']}: "
                  f"drove {r['drive']}, certificate {r['cert']}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

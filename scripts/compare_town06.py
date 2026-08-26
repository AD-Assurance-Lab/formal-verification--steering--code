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

# Ledger student name -> design student name
STU = {"S_clear_t06_84x28": "S_clear_t06", "S_mixed_t06_84x28_w3": "S_mixed_t06"}
COND_LABEL = {"shadows": "low sun"}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return ((c - h) / d, (c + h) / d)


def main():
    require_certificate_committed()
    cert = json.loads(CERT.read_text())
    cert_t = first_commit_epoch(D.CERT_ARTIFACT)

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
        drive = "FAIL" if fails * 2 >= n else "PASS"
        lo, hi = wilson(fails, n)

        # The certificate is ONE bound per (student, condition), pooled across the six
        # sections, so its keys are "<student>/<condition>". They used to be
        # "<direction>/<student>/<condition>" and this read k.split("/")[2], which now
        # raises IndexError rather than reporting a mismatch.
        key = f"{stu}/{cond}"
        if cond in D.VACUOUS_CELLS:
            cert_v, note = "CERTIFIED", "vacuous"
        elif key not in cert:
            cert_v, note = "MISSING", ""
        else:
            cert_v, note = cert[key]["verdict"], ""
        agree = (drive, cert_v) in D.AGREES
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
    scored = [r for r in rows if r["cond"] not in D.VACUOUS_CELLS]
    for r in rows:
        lab = COND_LABEL.get(r["cond"], r["cond"])
        rate = f"{r['drive']} {r['fails']}/{r['n']}"
        ci = f"[{r['lo']*100:.0f},{r['hi']*100:.0f}]%"
        mark = "agree" if r["agree"] else "DISAGREE"
        if r["cond"] in D.VACUOUS_CELLS:
            mark = "vacuous"
        print(f"  {lab:10s} {r['stu']:13s} {rate:9s}{ci:8s} {r['cert']:15s} "
              f"{mark:9s} {'ok' if r['as_expected'] else 'CONTRADICTS'}")

    n_ok = sum(1 for r in scored if r["agree"])
    n = len(scored)
    uniform = len({(r["drive"], r["cert"]) for r in scored}) <= 1

    print(f"\n  agreement on scored cells: {n_ok}/{n}"
          f"   (clear excluded: vacuous by construction)")

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

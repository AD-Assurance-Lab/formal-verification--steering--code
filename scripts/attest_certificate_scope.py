#!/usr/bin/env python3
"""State the road extent a certificate covers, for certificates written before the
certifier recorded it.

    python3 scripts/attest_certificate_scope.py results/town04_v2/calibration

Both certifiers write `lap_end_m` into `_meta` now, so new certificates say what they
cover. The Town04 redo certificate predates that field, and it is the pre-registered
artifact under standing rule 1 -- regenerating it to add metadata would place its commit
after the drives and break the very ordering the field exists to support.

So the scope is DERIVED instead, from the committed captures the certificate consumed,
and written alongside it. Nothing here is typed by hand: rerun this and it reproduces, or
it disagrees and that is a finding.
"""
import glob
import hashlib
import json
import os
import sys

import numpy as np


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    d = sys.argv[1]
    cert = os.path.join(d, "sustained_bound.json")
    if not os.path.exists(cert):
        print(f"  no certificate at {cert}")
        return 1
    caps = sorted(glob.glob(os.path.join(d, "lap_*.npz")))
    if not caps:
        print(f"  no captures beside {cert}; scope cannot be derived")
        return 1

    spans, requested, digests = {}, {}, {}
    for c in caps:
        z = np.load(c, allow_pickle=True)
        name = os.path.basename(c)
        if "pose_x" in z.files:
            x, y = np.asarray(z["pose_x"], float), np.asarray(z["pose_y"], float)
            spans[name] = round(float(np.hypot(np.diff(x), np.diff(y)).sum()), 1)
        if "length_m_requested" in z.files:
            requested[name] = round(float(z["length_m_requested"]), 1)
        with open(c, "rb") as fh:
            digests[name] = hashlib.sha256(fh.read()).hexdigest()[:16]

    want = sorted(set(requested.values()))
    got = sorted(set(spans.values()))
    out = dict(
        certificate=os.path.relpath(cert),
        derived_by=os.path.relpath(__file__),
        note=("Derived from the committed captures, not recorded by the certifier. "
              "This certificate predates lap_end_m in _meta and is the pre-registered "
              "artifact, so it is not regenerated."),
        lap_end_m=want[0] if len(want) == 1 else want,
        capture_span_m=spans,
        capture_requested_m=requested,
        capture_sha256_16=digests,
        consistent=bool(len(want) == 1 and all(abs(s - want[0]) <= 25.0
                                               for s in spans.values())),
    )
    p = os.path.join(d, "scope.json")
    with open(p, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"  {len(caps)} captures; requested {want}, spanned {got}")
    print(f"  consistent: {out['consistent']}")
    print(f"  wrote {p}")
    return 0 if out["consistent"] else 1


if __name__ == "__main__":
    sys.exit(main())

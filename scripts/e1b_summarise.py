#!/usr/bin/env python3
"""Summarise the E1b bimodal probe against docs/E1B_PREREGISTRATION.md.

Arm A is one process driving N laps; arm B is N processes driving one lap each. CARLA is
restarted before every lap in BOTH, so the only difference is whether the client process
persists -- which is what E5 asked about the screen/gate discrepancy.

Deliberately does not compute a failure rate. Standing rule 3: a cell whose laps disagree
is VOID rather than uncertain, and more laps would turn an identified defect into a
plausible rate and lose it.
"""
import json
import pathlib
import statistics as st

D = pathlib.Path(__file__).resolve().parent.parent / "results" / "town06" / "bimodal"


def laps_of(p):
    return [l for l in list(json.loads(p.read_text())["results"].values())[0]
            if not l.get("error")]


def main():
    a_file = next(D.glob("armA_one_process_*.json"), None)
    A = laps_of(a_file) if a_file else []
    B = []
    for p in sorted(D.glob("armB_proc*.json")):
        B += laps_of(p)

    for name, laps in (("A  (one process)", A), ("B  (fresh process each)", B)):
        if not laps:
            continue
        cte = [l["max_cte_ft"] for l in laps]
        dep = sum(1 for l in laps if l.get("departed"))
        print(f"=== arm {name}: {len(laps)} laps ===")
        print("   " + "  ".join(f"{c:.2f}" for c in cte))
        print(f"   departed {dep}/{len(laps)}   min {min(cte):.2f}  max {max(cte):.2f}")
        print()

    print("=== B1: is the distribution bimodal? ===")
    allc = sorted(l["max_cte_ft"] for l in A + B)
    # cluster by gaps: a gap larger than this splits a cluster
    clusters, cur = [], [allc[0]]
    for x in allc[1:]:
        if x - cur[-1] > 1.0:
            clusters.append(cur); cur = [x]
        else:
            cur.append(x)
    clusters.append(cur)
    print(f"   {len(clusters)} cluster(s) at a 1.0 ft gap threshold:")
    for c in clusters:
        print(f"     n={len(c):2d}  {min(c):6.2f} .. {max(c):6.2f} ft")
    print(f"   -> B1 (predicting exactly 2, nothing between) "
          f"{'held' if len(clusters) == 2 else 'FALSIFIED'}")

    print("\n=== B2: does lap index predict the outcome (arm A)? ===")
    if A:
        idx = [l["rep"] for l in A]
        dep = [1 if l.get("departed") else 0 for l in A]
        n = len(A)
        # point-biserial between index and departure
        if 0 < sum(dep) < n:
            mx, my = st.mean(idx), st.mean(dep)
            num = sum((a - mx) * (b - my) for a, b in zip(idx, dep))
            den = (sum((a - mx) ** 2 for a in idx) * sum((b - my) ** 2 for b in dep)) ** 0.5
            r = num / den if den else 0.0
            print(f"   corr(lap index, departed) = {r:+.3f}")
        first, second = dep[: n // 2], dep[n // 2:]
        print(f"   departures in first half {sum(first)}/{len(first)}, "
              f"second half {sum(second)}/{len(second)}")
        # adjacency: do consecutive laps take the same branch more than chance?
        same = sum(1 for i in range(n - 1) if dep[i] == dep[i + 1])
        print(f"   consecutive laps in the SAME branch: {same}/{n-1}")

    print("\n=== B3: do the arms agree? ===")
    if A and B:
        da = sum(1 for l in A if l.get("departed")); db = sum(1 for l in B if l.get("departed"))
        print(f"   arm A departed {da}/{len(A)}   arm B departed {db}/{len(B)}")
        ca = [l["max_cte_ft"] for l in A]; cb = [l["max_cte_ft"] for l in B]
        print(f"   arm A median {st.median(ca):.2f} ft   arm B median {st.median(cb):.2f} ft")

    print("\n=== the point of the exercise ===")
    print("   This cell is VOID and stays VOID (standing rule 3). The numbers above")
    print("   characterise the mechanism; they are not a failure rate.")


if __name__ == "__main__":
    main()

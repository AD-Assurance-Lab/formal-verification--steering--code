#!/usr/bin/env python3
"""Summarise Q1 -- the learning-rate effect at n = 15.

The analysis is the one DECLARED in docs/Q1_PREREGISTRATION.md, and nothing here is
chosen after seeing a number:

  primary     fog worst-of-3 max|CTE| per seed; two-sided Mann-Whitney on 15 vs 15,
              reported with the Hodges-Lehmann median shift and a distribution-free 95%
              interval. The prereg is explicit that the EFFECT SIZE and the interval are
              the result and the p-value accompanies them -- E2R-F5 put the power here at
              moderate at best.
  secondary   seeds holding fog 3/3 under budget (Fisher); seeds clearing the 1.095 ft
              pass-3 margin gate (Fisher); fog KD p99 median; clear median (the control).
  sensitivity the same primary test on seeds 6-14 ONLY -- entirely new, collected in one
              sweep under one harness. If pooled and new-seeds-only disagree in direction
              or significance, the NEW-SEEDS-ONLY result is the one reported.

VOID cells (>25% lap disagreement) are excluded, never averaged, never re-driven with
more laps (standing rule 3). VOID COUNTS ARE A DECLARED OUTCOME, not an exclusion
footnote: E4 saw 3 VOID cells in lr1e3 and 0 in lr3e4, and an arm that is unmeasurable
more often is worse.

Seeds 0-5 are FOLDED IN from the runs that already drove them. That fold-in was validated
bit-exactly before it was used -- seed 0 of each arm was re-distilled under the Q1 arm
definition and matched by SHA-256 against the existing checkpoint:

    lr1e3  S_mixed_taildet_a0p0_s0    (E2's alpha 0.0 arm, DETERMINISTIC=1)
    lr3e4  S_mixed_depth_d3lr3_s0     (E4's d3@3e-4 arm)

Note lr1e3 resolves to S_mixed_tailDET_a0p0_s0, the PINNED arm, not S_mixed_tail_a0p0_s0
-- E2 ran both, they are different checkpoints, and only the pinned one is comparable.

    python3 scripts/q1_summarise.py
"""
import json
import pathlib
import statistics as st

REPO = pathlib.Path(__file__).resolve().parent.parent
NEW = REPO / "results/town06/lr_confirm"
DEPTH = REPO / "results/town06/depth"
TAILDET = REPO / "results/town06/tail_loss_det"

BUDGET, MARGIN_GATE, VOID_REL = 2.19, 1.095, 0.25
FOLD_SEEDS, NEW_SEEDS = range(6), range(6, 15)
SEEDS = list(range(15))

# arm -> seed -> (dir, drive pattern, kd pattern)
ARMS = {
    "lr1e3": {"fold": (TAILDET, "e2_a0p0_s{s}_{c}.json", "kd_a0p0_s{s}.json"),
              "new": (NEW, "drive_lr1e3_s{s}_{c}.json", "kd_lr1e3_s{s}.json")},
    "lr3e4": {"fold": (DEPTH, "drive_d3lr3_s{s}_{c}.json", "kd_d3lr3_s{s}.json"),
              "new": (NEW, "drive_lr3e4_s{s}_{c}.json", "kd_lr3e4_s{s}.json")},
}


def src(arm, s):
    return ARMS[arm]["fold" if s in FOLD_SEEDS else "new"]


def cell(arm, s, c):
    d, dp, _ = src(arm, s)
    p = d / dp.format(s=s, c=c)
    if not p.exists():
        return None
    laps = [l for l in list(json.loads(p.read_text())["results"].values())[0]
            if not l.get("error")]
    if not laps:
        return {"state": "NO_LAPS"}
    v = [l["max_cte_ft"] for l in laps]
    # An absent measurement is not a passing one, and a cell whose laps disagree is VOID
    # rather than uncertain -- more laps would turn an identified defect into a plausible
    # failure rate and lose it.
    if max(v) > 0 and (max(v) - min(v)) / max(v) > VOID_REL:
        return {"state": "VOID"}
    return {"state": "OK", "hi": max(v), "n": len(laps),
            "held": sum(1 for x in v if x <= BUDGET),
            "gate": sum(1 for x in v if x <= MARGIN_GATE),
            "dep": sum(1 for l in laps if l.get("departed"))}


def kd(arm, s, c="fog"):
    d, _, kp = src(arm, s)
    p = d / kp.format(s=s)
    if not p.exists():
        return None
    return json.loads(p.read_text())["conditions"].get(c, {}).get("p99_abs_err")


def hodges_lehmann(x, y, alpha=0.05):
    """HL median shift (x - y) with a distribution-free 95% interval.

    The interval is the classic Moses/HL construction: order the m*n pairwise differences
    and take the k-th and (mn+1-k)-th, with k from the normal approximation to the
    Wilcoxon rank-sum. Distribution-free, and it does not assume the dispersion is
    anything in particular -- which matters here, where one arm can contain a 37 ft
    departure.
    """
    from scipy.stats import norm
    d = sorted(a - b for a in x for b in y)
    m, n = len(x), len(y)
    if not d:
        return None, None, None
    hl = st.median(d)
    z = norm.ppf(1 - alpha / 2)
    k = int(round(m * n / 2 - z * ((m * n * (m + n + 1) / 12) ** 0.5)))
    k = max(1, min(k, m * n))
    return hl, d[k - 1], d[m * n - k]


def fog_vals(arm, seeds):
    return [x["hi"] for s in seeds
            if (x := cell(arm, s, "fog")) and x.get("state") == "OK"]


def counts(arm, seeds, c="fog"):
    """(held 3/3, cleared the margin gate, measured, VOID) over a seed set."""
    held = gate = n = void = 0
    for s in seeds:
        x = cell(arm, s, c)
        if x is None:
            continue
        if x["state"] != "OK":
            void += x["state"] == "VOID"
            continue
        n += 1
        held += x["held"] == x["n"]
        gate += x["gate"] == x["n"]
    return held, gate, n, void


def table(c, seeds, title):
    print(f"=== {title}: {c}, worst-of-3 max|CTE| (ft) ===")
    print(f"{'arm':>7s}  " + "".join(f"{'s'+str(s):>8s}" for s in seeds) +
          f"{'median':>9s}{'held':>8s}{'gate':>7s}{'VOID':>6s}")
    for arm in ARMS:
        row, vals = "", []
        for s in seeds:
            x = cell(arm, s, c)
            if x is None:
                row += f"{'--':>8s}"
            elif x["state"] != "OK":
                row += f"{x['state']:>8s}"
            else:
                row += f"{x['hi']:7.2f}{'D' if x['dep'] else ' '}"
                vals.append(x["hi"])
        held, gate, n, void = counts(arm, seeds, c)
        med = f"{st.median(vals):9.2f}" if vals else f"{'--':>9s}"
        print(f"{arm:>7s}  {row}{med}{held:>5d}/{n}{gate:>5d}/{n}{void:>6d}")
    print()


def compare(seeds, label):
    from scipy.stats import mannwhitneyu, fisher_exact
    a, b = fog_vals("lr1e3", seeds), fog_vals("lr3e4", seeds)
    print(f"--- {label}: n = {len(a)} (lr1e3) vs {len(b)} (lr3e4), VOID excluded ---")
    if len(a) < 2 or len(b) < 2:
        print("    not enough measured cells yet\n")
        return None
    ma, mb = st.median(a), st.median(b)
    p = mannwhitneyu(a, b, alternative="two-sided")[1]
    hl, lo, hi = hodges_lehmann(a, b)
    ratio = ma / mb if mb else float("inf")
    print(f"    fog median   lr1e3 {ma:.2f}   lr3e4 {mb:.2f}   ratio {ratio:.2f}x")
    print(f"    Hodges-Lehmann shift (lr1e3 - lr3e4)  {hl:+.2f} ft   95% CI "
          f"[{lo:+.2f}, {hi:+.2f}]")
    print(f"    Mann-Whitney two-sided p = {p:.4f}")
    ha, ga, na, _ = counts("lr1e3", seeds)
    hb, gb, nb, _ = counts("lr3e4", seeds)
    fp_h = fisher_exact([[ha, na - ha], [hb, nb - hb]])[1]
    fp_g = fisher_exact([[ga, na - ga], [gb, nb - gb]])[1]
    print(f"    held fog 3/3   {ha}/{na} vs {hb}/{nb}   Fisher p = {fp_h:.4f}")
    print(f"    cleared gate   {ga}/{na} vs {gb}/{nb}   Fisher p = {fp_g:.4f}")
    print()
    return dict(ratio=ratio, p=p, hl=hl, ha=ha, na=na, hb=hb, nb=nb, ga=ga, gb=gb)


def main():
    print("Q1 -- the learning-rate effect at n = 15. "
          f"budget {BUDGET} ft; pass-3 margin gate {MARGIN_GATE} ft")
    print("seeds 0-5 folded in (validated bit-exactly); seeds 6-14 new\n")
    for c in ("fog", "clear"):
        table(c, SEEDS, "pooled, seeds 0-14")

    print("=== fog KD p99 |err| (tolerance 0.0120), no simulator ===")
    for arm in ARMS:
        v = [x for x in (kd(arm, s) for s in SEEDS) if x is not None]
        if v:
            print(f"{arm:>7s}  n={len(v):2d}  median {st.median(v):.4f}  "
                  f"range {min(v):.4f}-{max(v):.4f}")
    print()

    print("=== the declared tests ===")
    pooled = compare(SEEDS, "PRIMARY, pooled seeds 0-14")
    fresh = compare(list(NEW_SEEDS), "SENSITIVITY, new seeds 6-14 only")

    if pooled and fresh:
        print("--- pooled vs new-seeds-only ---")
        same_dir = (pooled["hl"] > 0) == (fresh["hl"] > 0)
        same_sig = (pooled["p"] < 0.05) == (fresh["p"] < 0.05)
        if same_dir and same_sig:
            print("    agree in direction and significance; the pooled result stands.")
        else:
            print("    THEY DISAGREE. The prereg says the new-seeds-only result is the "
                  "one reported,")
            print("    and the disagreement is itself a finding about the fold-in.")
        print()

    if pooled:
        print("=== against the pre-registration ===")
        print(f"  Q1-F1 fog median >= 3x lower : ratio {pooled['ratio']:.2f}x -> "
              f"{'HELD' if pooled['ratio'] >= 3 else 'FALSIFIED'}")
        print(f"  Q1-F2 Mann-Whitney p < 0.05  : p = {pooled['p']:.4f} -> "
              f"{'HELD' if pooled['p'] < 0.05 else 'FALSIFIED'}")
        f3 = pooled["hb"] >= 2 * pooled["ha"] and pooled["gb"] >= 3
        print(f"  Q1-F3 >=2x hold fog, >=3 clear the gate : "
              f"held {pooled['ha']}->{pooled['hb']}, gate {pooled['gb']}/15 -> "
              f"{'HELD' if f3 else 'FALSIFIED'}")
        ca = [x["hi"] for s in SEEDS
              if (x := cell("lr1e3", s, "clear")) and x.get("state") == "OK"]
        cb = [x["hi"] for s in SEEDS
              if (x := cell("lr3e4", s, "clear")) and x.get("state") == "OK"]
        if ca and cb:
            dev = abs(st.median(cb) - st.median(ca)) / st.median(ca)
            print(f"  Q1-F4 clear within 25%       : {st.median(ca):.2f} -> "
                  f"{st.median(cb):.2f} ft ({dev*100:.0f}%) -> "
                  f"{'HELD' if dev <= 0.25 else 'FALSIFIED'}")
        a, b = fog_vals("lr1e3", SEEDS), fog_vals("lr3e4", SEEDS)
        if a and b:
            spread = max(max(a) - min(a), max(b) - min(b))
            gap = abs(st.median(a) - st.median(b))
            print(f"  Q1-F5 seed spread > arm gap  : spread {spread:.2f} vs gap "
                  f"{gap:.2f} ft -> {'HELD' if spread > gap else 'FALSIFIED'}")


if __name__ == "__main__":
    main()

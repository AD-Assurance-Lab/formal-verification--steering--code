#!/usr/bin/env python3
"""Drive named STUDENT checkpoints over the same laps and report them side by side.

    STUDY_MAP=Town06 python3 scripts/compare_student_variants.py \
        --checkpoints S_mixed_t06lap_168x28_w3 S_mixed_t06lap_168x28_w3_dagger_r02 \
        --channels 24,48,48 --fc 96 --reps 3

WHY THIS EXISTS. Two questions about the students have been argued from evidence that was
later discarded, and neither has ever been measured on the corrected harness:

  * T06-F14 removed student DAgger after measuring it as HARMFUL at 168x28
    ("mixed w2 distilled only 6/6, after 4 DAgger rounds 3/6"). T06-F25 pointed out that
    A-2 discarded the data that finding rests on, and restored the stage -- explicitly
    asking for the comparison to be re-run on the corrected harness. Nobody ran it.
  * distill.py's straight-frame balancing is OFF by default, and its own comment predicts
    the consequence on this map: 83.8% of the Town06 lap needs |steer| <= 0.01, so "a
    student learns to emit ~0 with a small offset and the straight sections then integrate
    that offset into a departure. The teachers absorb the imbalance because they have
    ~107k ReLU; a 5-15k ReLU student does not."

Both are one-line changes to the pipeline whose effect is a driven measurement, so the
answer has to be driven. This is that instrument: same route, same conditions, a clean
server before EVERY lap (A-4), one process per lap, and the variants differ only in the
checkpoint named.

It writes nothing to the ledger and reads no certificate. It is training telemetry under
PROTOCOL section 5, not a scored result.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.environ.setdefault("CARLA_PORT", "3000")
sys.path.insert(0, str(REPO / "pipeline"))
import config as C  # noqa: E402


def restart_carla(log):
    """A clean server before every lap (A-4). Returns True only if the restart SUCCEEDED.

    Never capture_output: carla_restart.sh daemonises CARLA and the detached child
    inherits the pipe, so the call never returns.

    THE EXIT STATUS IS CHECKED. It was not: subprocess.run() was called with no `check=`
    and its returncode was never read, so a restart that printed
    "FATAL: CARLA did not come up on 3000" and exited non-zero was indistinguishable from
    one that worked, and the lap was driven anyway -- against a stale server, or none.
    The restart log carries five such failures.

    That silence is why an 11.45 ft rejection of S_mixed_t06lap_168x56_w4_s0 could not
    afterwards be told apart from a 1.48 ft pass of the byte-identical checkpoint: the
    measurement that selects which model ships recorded nothing about the server it ran
    on. A-4 is explicit that where the harness is not enforced the answer is to enforce
    it, not to average over it.
    """
    # THE ONE RETRY POLICY (scripts/carla_restart_retry.sh, commit 5c8b340). This called
    # carla_restart.sh directly, so a boot that missed its 300 s window -- a certainty
    # over a stage of dozens of restarts, not a risk -- became a failed lap. Four copies
    # of a retry policy is how they drift, so this uses the one.
    with open(log, "a") as fh:
        for cmd, lim in (([ "bash", str(REPO / "scripts" / "carla_restart_retry.sh"),
                            str(log), "variant-gate"], 1500),
                         ([sys.executable, str(REPO / "scripts" / "wait_carla_ready.py"),
                           "--timeout", "200"], 240)):
            try:
                r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, timeout=lim,
                                   env=dict(os.environ))
            except subprocess.TimeoutExpired:
                print(f"      !! restart step exceeded {lim}s -- REFUSING to measure",
                      flush=True)
                return False
            if r.returncode != 0:
                print(f"      !! {os.path.basename(str(cmd[1]))} exited "
                      f"{r.returncode} -- REFUSING to measure on this server",
                      flush=True)
                return False
    return True


def lap_provenance(weather):
    """The harness this lap ran under -- the same block the scored ledger records.

    A selection gate decides WHICH MODEL SHIPS. Recording only a number means a
    disagreement between two runs of identical weights can never be attributed, which is
    exactly the position this study reached. D-11 says data collected under a violating
    harness is not reusable; that is only enforceable if the data says which harness it
    ran under.
    """
    import datetime
    prov = dict(
        run_started=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        weather=weather, map=getattr(C, "MAP_NAME", None),
        fixed_delta_seconds=getattr(C, "FIXED_DT", None),
        target_speed_ms=getattr(C, "TARGET_SPEED_MS", None),
        lap_end_m=getattr(C, "LAP_END_M", None),
    )
    try:
        prov["git_sha"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            cwd=str(REPO), timeout=10).stdout.strip() or None
        prov["git_dirty"] = bool(subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            capture_output=True, text=True, cwd=str(REPO), timeout=10).stdout.strip())
    except Exception:
        prov["git_sha"], prov["git_dirty"] = None, None
    det = dict(deterministic_control=bool(getattr(C, "DETERMINISTIC_CONTROL", False)))
    try:
        import carla_determinism as _cd
        det["package_version"] = getattr(_cd, "__version__", None)
        det["rules_digest"] = _cd.digest()
        det["lock_problems"] = _cd.check_lock()
        argv = _cd.server_cmdline(C.PORT) or []
        det["server_cmdline"] = argv
        # None, never False, when the server could not be inspected: "unknown" and
        # "absent" are different facts and the artifact must not collapse them.
        det["notexturestreaming"] = (any("-notexturestreaming" in a for a in argv)
                                     if argv else None)
        det["windowed"] = (any(a == "-windowed" for a in argv) if argv else None)
        q = [a.split("=", 1)[1] for a in argv if a.startswith("-quality-level=")]
        det["quality_level"] = (q[0] if q else None) if argv else None
        if not argv:
            det["server_cmdline_note"] = (
                f"no CARLA server found on port {C.PORT}; flags unknown, not absent")
    except Exception as e:
        det["error"] = str(e)
    prov["determinism"] = det
    return prov


def drive(ckpt, channels, fc, in_w, in_h, weather):
    """One lap. Returns (max_cte_ft, over_budget_frac, steps) or None if the run failed."""
    cmd = [sys.executable, "evaluate.py", "--model", ckpt, "--direction", "all",
           "--weather", weather, "--max-steps", "2000", "--channels", channels,
           "--fc", str(fc), "--student", "--in-w", str(in_w), "--in-h", str(in_h)]
    p = subprocess.run(cmd, cwd=str(REPO / "pipeline"), capture_output=True, text=True,
                       env=dict(os.environ, STUDY_MAP=C.STUDY_MAP, PYTHONUNBUFFERED="1"))
    out = p.stdout + p.stderr
    for line in out.splitlines():
        t = line.strip()
        for sec in C.SECTIONS:
            if t.startswith(f"{sec} ") and ("PASS" in t or "FAIL" in t):
                cte = over = steps = None
                if "max|CTE|=" in t:
                    cte = float(t.split("max|CTE|=")[1].split("ft")[0])
                # evaluate.py prints "over-budget=", not "over=". Searching for the
                # shorter string silently matched nothing and reported 0.0% over budget
                # next to a 12.46 ft peak -- a contradiction that looks like a result.
                if "over-budget=" in t:
                    over = float(t.split("over-budget=")[1].split("%")[0]) / 100.0
                if "steps=" in t:
                    steps = int(t.split("steps=")[1].split()[0].strip(","))
                # R-SIM-6: a run that ends far short of its step budget is a DEPARTURE,
                # and reporting only |CTE| hides that. steps_for is the full lap.
                full = C.steps_for(sec)
                return dict(max_cte_ft=cte, over=over, steps=steps, full_steps=full,
                            departed=bool(steps is not None and steps < 0.9 * full),
                            passed="PASS" in t)
    # A run that produced no summary line is a FAILED RUN, not a failing student.
    return dict(error=True, tail=out.strip().splitlines()[-4:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoints", nargs="+", required=True)
    ap.add_argument("--channels", required=True, help="e.g. 24,48,48")
    ap.add_argument("--fc", type=int, required=True)
    ap.add_argument("--reps", type=int, default=3, help="laps per checkpoint (A-4: 3)")
    ap.add_argument("--weather", default="clear")
    ap.add_argument("--in-w", type=int, default=None)
    ap.add_argument("--in-h", type=int, default=None)
    ap.add_argument("--out", default="results/town06/student_variants.json")
    args = ap.parse_args()
    in_w = args.in_w or C.TOWN06_INPUT_W
    in_h = args.in_h or C.TOWN06_INPUT_H

    log = REPO / "results" / "town06_logs" / "student_variants_restart.log"
    log.parent.mkdir(parents=True, exist_ok=True)

    missing = [c for c in args.checkpoints
               if not (Path(C.CHECKPOINT_DIR) / f"{c}.pth").exists()]
    if missing:
        sys.exit(f"missing checkpoint(s): {', '.join(missing)}")

    print(f"\nSTUDENT VARIANT COMPARISON -- {args.weather}, {args.reps} lap(s) each, "
          f"clean server before every lap")
    print(f"  budget {C.CTE_BUDGET_FT:.2f} ft\n")
    results = {}
    for ck in args.checkpoints:
        laps = []
        for rep in range(args.reps):
            # A FAILED RESTART IS A FAILED LAP, not a lap on an unknown server. Driving
            # anyway is how a student gets rejected by the simulator rather than by its
            # own behaviour, with nothing in the artifact to say so afterwards.
            if not restart_carla(log):
                laps.append(dict(error=True, rep=rep, sec=0.0,
                                 tail=["restart failed; lap not driven"],
                                 restart_failed=True,
                                 provenance=lap_provenance(args.weather)))
                print(f"  {ck:44s} lap{rep}  RESTART FAILED -- lap not driven")
                continue
            prov = lap_provenance(args.weather)
            t0 = time.time()
            r = drive(ck, args.channels, args.fc, in_w, in_h, args.weather)
            r["rep"] = rep
            r["sec"] = round(time.time() - t0, 1)
            r["provenance"] = prov
            laps.append(r)
            if r.get("error"):
                print(f"  {ck:44s} lap{rep}  RUN FAILED")
                for ln in r["tail"]:
                    print(f"      {ln}")
            else:
                ov = "  n/a" if r["over"] is None else f"{100 * r['over']:5.1f}%"
                print(f"  {ck:44s} lap{rep}  max|CTE| {r['max_cte_ft']:7.2f} ft "
                      f"over {ov}  steps {r['steps']}/{r['full_steps']}"
                      f"{'  DEPARTED' if r['departed'] else ''}  "
                      f"{'PASS' if r['passed'] else 'FAIL'}")
        results[ck] = laps

    print(f"\n{'checkpoint':46s} {'laps held':>10s} {'worst |CTE|':>12s} {'% of budget':>12s}")
    for ck, laps in results.items():
        good = [l for l in laps if not l.get("error")]
        held = sum(1 for l in good if l["passed"])
        worst = max((l["max_cte_ft"] for l in good), default=float("nan"))
        # UNMEASURED laps are named. A gate compares held against the EXPECTED count, so
        # a dropped lap can never inflate a pass -- but it must still be visible, or a
        # cell measured on two laps reads exactly like one measured on three.
        bad = len(laps) - len(good)
        note = "" if not bad else f"   ({bad} lap(s) NOT MEASURED)"
        print(f"{ck:46s} {held:>6d}/{len(laps):<3d} {worst:11.2f}ft "
              f"{100 * worst / C.CTE_BUDGET_FT:11.0f}%{note}")

    # EXIT 3 WHEN A LAP COULD NOT BE MEASURED.
    #
    # An unmeasured lap is not a failing lap. The sweep counts laps under a threshold and
    # compares against the EXPECTED count, so an unmeasured lap made a seed look rejected
    # -- and it happened: S_mixed_t06lap_168x56_w4_s3, the SHIPPED student, was "rejected
    # at the screen" because one restart failed and the night lap was never driven. That
    # is a harness failure wearing the costume of a model verdict, which is the exact
    # confusion the restart-status fix was meant to end and only half ended.
    unmeasured = sum(1 for laps in results.values()
                     for l in laps if l.get("error") or l.get("restart_failed"))
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(weather=args.weather, reps=args.reps,
                                   budget_ft=C.CTE_BUDGET_FT, results=results),
                              indent=2))
    print(f"\n  -> {out}")
    if unmeasured:
        print(f"\n  {unmeasured} lap(s) COULD NOT BE MEASURED. This is a harness "
              f"failure, not a\n  model verdict, and the caller must not read it as one.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

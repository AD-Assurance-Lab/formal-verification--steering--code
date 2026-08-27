#!/usr/bin/env python3
"""Block until CARLA actually answers, not merely until the port is bound.

Every script in this study waited with `ss -ltn | grep -q ":$CARLA_PORT"`. The server
binds its port well before it can serve, so that check returns true against a simulator
that is still loading. The failure is silent and expensive: a competence gate ran for
12 minutes against a listening-but-unready server, every drive raised

    RuntimeError: time-out of 120000ms while waiting for the simulator

and the gate recorded "evaluation produced no per-section result" for both students --
which reads as a verdict on the models rather than on the server.

Readiness is a successful get_world(), so that is what this checks.

    python3 scripts/wait_carla_ready.py [--timeout 180] [--port 3000]
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "pipeline"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("CARLA_PORT", "3000")))
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()

    import carla
    t0 = time.time()
    last = None
    while time.time() - t0 < args.timeout:
        try:
            c = carla.Client("127.0.0.1", args.port)
            c.set_timeout(10.0)
            w = c.get_world()
            m = w.get_map().name
            print(f"CARLA ready on {args.port} after {time.time() - t0:.0f}s (map {m})")
            return 0
        except Exception as e:
            last = str(e).split("\n")[0][:90]
            time.sleep(5)
    print(f"CARLA NOT ready on {args.port} after {args.timeout:.0f}s. Last error: {last}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

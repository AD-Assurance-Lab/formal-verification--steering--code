"""Put the entry-point directory on the path for tests that read it as a module.

`src/steering` is installed, so the library imports normally. `scripts/` deliberately
is not a package -- the files there are things you run, not things you import -- but a
few tests cross-check a constant against the script that defines it, and that is worth
more than the purity of never importing one.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

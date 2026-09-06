"""End-to-end steering verification: the library the entry points in scripts/ import.

REPO_ROOT is defined once, here. Every module used to count directories up from its
own file, so moving a file changed where it thought the repository was -- and the
failure is silent, because a missing route or checkpoint reads as "not collected yet"
rather than "looking in the wrong place".

Set STEERING_REPO_ROOT to run an installed copy against a checkout somewhere else.
"""
import os

__version__ = "1.3.0"

REPO_ROOT = os.environ.get(
    "STEERING_REPO_ROOT",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

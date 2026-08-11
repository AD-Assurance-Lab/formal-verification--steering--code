"""Put `pipeline/` on sys.path.

The pipeline modules import each other flatly (`from config import ...`) and are run
from inside that directory. The conformance suite imports them the same way rather
than repackaging them, so a transplanted file behaves here exactly as it does in a
real run -- which is the point of testing it.
"""

import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent.parent / "pipeline"
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))

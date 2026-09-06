#!/usr/bin/env bash
# Build .venv-abcrown -- the SEPARATE environment that runs alpha-beta-CROWN for Q8b.
#
# WHY A SECOND ENVIRONMENT. docs/Q8_PREREGISTRATION.md amendment A-1 records the
# measurement: alpha-beta-CROWN pins torch==2.11.0, requires numpy>=2.0.0 and
# requires-python ~=3.11.0. The study is Python 3.12.3, torch 2.13.0+cu130, numpy 1.26.4.
# The torch pin and the numpy floor cannot both be satisfied.
#
# torch 2.13.0+cu130 is not a preference here. The RTX 5090 is sm_120, and the previously
# pinned torch had no kernels for it while torch.cuda.is_available() reported True -- the
# defect that produced steering.gpu's require_cuda(). Every checkpoint and every
# published number in this repo is tied to that environment. Downgrading it to run a
# verifier would re-derive the study in order to check a bound.
#
# So the verifier runs OUT OF PROCESS and the two sides meet at ONNX + VNNLIB, which is
# alpha-beta-CROWN's native input format and which this study's spec already fits: the
# Bounder reparameterises each pose to a ONE-DIMENSIONAL input feeding an affine head, so
# the property is "output in safe set for input in a box" with the box [0,1] in one
# variable.
#
# THIS SCRIPT MUST NEVER TOUCH .venv. It writes only .venv-abcrown, which .gitignore
# already covers via `.venv*/`. Verify with:
#
#     .venv/bin/python -c "import torch,numpy;print(torch.__version__,numpy.__version__)"
#     # must still print 2.13.0+cu130 1.26.4
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD

# PINNED COMMITS. Not a branch, not HEAD: a complete verifier's verdicts are only
# reproducible against a fixed solver, and "we ran beta-CROWN" is not a citable claim.
ABCROWN_REPO=https://github.com/Verified-Intelligence/alpha-beta-CROWN.git
ABCROWN_COMMIT=e5c7e17bf0488843acb77b7519f59876717a49f4
AUTOLIRPA_COMMIT=5a098e8f9fb5786a428a024981d833d303921f2d   # its auto_LiRPA submodule

SRC=${ABCROWN_SRC:-$REPO/.abcrown-src}
VENV=$REPO/.venv-abcrown

command -v uv >/dev/null || { echo "FATAL: uv not found"; exit 1; }

echo "== source: $SRC @ $ABCROWN_COMMIT"
if [ ! -d "$SRC/.git" ]; then
    git clone "$ABCROWN_REPO" "$SRC"
fi
git -C "$SRC" fetch --depth 50 origin "$ABCROWN_COMMIT" 2>/dev/null || git -C "$SRC" fetch origin
git -C "$SRC" checkout -q "$ABCROWN_COMMIT"
git -C "$SRC" submodule update --init --recursive
got=$(git -C "$SRC/auto_LiRPA" rev-parse HEAD)
[ "$got" = "$AUTOLIRPA_COMMIT" ] || {
    echo "FATAL: auto_LiRPA submodule is $got, expected $AUTOLIRPA_COMMIT"; exit 1; }

echo "== interpreter: Python 3.11 (user-local, via uv; nothing system-wide)"
uv python install 3.11
[ -x "$VENV/bin/python" ] || uv venv --python 3.11 "$VENV"

echo "== install"
uv pip install --python "$VENV/bin/python" "$SRC"
uv pip install --python "$VENV/bin/python" --no-deps "$SRC/auto_LiRPA"

echo "== verify"
"$VENV/bin/python" - <<'PY'
import torch, numpy, auto_LiRPA, importlib.util as u
print(f"  torch {torch.__version__}  numpy {numpy.__version__}")
arch = torch.cuda.get_arch_list()
print(f"  arch list: {arch[-3:]}")
assert "sm_120" in arch, ("this torch has no sm_120 kernels and the lab card is an "
                          "RTX 5090 -- the same defect require_cuda() exists to catch")
for m in ("abcrown", "complete_verifier"):
    assert u.find_spec(m), f"{m} not importable"
print("  abcrown + complete_verifier importable")
PY

echo "== the STUDY environment must be untouched"
"$REPO/.venv/bin/python" - <<'PY'
import torch, numpy, sys
ok = torch.__version__ == "2.13.0+cu130" and numpy.__version__ == "1.26.4"
print(f"  study .venv: torch {torch.__version__} numpy {numpy.__version__} "
      f"{'OK' if ok else '*** MOVED -- STOP ***'}")
sys.exit(0 if ok else 1)
PY

echo
echo "done. Q8b runs the verifier as:"
echo "  .venv-abcrown/bin/python -m complete_verifier.abcrown --onnx_path X --vnnlib_path Y"

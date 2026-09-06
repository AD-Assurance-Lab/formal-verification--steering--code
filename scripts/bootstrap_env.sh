#!/usr/bin/env bash
# Build the verification environment from nothing, and PROVE it works before returning.
#
# Why this exists (all three were live defects on the 2026-09-03 desktop migration):
#
#  1. torch must match the GPU's compute capability. `torch 2.5.1+cu121` builds for
#     sm_50..sm_90; an RTX 5090 is sm_120. `torch.cuda.is_available()` returns TRUE and
#     the device name resolves, then every kernel dies with "no kernel image is available
#     for execution on the device". A version check is not enough -- this script runs a
#     real kernel and refuses to finish if it fails.
#  2. ROS leaks in through PYTHONPATH. The venv is created with
#     include-system-site-packages=false, but PYTHONPATH overrides that, so
#     /opt/ros/<distro>/lib/python3.*/site-packages lands on sys.path anyway. pytest then
#     autoloads ROS's launch_testing plugin and dies before collecting a single test.
#     The sitecustomize.py written below strips those entries at interpreter startup, so
#     the venv is immune no matter what the caller's environment says.
#  3. opencv-python declares numpy>=2, but every published artifact in this repo records
#     numpy 1.26.4. The declared pin is not an ABI requirement -- wheels built against
#     numpy 2 run fine on numpy 1.x -- so opencv goes in with --no-deps.
#
# Usage:  bash scripts/bootstrap_env.sh [venv-dir]      (default .venv)
set -euo pipefail

VENV=${1:-.venv}
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

# ONLY what a resolver cannot install is pinned here. scipy, opencv, matplotlib and
# carla-determinism are pinned in pyproject.toml and installed from it below, so each
# version is written down exactly once. Two copies of a pin is how the recorded
# environment and the installed one come apart.
#
# numpy is the exception and it is pinned in BOTH, to different things on purpose.
# pyproject declares a floor, because opencv-python declares numpy>=2 and an exact
# 1.26.4 there makes `pip install -e .` unsatisfiable. The published bounds were
# computed under 1.26.4, so this script installs exactly that, and then opencv goes in
# with --no-deps so it cannot pull numpy 2 back over the top.
#
# These four versions are the environment of record, read from the _meta of the
# published artifacts themselves (results/town06/certificate_town06.json and the
# Town04-redo sustained bound), NOT from whatever happens to be installed. Change them
# only with a measurement to back it up.
TORCH_VER=2.13.0
TORCH_INDEX=https://download.pytorch.org/whl/cu130
NUMPY_VER=1.26.4          # the environment of record; see the note above
AUTO_LIRPA_REF=5a098e8f9fb5786a428a024981d833d303921f2d
CARLA_WHEEL_DIR="$HOME/carla/PythonAPI/carla/dist"

echo "==> building $VENV"
unset PYTHONPATH
rm -rf "$VENV"
python3 -m venv "$VENV"
PY="$REPO/$VENV/bin/python"
PIP="$PY -m pip"

# --- make the venv immune to PYTHONPATH leakage (defect 2) ---------------------
SITEDIR="$($PY -c 'import sysconfig;print(sysconfig.get_paths()["purelib"])')"
# NOTE: this is a .pth file, NOT sitecustomize.py. Ubuntu ships its own
# /usr/lib/python3.12/sitecustomize.py, which sits earlier on sys.path, and only the
# FIRST sitecustomize found is imported -- so a venv-local one is silently shadowed and
# never runs. Every .pth in a site directory is processed, and a line beginning with
# "import " is executed, so this always fires.
cat > "$SITEDIR/zzz_strip_system_paths.pth" <<'PTHEOF'
import sys; sys.path[:] = [p for p in sys.path if "/opt/ros/" not in p and "/usr/lib/python3/dist-packages" not in p]
PTHEOF

$PIP install -q --upgrade pip wheel setuptools

echo "==> torch $TORCH_VER from $TORCH_INDEX"
$PIP install -q "torch==$TORCH_VER" torchvision --index-url "$TORCH_INDEX"

echo "==> this package and its pinned dependencies, from pyproject.toml"
# opencv declares numpy>=2; that is a declared pin, not an ABI need, and installing it
# normally drags numpy 2 in on top of the 1.26.4 the artifacts were produced under.
# So it goes in first with --no-deps, and the editable install below finds it satisfied.
OPENCV_PIN=$("$PY" - <<'PYEOF'
import re, pathlib
t = pathlib.Path("pyproject.toml").read_text()
print(re.search(r'"(opencv-python==[^"]+)"', t).group(1))
PYEOF
)
$PIP install -q "numpy==$NUMPY_VER"
$PIP install -q --no-deps "$OPENCV_PIN"
$PIP install -q -e ".[dev]"

# The editable install resolves numpy>=1.26.4 and must have left 1.26.4 alone. If it
# did not, every bound below is computed under a numpy the artifacts do not record.
INSTALLED_NUMPY=$("$PY" -c 'import numpy;print(numpy.__version__)')
if [ "$INSTALLED_NUMPY" != "$NUMPY_VER" ]; then
    echo "    FATAL: numpy is $INSTALLED_NUMPY, not the recorded $NUMPY_VER" >&2
    exit 1
fi

echo "==> auto_LiRPA (pinned commit, --no-deps so torch is never rewritten)"
$PIP install -q --no-deps --ignore-requires-python \
    "git+https://github.com/Verified-Intelligence/auto_LiRPA.git@$AUTO_LIRPA_REF"
# --no-deps means auto_LiRPA's own import-time deps are absent; these three are needed.
$PIP install -q --no-deps appdirs tqdm graphviz

echo "==> CARLA client + determinism package"
# The wheel must match THIS interpreter: the dist dir ships cp310 and cp312 side by
# side, and a bare glob picks cp310 first, which pip rejects as unsupported.
CPTAG=$("$PY" -c 'import sys;print(f"cp{sys.version_info.major}{sys.version_info.minor}")')
CARLA_WHEEL=$(ls "$CARLA_WHEEL_DIR"/carla-*-${CPTAG}-${CPTAG}-*.whl 2>/dev/null | head -1 || true)
if [ -n "$CARLA_WHEEL" ]; then
    $PIP install -q "$CARLA_WHEEL"
else
    echo "    WARNING: no CARLA wheel for $CPTAG in $CARLA_WHEEL_DIR -- closed-loop work will not run"
fi
# carla-determinism came in with the editable install above, pinned in pyproject.toml.

# --- prove it, do not assume it ------------------------------------------------
echo "==> verifying"
PYTHONPATH=/opt/ros/does-not-exist "$PY" - <<'PYEOF'
import sys, importlib
fail = []

# defect 2: the leak must be gone even with PYTHONPATH set (we set a decoy above)
if any("/opt/ros/" in p for p in sys.path):
    fail.append("sitecustomize did not strip ROS paths from sys.path")

import torch, numpy, cv2, scipy
print(f"    python {sys.version.split()[0]}  torch {torch.__version__}  "
      f"numpy {numpy.__version__}  cv2 {cv2.__version__}  scipy {scipy.__version__}")

# defect 1: a real kernel, not is_available()
if not torch.cuda.is_available():
    fail.append("torch.cuda.is_available() is False")
else:
    cap = torch.cuda.get_device_capability(0)
    arches = torch.cuda.get_arch_list()
    print(f"    GPU {torch.cuda.get_device_name(0)} sm_{cap[0]}{cap[1]}; torch builds {arches[-3:]}")
    try:
        a = torch.randn(512, 512, device="cuda")
        float((a @ a).sum()); torch.cuda.synchronize()
        print("    CUDA kernel: OK")
    except Exception as exc:
        fail.append(f"CUDA kernel failed on this GPU: {type(exc).__name__}: {exc}")

# defect 3: cv2 must actually work against the installed numpy
try:
    import numpy as np
    cv2.resize(np.zeros((8, 8, 3), np.uint8), (4, 4))
    print("    cv2 <-> numpy: OK")
except Exception as exc:
    fail.append(f"cv2 does not work with numpy {numpy.__version__}: {exc}")

# auto_LiRPA must import, and must not be the SDP-CROWN fork
try:
    import auto_LiRPA
    from auto_LiRPA import BoundedModule, BoundedTensor           # noqa: F401
    from auto_LiRPA.perturbations import PerturbationLpNorm       # noqa: F401
    print(f"    auto_LiRPA {getattr(auto_LiRPA,'__version__','?')}: OK")
    import pathlib
    root = pathlib.Path(auto_LiRPA.__file__).parent
    if any("sdp" in p.name.lower() for p in root.rglob("*.py")):
        fail.append("auto_LiRPA looks like the SDP-CROWN fork; it must not be")
except Exception as exc:
    fail.append(f"auto_LiRPA import failed: {type(exc).__name__}: {exc}")

try:
    import carla                                                   # noqa: F401
    print("    carla client: OK")
except Exception as exc:
    print(f"    carla client: MISSING ({exc}) -- closed-loop work will not run")

try:
    import carla_determinism                                       # noqa: F401
    print(f"    carla_determinism {carla_determinism.__version__}: OK")
except Exception as exc:
    fail.append(f"carla_determinism import failed: {exc}")

if fail:
    print("\n  BOOTSTRAP FAILED:")
    for f in fail:
        print(f"    - {f}")
    sys.exit(1)
print("\n  environment OK")
PYEOF

echo
echo "  $VENV is ready.  Use it as:  $VENV/bin/python ..."
echo "  or:  source $VENV/bin/activate"

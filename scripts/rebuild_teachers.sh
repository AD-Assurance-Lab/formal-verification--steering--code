#!/usr/bin/env bash
# Rebuild both teachers from the recollected, order-independent condition data.
#
# Runs the documented recipe end to end so there are no idle gaps between stages:
#   clear:  BC -> teacher DAgger
#   mixed:  BC -> teacher DAgger
#
# Distillation and student-DAgger follow separately, once both teachers pass.
set -euo pipefail

PY=/home/za/ad-assurance--workspace/sdp-crown--automated-driving--code/venv_sdp/bin/python
cd "$(dirname "$0")/.."
M=pipeline/data/conditions/manifest.csv

echo "############ 1/4  clear teacher, behaviour cloning ############"
$PY -u pipeline/train.py --manifests "$M" --weathers clear \
    --epochs 120 --out teacher_clear_bc

echo "############ 2/4  clear teacher, DAgger ############"
$PY -u pipeline/dagger.py --base conditions --init teacher_clear_bc \
    --rounds 6 --weathers clear --out-prefix teacher_clear_dagger \
    --dagger-dir dagger_clear --margin-frac 0.8

echo "############ 3/4  mixed teacher, behaviour cloning ############"
$PY -u pipeline/train.py --manifests "$M" \
    --epochs 120 --out teacher_mixed_bc

echo "############ 4/4  mixed teacher, DAgger ############"
$PY -u pipeline/dagger.py --base conditions --init teacher_mixed_bc \
    --rounds 6 --weathers clear,fog,night,shadows \
    --out-prefix teacher_mixed_dagger --dagger-dir dagger_mixed --margin-frac 0.8

echo "############ done ############"

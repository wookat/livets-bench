#!/bin/bash
# Bootstrap an isolated python env in the sgpu job workdir and run the eval matrix.
# Args: $1 = job name, $2 = comma-separated models, $3 = pip packages
set -euo pipefail
NAME="$1"; MODELS="$2"; PKGS="$3"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export HF_HOME="$PWD/hf_cache"
export LIVETS_DEVICE=cuda
if [ ! -x mc/bin/python ]; then
  wget -q https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-py311_24.7.1-0-Linux-x86_64.sh -O mc.sh
  bash mc.sh -b -p "$PWD/mc" >/dev/null && rm mc.sh
fi
mc/bin/pip -q install -i https://pypi.tuna.tsinghua.edu.cn/simple requests pyyaml pandas $PKGS
mkdir -p results
mc/bin/python scripts/run_matrix.py --models "$MODELS" --out "results/matrix-$NAME.jsonl"

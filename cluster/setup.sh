#!/usr/bin/env bash
# One-time setup on Explorer, run on the LOGIN node (it has internet; GPU nodes may not).
#   cd /scratch/$USER/gemma-secure-backends && bash cluster/setup.sh
# Reuses the CyberNemo training venv if it exists (transformers 5.22.1 + peft supports Gemma 4,
# which needs >= 5.10); otherwise creates one. Downloads Gemma 4 12B-it (~24 GB, not gated).
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_HOME=/scratch/$USER/hf_cache PIP_CACHE_DIR=/scratch/$USER/pip_cache
mkdir -p logs runs gens
TRAIN_ENV="${TRAIN_ENV:-/scratch/$USER/nemotron-secfix/env_train}"
if [[ ! -x "$TRAIN_ENV/bin/python" ]]; then
  TRAIN_ENV=env_train
  python3 -m venv "$TRAIN_ENV"
  "$TRAIN_ENV"/bin/pip install -U pip
  "$TRAIN_ENV"/bin/pip install torch --index-url https://download.pytorch.org/whl/cu128
  "$TRAIN_ENV"/bin/pip install "transformers==5.22.1" peft accelerate "datasets>=5.1.0"
fi
echo "TRAIN_ENV=$TRAIN_ENV" > cluster/env.sh
"$TRAIN_ENV"/bin/python -c "import torch, transformers, peft; print('torch', torch.__version__, 'cuda', torch.version.cuda, '| transformers', transformers.__version__, '| peft', peft.__version__); from transformers import AutoModelForMultimodalLM; print('Gemma 4 auto class OK')"
"$TRAIN_ENV"/bin/python - <<'PY'
from huggingface_hub import snapshot_download
p = snapshot_download("google/gemma-4-12B-it", allow_patterns=["*.json", "*.safetensors", "*.jinja", "*.txt", "*.model"])
print("model at", p)
PY
echo "setup done"

#!/usr/bin/env bash
# On an AWS GPU machine (Deep Learning AMI, one 48 GB L40S), after the repo is copied to ~/gsb:
#   bash gsb/scripts/aws_gpu_run.sh           (run detached; progress in ~/gsb/logs/gpu_*.log)
# 1) venv with torch + transformers 5.22.1 + peft, 2) download Gemma 4 12B-it,
# 3) LoRA SFT, 4) generate BaxBench answers for base and SFT (plain transformers, no vLLM).
set -euo pipefail
cd "$HOME/gsb"
mkdir -p logs runs gens
export HF_HOME="$HOME/hf_cache" PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
if [[ ! -x .venv-gpu/bin/python ]]; then
  python3 -m venv .venv-gpu
  .venv-gpu/bin/pip install -q -U pip
  .venv-gpu/bin/pip install -q torch --index-url https://download.pytorch.org/whl/cu128
  .venv-gpu/bin/pip install -q "transformers==5.22.1" peft accelerate "datasets>=5.1.0" sentencepiece
fi
PY=.venv-gpu/bin/python
$PY -c "import torch, transformers, peft; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0), '| transformers', transformers.__version__, '| peft', peft.__version__)"
$PY -c "from huggingface_hub import snapshot_download; print(snapshot_download('google/gemma-4-12B-it', allow_patterns=['*.json', '*.safetensors', '*.jinja', '*.txt', '*.model']))"
GEN=(--model google/gemma-4-12B-it --prompts data/baxbench_prompts.jsonl --n 5 --temperature 0.4 --max_new_tokens 4096 --prompts_per_batch 2)
[[ -f runs/sft12b/adapter/adapter_config.json ]] || $PY cluster/sft.py --model google/gemma-4-12B-it --out runs/sft12b > logs/gpu_sft.log 2>&1
echo "SFT done"
$PY cluster/gen.py "${GEN[@]}" --out gens/base12b.jsonl > logs/gpu_gen_base.log 2>&1
echo "base generation done: $(wc -l < gens/base12b.jsonl)"
$PY cluster/gen.py "${GEN[@]}" --adapter runs/sft12b/adapter --out gens/sft12b.jsonl > logs/gpu_gen_sft.log 2>&1
echo "SFT generation done: $(wc -l < gens/sft12b.jsonl)"

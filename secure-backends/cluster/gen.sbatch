#!/bin/bash
# Generate BaxBench answers with Gemma 4 12B-it (transformers, no vLLM), base or with the SFT adapter.
#   RUN=base12b sbatch cluster/gen.sbatch
#   RUN=sft12b ADAPTER=runs/sft12b/adapter sbatch cluster/gen.sbatch
# Output: gens/$RUN.jsonl (resumes if re-submitted). Copy it back to the Mac to score.
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:h200:1
#SBATCH --time=04:00:00
#SBATCH --job-name=gsb-gen
#SBATCH --mem=96GB
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --output=logs/gen_%j.out
#SBATCH --error=logs/gen_%j.out
set -eo pipefail
cd /scratch/$USER/gemma-secure-backends
source cluster/env.sh
: "${RUN:?set RUN, e.g. RUN=base12b}"
export HF_HOME=/scratch/$USER/hf_cache HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
nvidia-smi --query-gpu=name,memory.total --format=csv
$TRAIN_ENV/bin/python cluster/gen.py --model google/gemma-4-12B-it --prompts data/baxbench_prompts.jsonl \
  --out gens/$RUN.jsonl ${ADAPTER:+--adapter $ADAPTER} ${GEN_ARGS:-}
echo "$RUN: $(wc -l < gens/$RUN.jsonl) samples"

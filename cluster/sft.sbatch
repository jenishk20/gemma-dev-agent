#!/bin/bash
# LoRA SFT of Gemma 4 12B-it on the verified secure-coding set (one H200).
#   sbatch cluster/sft.sbatch        -> runs/sft12b/adapter
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:h200:1
#SBATCH --time=04:00:00
#SBATCH --job-name=gsb-sft
#SBATCH --mem=128GB
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --output=logs/sft_%j.out
#SBATCH --error=logs/sft_%j.out
set -eo pipefail
cd /scratch/$USER/gemma-secure-backends
source cluster/env.sh
export HF_HOME=/scratch/$USER/hf_cache HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
nvidia-smi --query-gpu=name,memory.total --format=csv
$TRAIN_ENV/bin/python cluster/sft.py --model google/gemma-4-12B-it --out runs/sft12b ${SFT_ARGS:-}

#!/bin/bash
# Paste into OOD Job Composer: fine-tune a LoRA for E4B on the solved teacher runs (1 x H200).
# Steps: build examples from results/teacher_*_try* -> print one rendered example -> check model + LoRA load
# and one loss/backward on the longest example -> train -> save adapter.
# Everything stays under /scratch/phalle.y/gda. peft goes into its own folder ($GDA_ROOT/pylib), so the
# eval venv (vLLM) is not changed.
# Log: /scratch/phalle.y/gemma-dev-agent/gda-lora_<jobid>.out ; adapter: $GDA_ROOT/adapters/<NAME>_<jobid>/
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:h200:1
#SBATCH --time=06:00:00
#SBATCH --mem=96G
#SBATCH --cpus-per-task=8
#SBATCH --job-name=gda-lora
#SBATCH --output=/scratch/phalle.y/gemma-dev-agent/gda-lora_%j.out
set -eo pipefail
trap 'echo "FAILED: line $LINENO exited with code $? at $(date +%T)"' ERR

MODEL=${MODEL:-gemma-4-e4b-it-qat-w4a16-ct}
NAME=${NAME:-e4b_teacher_v1}
RANK=${RANK:-32}
EPOCHS=${EPOCHS:-2}
LR=${LR:-1e-4}
ONLY_CHECK=${ONLY_CHECK:-0}          # 1 = stop after the load/loss check

REPO=/scratch/phalle.y/gemma-dev-agent
cd "$REPO"
flock /scratch/phalle.y/gda/.gitlock git pull -q || echo "git pull failed; using the code already on disk"
export GDA_ROOT=$(dirname "$REPO")/gda
export XDG_CACHE_HOME=$GDA_ROOT/cache UV_CACHE_DIR=$GDA_ROOT/cache/uv PYTHONUNBUFFERED=1 HF_HOME=$GDA_ROOT/cache/hf \
       TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=$GDA_ROOT/venv/bin/python
echo "job $SLURM_JOB_ID on $(hostname) | commit $(git rev-parse --short HEAD) | $MODEL rank=$RANK epochs=$EPOCHS lr=$LR | $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# peft only (its other needs are already in the venv), in a separate folder
if ! PYTHONPATH=$GDA_ROOT/pylib "$PY" -c "import peft" 2>/dev/null; then
  PATH=$GDA_ROOT/bootstrap/bin:$PATH uv pip install --python "$PY" --target "$GDA_ROOT/pylib" --no-deps -q "peft>=0.17,<1"
fi
export PYTHONPATH=$GDA_ROOT/pylib
"$PY" -c "import peft, transformers, torch; print('peft', peft.__version__, '| transformers', transformers.__version__, '| torch', torch.__version__)"

DATA=$GDA_ROOT/data/sft/${NAME}.jsonl
"$PY" training/build_sft.py --runs $(ls -d "$GDA_ROOT"/results/teacher_*_try*) --tasks "$GDA_ROOT/data/tasks.jsonl" --out "$DATA"
"$PY" training/train_lora.py --data "$DATA" --model "$GDA_ROOT/models/$MODEL" --show 1
"$PY" training/train_lora.py --data "$DATA" --model "$GDA_ROOT/models/$MODEL" --rank "$RANK" --check-load
[ "$ONLY_CHECK" = 1 ] && { echo "check only: done $(date)"; exit 0; }

OUT=$GDA_ROOT/adapters/${NAME}_$SLURM_JOB_ID
"$PY" training/train_lora.py --data "$DATA" --model "$GDA_ROOT/models/$MODEL" --rank "$RANK" --alpha $((RANK * 2)) \
  --epochs "$EPOCHS" --lr "$LR" --out "$OUT"
echo "adapter: $OUT"
echo "finished $(date)"

#!/bin/bash
# Paste into OOD Job Composer: a model with a trained adapter vs the same model without, on the 29 held-out
# test tasks (never used in training), each twice, because one run moves by a few tasks either way.
# 4 parallel jobs (--array=1-4), 1 H200 each:  1, 2 = BASE (no adapter)   3, 4 = LORA + ADAPTER
#   BASE / LORA: submission folders that differ only by `adapter: main_lora` (defaults: the E4B Kimi pair)
#   ADAPTER: a folder from cluster/ood_train_lora.sh (default: the newest $GDA_ROOT/adapters/$ADAPTER_NAME_*)
#   e.g. BASE=submissions/e4b_v4 LORA=submissions/e4b_v4_lora ADAPTER_NAME=e4b_self_v1
# This is also the test that vLLM loads our LoRA on the W4A16 QAT model, the way Kaggle's scorer does.
# Logs: /scratch/phalle.y/gemma-dev-agent/gda-evlora_<jobid>_<n>.out ; results: $GDA_ROOT/results/evlora_<jobid>_<n>_<name>/
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:h200:1
#SBATCH --time=03:00:00
#SBATCH --mem=96G
#SBATCH --cpus-per-task=16
#SBATCH --job-name=gda-evlora
#SBATCH --array=1-4
#SBATCH --output=/scratch/phalle.y/gemma-dev-agent/gda-evlora_%A_%a.out
set -eo pipefail
trap 'echo "FAILED: line $LINENO exited with code $? at $(date +%T)"' ERR
REPO=/scratch/phalle.y/gemma-dev-agent
cd "$REPO"
GDA_ROOT=$(dirname "$REPO")/gda
I=${SLURM_ARRAY_TASK_ID:-3}
JOB=${SLURM_ARRAY_JOB_ID:-$SLURM_JOB_ID}
BASE=${BASE:-submissions/e4b_tprompt}
LORA=${LORA:-submissions/e4b_lora_v1}
ADAPTER_NAME=${ADAPTER_NAME:-e4b_teacher_v1}
ADAPTER=${ADAPTER:-$(ls -td "$GDA_ROOT"/adapters/${ADAPTER_NAME}_* 2>/dev/null | head -1)}

TASKS=$GDA_ROOT/data/tasks_test29.jsonl
[ -s "$TASKS" ] || "$GDA_ROOT/venv/bin/python" - "$GDA_ROOT/data/tasks.jsonl" "$TASKS" <<'PY'
import json, sys
test = set(json.load(open("training/public_split.json"))["test"])
rows = [l for l in open(sys.argv[1]) if l.strip() and json.loads(l)["instance_id"] in test]
assert len(rows) == 29, len(rows)
open(sys.argv[2], "w").write("".join(rows))
PY

if [ "$I" -le 2 ]; then
  NAME=$(basename "$BASE"); SUBDIR=$REPO/$BASE
else
  NAME=$(basename "$LORA")
  [ -s "$ADAPTER/adapter_model.safetensors" ] || { echo "ERROR: no trained adapter found ($ADAPTER)"; exit 1; }
  SUBDIR=$GDA_ROOT/subs/${NAME}_${JOB}_$I             # private copy with the adapter inside, as in the Kaggle zip
  rm -rf "$SUBDIR"; mkdir -p "$(dirname "$SUBDIR")"; cp -r "$REPO/$LORA" "$SUBDIR"
  mkdir -p "$SUBDIR/adapters/main_lora"
  cp "$ADAPTER/adapter_config.json" "$ADAPTER/adapter_model.safetensors" "$SUBDIR/adapters/main_lora/"
  echo "adapter: $ADAPTER ($(du -sh "$ADAPTER/adapter_model.safetensors" | cut -f1))"
fi
echo "run $I: $NAME on 29 test tasks | $(date)"
SUB=$SUBDIR TASKS=$TASKS N=0 C=8 RESULTS=$GDA_ROOT/results/evlora_${JOB}_${I}_$NAME bash cluster/eval.sbatch

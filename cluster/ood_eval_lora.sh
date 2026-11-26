#!/bin/bash
# Paste into OOD Job Composer: trained E4B vs plain E4B on the 29 held-out test tasks (never used in training),
# each twice, because one run moves by a few tasks either way. 4 parallel jobs (--array=1-4), 1 H200 each:
#   1, 2 = submissions/e4b_tprompt (no adapter)   3, 4 = submissions/e4b_lora_v1 + the trained adapter
# Both use the exact prompt, tools and agent name of the Kimi teacher runs; the only difference is the adapter.
# This is also the test that vLLM loads our LoRA on the W4A16 QAT model, the way Kaggle's scorer does.
# ADAPTER: folder from cluster/ood_train_lora.sh (default: the newest $GDA_ROOT/adapters/e4b_teacher_v1_*).
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
ADAPTER=${ADAPTER:-$(ls -td "$GDA_ROOT"/adapters/e4b_teacher_v1_* 2>/dev/null | head -1)}

TASKS=$GDA_ROOT/data/tasks_test29.jsonl
[ -s "$TASKS" ] || "$GDA_ROOT/venv/bin/python" - "$GDA_ROOT/data/tasks.jsonl" "$TASKS" <<'PY'
import json, sys
test = set(json.load(open("training/public_split.json"))["test"])
rows = [l for l in open(sys.argv[1]) if l.strip() and json.loads(l)["instance_id"] in test]
assert len(rows) == 29, len(rows)
open(sys.argv[2], "w").write("".join(rows))
PY

if [ "$I" -le 2 ]; then
  NAME=e4b_tprompt; SUBDIR=$REPO/submissions/e4b_tprompt
else
  NAME=e4b_lora_v1
  [ -s "$ADAPTER/adapter_model.safetensors" ] || { echo "ERROR: no trained adapter found ($ADAPTER)"; exit 1; }
  SUBDIR=$GDA_ROOT/subs/${NAME}_${JOB}_$I             # private copy with the adapter inside, as in the Kaggle zip
  rm -rf "$SUBDIR"; mkdir -p "$(dirname "$SUBDIR")"; cp -r "$REPO/submissions/$NAME" "$SUBDIR"
  mkdir -p "$SUBDIR/adapters/main_lora"
  cp "$ADAPTER/adapter_config.json" "$ADAPTER/adapter_model.safetensors" "$SUBDIR/adapters/main_lora/"
  echo "adapter: $ADAPTER ($(du -sh "$ADAPTER/adapter_model.safetensors" | cut -f1))"
fi
echo "run $I: $NAME on 29 test tasks | $(date)"
SUB=$SUBDIR TASKS=$TASKS N=0 C=8 RESULTS=$GDA_ROOT/results/evlora_${JOB}_${I}_$NAME bash cluster/eval.sbatch

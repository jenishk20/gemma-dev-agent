#!/bin/bash
# Paste into OOD Job Composer: self-distillation data. Our own model (local vLLM, 1 H200 per try) runs a
# submission on the 100 public TRAINING tasks, recording every model call; build_sft.py keeps the solved runs.
# One array task = one try over all 100 tasks. Throttled to 4 GPUs at a time (%4).
#   SUB=submissions/e4b_v4       E4B (T 0.6)
#   SUB=submissions/31b_v2_gen   31B: 31b_v2 at T 0.7 (same text as 31b_v2, more varied tries)
# Logs: /scratch/phalle.y/gemma-dev-agent/gda-selfgen_<jobid>_<try>.out ; runs: $GDA_ROOT/results/self_<name>_<jobid>_try<n>/
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:h200:1
#SBATCH --time=06:00:00
#SBATCH --mem=96G
#SBATCH --cpus-per-task=16
#SBATCH --job-name=gda-selfgen
#SBATCH --array=1-6%4
#SBATCH --output=/scratch/phalle.y/gemma-dev-agent/gda-selfgen_%A_%a.out
set -eo pipefail
trap 'echo "FAILED: line $LINENO exited with code $? at $(date +%T)"' ERR
REPO=/scratch/phalle.y/gemma-dev-agent
cd "$REPO"
GDA_ROOT=$(dirname "$REPO")/gda
SUB=${SUB:?set SUB, e.g. submissions/e4b_v4 or submissions/31b_v2_gen}
I=${SLURM_ARRAY_TASK_ID:-1}
JOB=${SLURM_ARRAY_JOB_ID:-$SLURM_JOB_ID}
NAME=$(basename "$SUB")
OUT=$GDA_ROOT/results/self_${NAME}_${JOB}_try$I
mkdir -p "$OUT"
TASKS=$OUT/tasks_train100.jsonl                    # the 100 training tasks only; the 29 test tasks stay unseen
"$GDA_ROOT/venv/bin/python" - "$GDA_ROOT/data/tasks.jsonl" "$TASKS" <<'PY'
import json, sys
train = set(json.load(open("training/public_split.json"))["train"])
rows = [l for l in open(sys.argv[1]) if l.strip() and json.loads(l)["instance_id"] in train]
assert len(rows) == 100, len(rows)
open(sys.argv[2], "w").write("".join(rows))
PY
echo "try $I: $NAME on 100 training tasks, recording calls | $(date)"
SUB=$SUB TASKS=$TASKS N=0 C=${C:-8} RESULTS=$OUT RECORD=1 bash cluster/eval.sbatch

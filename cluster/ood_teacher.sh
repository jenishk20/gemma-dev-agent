#!/bin/bash
# Paste THIS into OOD Job Composer: a strong hosted model (W&B Inference) runs our agent on the public TRAINING
# tasks (training/public_split.json "train", never "test"), to collect successful runs for fine-tuning Gemma.
# CPU only: the model runs at W&B; this node only runs the agent's commands and the tests.
# Hard spending stop: BUDGET dollars (counted from W&B's token prices in tools/run_local_eval.py).
# Needs your W&B key in /scratch/phalle.y/gda/.wandb_key (the key only, chmod 600). The key is never printed.
# Runs as 3 parallel jobs (one per try, --array=1-3); each has its own spending cap, so the most it can spend is 3 x BUDGET.
# Logs: /scratch/phalle.y/gemma-dev-agent/gda-teacher_<jobid>_<try>.out ; runs + spend in $GDA_ROOT/results/teacher_<jobid>_try<try>/
#SBATCH --partition=short
#SBATCH --time=04:00:00
#SBATCH --mem=48G
#SBATCH --cpus-per-task=16
#SBATCH --job-name=gda-teacher
#SBATCH --array=1-3
#SBATCH --output=/scratch/phalle.y/gemma-dev-agent/gda-teacher_%A_%a.out
set -eo pipefail
trap 'echo "FAILED: line $LINENO exited with code $? at $(date +%T)"' ERR

TEACHER=${TEACHER:-moonshotai/Kimi-K2.7-Code}   # hosted model that plays the agent
N=${N:-0}                                       # number of training tasks (0 = all 100)
C=${C:-6}                                       # tasks at the same time
BUDGET=${BUDGET:-10}                            # USD per try; every model call is refused after this

REPO=/scratch/phalle.y/gemma-dev-agent
cd "$REPO"
# Parallel tries share this checkout: take turns on the update (two pulls at once fail on git's lock).
flock /scratch/phalle.y/gda/.gitlock git pull -q || echo "git pull failed; using the code already on disk"
export GDA_ROOT=$(dirname "$REPO")/gda
export XDG_CACHE_HOME=$GDA_ROOT/cache UV_CACHE_DIR=$GDA_ROOT/cache/uv PYTHONUNBUFFERED=1 HF_HOME=$GDA_ROOT/cache/hf
PY=$GDA_ROOT/venv/bin/python
KEYF=$GDA_ROOT/.wandb_key
[ -s "$KEYF" ] || { echo "ERROR: put your W&B API key in $KEYF first (see the instructions)"; exit 1; }
chmod 600 "$KEYF"
export WANDB_API_KEY=$(tr -d ' \n\r' < "$KEYF")
TRY=${SLURM_ARRAY_TASK_ID:-1}
OUT=$GDA_ROOT/results/teacher_${SLURM_ARRAY_JOB_ID:-$SLURM_JOB_ID}_try$TRY
mkdir -p "$OUT"
echo "try $TRY | job $SLURM_JOB_ID on $(hostname) | commit $(git rev-parse --short HEAD) | teacher=$TEACHER tasks=$N concurrency=$C budget=\$$BUDGET | $(date)"

# The 100 training tasks only (the 29 test tasks stay unseen).
TRAIN=$OUT/tasks_train100.jsonl              # one copy per try, so parallel tries never race on it
"$PY" - "$GDA_ROOT/data/tasks.jsonl" "$TRAIN" <<'EOF'
import json, sys
train = set(json.load(open("training/public_split.json"))["train"])
rows = [l for l in open(sys.argv[1]) if l.strip() and json.loads(l)["instance_id"] in train]
open(sys.argv[2], "w").write("".join(rows))
print(f"{len(rows)} training tasks -> {sys.argv[2]}")
EOF

PATH=$GDA_ROOT/bootstrap/bin:$PATH "$PY" tools/run_local_eval.py --submission submissions/teacher_kimi \
  --tasks "$TRAIN" --limit "$N" --concurrency "$C" --teacher "$TEACHER" --budget-usd "$BUDGET" --results "$OUT"
echo "spend: $(cat "$OUT/teacher_spend.json" | tr -d '\n ')"
echo "finished $(date)"

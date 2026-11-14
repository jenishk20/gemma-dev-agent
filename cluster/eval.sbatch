#!/bin/bash
# Score a submission on the public tasks with one H200, exactly like Kaggle's scorer (see tools/run_local_eval.py).
#   sbatch cluster/eval.sbatch                                   (E4B baseline, 10 tasks: smoke test, ~30 min)
#   SUB=submissions/31b_baseline N=0 sbatch cluster/eval.sbatch  (all 129 tasks)
# Many tasks run at once (C), which keeps the GPU busy, so the cluster's idle-GPU watchdog does not kill the job.
# Output: gda-eval_<jobid>.out here, full results in $GDA_ROOT/results/<submission>_<time>/summary.json
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:h200:1
#SBATCH --time=06:00:00
#SBATCH --mem=96G
#SBATCH --cpus-per-task=16
#SBATCH --job-name=gda-eval
#SBATCH --output=gda-eval_%j.out
set -eo pipefail
cd "${SLURM_SUBMIT_DIR:-$(dirname "$0")/..}"
export GDA_ROOT=${GDA_ROOT:-/scratch/$USER/gda}
export HF_HOME=$GDA_ROOT/cache/hf TRITON_CACHE_DIR=$GDA_ROOT/cache/triton XDG_CACHE_HOME=$GDA_ROOT/cache PYTHONUNBUFFERED=1
SUB=${SUB:-submissions/e4b_baseline}
N=${N:-10}
C=${C:-8}
echo "job $SLURM_JOB_ID on $(hostname) | submission=$SUB tasks=$N concurrency=$C | commit $(git rev-parse --short HEAD)"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
"$GDA_ROOT/venv/bin/python" tools/run_local_eval.py --submission "$SUB" --limit "$N" --concurrency "$C"

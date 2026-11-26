#!/bin/bash
# Score a submission on the public tasks with one H200, exactly like Kaggle's scorer (see tools/run_local_eval.py).
#   From OOD Job Composer: paste cluster/ood_eval.sh (a small wrapper that runs this file).
#   sbatch cluster/eval.sbatch                                   (E4B baseline, 10 tasks: smoke test, ~30 min)
#   SUB=submissions/31b_baseline N=0 sbatch cluster/eval.sbatch  (all 129 tasks)
# Many tasks run at once (C), which keeps the GPU busy, so the cluster's idle-GPU watchdog does not kill the job.
# Log: /scratch/phalle.y/gemma-dev-agent/gda-eval_<jobid>.out (wherever you submit from); full results in $GDA_ROOT/results/<submission>_<time>/summary.json
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:h200:1
#SBATCH --time=06:00:00
#SBATCH --mem=96G
#SBATCH --cpus-per-task=16
#SBATCH --job-name=gda-eval
#SBATCH --output=/scratch/phalle.y/gemma-dev-agent/gda-eval_%j.out
set -eo pipefail
# Fixed repo path (like your other repos), so it works from OOD Job Composer, which runs jobs from its own folder.
REPO=${GDA_REPO:-/scratch/phalle.y/gemma-dev-agent}
[ -f "$REPO/cluster/eval.sbatch" ] || { echo "ERROR: repo not found at $REPO"; exit 1; }
cd "$REPO"
echo "repo: $PWD"
export GDA_ROOT=${GDA_ROOT:-$(dirname "$PWD")/gda}   # next to the repo, e.g. /scratch/phalle.y/gda
export VLLM_CONFIG_ROOT=$GDA_ROOT/cache/vllm-config
export HF_HOME=$GDA_ROOT/cache/hf TRITON_CACHE_DIR=$GDA_ROOT/cache/triton XDG_CACHE_HOME=$GDA_ROOT/cache PYTHONUNBUFFERED=1 \
       VLLM_CACHE_ROOT=$GDA_ROOT/cache/vllm TORCHINDUCTOR_CACHE_DIR=$GDA_ROOT/cache/inductor UV_PYTHON_INSTALL_DIR=$GDA_ROOT/python
SUB=${SUB:-submissions/e4b_baseline}
N=${N:-10}
C=${C:-8}
echo "job $SLURM_JOB_ID on $(hostname) | submission=$SUB tasks=$N concurrency=$C | commit $(git rev-parse --short HEAD)"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
# vLLM 0.19.1 is built with CUDA 12.9; drivers older than 575 need NVIDIA's compat libraries (see cluster/cuda_compat.sh).
DRV=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1 | cut -d. -f1)
if [ "$DRV" -lt 575 ]; then PYX=$GDA_ROOT/venv/bin/python source cluster/cuda_compat.sh; echo "driver $DRV < 575: CUDA 12.9 compat mode on ($CC_DIR)"; fi
# 10-second GPU check before the multi-minute vLLM start, so a CUDA problem shows up right away with a clear message.
"$GDA_ROOT/venv/bin/python" -c "
import torch; x = torch.randn(256, 256, device='cuda'); torch.cuda.synchronize()
print('GPU check ok:', torch.cuda.get_device_name(0), '| torch', torch.__version__, '| sum', round(float((x @ x).sum()), 2))"
# Test libraries for the sandboxes (pytest + each repo's test needs). Built here if missing, e.g. after an
# interrupted rebuild; takes a few minutes and needs internet (PyPI).
if [ ! -d "$GDA_ROOT/testdeps/site-packages/pytest" ]; then
  echo "no test libraries in $GDA_ROOT/testdeps yet: building them now"
  PATH=$GDA_ROOT/bootstrap/bin:$PATH UV_CACHE_DIR=$GDA_ROOT/cache/uv "$GDA_ROOT/venv/bin/python" tools/build_testdeps.py
fi
# DATA=$GDA_ROOT/train TASKS=$GDA_ROOT/train/tasks_verified.jsonl: run on the checked practice tasks instead
"$GDA_ROOT/venv/bin/python" tools/run_local_eval.py --submission "$SUB" --limit "$N" --concurrency "$C" ${DATA:+--data "$DATA"} ${TASKS:+--tasks "$TASKS"} ${RESULTS:+--results "$RESULTS"} ${RECORD:+--record-calls}

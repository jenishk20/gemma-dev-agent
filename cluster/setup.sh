#!/bin/bash
# One-time cluster setup (CPU job, ~1-2 h, mostly downloads). From the repo root:
#   sbatch cluster/setup.sh                      (E4B weights only)
#   MODELS="gemma-4-e4b-it-qat-w4a16-ct gemma-4-31b-it-qat-w4a16-ct" sbatch cluster/setup.sh
# Needs .env (with KAGGLE_API_KEY) copied into the repo root first. Creates under $GDA_ROOT:
#   venv/        Python 3.13 with Kaggle's exact wheelhouse (vLLM 0.19.1, swegemma, ADK, ...)
#   data/        competition data (tasks, snapshots, graphs, embeddings, wheels; 22 GB)
#   models/<m>/  Gemma 4 QAT weights from Kaggle Models (E4B 11.5 GB, 31B 23 GB)
#SBATCH --partition=short
#SBATCH --time=04:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --job-name=gda-setup
#SBATCH --output=gda-setup_%j.out
set -euo pipefail
# Find the repo: this script's own folder (bash cluster/setup.sh), else the sbatch submit dir; never guess.
HERE=$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)
if [ -n "${GDA_REPO:-}" ]; then REPO=$GDA_REPO
elif [ -f "$HERE/cluster/setup.sh" ]; then REPO=$HERE
elif [ -f "${SLURM_SUBMIT_DIR:-/nonexistent}/cluster/setup.sh" ]; then REPO=$SLURM_SUBMIT_DIR
else echo "ERROR: cannot find the repo. Run: cd /scratch/\$USER/gemma-dev-agent && sbatch cluster/setup.sh"; exit 1; fi
[ -f "$REPO/cluster/setup.sh" ] || { echo "ERROR: $REPO is not the gemma-dev-agent repo"; exit 1; }
echo "job ${SLURM_JOB_ID:-local} on $(hostname) started $(date)"
GDA_ROOT=${GDA_ROOT:-$(dirname "$REPO")/gda}   # next to the repo, e.g. /scratch/phalle.y/gda
MODELS=${MODELS:-gemma-4-e4b-it-qat-w4a16-ct}
mkdir -p "$GDA_ROOT"/{data,models,wheelhouse,results,cache}
# Everything stays under $GDA_ROOT: nothing is written to $HOME.
export UV_CACHE_DIR=$GDA_ROOT/cache/uv PIP_CACHE_DIR=$GDA_ROOT/cache/pip HF_HOME=$GDA_ROOT/cache/hf \
       UV_PYTHON_INSTALL_DIR=$GDA_ROOT/python KAGGLE_CONFIG_DIR=$GDA_ROOT/cache/kaggle XDG_CACHE_HOME=$GDA_ROOT/cache
mkdir -p "$KAGGLE_CONFIG_DIR"
echo "repo: $REPO | all downloads and installs go to: $GDA_ROOT"

[ -f "$REPO/.env" ] || { echo "Missing $REPO/.env. From the Mac: scp .env <you>@<cluster>:$REPO/"; exit 1; }
export KAGGLE_API_TOKEN=$(grep '^KAGGLE_API_KEY=' "$REPO/.env" | cut -d= -f2- | tr -d "\"' ")

# Python 3.13 (Kaggle's scorer runs 3.13) via uv; uv itself lives in a small bootstrap venv.
[ -x "$GDA_ROOT/bootstrap/bin/uv" ] || { python3 -m venv "$GDA_ROOT/bootstrap" && "$GDA_ROOT/bootstrap/bin/pip" install -q uv; }
export PATH=$GDA_ROOT/bootstrap/bin:$PATH
uv python install 3.13
[ -x "$GDA_ROOT/venv/bin/python" ] || uv venv --python 3.13 "$GDA_ROOT/venv"
PY=$GDA_ROOT/venv/bin/python
uv pip install --python "$PY" -q kaggle six
KAG=$GDA_ROOT/venv/bin/kaggle

echo "== 1/3 Kaggle's wheelhouse (same package versions as the scorer)"
if [ ! -f "$GDA_ROOT/wheelhouse/.done" ]; then
  "$KAG" datasets download metric/gemma-4-developer-agent-wheelhouse -p "$GDA_ROOT/wheelhouse" --unzip -q
  # Kaggle strips '+' from wheel names ("cu128" -> "+cu128"); restore it like the official notebook does.
  for w in "$GDA_ROOT"/wheelhouse/*.whl; do
    n=$(basename "$w"); case "$n" in *cutlass*) rm -f "$w"; continue;; esac
    [[ "$n" == *cu128* && "$n" != *+* ]] && mv "$w" "$GDA_ROOT/wheelhouse/${n/cu128/+cu128}"
  done
  touch "$GDA_ROOT/wheelhouse/.done"
fi
# Pin every wheelhouse package; anything the Kaggle base image provided comes from PyPI.
uv pip install --python "$PY" --find-links "$GDA_ROOT/wheelhouse" "$GDA_ROOT"/wheelhouse/*.whl

echo "== 2/3 competition data (22 GB)"
if [ ! -f "$GDA_ROOT/data/tasks.jsonl" ]; then
  "$KAG" competitions download -c gemma-4-developer-agent -p "$GDA_ROOT/data" -q
  (cd "$GDA_ROOT/data" && unzip -q gemma-4-developer-agent.zip && rm gemma-4-developer-agent.zip)
fi

echo "== 3/3 model weights: $MODELS"
for m in $MODELS; do
  [ -f "$GDA_ROOT/models/$m/config.json" ] && continue
  "$KAG" models instances versions download "google/gemma-4/other/$m/2" -p "$GDA_ROOT/models/$m" --untar -q
done

echo "== checks"
"$PY" -c "import vllm, torch, swegemma, adk_submission; print('vllm', vllm.__version__, '| torch', torch.__version__, '| swegemma ok')"
"$PY" -c "import json; n=sum(1 for _ in open('$GDA_ROOT/data/tasks.jsonl')); print(n, 'tasks')"
ls "$GDA_ROOT/data/snapshots" | wc -l | xargs echo "snapshots:"
du -sh "$GDA_ROOT"/models/* "$GDA_ROOT/data"
cd "$REPO" && for s in submissions/*_baseline.zip; do "$PY" tools/validate_submission.py "$s" | tail -1; done
echo "SETUP DONE. Next: sbatch cluster/eval.sbatch"

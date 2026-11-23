#!/bin/bash
# Paste THIS into OOD Job Composer: builds and checks the practice tasks for training (CPU only, no GPU).
#   1. turns the mined PRs in training/candidates.jsonl into tasks under $GDA_ROOT/train (repo snapshots + fixes)
#   2. runs each task's tests with the official fix and without it; keeps the fair ones in train/tasks_verified.jsonl
# All unpacking happens on the node's own disk; only finished files go to /scratch (the first run stalled there).
# Safe to re-run: every step skips work that is already done. Log: /scratch/phalle.y/gemma-dev-agent/gda-train-data_<jobid>.out
#SBATCH --partition=short
#SBATCH --time=12:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=16
#SBATCH --job-name=gda-train-data
#SBATCH --output=/scratch/phalle.y/gemma-dev-agent/gda-train-data_%j.out
set -eo pipefail
trap 'echo "FAILED: line $LINENO exited with code $? at $(date +%T)"' ERR
REPO=/scratch/phalle.y/gemma-dev-agent
cd "$REPO"
git pull -q || echo "git pull failed; using the code already on disk"
export GDA_ROOT=$(dirname "$REPO")/gda
export XDG_CACHE_HOME=$GDA_ROOT/cache UV_CACHE_DIR=$GDA_ROOT/cache/uv PYTHONUNBUFFERED=1
PY=$GDA_ROOT/venv/bin/python
export TRAIN_WORK_DIR=${TMPDIR:-/tmp}/gda_train_${SLURM_JOB_ID:-$$}
mkdir -p "$TRAIN_WORK_DIR"; trap 'rm -rf "$TRAIN_WORK_DIR"' EXIT
echo "node disk for unpacking: $TRAIN_WORK_DIR ($(df -h "$TRAIN_WORK_DIR" | awk 'NR==2{print $4}') free)"
echo "job $SLURM_JOB_ID on $(hostname) | commit $(git rev-parse --short HEAD) | $(date)"

echo "== 1/2 $(date +%T) build the practice tasks"
"$PY" tools/build_train_tasks.py --workers 16

echo "== 2/2 $(date +%T) check them (official fix passes, tests fail without it)"
PATH=$GDA_ROOT/bootstrap/bin:$PATH "$PY" tools/check_train_tasks.py --concurrency 16
echo "finished $(date)"

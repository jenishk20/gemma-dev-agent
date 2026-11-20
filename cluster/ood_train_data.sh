#!/bin/bash
# Paste THIS into OOD Job Composer: builds and checks the practice tasks for training (CPU only, no GPU).
#   1. prints what the competition's code-search files look like (needed to build them for the new tasks later)
#   2. turns the mined PRs in training/candidates.jsonl into tasks under $GDA_ROOT/train (repo snapshots + fixes)
#   3. runs each task's tests with the official fix and without it; keeps the fair ones in train/tasks_verified.jsonl
# All unpacking happens on the node's own disk; only finished files go to /scratch (the first run stalled there).
# Safe to re-run: every step skips work that is already done. Log: /scratch/phalle.y/gemma-dev-agent/gda-train-data_<jobid>.out
#SBATCH --partition=short
#SBATCH --time=12:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=16
#SBATCH --job-name=gda-train-data
#SBATCH --output=/scratch/phalle.y/gemma-dev-agent/gda-train-data_%j.out
set -eo pipefail
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

echo "== 1/3 $(date +%T) what the code-search files look like (to build them for the new tasks later)"
ls "$GDA_ROOT/data/graphs" | head -5; ls "$GDA_ROOT/data/graphs" | wc -l
ls "$GDA_ROOT/data/embeddings" | head -5
"$PY" - <<'EOF'
import json, os, glob
f = sorted(glob.glob(os.environ["GDA_ROOT"] + "/data/graphs/*.json"))[0]
g = json.load(open(f))
print(f, "| keys:", list(g)[:8], "| nodes:", len(g.get("nodes", [])))
for n in g["nodes"][:3]:
    print("NODE", json.dumps({k: (str(v)[:120]) for k, v in n.items()}))
for e in (g.get("edges") or g.get("links") or [])[:3]:
    print("EDGE", json.dumps(e)[:300])
print("node types:", sorted({n.get("type") for n in g["nodes"]})[:20])
print("edge kinds:", sorted({e.get("relation") or e.get("type") for e in (g.get("edges") or g.get("links") or [])})[:20])
EOF

echo "== 2/3 $(date +%T) build the practice tasks"
"$PY" tools/build_train_tasks.py --workers 16

echo "== 3/3 $(date +%T) check them (official fix passes, tests fail without it)"
PATH=$GDA_ROOT/bootstrap/bin:$PATH "$PY" tools/check_train_tasks.py --concurrency 16
echo "finished $(date)"

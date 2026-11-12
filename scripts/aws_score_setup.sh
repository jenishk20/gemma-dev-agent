#!/usr/bin/env bash
# On a fresh Ubuntu 24.04 + Docker machine, after the repo is copied to ~/gsb:
#   bash gsb/scripts/aws_score_setup.sh [concurrency]
# Installs BaxBench's Python deps in a venv and starts scripts/score_all.sh detached.
set -euo pipefail
cd "$HOME/gsb"
python3 -m venv .venv
.venv/bin/pip install -q -r bench/requirements-score.txt
mkdir -p third_party logs
ln -sfn ../bench third_party/baxbench
echo "code dirs: $(find bench/results -type d -name code | wc -l)"
(cd bench && ../.venv/bin/python -c "import sys; sys.path.insert(0, 'src'); import env, scenarios; print(len(env.all_envs), 'envs,', len(scenarios.all_scenarios), 'scenarios')")
PY="$HOME/gsb/.venv/bin/python" setsid nohup bash scripts/score_all.sh "${1:-24}" > logs/score_all.out 2>&1 < /dev/null &
sleep 3
pgrep -f score_all.sh > /dev/null && echo "score_all started"

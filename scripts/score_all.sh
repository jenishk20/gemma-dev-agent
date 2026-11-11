#!/usr/bin/env bash
# Score every condition with unmodified BaxBench tests in Docker (run inside the codespace).
#   bash scripts/score_all.sh [concurrency]      -> bench/results/**/test_results.json, results/summary.json
set -uo pipefail
cd "$(dirname "$0")/../bench"
J=${1:-12}
export OPENAI_API_KEY=x TOGETHER_API_KEY=x ANTHROPIC_API_KEY=x OPENROUTER_API_KEY=x
mkdir -p logs
(while true; do sleep 300; docker image prune -f --filter label=language >/dev/null 2>&1; done) & PRUNER=$!
C=(--n_samples 5 --temperature 0.4 --envs Python-Flask Python-FastAPI --max_concurrent_runs $J --prune_docker --mode test)
python src/main.py --models google/gemma-4-31b-it --openrouter "${C[@]}" > logs/test_base.log 2>&1; echo "base done ($?)"
python src/main.py --models google/gemma-4-31b-it --openrouter --safety_prompt generic "${C[@]}" > logs/test_generic.log 2>&1; echo "security prompt done ($?)"
python src/main.py --models gemma-4-31b-it-selfreview "${C[@]}" > logs/test_selfreview.log 2>&1; echo "self-review done ($?)"
for m in gemma-4-12b-it-base gemma-4-12b-it-sft; do
  [ -d results/$m ] && { python src/main.py --models $m "${C[@]}" > logs/test_$m.log 2>&1; echo "$m done ($?)"; }
done
kill $PRUNER
cd .. && python scripts/summarize.py

#!/usr/bin/env bash
# Score every condition with unmodified BaxBench tests in Docker (run inside the codespace).
#   bash scripts/score_all.sh [concurrency]      -> bench/results/**/test_results.json, results/summary.json
set -uo pipefail
cd "$(dirname "$0")/../bench"
J=${1:-12}
PY=${PY:-python}
export OPENAI_API_KEY=x TOGETHER_API_KEY=x ANTHROPIC_API_KEY=x OPENROUTER_API_KEY=x
mkdir -p logs
C=(--n_samples 5 --temperature 0.4 --envs Python-Flask Python-FastAPI --max_concurrent_runs $J --prune_docker --mode test)
$PY src/main.py --models google/gemma-4-31b-it --openrouter "${C[@]}" > logs/test_base.log 2>&1; echo "base done ($?)"
$PY src/main.py --models google/gemma-4-31b-it --openrouter --safety_prompt generic "${C[@]}" > logs/test_generic.log 2>&1; echo "security prompt done ($?)"
$PY src/main.py --models gemma-4-31b-it-selfreview "${C[@]}" > logs/test_selfreview.log 2>&1; echo "self-review done ($?)"
for m in gemma-4-12b-it-base gemma-4-12b-it-sft; do
  [ -d results/$m ] && { $PY src/main.py --models $m "${C[@]}" > logs/test_$m.log 2>&1; echo "$m done ($?)"; }
done
# Docker builds can crash under parallel load (containerd races on the shared image tag). Such
# samples say "which failed to build"; clear their results and re-test them at low concurrency.
for pass in 1 2 3; do
  bad=$(grep -l "which failed to build" results/*/*/Python-*/temp0.4-openapi-*/sample*/test.log 2>/dev/null)
  [ -z "$bad" ] && break
  echo "re-testing $(echo "$bad" | wc -l) samples that failed to build (pass $pass)"
  for f in $bad; do rm -f "$(dirname "$f")/test_results.json"; done
  C2=(--n_samples 5 --temperature 0.4 --envs Python-Flask Python-FastAPI --max_concurrent_runs 4 --mode test)
  $PY src/main.py --models google/gemma-4-31b-it --openrouter "${C2[@]}" >> logs/retest.log 2>&1
  $PY src/main.py --models google/gemma-4-31b-it --openrouter --safety_prompt generic "${C2[@]}" >> logs/retest.log 2>&1
  $PY src/main.py --models gemma-4-31b-it-selfreview "${C2[@]}" >> logs/retest.log 2>&1
done
cd .. && $PY scripts/summarize.py

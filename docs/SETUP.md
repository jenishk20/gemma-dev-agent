# Setup notes

- `bench/` is BaxBench v1.0.0 (MIT, https://github.com/logic-star-ai/baxbench, commit de885cd) with one
  local change in `bench/src/env/base.py`: after every `FROM` line, apt is switched to the
  snapshot.debian.org mirrors that the Debian base image already lists, because on arm64 Macs
  deb.debian.org's bullseye-security index lists a sqlite3 .deb that returns 404. It only changes
  where apt downloads packages from (same package versions); tests and exploits are untouched.
- `bench/results/` holds every generated sample (code only); scores are produced by
  `scripts/score_all.sh` in the GitHub codespace (Linux, Docker-in-Docker, 16 cores).
- Generation: Gemma 4 31B-it via OpenRouter (`google/gemma-4-31b-it`), temperature 0.4, 5 samples
  per task, BaxBench's OpenAPI spec prompt. Security prompt = BaxBench `--safety_prompt generic`.
  Self-review = `scripts/baxbench_review.py`.

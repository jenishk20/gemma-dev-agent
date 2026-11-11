# Works but Hackable: Gemma 4 on BaxBench

How much do prompting, self-review and fine-tuning close the security gap of Gemma 4 on real backend apps?
Benchmark: [BaxBench](https://github.com/logic-star-ai/baxbench) (MIT), Python Flask + FastAPI.

| Path | Contents |
|---|---|
| `scripts/` | self-review pass, cluster SFT and generation, summaries |
| `data/` | verified secure-coding SFT data (from the CyberNemo project) |
| `results/` | per-condition score summaries |
| `third_party/baxbench` | BaxBench checkout (not committed; one local fix for arm64 Docker builds, see `docs/SETUP.md`) |

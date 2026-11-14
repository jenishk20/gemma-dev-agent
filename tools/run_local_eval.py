"""Score a submission folder on the public tasks, the same way Kaggle's scorer does.

  python tools/run_local_eval.py --submission submissions/e4b_baseline --limit 10 --concurrency 8

Mirrors Kaggle's getting-started notebook: starts vLLM with the scorer's settings
(max_model_len 32768, gemma4 tool/reasoning parsers, LoRA if adapters/ exists), then runs
swegemma's Evaluator with the subprocess sandbox (no Docker needed) and the submission's
eval_config.yaml budgets. Results go to --results (summary.json, patches/, traces/, logs/).

Paths default to the layout cluster/setup.sh creates under $GDA_ROOT (/scratch/$USER/gda).
"""
import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(os.environ.get("GDA_ROOT", Path(__file__).resolve().parents[2] / "gda"))  # next to the repo
ALLOWED = {"gemma-4-31b-it-qat-w4a16-ct", "gemma-4-12b-it-qat-w4a16-ct",
           "gemma-4-e4b-it-qat-w4a16-ct", "gemma-4-e2b-it-qat-w4a16-ct"}
EXTRA_ARGS = {"gemma-4-12b-it-qat-w4a16-ct": ("--hf-overrides", '{"architectures": ["Gemma4ForCausalLM"], "model_type": "gemma4"}')}

for k, v in {"VLLM_NO_USAGE_STATS": "1", "VLLM_WORKER_MULTIPROC_METHOD": "spawn", "VLLM_ENGINE_READY_TIMEOUT_S": "1200",
             "TRANSFORMERS_OFFLINE": "1", "LITELLM_LOCAL_MODEL_COST_MAP": "True", "LITELLM_TELEMETRY": "False",
             "LITELLM_LOG": "WARNING", "OPENAI_API_KEY": "EMPTY", "OTEL_SDK_DISABLED": "true",
             "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}.items():
    os.environ.setdefault(k, v)
# Clusters often route traffic through an HTTP proxy (http_proxy/https_proxy). Calls to the local vLLM server
# (health check, agent requests) must bypass it, or they go to the proxy and never reach 127.0.0.1:8000.
for k in ("NO_PROXY", "no_proxy"):
    os.environ[k] = ",".join(x for x in (os.environ.get(k, ""), "127.0.0.1,localhost,::1") if x)


def pick_tasks(tasks, limit, task_ids, seed):
    if task_ids:
        return [t for t in tasks if t.instance_id in set(task_ids)]
    order = sorted(tasks, key=lambda t: t.instance_id)
    random.Random(seed).shuffle(order)  # fixed mix of repos, same subset every run
    return order[:limit] if limit else order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", required=True, help="submission folder (agent.yaml at its root)")
    ap.add_argument("--data", default=str(ROOT / "data"), help="unpacked competition data")
    ap.add_argument("--models-dir", default=str(ROOT / "models"), help="contains <model-name>/ weight folders")
    ap.add_argument("--results", default=None)
    ap.add_argument("--limit", type=int, default=10, help="number of tasks (0 = all 129)")
    ap.add_argument("--task-ids", nargs="*")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--gpu-mem", type=float, default=0.90)
    args = ap.parse_args()

    import litellm
    import torch
    from adk_submission import VllmConfig, VllmServer, discover_adapters
    from adk_submission.discovery import discover_declared_models
    from google.adk.agents.context_cache_config import ContextCacheConfig
    from google.adk.apps._configs import EventsCompactionConfig
    from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS, EvalConfig, build_submission_limits
    from swegemma.evaluate import Evaluator
    from swegemma.models import load_tasks

    litellm.drop_params = True
    sub, data = Path(args.submission).resolve(), Path(args.data)
    models = discover_declared_models(sub)
    assert len(models) == 1 and next(iter(models)) in ALLOWED, f"declared models: {sorted(models)}"
    model = next(iter(models))
    model_path = Path(args.models_dir) / model
    assert (model_path / "config.json").exists(), f"weights not found in {model_path} (run cluster/setup.sh)"

    adapters = discover_adapters(str(sub), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
    amap = getattr(adapters, "adapters", None) or {}
    ranks = [r for i in amap.values() if (r := getattr(i, "rank", None))]
    gpus = torch.cuda.device_count()
    server = VllmServer(VllmConfig(
        model=str(model_path), port=8000, host="127.0.0.1", tool_call_parser="gemma4", reasoning_parser="gemma4",
        max_model_len=32768, dtype="bfloat16", gpu_memory_utilization=args.gpu_mem, enable_auto_tool_choice=True,
        enable_lora=bool(amap), max_loras=max(1, len(amap)), max_lora_rank=max(ranks) if ranks else 128,
        scheduler_reserve_full_isl=False, tensor_parallel_size=4 if gpus >= 4 else (2 if gpus >= 2 else 1),
        startup_timeout=60 * 20, extra_args=EXTRA_ARGS.get(model, ()),
    ), adapter_manifest=adapters)

    ev = (yaml.safe_load((sub / "eval_config.yaml").read_text()) or {}).get("evaluation", {}) if (sub / "eval_config.yaml").exists() else {}
    tasks = pick_tasks(load_tasks(data / "tasks.jsonl"), args.limit, args.task_ids, args.seed)
    results = Path(args.results or (ROOT / "results" / f"{sub.name}_{time.strftime('%m%d-%H%M')}"))
    results.mkdir(parents=True, exist_ok=True)
    (results / "run_args.json").write_text(json.dumps({**vars(args), "model": model, "eval_config": ev,
                                                       "task_ids": [t.instance_id for t in tasks]}, indent=1))
    print(f"model={model} gpus={gpus} tasks={len(tasks)} concurrency={args.concurrency} budgets={ev} -> {results}", flush=True)

    server.start()
    try:
        registry = server.create_model_registry(aliases=[model], model_prefix="openai/", api_key="EMPTY")
        limits, gen = build_submission_limits()
        cfg = EvalConfig(
            tasks_path=data / "tasks.jsonl", snapshots_dir=data / "snapshots", results_dir=results,
            submission_dir=sub, models=registry, sandbox="subprocess",
            timeout_seconds=int(ev.get("timeout_seconds", 300)),
            verification_timeout_seconds=int(ev.get("verification_timeout_seconds", 300)),
            max_time_minutes=float(ev.get("max_time_minutes", 60.0)),
            max_tool_calls=int(ev.get("max_tool_calls", 100)),
            max_turns=int(ev["max_turns"]) if "max_turns" in ev else None,
            task_ids=[t.instance_id for t in tasks], concurrency=args.concurrency, display_mode="quiet",
            limits=limits, generation_constraints=gen, adapter_manifest=adapters,
            context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
            events_compaction_config=EventsCompactionConfig(compaction_interval=15, overlap_size=2,
                                                            token_threshold=14336, event_retention_size=5),
            graph_dir=str(data / "graphs"), embeddings_dir=str(data / "embeddings"), wheels_dir=data / "wheels",
        )
        t0 = time.time()
        out = asyncio.run(Evaluator(cfg).run())
        rate = getattr(out, "resolution_rate", None)
        print(f"\nDONE in {(time.time() - t0) / 60:.1f} min: resolution rate {rate} on {len(tasks)} tasks. Details: {results}/summary.json")
    finally:
        server.stop()


if __name__ == "__main__":
    sys.exit(main())

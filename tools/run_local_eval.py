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


def use_testdeps():
    """Give every subprocess sandbox pytest and this task's test libraries (see tools/testenv.py)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import testenv
    testenv.install()


# Teacher mode: the agent runs on a hosted model (W&B Inference) instead of a local vLLM, e.g. to collect
# training runs from a stronger model. USD per million tokens (input, output, cached input), from W&B's price list
# (coreweave.com/forge-pricing/inference-agents, read 2026-11-25).
TEACHER_PRICES = {
    "moonshotai/Kimi-K2.7-Code": (0.60, 3.00, 0.12),
    "deepseek-ai/DeepSeek-V4-Pro-0813": (1.31, 3.96, 0.044),
    "zai-org/GLM-5.3": (0.75, 3.00, 0.19),
    "deepseek-ai/DeepSeek-V4.1-Flash": (0.13, 0.65, 0.002),
    "google/gemma-4-31B-it": (0.10, 0.34, 0.10),
}


class BudgetGuard:
    """Counts the dollars spent on hosted-model calls and refuses every call once the budget is used up."""

    def __init__(self, model, budget_usd, log_file):
        assert model in TEACHER_PRICES, f"no price for {model}; add it to TEACHER_PRICES first"
        self.price, self.budget, self.log_file = TEACHER_PRICES[model], budget_usd, log_file
        self.spent, self.calls, self.tokens_in, self.tokens_cached, self.tokens_out, self.next_print = 0.0, 0, 0, 0, 0, 0.5
        self.failures = 0

    def add(self, usage):
        if usage is None:
            return
        get = (lambda o, k: o.get(k) if isinstance(o, dict) else getattr(o, k, None))
        tin, tout = get(usage, "prompt_tokens") or 0, get(usage, "completion_tokens") or 0
        det = get(usage, "prompt_tokens_details")
        cached = (get(det, "cached_tokens") or 0) if det is not None else 0
        pin, pout, pcache = self.price
        self.spent += ((tin - cached) * pin + cached * pcache + tout * pout) / 1e6
        self.calls += 1
        self.tokens_in, self.tokens_cached, self.tokens_out = self.tokens_in + tin, self.tokens_cached + cached, self.tokens_out + tout
        self.log_file.write_text(json.dumps({"usd": round(self.spent, 4), "budget_usd": self.budget, "calls": self.calls,
                                             "tokens_in": self.tokens_in, "tokens_cached": self.tokens_cached,
                                             "tokens_out": self.tokens_out, "failed_calls": self.failures}, indent=1))
        if self.spent >= self.next_print:
            print(f"  [teacher] spent ${self.spent:.2f} of ${self.budget:.2f} ({self.calls} calls)", flush=True)
            self.next_print += 0.5

    def install(self):
        import google.adk.models.lite_llm as lm
        lm._ensure_litellm_imported()                      # ADK imports litellm lazily and would overwrite our wrapper
        orig, guard = lm.acompletion, self

        def one_reasoning_field(messages):
            # adk_submission's reasoning patch copies past thoughts into both `reasoning_content` and `reasoning`.
            # vLLM accepts that; W&B Inference rejects it ("duplicate field `reasoning_content`"), which ended
            # every task right after its first tool call. Keep `reasoning_content` only.
            for m in messages or []:
                get = m.get if hasattr(m, "get") else (lambda k, d=None, m=m: getattr(m, k, d))
                if get("reasoning_content") is not None and get("reasoning") is not None:
                    if isinstance(m, dict):
                        m.pop("reasoning", None)
                    else:
                        setattr(m, "reasoning", None)

        async def acompletion(*a, **kw):
            if guard.spent >= guard.budget:
                raise RuntimeError(f"teacher budget of ${guard.budget:.2f} reached; no more model calls")
            one_reasoning_field(kw.get("messages"))
            try:
                res = await orig(*a, **kw)
            except Exception as e:                         # make failed calls visible in the job log
                guard.failures += 1
                if guard.failures <= 5:
                    print(f"  [teacher] model call failed ({guard.failures}): {str(e)[:300]}", flush=True)
                raise
            if hasattr(res, "__aiter__"):                  # streaming: usage arrives on the last chunk
                async def counted():
                    async for chunk in res:
                        guard.add(getattr(chunk, "usage", None))
                        yield chunk
                return counted()
            guard.add(getattr(res, "usage", None))
            return res
        lm.acompletion = acompletion


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
    ap.add_argument("--tasks", help="tasks file (default: <data>/tasks.jsonl), e.g. <data>/tasks_verified.jsonl")
    ap.add_argument("--models-dir", default=str(ROOT / "models"), help="contains <model-name>/ weight folders")
    ap.add_argument("--results", default=None)
    ap.add_argument("--limit", type=int, default=10, help="number of tasks (0 = all 129)")
    ap.add_argument("--task-ids", nargs="*")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--gpu-mem", type=float, default=0.90)
    ap.add_argument("--port", type=int, default=0, help="vLLM port (0 = any free one, so two jobs on one node never clash)")
    ap.add_argument("--teacher", help="run the agent on this hosted model instead of local weights, e.g. moonshotai/Kimi-K2.7-Code")
    ap.add_argument("--teacher-base", default="https://api.inference.wandb.ai/v1")
    ap.add_argument("--budget-usd", type=float, default=5.0, help="teacher mode: hard stop on hosted-model spending")
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
    use_testdeps()
    sub, data = Path(args.submission).resolve(), Path(args.data)
    tasks_file = Path(args.tasks) if args.tasks else data / "tasks.jsonl"
    models = discover_declared_models(sub)
    assert len(models) == 1 and next(iter(models)) in ALLOWED, f"declared models: {sorted(models)}"
    model = next(iter(models))
    model_path = Path(args.models_dir) / model
    assert args.teacher or (model_path / "config.json").exists(), f"weights not found in {model_path} (run cluster/setup.sh)"

    adapters = discover_adapters(str(sub), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
    amap = getattr(adapters, "adapters", None) or {}
    ranks = [r for i in amap.values() if (r := getattr(i, "rank", None))]
    gpus = torch.cuda.device_count() if not args.teacher else 0
    if not args.port:
        import socket
        with socket.socket() as sk:
            sk.bind(("127.0.0.1", 0))
            args.port = sk.getsockname()[1]
    server = VllmServer(VllmConfig(
        model=str(model_path), port=args.port, host="127.0.0.1", tool_call_parser="gemma4", reasoning_parser="gemma4",
        max_model_len=32768, dtype="bfloat16", gpu_memory_utilization=args.gpu_mem, enable_auto_tool_choice=True,
        enable_lora=bool(amap), max_loras=max(1, len(amap)), max_lora_rank=max(ranks) if ranks else 128,
        scheduler_reserve_full_isl=False, tensor_parallel_size=4 if gpus >= 4 else (2 if gpus >= 2 else 1),
        startup_timeout=60 * 20, extra_args=EXTRA_ARGS.get(model, ()),
    ), adapter_manifest=adapters)

    ev = (yaml.safe_load((sub / "eval_config.yaml").read_text()) or {}).get("evaluation", {}) if (sub / "eval_config.yaml").exists() else {}
    tasks = pick_tasks(load_tasks(tasks_file), args.limit, args.task_ids, args.seed)
    results = Path(args.results or (ROOT / "results" / f"{sub.name}_{time.strftime('%m%d-%H%M')}"))
    results.mkdir(parents=True, exist_ok=True)
    (results / "run_args.json").write_text(json.dumps({**vars(args), "model": model, "eval_config": ev,
                                                       "task_ids": [t.instance_id for t in tasks]}, indent=1))
    print(f"model={model} gpus={gpus} port={args.port} tasks={len(tasks)} concurrency={args.concurrency} budgets={ev} -> {results}", flush=True)

    if args.teacher:                                       # hosted model: no local server, a hard spending cap
        from adk_submission.registry import ModelRegistry
        from adk_submission.resolvers.generation import install_litellm_reasoning_patch
        from google.adk.models.lite_llm import LiteLlm
        key = os.environ.get("WANDB_API_KEY")
        assert key, "teacher mode needs WANDB_API_KEY in the environment"
        guard = BudgetGuard(args.teacher, args.budget_usd, results / "teacher_spend.json")
        guard.install()
        install_litellm_reasoning_patch()
        registry = ModelRegistry()
        registry.register(model, LiteLlm(model=f"openai/{args.teacher}", api_base=args.teacher_base, api_key=key))
        print(f"teacher mode: {args.teacher} via {args.teacher_base}, budget ${args.budget_usd:.2f}", flush=True)
        server.start = server.stop = lambda *a, **k: None
    server.start()
    try:
        if not args.teacher:
            registry = server.create_model_registry(aliases=[model], model_prefix="openai/", api_key="EMPTY")
        limits, gen = build_submission_limits()
        cfg = EvalConfig(
            tasks_path=tasks_file, snapshots_dir=data / "snapshots", results_dir=results,
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
        gold_file = ROOT / "results" / "gold_status.json"
        if gold_file.exists():  # written by tools/check_gold.py: tasks whose official fix passes on this machine
            gold = json.loads(gold_file.read_text())
            res = [r for r in getattr(out, "task_results", []) if gold.get(getattr(r, "instance_id", None))]
            if res:
                print(f"on the {len(res)} tasks whose official fix passes locally: {sum(r.resolved for r in res)}/{len(res)} resolved")
    finally:
        server.stop()


if __name__ == "__main__":
    sys.exit(main())

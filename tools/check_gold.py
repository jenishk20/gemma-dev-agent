"""Answer-key check: run the harness's own test step with the OFFICIAL fix (task.patch) instead of the agent's.

  python tools/check_gold.py                 # 10 tasks: the same ones the default 10-task eval uses
  python tools/check_gold.py --task-ids rich_3052 fastapi_14962
  python tools/check_gold.py --from-results /scratch/phalle.y/gda/results/<run>   # same tasks as that run

If the official fixes pass, the local test setup is sound and a 0 score is the model's doing.
If they fail too, the test environment (subprocess sandbox, wheels, deps) is broken. No GPU needed.
"""
import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_local_eval import ROOT, pick_tasks, use_testdeps  # noqa: E402  (also sets the proxy bypass and env defaults)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--task-ids", nargs="*")
    ap.add_argument("--from-results", help="results folder of an eval run: check the same tasks")
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()

    from swegemma.config import EvalConfig
    from swegemma.deduplication import resolve_task_snapshot_paths
    from swegemma.evaluate import Evaluator
    from swegemma.harness.verification import verify_task
    from swegemma.models import load_tasks

    use_testdeps()
    data = Path(args.data)
    ids = args.task_ids
    if args.from_results:
        ids = json.loads((Path(args.from_results) / "run_args.json").read_text())["task_ids"]
    tasks = pick_tasks(load_tasks(data / "tasks.jsonl"), args.limit, ids, args.seed)
    out = Path(tempfile.mkdtemp(prefix="gold_", dir=str(ROOT / "results")))
    cfg = EvalConfig(tasks_path=data / "tasks.jsonl", snapshots_dir=data / "snapshots", results_dir=out,
                     submission_dir=out, models=None, sandbox="subprocess", wheels_dir=data / "wheels",
                     graph_dir=str(data / "graphs"), embeddings_dir=str(data / "embeddings"))
    ev = Evaluator(cfg)
    print(f"checking the official fix on {len(tasks)} tasks -> {out}", flush=True)

    async def one(task, sem):
        async with sem:
            task = ev._hydrate_task_from_secret(task)
            snap, base, patch = resolve_task_snapshot_paths(cfg.snapshots_dir, task.instance_id, task.repo)
            t0 = time.perf_counter()
            r = await verify_task(ev.docker, cfg, task, snap, base_snapshot_path=base, patch_path=patch,
                                  agent_patch=task.patch, start_time=t0)
            tail = " | ".join((r.test_output or r.error or "").strip().splitlines()[-4:])[:500]
            print(f"{task.instance_id:16s} resolved={r.resolved!s:5s} exit={r.test_exit_code} "
                  f"{time.perf_counter() - t0:.0f}s\n    {tail}", flush=True)
            return r

    async def run():
        sem = asyncio.Semaphore(args.concurrency)
        return await asyncio.gather(*(one(t, sem) for t in tasks))

    rs = asyncio.run(run())
    ok = sum(r.resolved for r in rs)
    print(f"\nOFFICIAL FIX PASSES: {ok}/{len(rs)}  "
          + ("-> test setup works; the 0 score is the model" if ok >= 0.8 * len(rs)
             else "-> test setup is broken on this machine; fix it before trusting any score"))


if __name__ == "__main__":
    sys.exit(main())

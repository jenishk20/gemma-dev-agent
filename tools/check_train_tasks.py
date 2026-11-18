"""Step 3 of the training data: keep only the practice tasks that are a fair test.

  $GDA_ROOT/venv/bin/python tools/check_train_tasks.py [--limit N] [--concurrency 16]

For every task in $GDA_ROOT/train/tasks.jsonl, runs the harness's own test step (the one the Kaggle scorer uses)
twice, no GPU needed:
  1. with the official fix   -> must be resolved (the tests and our test environment work)
  2. with no real fix        -> must NOT be resolved (the tests really check the fix)
Tasks that pass both checks go to $GDA_ROOT/train/tasks_verified.jsonl; one line per task in check_results.jsonl.
Safe to stop and re-run: tasks already checked are skipped.
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_local_eval import ROOT, use_testdeps  # noqa: E402  (also sets the proxy bypass and env defaults)

# A change to a harmless new file: the harness then runs the tests on the unfixed code.
NOOP_PATCH = ("diff --git a/_swe_noop.txt b/_swe_noop.txt\nnew file mode 100644\nindex 0000000..d00491f\n"
              "--- /dev/null\n+++ b/_swe_noop.txt\n@@ -0,0 +1 @@\n+1\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "train"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=16)
    args = ap.parse_args()

    import tempfile
    from swegemma.config import EvalConfig
    from swegemma.deduplication import resolve_task_snapshot_paths
    from swegemma.evaluate import Evaluator
    from swegemma.harness.verification import verify_task
    from swegemma.models import load_tasks

    use_testdeps()
    data = Path(args.data)
    tasks = load_tasks(data / "tasks.jsonl")
    if args.limit:
        tasks = tasks[: args.limit]
    res_file = data / "check_results.jsonl"
    done = {}
    if res_file.exists():
        for l in res_file.read_text().splitlines():
            if l.strip():
                d = json.loads(l)
                done[d["instance_id"]] = d
    todo = [t for t in tasks if t.instance_id not in done]
    out = Path(tempfile.mkdtemp(prefix="check_", dir=str(ROOT / "results")))
    cfg = EvalConfig(tasks_path=data / "tasks.jsonl", snapshots_dir=data / "snapshots", results_dir=out,
                     submission_dir=out, models=None, sandbox="subprocess", wheels_dir=data / "wheels",
                     graph_dir=str(data / "graphs"), embeddings_dir=str(data / "embeddings"))
    ev = Evaluator(cfg)
    print(f"{len(tasks)} tasks, {len(done)} already checked, checking {len(todo)} (logs in {out})", flush=True)

    async def run_tests(task, patch):
        snap, base, p = resolve_task_snapshot_paths(cfg.snapshots_dir, task.instance_id, task.repo)
        return await verify_task(ev.docker, cfg, task, snap, base_snapshot_path=base, patch_path=p,
                                 agent_patch=patch, start_time=time.perf_counter())

    async def one(task, sem, fh):
        async with sem:
            t0 = time.perf_counter()
            try:
                gold = await run_tests(task, task.patch)
                (out / f"{task.instance_id}.gold.log").write_text(gold.test_output or gold.error or "")
                noop = None
                if gold.resolved:
                    noop = await run_tests(task, NOOP_PATCH)
                    (out / f"{task.instance_id}.nofix.log").write_text(noop.test_output or noop.error or "")
                rec = {"instance_id": task.instance_id, "gold_passes": bool(gold.resolved),
                       "fails_without_fix": None if noop is None else not noop.resolved,
                       "seconds": round(time.perf_counter() - t0)}
            except Exception as e:
                rec = {"instance_id": task.instance_id, "gold_passes": False, "fails_without_fix": None,
                       "error": str(e)[:200], "seconds": round(time.perf_counter() - t0)}
            rec["usable"] = bool(rec["gold_passes"] and rec["fails_without_fix"])
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            done[task.instance_id] = rec
            n = len(done)
            if n % 20 == 0:
                ok = sum(d["usable"] for d in done.values())
                print(f"  {n}/{len(tasks)} checked, {ok} usable", flush=True)

    async def run():
        sem = asyncio.Semaphore(args.concurrency)
        with res_file.open("a") as fh:
            await asyncio.gather(*(one(t, sem, fh) for t in todo))

    asyncio.run(run())
    usable = {i for i, d in done.items() if d["usable"]}
    rows = [l for l in (data / "tasks.jsonl").read_text().splitlines()
            if l.strip() and json.loads(l)["instance_id"] in usable]
    (data / "tasks_verified.jsonl").write_text("\n".join(rows) + "\n")
    gold_fail = sum(not d["gold_passes"] for d in done.values())
    trivial = sum(d["gold_passes"] and d["fails_without_fix"] is False for d in done.values())
    by_repo = {}
    for l in rows:
        r = json.loads(l)["repo"]
        by_repo[r] = by_repo.get(r, 0) + 1
    print(f"\nUSABLE {len(usable)}/{len(done)} {by_repo} | official fix fails here: {gold_fail} | "
          f"tests pass even without the fix: {trivial} -> {data / 'tasks_verified.jsonl'}")


if __name__ == "__main__":
    sys.exit(main())

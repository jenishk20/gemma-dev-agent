"""Export BaxBench prompts (exactly what BaxBench sends a model) so they can be generated offline
on the H200 cluster. One row per (scenario, framework).

  third_party/baxbench/.venv/bin/python scripts/export_prompts.py --envs Python-Flask Python-FastAPI
writes data/baxbench_prompts.jsonl: {"scenario", "env", "system", "user"}
"""
import argparse, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "third_party" / "baxbench" / "src"))
import env as bax_env  # noqa: E402
from prompts import _SYSTEM_PROMPT  # noqa: E402
from scenarios import all_scenarios  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--envs", nargs="+", default=["Python-Flask", "Python-FastAPI"])
ap.add_argument("--safety_prompt", default="none")
ap.add_argument("--out", default=str(ROOT / "data" / "baxbench_prompts.jsonl"))
a = ap.parse_args()
envs = [e for e in bax_env.all_envs if e.id in a.envs]
rows = [{"scenario": s.id, "env": e.id, "system": _SYSTEM_PROMPT,
         "user": s.build_prompt(e, "openapi", a.safety_prompt, agent=False)}
        for s in all_scenarios for e in envs]
with open(a.out, "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
print(f"wrote {len(rows)} prompts to {a.out}")

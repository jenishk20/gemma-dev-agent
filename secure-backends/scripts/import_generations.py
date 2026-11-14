"""Import cluster generations into BaxBench's results layout, parsed with BaxBench's own Parser,
so `main.py --mode test --models <name>` scores them unchanged.

  third_party/baxbench/.venv/bin/python scripts/import_generations.py gens/base12b.jsonl gemma-4-12b-it-base
Rows: {"scenario", "env", "sample", "response"}. Unparsable replies are saved the way BaxBench
saves them (a `failed` file), so they score as failures, exactly as in a normal BaxBench run.
"""
import argparse, json, logging, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BAX = ROOT / "third_party" / "baxbench"
sys.path.insert(0, str(BAX / "src"))
import env as bax_env  # noqa: E402
from prompts import Parser  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("gens"); ap.add_argument("model_name")
ap.add_argument("--tag", default="temp0.4-openapi-none")
a = ap.parse_args()
logging.basicConfig(level=logging.ERROR)
envs = {e.id: e for e in bax_env.all_envs}
n = failed = 0
for line in open(a.gens):
    r = json.loads(line)
    e = envs[r["env"]]
    files = Parser(e, logging.getLogger("import")).parse_response(r["response"] or "")
    code = BAX / "results" / a.model_name / r["scenario"] / r["env"] / a.tag / f"sample{r['sample']}" / "code"
    code.mkdir(parents=True, exist_ok=True)
    for p, c in files.items():
        (code / p).parent.mkdir(parents=True, exist_ok=True)
        (code / p).write_text(c)
    n += 1
    failed += "failed" in {str(p) for p in files}
print(f"imported {n} samples into results/{a.model_name} ({failed} unparsable)")

"""One line per task for an eval run: solved?, patch size, tool calls, time, error.

  python3 tools/show_results.py                       # newest run in $GDA_ROOT/results
  python3 tools/show_results.py /scratch/phalle.y/gda/results/e4b_baseline_1115-1235
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("GDA_ROOT", Path(__file__).resolve().parents[2] / "gda"))


def main():
    if len(sys.argv) > 1:
        run = Path(sys.argv[1])
    else:
        runs = [p for p in (ROOT / "results").glob("*/task_results.jsonl")]
        if not runs:
            sys.exit(f"no runs with task_results.jsonl under {ROOT / 'results'}")
        run = max(runs, key=lambda p: p.stat().st_mtime).parent
    rows = [json.loads(l) for l in (run / "task_results.jsonl").read_text().splitlines() if l.strip()]
    print(f"{run}  ({len(rows)} tasks)")
    print(f"{'task':18s} {'solved':6s} {'patch':>7s} {'tools':>5s} {'llm':>4s} {'time':>6s} {'exit':>4s}  error")
    for d in rows:
        err = str(d.get("error") or "").replace("\n", " ")[:120]
        print(f"{d['instance_id']:18s} {'YES' if d['resolved'] else 'no':6s} {d['agent_patch_size']:6d}B "
              f"{d.get('tool_calls', 0):5d} {d.get('total_llm_calls', 0):4d} {d['duration_seconds']:5.0f}s "
              f"{str(d.get('test_exit_code')):>4s}  {err}")
    solved = sum(d["resolved"] for d in rows)
    print(f"solved {solved}/{len(rows)} | empty patches: {sum(d['agent_patch_size'] == 0 for d in rows)} "
          f"| with errors: {sum(bool(d.get('error')) for d in rows)}")
    print("folders here:", ", ".join(sorted(p.name for p in run.iterdir())))


if __name__ == "__main__":
    main()

"""How the agent spent its steps on each task of an eval run, from the saved traces.

  /scratch/phalle.y/gda/venv/bin/python tools/trace_report.py                 # newest run
  /scratch/phalle.y/gda/venv/bin/python tools/trace_report.py <results dir> --save

Per task: solved?, tool calls before the first edit, whether it ran tests, whether it called submit_patch,
nudges from the harness, and the compact step sequence (R=read_file, E=edit_file, W=write_file, C=run_command,
T=run_command running tests, S=submit_patch, G=graph tools, A=analyzer sub-agent, ?=get_status).
--save also writes reports/<run>/ in the repo (summary.md + one short markdown trace per task) to commit and push.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("GDA_ROOT", Path(__file__).resolve().parents[2] / "gda"))
REPO = Path(__file__).resolve().parents[1]
CODE = {"read_file": "R", "edit_file": "E", "write_file": "W", "run_command": "C", "submit_patch": "S",
        "get_status": "?", "search_similar_code": "G", "get_code_neighbors": "G", "get_code_subgraph": "G"}
TEST_CMD = re.compile(r"\bpytest\b|\bunittest\b|python3? -m pytest")


def steps(trace):
    out = []
    for e in trace._entries:
        if e.event_type == "tool_call":
            name, args = e.tool_name, e.tool_args or {}
            code = CODE.get(name, "A" if "agent" in name else "x")
            if name == "run_command" and TEST_CMD.search(str(args.get("command", ""))):
                code = "T"
            out.append((code, name, args))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?")
    ap.add_argument("--save", action="store_true", help="write reports/<run>/ in the repo")
    args = ap.parse_args()
    from adk_eval_core.tracing.trace import SessionTrace

    if args.run:
        run = Path(args.run)
    else:
        runs = list((ROOT / "results").glob("*/task_results.jsonl"))
        run = max(runs, key=lambda p: p.stat().st_mtime).parent
    results = {json.loads(l)["instance_id"]: json.loads(l)
               for l in (run / "task_results.jsonl").read_text().splitlines() if l.strip()}
    lines, md = [], {}
    agg = {"tasks": 0, "solved": 0, "ran_tests": 0, "submitted": 0, "no_edit": 0, "nudged": 0, "first_edit": []}
    for tid, r in sorted(results.items()):
        f = run / "traces" / f"trace_{tid.replace('/', '__')}.json"
        if not f.exists():
            lines.append(f"{tid:18s} (no trace)")
            continue
        tr = SessionTrace.from_json(f)
        st = steps(tr)
        codes = "".join(c for c, _, _ in st)
        first_edit = next((i + 1 for i, (c, _, _) in enumerate(st) if c in "EW"), None)
        nudges = sum(1 for e in tr._entries if e.event_type == "continuation_nudge"
                     or (e.metadata or {}).get("event_type") == "continuation_nudge")
        agg["tasks"] += 1
        agg["solved"] += bool(r["resolved"])
        agg["ran_tests"] += "T" in codes
        agg["submitted"] += "S" in codes
        agg["no_edit"] += first_edit is None
        agg["nudged"] += nudges > 0
        if first_edit:
            agg["first_edit"].append(first_edit)
        lines.append(f"{tid:18s} {'YES' if r['resolved'] else 'no ':3s} calls={len(st):2d} first_edit={first_edit or '-'!s:>2s} "
                     f"tests={'y' if 'T' in codes else 'n'} submit={'y' if 'S' in codes else 'n'} nudges={nudges} "
                     f"{r['duration_seconds']:4.0f}s  {codes}")
        if args.save:
            md[tid] = tr.to_markdown(max_thought_len=600, max_tool_args_len=400, max_tool_result_len=600,
                                     max_text_len=600, max_final_len=800, use_emojis=False)
    n = max(agg["tasks"], 1)
    fe = sorted(agg["first_edit"])
    summary = (f"{run.name}: solved {agg['solved']}/{agg['tasks']} | ran any test {agg['ran_tests']}/{n} | "
               f"called submit_patch {agg['submitted']}/{n} | never edited {agg['no_edit']}/{n} | nudged {agg['nudged']}/{n} | "
               f"median call of first edit {fe[len(fe) // 2] if fe else '-'}")
    legend = "steps: R=read E=edit W=write C=command T=test S=submit G=graph A=sub-agent ?=status"
    print("\n".join([legend, *lines, "", summary]))
    if args.save:
        out = REPO / "reports" / run.name
        (out / "traces").mkdir(parents=True, exist_ok=True)
        (out / "summary.md").write_text(f"# {run.name}\n\n```\n{legend}\n" + "\n".join(lines) + f"\n```\n\n{summary}\n")
        for tid, text in md.items():
            (out / "traces" / f"{tid}.md").write_text(text)
        print(f"\nsaved {out} ({len(md)} traces). To share: cd {REPO} && git add reports && git commit -m 'report {run.name}' && git push")


if __name__ == "__main__":
    sys.exit(main())

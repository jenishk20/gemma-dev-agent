"""Compare agent behaviour across result folders, from the per-task traces (counts only, no task text).

For each folder: tool calls by name, edit attempts and how many failed, when the first edit happened,
thinking length per step, and how often the agent submitted.

    python tools/diag_runs.py $GDA_ROOT/results/evlora_<job>_*
"""
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

EDITS = {"edit_file", "write_file"}


def failed(content):
    s = str(content).lower()
    return any(k in s for k in ('"status": "error"', "'status': 'error'", "not found in", "no match", "did not match",
                                "could not find", "failed to apply", "error:"))


def main():
    for d in map(Path, sys.argv[1:]):
        tools, think, first_edit, edits, edit_fail, submits, n = Counter(), [], [], 0, 0, 0, 0
        for f in sorted((d / "traces").glob("*.json")):
            n += 1
            steps = json.load(open(f)).get("steps", [])
            k, seen_edit = 0, False
            for s in steps:
                ex = s.get("extra") or {}
                if ex.get("author", "").startswith("code_analyzer"):
                    continue                                         # main agent only
                if ex.get("event_type") == "thinking" and isinstance(s.get("message"), str):
                    think.append(len(s["message"]))
                for tc in s.get("tool_calls") or []:
                    name = tc.get("function_name", "?")
                    tools[name] += 1
                    k += 1
                    if name in EDITS:
                        edits += 1
                        if not seen_edit:
                            first_edit.append(k)
                            seen_edit = True
                        if failed((s.get("observation") or {}).get("content")):
                            edit_fail += 1
                    if name == "submit_patch":
                        submits += 1
        if not n:
            print(f"{d.name}: no traces")
            continue
        print(f"\n{d.name}: {n} tasks")
        print("  tool calls per task:", {t: round(c / n, 1) for t, c in tools.most_common(9)})
        print(f"  edits: {edits} attempts, {edit_fail} failed ({edit_fail / max(1, edits):.0%}); tasks with an edit: "
              f"{len(first_edit)}/{n}; first edit at call #{st.median(first_edit) if first_edit else '-'} (median)")
        print(f"  submit_patch calls: {submits}; thinking per step: median {st.median(think) if think else 0:.0f} chars, "
              f"max {max(think) if think else 0}")


if __name__ == "__main__":
    main()

"""Sanity checks on teacher data before training (prints counts and short prefixes only).

1. The calls build_sft.py could not match to a task, grouped by system-prompt / first-user-message prefix
   (expected: code_analyzer sub-agent and compaction-summary calls; not main-agent calls).
2. For the built examples: how many end with a submit_patch call, and how many runs end in a "final"
   example (so the end of every solved run is in the data).

    python training/inspect_sft.py --runs $GDA_ROOT/results/teacher_*_try* --tasks $GDA_ROOT/data/tasks.jsonl \
        --sft $GDA_ROOT/data/sft/e4b_teacher_v1.jsonl
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_sft import read_calls, task_of  # noqa: E402


def text(m):
    c = m.get("content")
    if isinstance(c, list):
        c = " ".join(str(p.get("text", "")) for p in c if isinstance(p, dict))
    return (c or "").replace("\n", " ")


def tool_names(m):
    return [tc["function"]["name"] for tc in m.get("tool_calls") or []]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--sft", required=True)
    args = ap.parse_args()
    tasks = {json.loads(l)["instance_id"]: json.loads(l) for l in open(args.tasks) if l.strip()}
    statements = {iid: t["problem_statement"].strip()[:400] for iid, t in tasks.items()}

    groups, main_calls, last_reply = Counter(), 0, {}
    for run in map(Path, args.runs):
        for c in read_calls(run / "model_calls.jsonl.gz"):
            msgs = c["messages"]
            iid = task_of(msgs, statements)
            if iid is None:
                sysm = next((text(m) for m in msgs if m.get("role") == "system"), "")
                user = next((text(m) for m in msgs if m.get("role") == "user"), "")
                groups[(sysm[:70], user[:70], "PS" if "Problem Statement:" in json.dumps(msgs) else "-")] += 1
            else:
                main_calls += 1
                last_reply[(run.name, iid)] = (c["t"], tool_names(c["reply"]), text(c["reply"])[:80])
    print(f"main-agent calls: {main_calls}; unmatched calls by (system prefix | first user prefix | 'PS' if the "
          f"problem statement appears anywhere):")
    for (s, u, ps), n in groups.most_common(12):
        print(f"  {n:5d}  [{ps}]  SYS: {s!r}\n         USER: {u!r}")

    ex = [json.loads(l) for l in open(args.sft) if l.strip()]
    ends = Counter()
    per_run = defaultdict(list)
    for e in ex:
        last = e["messages"][-1]
        ends["ends with submit_patch" if "submit_patch" in tool_names(last) else
             ("ends with other tool call" if tool_names(last) else "ends with text")] += 1
        per_run[(e["run"], e["instance_id"])].append(e)
    print(f"\n{len(ex)} examples from {len(per_run)} solved runs: {dict(ends)}")
    has_submit = sum(any("submit_patch" in tool_names(m) for e in es for m in e["messages"])
                     for es in per_run.values())
    print(f"solved runs with a submit_patch call somewhere in their examples: {has_submit}/{len(per_run)}")
    last_kinds = Counter(("submit_patch" if "submit_patch" in v[1] else (",".join(v[1]) or "text"))
                         for k, v in last_reply.items() if k in per_run)
    print("what the LAST matched main-agent call of each solved run did:", dict(last_kinds.most_common(6)))
    chars = sorted(sum(len(json.dumps(m)) for m in e["messages"]) for e in ex)
    print(f"example size in characters: median {chars[len(chars) // 2]}, max {chars[-1]} "
          f"(~4 chars per token; the limit is 32768 tokens)")


if __name__ == "__main__":
    main()

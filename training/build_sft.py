"""Turn teacher runs into fine-tuning examples (one per solved run).

Reads results/teacher_*/model_calls.jsonl.gz (every model call's exact request and reply, written by
tools/run_local_eval.py --teacher) and keeps only runs whose patch passed the task's tests.

The last call of a run holds the whole conversation exactly as the model saw it, so an example is just
that call's messages + its reply. If context compaction rewrote the history mid-run, the run has several
"final" calls (each one not continued by a later call); each becomes its own example.

Only the main agent's calls are used; sub-agent (code_analyzer) and compaction-summary calls are skipped.
A main-agent call is matched to its task by the problem statement in its task message. After compaction
the task message is gone (the history starts with "For context: [model] said: <summary>"), so those calls
are matched by the model's own earlier messages they still carry (compaction keeps the last few events):
an assistant message, with its thinking text, belongs to exactly one conversation.

Only training tasks are allowed in: any task from the "test" side of training/public_split.json stops the build.

    python training/build_sft.py --runs $GDA_ROOT/results/teacher_*_try* --tasks $GDA_ROOT/data/tasks.jsonl \
        --out $GDA_ROOT/data/sft/teacher_v1.jsonl
"""
import argparse
import gzip
import json
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEEP = ("role", "content", "tool_calls", "tool_call_id", "name", "reasoning_content")


def clean(msg):
    """Keep only the fields a chat template uses; `reasoning` duplicates `reasoning_content`."""
    out = {k: msg[k] for k in KEEP if msg.get(k) is not None}
    if "reasoning_content" not in out and msg.get("reasoning"):
        out["reasoning_content"] = msg["reasoning"]
    for tc in out.get("tool_calls") or []:
        tc.pop("index", None)
    return out


def read_calls(path):
    rows = []
    try:
        with gzip.open(path, "rt") as f:
            for line in f:
                rows.append(json.loads(line))
    except (EOFError, zlib.error, json.JSONDecodeError):  # the job may still be writing the last line
        pass
    return rows


def task_of(messages, statements):
    """instance_id of the task this main-agent call belongs to, or None for sub-agent calls."""
    user = next((m.get("content") for m in messages if m.get("role") == "user"), None)
    if not isinstance(user, str) or "Problem Statement:" not in user:
        return None
    hits = [iid for iid, key in statements.items() if key in user]
    return hits[0] if len(hits) == 1 else None


def asst_keys(c):
    """Keys of the model's own messages in a call (history + reply); thinking text makes them unique."""
    out = set()
    for m in c["messages"] + [c["reply"]]:
        if m.get("role", "assistant") == "assistant" and (m.get("reasoning_content") or m.get("reasoning")):
            out.add(json.dumps([m.get("reasoning_content") or m.get("reasoning"), m.get("content") or "",
                                [tc.get("function") for tc in m.get("tool_calls") or []]], sort_keys=True))
    return out


def match_calls(calls, statements):
    """{call index: instance_id} for main-agent calls, including the ones after compaction."""
    match = {i: iid for i, c in enumerate(calls) if (iid := task_of(c["messages"], statements))}
    systems = Counter(json.dumps(calls[i]["messages"][0]) for i in match if calls[i]["messages"])
    main_system = systems.most_common(1)[0][0] if systems else None
    owner = defaultdict(set)                              # message key -> tasks it was seen in
    for i, iid in match.items():
        for k in asst_keys(calls[i]):
            owner[k].add(iid)
    todo = [i for i, c in enumerate(calls)
            if i not in match and c["messages"] and json.dumps(c["messages"][0]) == main_system]
    changed = True
    while changed:                                        # repeat: a run can be compacted more than once
        changed = False
        for i in list(todo):
            ks = asst_keys(calls[i])
            hits = {t for k in ks for t in owner.get(k, ())}
            if len(hits) == 1:
                iid = hits.pop()
                match[i] = iid
                for k in ks:
                    owner[k].add(iid)
                todo.remove(i)
                changed = True
    return match, len(todo)


def final_calls(calls):
    """Calls whose conversation no later call continues (normally just the last one)."""
    keys = [[json.dumps(m, sort_keys=True, default=str) for m in c["messages"]] for c in calls]
    out = []
    for i, c in enumerate(calls):
        n = len(keys[i])
        continued = any(len(keys[j]) > n and keys[j][:n] == keys[i] for j in range(i + 1, len(calls)))
        if not continued:
            out.append(c)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True, help="teacher result folders")
    ap.add_argument("--tasks", required=True, help="tasks.jsonl (for problem statements)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default=str(ROOT / "training" / "public_split.json"))
    args = ap.parse_args()

    split = json.load(open(args.split))
    test_ids = set(split["test"])
    tasks = {json.loads(l)["instance_id"]: json.loads(l) for l in open(args.tasks) if l.strip()}
    statements = {iid: t["problem_statement"].strip()[:400] for iid, t in tasks.items()}

    examples, stats = [], Counter()
    for run in map(Path, args.runs):
        calls_file, results_file = run / "model_calls.jsonl.gz", run / "task_results.jsonl"
        if not calls_file.exists() or not results_file.exists():
            print(f"skip {run.name}: no recorded calls or results")
            continue
        results = [json.loads(l) for l in open(results_file) if l.strip()]
        solved = {r["instance_id"] for r in results if r.get("resolved")}
        by_task = defaultdict(list)
        calls = read_calls(calls_file)
        match, unmatched_main = match_calls(calls, statements)
        for i, c in enumerate(calls):
            if i in match:
                by_task[match[i]].append(c)
        stats["main-agent calls matched"] += len(match)
        stats["main-agent calls NOT matched"] += unmatched_main
        stats["sub-agent / summary calls (skipped)"] += len(calls) - len(match) - unmatched_main
        stats["solved runs"] += len(solved)
        for iid in sorted(solved):
            if iid in test_ids:
                sys.exit(f"STOP: {iid} is a test task; teacher runs must use training tasks only")
            calls = sorted(by_task.get(iid, []), key=lambda c: c["t"])
            if not calls:
                stats["solved runs with no recorded calls"] += 1
                continue
            for c in final_calls(calls):
                msgs = [clean(m) for m in c["messages"]] + [clean({**c["reply"], "role": "assistant"})]
                examples.append({"instance_id": iid, "run": run.name, "repo": tasks[iid]["repo"],
                                 "n_calls": len(calls), "messages": msgs, "tools": c.get("tools") or []})
            stats["solved runs used"] += 1
            if any(tc["function"]["name"] == "submit_patch" for c in calls for tc in c["reply"].get("tool_calls") or []):
                stats["solved runs whose data includes submit_patch"] += 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        for e in examples:
            f.write(json.dumps(e) + "\n")
    per_task = Counter(e["instance_id"] for e in examples)
    turns = [sum(m["role"] == "assistant" for m in e["messages"]) for e in examples]
    print(dict(stats))
    print(f"{len(examples)} examples from {len(per_task)} different tasks -> {out}")
    if turns:
        print(f"assistant turns per example: min {min(turns)}, median {sorted(turns)[len(turns) // 2]}, max {max(turns)}")
    print("examples per repo:", dict(Counter(e["repo"] for e in examples)))


if __name__ == "__main__":
    main()

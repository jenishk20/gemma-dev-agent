"""Summarize BaxBench results per condition, with paired bootstrap CIs over tasks.

  python3 scripts/summarize.py            (conditions defined in CONDITIONS below)
A sample counts as WORKS if every functional test passed with no exception; WORKS+SECURE if it
also triggered no CWE in any security test (BaxBench's sec_pass). Rates are averaged over the 5
samples of each task, then over tasks; CIs resample tasks (paired across conditions).
Writes results/summary.json and prints a table, the deltas vs base, and the top CWEs.
"""
import collections, json, pathlib, random

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = (ROOT / "bench" if (ROOT / "bench").exists() else ROOT / "third_party" / "baxbench") / "results"
ENVS = ["Python-Flask", "Python-FastAPI"]
CONDITIONS = {  # name -> (model dir, tag)
    "base 31B": ("google-gemma-4-31b-it", "temp0.4-openapi-none"),
    "security prompt 31B": ("google-gemma-4-31b-it", "temp0.4-openapi-generic"),
    "self-review 31B": ("gemma-4-31b-it-selfreview", "temp0.4-openapi-none"),
    "base 12B": ("gemma-4-12b-it-base", "temp0.4-openapi-none"),
    "SFT 12B": ("gemma-4-12b-it-sft", "temp0.4-openapi-none"),
}


def load(model, tag):
    """task (scenario, env) -> list of (works, secure, cwes) per scored sample."""
    out = collections.defaultdict(list)
    for env in ENVS:
        for f in (RES / model).glob(f"*/{env}/{tag}/sample*/test_results.json"):
            r = json.loads(f.read_text())
            works = r["num_total_ft"] > 0 and r["num_passed_ft"] == r["num_total_ft"] and r["num_ft_exceptions"] == 0
            cwes = [c["num"] if isinstance(c, dict) else c for c in r["cwes"]]
            out[(f.parts[-5], env)].append((works, works and not cwes, cwes, r["num_ft_exceptions"] == r["num_total_ft"]))
    return out


def rate(task_rows, idx):
    return sum(r[idx] for r in task_rows) / len(task_rows)


def boot(tasks, fn, n=5000, seed=0):
    rng = random.Random(seed)
    vals = sorted(fn([rng.choice(tasks) for _ in tasks]) for _ in range(n))
    return vals[int(0.025 * n)], vals[int(0.975 * n)]


def main():
    data = {name: load(*spec) for name, spec in CONDITIONS.items()}
    data = {k: v for k, v in data.items() if v}
    summary, base_names = {}, {"31B": "base 31B", "12B": "base 12B"}
    print(f"{'condition':22s} {'samples':>7s} {'tasks':>5s} {'works':>7s} {'works+secure':>13s} {'insecure|works':>15s} {'never ran':>9s}")
    for name, d in data.items():
        tasks = sorted(d)
        rows = [r for t in tasks for r in d[t]]
        w = sum(rate(d[t], 0) for t in tasks) / len(tasks)
        s = sum(rate(d[t], 1) for t in tasks) / len(tasks)
        n_works = sum(r[0] for r in rows)
        insec = 1 - sum(r[1] for r in rows) / n_works if n_works else float("nan")
        crash = sum(r[3] for r in rows) / len(rows)
        cwe = collections.Counter(c for r in rows if r[0] for c in r[2])
        summary[name] = {"samples": len(rows), "tasks": len(tasks), "works": w, "works_secure": s,
                         "insecure_given_works": insec, "never_ran": crash, "top_cwes": cwe.most_common(8)}
        print(f"{name:22s} {len(rows):7d} {len(tasks):5d} {w:7.1%} {s:13.1%} {insec:15.1%} {crash:9.1%}")

    print("\nDelta in works+secure vs the same-size base (paired bootstrap over tasks, 95% CI):")
    for name, d in data.items():
        b = base_names["31B" if "31B" in name else "12B"]
        if name == b or b not in data:
            continue
        common = sorted(set(d) & set(data[b]))
        fn = lambda ts: sum(rate(d[t], 1) - rate(data[b][t], 1) for t in ts) / len(ts)  # noqa: E731
        lo, hi = boot(common, fn)
        summary[name]["delta_vs_base"] = {"base": b, "delta": fn(common), "ci95": [lo, hi], "tasks": len(common)}
        print(f"  {name:22s} {fn(common):+6.1%}  [{lo:+.1%}, {hi:+.1%}]  over {len(common)} tasks")

    print("\nMost common CWEs among WORKING apps (count of samples):")
    for name, v in summary.items():
        print(f"  {name:22s} " + ", ".join(f"CWE-{c}: {n}" for c, n in v["top_cwes"][:6]))
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

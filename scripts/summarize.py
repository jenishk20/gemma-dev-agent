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
    "review+start check 31B": ("gemma-4-31b-it-selfreview", "temp0.4-openapi-none", ("google-gemma-4-31b-it", "temp0.4-openapi-none")),
    "base 12B": ("gemma-4-12b-it-base", "temp0.4-openapi-none"),
    "SFT 12B": ("gemma-4-12b-it-sft", "temp0.4-openapi-none"),
}


def row(r):
    """(works, works and secure, cwes, never started) for one test_results.json."""
    works = r["num_total_ft"] > 0 and r["num_passed_ft"] == r["num_total_ft"] and r["num_ft_exceptions"] == 0
    cwes = [c["num"] if isinstance(c, dict) else c for c in r["cwes"]]
    return (works, works and not cwes, cwes, r["num_ft_exceptions"] == r["num_total_ft"])


def load(model, tag, fallback=None):
    """task (scenario, env) -> list of row() per scored sample.
    fallback=(model, tag): use that run's sample instead whenever this run's app never started
    (every functional request failed), i.e. the developer launches the reviewed app once and
    keeps the original if it does not come up."""
    out = collections.defaultdict(list)
    for env in ENVS:
        for f in sorted((RES / model).glob(f"*/{env}/{tag}/sample*/test_results.json")):
            r = row(json.loads(f.read_text()))
            if fallback and r[3]:
                g = RES / fallback[0] / f.parts[-5] / env / fallback[1] / f.parts[-2] / "test_results.json"
                if g.exists():
                    r = row(json.loads(g.read_text()))
            out[(f.parts[-5], env)].append(r)
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
    print(f"{'condition':24s} {'samples':>7s} {'tasks':>5s} {'works':>7s} {'works+secure':>13s} {'insecure|works':>15s} {'never ran':>9s}")
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
        print(f"{name:24s} {len(rows):7d} {len(tasks):5d} {w:7.1%} {s:13.1%} {insec:15.1%} {crash:9.1%}")

    print("\nDelta in works+secure vs the same-size base (paired bootstrap over tasks, 95% CI):")
    for name, d in data.items():
        b = base_names["31B" if "31B" in name else "12B"]
        if name == b or b not in data:
            continue
        common = sorted(set(d) & set(data[b]))
        fn = lambda ts: sum(rate(d[t], 1) - rate(data[b][t], 1) for t in ts) / len(ts)  # noqa: E731
        lo, hi = boot(common, fn)
        summary[name]["delta_vs_base"] = {"base": b, "delta": fn(common), "ci95": [lo, hi], "tasks": len(common)}
        print(f"  {name:24s} {fn(common):+6.1%}  [{lo:+.1%}, {hi:+.1%}]  over {len(common)} tasks")

    print("\nMost common CWEs among WORKING apps (count of samples):")
    for name, v in summary.items():
        print(f"  {name:24s} " + ", ".join(f"CWE-{c}: {n}" for c, n in v["top_cwes"][:6]))
    # Self-review revises one specific base sample, so outcomes can be paired sample by sample.
    if "self-review 31B" in data and "base 31B" in data:
        trans = transitions(CONDITIONS["base 31B"], CONDITIONS["self-review 31B"][:2])
        summary["self-review 31B"]["transitions_from_base"] = trans
        print("\nSelf-review vs the base sample it revised (paired by sample):")
        for k, v in trans.items():
            print(f"  {k:28s} {v}")

    print("\nPer framework (works / works+secure):")
    for name, d in data.items():
        for env in ENVS:
            rows = [r for t, rs in d.items() if t[1] == env for r in rs]
            if not rows:
                continue
            w, s = sum(r[0] for r in rows) / len(rows), sum(r[1] for r in rows) / len(rows)
            summary[name].setdefault("per_env", {})[env] = {"n": len(rows), "works": w, "works_secure": s}
            print(f"  {name:24s} {env:15s} n={len(rows):3d} works {w:6.1%}  works+secure {s:6.1%}")
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "summary.json").write_text(json.dumps(summary, indent=2))


def state(r):
    works = r["num_total_ft"] > 0 and r["num_passed_ft"] == r["num_total_ft"] and r["num_ft_exceptions"] == 0
    return "secure" if works and not r["cwes"] else ("exploitable" if works else "broken")


def transitions(base_spec, rev_spec):
    """Count base-state -> reviewed-state over samples present in both runs."""
    counts = collections.Counter()
    fixed_cwes, new_cwes = collections.Counter(), collections.Counter()
    for f in (RES / base_spec[0]).glob(f"*/*/{base_spec[1]}/sample*/test_results.json"):
        if f.parts[-4] not in ENVS:
            continue
        g = RES / rev_spec[0] / f.relative_to(RES / base_spec[0])
        if not g.exists():
            continue
        a, b = json.loads(f.read_text()), json.loads(g.read_text())
        counts[f"{state(a)} -> {state(b)}"] += 1
        ca = {c["num"] if isinstance(c, dict) else c for c in a["cwes"]}
        cb = {c["num"] if isinstance(c, dict) else c for c in b["cwes"]}
        if state(b) != "broken":
            fixed_cwes.update(ca - cb)
            new_cwes.update(cb - ca)
    out = dict(sorted(counts.items()))
    out["cwes_removed"] = fixed_cwes.most_common(8)
    out["cwes_introduced"] = new_cwes.most_common(8)
    return out


if __name__ == "__main__":
    main()

"""Step 1 of the training data: list merged PRs of the competition's 4 repos that could become practice tasks.

  python3 tools/mine_prs.py            # needs the GitHub CLI (gh) logged in; writes training/candidates.jsonl

A candidate is a merged PR that changes library source AND tests, merged BEFORE the earliest public task of
its repo (so it cannot be one of the hidden test tasks, which come from the same time window as the public
ones) and that is not one of the 129 public tasks. The task row copies the competition's format:
instance_id = <repo>_<PR number>, problem_statement = title + blank line + body, created_at = merged time.
Diffs and base commits are computed later from a git clone (tools/build_train_tasks.py).
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "training" / "candidates.jsonl"
# repo -> (instance prefix, package dirs that count as library source)
REPOS = {
    "fastapi/fastapi": ("fastapi", ("fastapi/",)),
    "Textualize/rich": ("rich", ("rich/",)),
    "psf/requests": ("requests", ("requests/", "src/requests/")),
    "encode/httpx": ("httpx", ("httpx/",)),
}
QUERY = """
query($owner:String!, $name:String!, $after:String) {
  repository(owner:$owner, name:$name) {
    pullRequests(states:MERGED, first:50, after:$after, orderBy:{field:CREATED_AT, direction:ASC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title body mergedAt baseRefName baseRefOid headRefOid mergeCommit { oid } additions deletions changedFiles
        files(first:100) { nodes { path additions deletions } }
      }
    }
  }
}"""


def is_test(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (path.startswith(("tests/", "test/", "testing/")) or "/tests/" in path
            or name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py")


def gh_page(owner, name, after):
    cmd = ["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", f"owner={owner}", "-F", f"name={name}"]
    if after:
        cmd += ["-F", f"after={after}"]
    for attempt in range(4):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return json.loads(r.stdout)["data"]["repository"]["pullRequests"]
        print(f"  retry {attempt + 1}: {r.stderr.strip()[:200]}", file=sys.stderr)
    raise SystemExit(f"GitHub query failed for {owner}/{name}")


def main():
    public = [json.loads(l) for l in (REPO / "kaggle_data" / "tasks.jsonl").read_text().splitlines() if l.strip()]
    public_ids = {t["instance_id"] for t in public}
    cutoff = {}
    for t in public:
        cutoff[t["repo"]] = min(cutoff.get(t["repo"], "9999"), t["created_at"])
    OUT.parent.mkdir(exist_ok=True)
    rows, stats = [], {}
    for repo, (prefix, src_dirs) in REPOS.items():
        owner, name = repo.split("/")
        after, seen, kept = None, 0, 0
        while True:
            page = gh_page(owner, name, after)
            for pr in page["nodes"]:
                seen += 1
                iid = f"{prefix}_{pr['number']}"
                if not pr["mergedAt"] or pr["mergedAt"] >= cutoff[repo] or iid in public_ids:
                    continue
                files = [f["path"] for f in pr["files"]["nodes"]]
                src = [f for f in files if f.endswith(".py") and f.startswith(src_dirs) and not is_test(f)]
                tests = [f for f in files if f.endswith(".py") and is_test(f)]
                if not src or not tests or pr["changedFiles"] > 100:
                    continue
                src_lines = sum(f["additions"] + f["deletions"] for f in pr["files"]["nodes"] if f["path"] in src)
                rows.append({"instance_id": iid, "repo": repo, "number": pr["number"], "merged_at": pr["mergedAt"],
                             "base_ref": pr["baseRefName"], "base_commit": pr["baseRefOid"], "head_commit": pr["headRefOid"],
                             "merge_commit": (pr["mergeCommit"] or {}).get("oid"), "title": pr["title"], "body": pr["body"] or "",
                             "src_files": src, "test_files": tests, "src_lines": src_lines})
                kept += 1
            if not page["pageInfo"]["hasNextPage"]:
                break
            after = page["pageInfo"]["endCursor"]
            print(f"  {repo}: {seen} PRs read, {kept} candidates", file=sys.stderr)
        stats[repo] = (seen, kept, cutoff[repo][:10])
    OUT.write_text("".join(json.dumps(r) + "\n" for r in rows))
    for repo, (seen, kept, cut) in stats.items():
        print(f"{repo:18s} merged PRs {seen:5d} | source+test PRs before {cut}: {kept}")
    print(f"total {len(rows)} candidates -> {OUT}")


if __name__ == "__main__":
    main()

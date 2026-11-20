"""Step 2 of the training data: turn the mined PRs (training/candidates.jsonl) into runnable practice tasks.

  $GDA_ROOT/venv/bin/python tools/build_train_tasks.py [--limit N] [--workers 8]

Runs on the cluster (CPU only, needs internet for the git clones). Writes, in the competition's own format:
  $GDA_ROOT/train/tasks.jsonl            one row per task (instance_id, repo, base_commit, patch, test_patch, ...)
  $GDA_ROOT/train/snapshots/<id>.tgz     the repo at base_commit with a fresh one-commit .git, like the official ones
  $GDA_ROOT/train/wheels                 link to the competition's wheels
For each PR: base_commit = the commit the PR was opened against; the PR's own changes are
diff(merge-base(base, head), head), split into test files (test_patch) and everything else (patch).
Tasks are only usable after tools/check_train_tasks.py has confirmed that the official fix passes the tests
and that the tests fail without it.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("GDA_ROOT", REPO.parent / "gda"))
TRAIN = ROOT / "train"
CLONES = ROOT / "train_repos"


# Scratch space for unpacking repos: the node's own disk. The cluster's shared /scratch is very slow at creating
# the thousands of small files each task needs (the first run built only ~50 tasks in 12 hours there).
WORK = Path(os.environ.get("TRAIN_WORK_DIR", tempfile.gettempdir()))
STEP_TIMEOUT = 600  # seconds; a stuck git/tar step makes that one PR a skip instead of stalling the job


def run(cmd, **kw):
    return subprocess.run(cmd, timeout=STEP_TIMEOUT, **kw)


def git(cwd, *args, check=True):
    r = run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args[:3])}: {r.stderr.strip()[:300]}")
    return r.stdout


def is_test(path: str) -> bool:
    """Same rule as the harness's protected test files: these go to test_patch, never to the fix."""
    name = path.rsplit("/", 1)[-1]
    return (path.split("/", 1)[0] in ("tests", "test", "testing") or "/tests/" in path
            or name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py")


def split_diff(diff: str):
    """Split a unified git diff into (fix, tests) by file."""
    parts = re.split(r"(?m)^(?=diff --git )", diff)
    fix, tests = [], []
    for p in parts:
        m = re.match(r"diff --git a/(\S+) b/(\S+)", p)
        if not m:
            continue
        (tests if is_test(m.group(2)) else fix).append(p)
    return "".join(fix), "".join(tests)


def clone(repo: str) -> Path:
    d = CLONES / repo.replace("/", "__")
    if not (d / ".git").exists():
        print(f"{time.strftime('%H:%M:%S')} cloning {repo}", flush=True)
        CLONES.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", f"https://github.com/{repo}.git", str(d)], check=True)
    print(f"{time.strftime('%H:%M:%S')} fetching PR heads of {repo}", flush=True)
    git(d, "fetch", "-q", "origin", "+refs/pull/*/head:refs/pr/*")
    return d


def build_one(c: dict, clone_dir: str) -> dict:
    iid, d = c["instance_id"], Path(clone_dir)
    out = TRAIN / "snapshots" / f"{iid}.tgz"
    base, head = c["base_commit"], c["head_commit"]
    try:
        git(d, "cat-file", "-e", f"{head}^{{commit}}")
    except RuntimeError:
        head = f"refs/pr/{c['number']}"
    mb = git(d, "merge-base", base, head).strip()
    diff = git(d, "diff", "--binary", "--no-color", f"{mb}..{head}")
    fix, tests = split_diff(diff)
    if not fix.strip() or not tests.strip():
        return {"instance_id": iid, "skip": "fix or tests empty after diff"}
    row = {"instance_id": iid, "repo": c["repo"], "base_commit": base, "patch": fix, "test_patch": tests,
           "problem_statement": f"{c['title']}\n\n{c['body']}".strip(), "hints_text": "",
           "created_at": c["merged_at"]}
    if out.exists():  # built (and apply-checked) by an earlier run
        return row
    # The PR diff is taken against the merge base; it must also apply on top of base_commit.
    with tempfile.TemporaryDirectory(dir=WORK, prefix="gda_build_") as tmp:
        ws = Path(tmp) / "ws"
        ws.mkdir()
        run(f"git -C {d} archive {base} | tar -x -C {ws}", shell=True, check=True)
        for name, p in (("fix", fix), ("tests", tests)):
            pf = Path(tmp) / f"{name}.patch"
            pf.write_text(p)
            r = run(["git", "apply", "--check", str(pf)], cwd=ws, capture_output=True, text=True)
            if r.returncode:
                return {"instance_id": iid, "skip": f"{name} does not apply on base: {r.stderr.strip()[:150]}"}
        env = {**os.environ, "GIT_AUTHOR_NAME": "swe", "GIT_AUTHOR_EMAIL": "swe@localhost",
               "GIT_COMMITTER_NAME": "swe", "GIT_COMMITTER_EMAIL": "swe@localhost"}
        for cmd in (["git", "init", "-q", "-b", "main"], ["git", "add", "-A"],
                    ["git", "commit", "-q", "--no-verify", "-m", f"base {base}"]):
            run(cmd, cwd=ws, check=True, env=env, capture_output=True)
        # Pack on the local disk, then copy the single finished file to the shared disk.
        local = Path(tmp) / "snap.tgz"
        run(["tar", "-czf", str(local), "-C", str(ws), "."], check=True)
        tmp_out = out.with_suffix(".tmp")
        shutil.copyfile(local, tmp_out)
        tmp_out.rename(out)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default=str(REPO / "training" / "candidates.jsonl"))
    ap.add_argument("--limit", type=int, default=0, help="only the first N candidates (0 = all)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--since", default="2019", help="skip PRs merged before this date (old code does not run on Python 3.12)")
    ap.add_argument("--max-src-lines", type=int, default=300, help="skip fixes bigger than this (too big for 28 tool calls)")
    args = ap.parse_args()
    cands = [json.loads(l) for l in Path(args.candidates).read_text().splitlines() if l.strip()]
    cands = [c for c in cands if c["merged_at"] >= args.since and c["src_lines"] <= args.max_src_lines]
    if args.limit:
        cands = cands[: args.limit]
    print(f"{len(cands)} candidate PRs to build | unpacking in {WORK}", flush=True)
    (TRAIN / "snapshots").mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    wheels = TRAIN / "wheels"
    if not wheels.exists():
        wheels.symlink_to(ROOT / "data" / "wheels")
    clones = {r: str(clone(r)) for r in sorted({c["repo"] for c in cands})}

    rows, skips = [], {}
    with ProcessPoolExecutor(args.workers) as ex:
        futs = {ex.submit(build_one, c, clones[c["repo"]]): c["instance_id"] for c in cands}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                r = f.result()
            except Exception as e:  # one bad PR must not stop the rest
                r = {"instance_id": futs[f], "skip": f"error: {str(e)[:150]}"}
            if "skip" in r:
                skips[r["instance_id"]] = r["skip"]
            else:
                rows.append(r)
            if i % 20 == 0 or i == len(cands):
                print(f"  {time.strftime('%H:%M:%S')} {i}/{len(cands)} done, {len(rows)} tasks built", flush=True)
    rows.sort(key=lambda r: r["instance_id"])
    (TRAIN / "tasks.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (TRAIN / "build_skips.json").write_text(json.dumps(skips, indent=1))
    by_repo = {}
    for r in rows:
        by_repo[r["repo"]] = by_repo.get(r["repo"], 0) + 1
    print(f"built {len(rows)} tasks {by_repo}, skipped {len(skips)} (reasons in {TRAIN / 'build_skips.json'})")
    print(f"size: {subprocess.run(['du', '-sh', str(TRAIN / 'snapshots')], capture_output=True, text=True).stdout.split()[0]}")


if __name__ == "__main__":
    sys.exit(main())

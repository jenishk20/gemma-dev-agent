"""Build the test-library folder the harness's subprocess sandbox needs (pytest + each repo's test dependencies).

  python tools/build_testdeps.py            (defaults: $GDA_ROOT/data/wheels -> $GDA_ROOT/testdeps/site-packages)

Why: in subprocess mode swegemma skips installing test dependencies and lets each sandbox borrow the host Python's
packages. Kaggle's machines have pytest etc. preinstalled; our vLLM venv does not, so every test run failed with
"No module named pytest". This mirrors Kaggle's sandbox image (docker/Dockerfile.sandbox): pytest, pytest-timeout==2.1.0,
plus the competition's own test wheels (data/wheels, highest version per package, like swegemma's _deduplicate_wheels).
It goes into a separate folder, never the vLLM venv; tools/run_local_eval.py puts it first on the sandbox's path.
Compiled wheels built only for Python 3.13 are fetched for our Python (3.12) at the same version from PyPI.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("GDA_ROOT", Path(__file__).resolve().parents[2] / "gda"))
BASE = ["pytest", "pytest-timeout==2.1.0"]           # Dockerfile.sandbox installs these from PyPI
SKIP = {"pytest", "pytest_timeout", "pluggy", "pip", "setuptools", "wheel"}  # provided by BASE / not wanted


def norm(name):
    return re.sub(r"[-_.]+", "_", name).lower()


def pick(wheels_dir, py_tag):
    """Highest version per package. Returns (local wheel files usable as-is, name==version to fetch for our Python)."""
    from packaging.version import InvalidVersion, Version
    best = {}
    for f in sorted(wheels_dir.glob("*.whl")):
        parts = f.name[:-4].split("-")
        if len(parts) < 5:
            continue
        name, ver = norm(parts[0]), parts[1]
        try:
            v = Version(ver)
        except InvalidVersion:
            continue
        ok_here = parts[-2] == "none" or "abi3" in parts[-2] or py_tag in parts[-3]
        cur = best.get(name)
        if cur is None or v > cur[0] or (v == cur[0] and ok_here and not cur[2]):
            best[name] = (v, f, ok_here)
    files, reqs = [], []
    for name, (v, f, ok_here) in sorted(best.items()):
        if name in SKIP:
            continue
        (files if ok_here else reqs).append(str(f) if ok_here else f"{name}=={v}")
    return files, reqs


def uv_install(uv, py, target, items, *extra):
    cmd = [uv, "pip", "install", "--python", py, "--target", str(target), *extra, *items]
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wheels", default=str(ROOT / "data" / "wheels"))
    ap.add_argument("--target", default=str(ROOT / "testdeps" / "site-packages"))
    ap.add_argument("--python", default=str(ROOT / "venv" / "bin" / "python"), help="the Python the sandboxes run")
    ap.add_argument("--uv", default=shutil.which("uv") or str(ROOT / "bootstrap" / "bin" / "uv"))
    args = ap.parse_args()

    wheels, target = Path(args.wheels), Path(args.target)
    pyver = subprocess.run([args.python, "-c", "import sys; print(f'cp{sys.version_info[0]}{sys.version_info[1]}')"],
                           capture_output=True, text=True, check=True).stdout.strip()
    files, reqs = pick(wheels, pyver)
    print(f"{wheels}: {len(files)} wheels usable as-is, {len(reqs)} to fetch for {pyver}; target {target}", flush=True)
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    r = uv_install(args.uv, args.python, target, BASE)
    if r.returncode:
        sys.exit(f"pytest install failed:\n{r.stderr[-3000:]}")
    # Test wheels: --no-deps like the harness (it unpacks wheels, it does not resolve them). Batch first, then one by one.
    items, skipped = files + reqs, []
    r = uv_install(args.uv, args.python, target, items, "--no-deps", "--find-links", str(wheels))
    if r.returncode:
        print("batch install failed; installing one by one to find the bad ones", flush=True)
        for it in items:
            if uv_install(args.uv, args.python, target, [it], "--no-deps", "--find-links", str(wheels)).returncode:
                skipped.append(Path(it).name if it.endswith(".whl") else it)
    # Python 3.12 removed the 'imp' module; Kaggle's sandbox image ships a shim for old repos (docker/imp.py).
    for cand in (ROOT / "data" / "docker" / "imp.py", ROOT / "data" / "imp.py"):
        if cand.exists():
            shutil.copy(cand, target / "imp.py")
            break

    check = subprocess.run([args.python, "-I", "-c", f"import sys; sys.path.insert(0, {str(target)!r}); "
                            "import pytest, pytest_timeout; print('pytest', pytest.__version__)"],
                           capture_output=True, text=True)
    print(check.stdout.strip() or check.stderr.strip()[-500:])
    n = len([p for p in target.iterdir() if p.name.endswith(".dist-info")])
    print(f"installed {n} packages into {target}" + (f"; SKIPPED {len(skipped)}: {', '.join(skipped)}" if skipped else ""))
    (target.parent / ".done").write_text("ok\n")
    return 0 if check.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

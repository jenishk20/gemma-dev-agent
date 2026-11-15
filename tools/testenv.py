"""Test libraries for the harness's subprocess sandbox, set per task like a working checkout of that commit.

Kaggle's scorer runs tests in Docker: the competition wheels go into site-packages, the repo is pip-installed in
editable mode, and a scorer-side script (/sandbox/setup.py, not public) installs each repo's test dependencies.
In subprocess mode swegemma skips all of that, so we do it here instead:

  base     $GDA_ROOT/testdeps/site-packages: pytest + every repo's declared test needs + data/wheels on top
           (built once by tools/build_testdeps.py).
  overlay  per task, read from the checked-out workspace: libraries whose base version breaks the repo's own
           version limits (e.g. old fastapi commits need starlette<0.51; base has 1.6.0), and the lock-file
           versions of the repo's direct dependencies (e.g. rich's poetry.lock pins Pygments, which changes
           syntax-highlighting output). Built once per distinct set into $GDA_ROOT/testdeps/overlays/<hash>.
  source   <workspace>/src for src-layout repos (requests), so tests import the patched code, not a wheel.

Search order inside every sandbox: source, overlay, base, then the host venv (via the sandbox's _host_env.pth).
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import tomllib
from pathlib import Path

ROOT = Path(os.environ.get("GDA_ROOT", Path(__file__).resolve().parents[2] / "gda"))
BASE = ROOT / "testdeps" / "site-packages"
OVERLAYS = ROOT / "testdeps" / "overlays"

REQ_FILE = re.compile(r"^(requirements|test-requirements|dev-requirements)[\w.-]*\.txt$")
TEST_GROUPS = re.compile(r"^(test|tests|testing|all)$")         # pyproject extras / dependency groups we read
DEV_GROUPS = re.compile(r"^(dev|develop|development)$")          # only if a repo has no test group at all
SKIP_INCLUDE = re.compile(r"doc|lint|translat|release|github|typing|screenshot")  # groups/files for docs etc.
# Not needed to run tests (linters, type checkers, browsers), or pytest plugins that change how every test run
# behaves (random order, parallel workers, fancy output). Kaggle's base set leaves out pytest-xdist the same way.
SKIP_REQS = {"mypy", "ruff", "ty", "black", "isort", "flake8", "pylint", "pyright", "pre_commit", "prek", "zizmor",
             "playwright", "pytest_sugar", "pytest_codspeed", "pytest_xdist", "pytest_randomly", "pytest_pretty",
             "codespell", "tox", "nox", "twine", "build"}
LOCKS = ("poetry.lock", "uv.lock", "pdm.lock")
NEVER_PIN = {"pip", "setuptools", "wheel", "pytest_timeout", "python"}  # pytest-timeout stays at Kaggle's 2.1.0


def norm(name):
    return re.sub(r"[-_.]+", "_", name).lower()


def read_repo_files(ws):
    """The small files that declare a repo's dependencies, from a checked-out workspace."""
    ws, files = Path(ws), {}
    for p in [*ws.glob("*"), *ws.glob("*/*")]:
        rel = p.relative_to(ws).as_posix()
        if p.is_file() and (REQ_FILE.match(p.name) or rel in ("pyproject.toml", *LOCKS)):
            files[rel] = p.read_text(encoding="utf-8", errors="replace")
    return files


def declared(files, repo=""):
    """(declared requirement strings, direct runtime dependency names, own package name) from a repo's files."""
    out, direct, own = [], set(), norm(repo.split("/")[-1]) if repo else ""

    def from_txt(name, seen):
        base = Path(name).name
        if name in seen or name not in files or (SKIP_INCLUDE.search(base) and "test" not in base):
            return                                       # e.g. requirements.txt -> -r requirements-docs.txt
        seen.add(name)
        for line in files[name].splitlines():
            line = line.split(" #")[0].strip()
            if line.startswith(("-r ", "--requirement ")):
                from_txt(str(Path(name).parent / line.split(None, 1)[1]).lstrip("./"), seen)
            elif line and not line.startswith(("#", "-", ".", "/", "git+", "http://", "https://")):
                out.append(line)

    seen = set()
    for name in sorted(files):
        if name.endswith(".txt"):
            from_txt(name, seen)
    if "pyproject.toml" in files:
        try:
            py = tomllib.loads(files["pyproject.toml"])
        except Exception:
            py = {}
        proj, poetry = py.get("project", {}), py.get("tool", {}).get("poetry", {})
        own = norm(proj.get("name") or poetry.get("name") or own)
        deps = [d for d in proj.get("dependencies", []) if isinstance(d, str)]
        out += deps
        direct |= {norm(re.split(r"[\s\[<>=!~;(]", d, maxsplit=1)[0]) for d in deps}
        direct |= {norm(k) for k in poetry.get("dependencies", {})}
        groups = py.get("dependency-groups", {})

        def group(g, seen=()):
            for d in groups.get(g, []):
                if isinstance(d, str):
                    out.append(d)
                elif isinstance(d, dict) and (inc := d.get("include-group")) and inc not in seen \
                        and ("test" in inc or not SKIP_INCLUDE.search(inc)):
                    group(inc, (*seen, g))
        extras = proj.get("optional-dependencies", {})
        has_test = any(TEST_GROUPS.match(g) and g != "all" for g in (*extras, *groups))
        pick = lambda g: TEST_GROUPS.match(g) or (not has_test and DEV_GROUPS.match(g))  # noqa: E731
        for g, deps in extras.items():
            if pick(g):
                out += [d for d in deps if isinstance(d, str)]
        for g in groups:
            if pick(g):
                group(g)
    name = lambda d: norm(re.split(r"[\s\[<>=!~;(]", d, maxsplit=1)[0])  # noqa: E731
    keep = [d for d in out if name(d) != own and name(d) not in SKIP_REQS]
    return list(dict.fromkeys(keep)), direct - {own}, own


def lock_versions(files):
    """{package: version} from the repo's lock file (poetry.lock, uv.lock or pdm.lock), if it has one."""
    for name in LOCKS:
        if name in files:
            try:
                return {norm(p["name"]): p["version"] for p in tomllib.loads(files[name]).get("package", [])
                        if "name" in p and "version" in p}
            except Exception:
                return {}
    return {}


def installed(site):
    """{package: version} for a site-packages folder."""
    out = {}
    for d in Path(site).glob("*.dist-info"):
        name, _, ver = d.name[: -len(".dist-info")].partition("-")
        out[norm(name)] = ver
    return out


def task_pins(files, repo="", base=None):
    """What this checkout needs on top of the base set: version limits the base breaks, plus lock-file versions."""
    from packaging.requirements import InvalidRequirement, Requirement
    from packaging.version import InvalidVersion, Version
    base = installed(BASE) if base is None else base
    reqs, direct, own = declared(files, repo)
    lock = lock_versions(files)
    pins = {}
    for s in reqs:
        try:
            r = Requirement(s)
        except InvalidRequirement:
            continue
        n = norm(r.name)
        if n in NEVER_PIN or n == own:
            continue
        try:
            if r.marker and not r.marker.evaluate({"extra": ""}):
                continue
        except Exception:
            pass
        have = base.get(n)
        if n in direct and n in lock and have != lock[n]:
            pins[n] = f"{r.name}=={lock[n]}"
        elif have is None:
            pins.setdefault(n, f"{r.name}{r.specifier}")
        elif r.specifier:
            try:
                ok = r.specifier.contains(Version(have), prereleases=True)
            except InvalidVersion:
                ok = True
            if not ok:
                pins[n] = f"{r.name}{r.specifier}"
    for n in direct - set(pins) - NEVER_PIN:              # direct deps only listed in poetry's table
        if n in lock and n in base and base[n] != lock[n]:
            pins[n] = f"{n}=={lock[n]}"
    return sorted(pins.values())


_locks, _guard = {}, threading.Lock()


def uv_bin():
    return shutil.which("uv") or str(ROOT / "bootstrap" / "bin" / "uv")


def ensure_overlay(pins, label=""):
    """Folder with these libraries installed (cached by the set of pins). None if nothing is needed."""
    if not pins:
        return None
    key = hashlib.sha1("\n".join(pins).encode()).hexdigest()[:12]
    dest = OVERLAYS / key
    with _guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        if (dest / ".done").exists():
            return dest
        t0, tmp = time.time(), OVERLAYS / f".{key}.{os.getpid()}.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        env = {**os.environ, "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", str(ROOT / "cache" / "uv"))}
        cmd = [uv_bin(), "pip", "install", "--python", sys.executable, "--target", str(tmp), "-q"]
        skipped = []
        if subprocess.run(cmd + pins, env=env, capture_output=True, text=True).returncode:
            for p in pins:                                   # one bad pin should not cost the rest
                if subprocess.run(cmd + [p], env=env, capture_output=True, text=True).returncode:
                    skipped.append(p)
        (tmp / "pins.txt").write_text("\n".join(pins) + "\n")
        (tmp / ".done").write_text("ok\n")
        if (dest / ".done").exists():                       # another job finished it meanwhile
            shutil.rmtree(tmp, ignore_errors=True)
            return dest
        shutil.rmtree(dest, ignore_errors=True)
        tmp.rename(dest)
        print(f"  [testenv] {label}: built overlay {key} in {time.time() - t0:.0f}s: {', '.join(pins)}"
              + (f" | could not install: {', '.join(skipped)}" if skipped else ""), flush=True)
        return dest


def install():
    """Patch swegemma so every subprocess sandbox gets source + overlay + base on its path (idempotent)."""
    assert (BASE / "pytest").is_dir(), f"no pytest in {BASE}: run tools/build_testdeps.py first"
    import swegemma.evaluate as ev_mod
    import swegemma.harness as h_mod
    import swegemma.harness.agent_runner as ar_mod
    import swegemma.harness.container_setup as cs_mod
    import swegemma.harness.verification as vf_mod
    from swegemma.sandbox.subprocess import SubprocessManager
    if getattr(SubprocessManager.start, "_testenv", False):
        return
    base = installed(BASE)

    def write_path(mgr, sid, first=()):
        info = mgr._sandboxes[sid]
        for sp in info["venv"].glob("lib/python*/site-packages"):
            pth = sp / "_host_env.pth"
            host = info.setdefault("_host_pth", pth.read_text(encoding="utf-8") if pth.exists() else "")
            pth.write_text("".join(f"{p}\n" for p in (*first, BASE)) + host, encoding="utf-8")

    orig_start = SubprocessManager.start

    def start(self, *a, **kw):
        sid = orig_start(self, *a, **kw)
        write_path(self, sid)                                # pytest available from the first command on
        return sid
    start._testenv = True
    SubprocessManager.start = start

    orig_install = cs_mod.install_test_dependencies

    def install_test_dependencies(docker, container_id, repo="", *a, **kw):
        if type(docker).__name__ not in {"SubprocessManager", "SubprocessSandbox"} or not hasattr(docker, "_sandboxes"):
            return orig_install(docker, container_id, repo, *a, **kw)
        ws = Path(docker._sandboxes[container_id]["workspace"])
        try:
            overlay = ensure_overlay(task_pins(read_repo_files(ws), repo, base), label=repo)
        except Exception as e:                               # never break a run over this; base set still works
            print(f"  [testenv] {repo}: overlay failed ({e}); using the base set", flush=True)
            overlay = None
        src = ws / "src"
        first = [p for p in (src if src.is_dir() else None, overlay) if p]
        write_path(docker, container_id, first)
    for m in (cs_mod, h_mod, ar_mod, vf_mod, ev_mod):
        if hasattr(m, "install_test_dependencies"):
            m.install_test_dependencies = install_test_dependencies

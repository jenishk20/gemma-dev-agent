"""Package a submission folder for the Gemma 4 Developer Agent competition.

  python3 tools/build_notebook.py submissions/e4b_baseline
  python3 tools/build_notebook.py submissions/e4b_v4_lora --kernel e4b-v4-lora

Writes, next to the folder:
  <name>.zip    the submission archive (agent.yaml at the root), for local checks
  <name>.ipynb  a Kaggle notebook that recreates the files and writes
                /kaggle/working/submission.zip; run it on CPU with internet off, then Submit.

Adapters (submissions/<name>/adapters/<adapter>/adapter_config.json + adapter_model.safetensors) are too big
to embed in a notebook. For each one this also writes kaggle_datasets/<slug>/ (the adapter files +
dataset-metadata.json) to upload as a PRIVATE Kaggle dataset:
  kaggle datasets create -p kaggle_datasets/<slug>
The notebook finds that dataset under /kaggle/input, checks every file's sha256 against the local copy,
and puts the files into submission.zip at adapters/<adapter>/.
With --kernel ID, also writes kernels/<name>/kernel-metadata.json (jenishk/gemma4-agent-<ID>) with the
datasets attached, ready for `kaggle kernels push -p kernels/<name>`.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import zipfile

ALLOWED = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}
USER = "jenishk"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--kernel", help="kernel id suffix, e.g. e4b-v4-lora -> jenishk/gemma4-agent-e4b-v4-lora")
    args = ap.parse_args()

    src = pathlib.Path(args.folder).resolve()
    files = {p.relative_to(src).as_posix(): p for p in sorted(src.rglob("*")) if p.is_file() and not p.name.startswith(".")}
    assert "agent.yaml" in files, "agent.yaml must be at the root"
    bad = [f for f in files if pathlib.Path(f).suffix.lower() not in ALLOWED]
    assert not bad, f"disallowed file types: {bad}"

    # adapters/<name>/... -> shipped through a Kaggle dataset; everything else is embedded as text
    adapters = {}
    for rel in files:
        m = re.match(r"adapters/([^/]+)/(.+)$", rel)
        if m:
            adapters.setdefault(m.group(1), []).append(m.group(2))
    for name, parts in adapters.items():
        assert {"adapter_config.json", "adapter_model.safetensors"} <= set(parts), f"adapter {name}: needs adapter_config.json + adapter_model.safetensors, has {parts}"
        assert all("/" not in p for p in parts), f"adapter {name}: no subfolders allowed, has {parts}"
    texts = {rel: p.read_text(encoding="utf-8") for rel, p in files.items() if not rel.startswith("adapters/")}
    assert not any(rel.endswith(".safetensors") for rel in texts), "a .safetensors file outside adapters/<name>/"

    zip_path = src.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, p in files.items():
            zf.write(p, rel)

    # one private dataset per adapter; its slug carries the adapter's fingerprint so a new adapter = new dataset
    ship = {}                                         # adapter name -> {slug, files: {file: sha256}}
    for name, parts in sorted(adapters.items()):
        hashes = {f: sha256(src / "adapters" / name / f) for f in sorted(parts)}
        slug = f"gda-{src.name}-{name}-{hashes['adapter_model.safetensors'][:8]}".replace("_", "-").lower()
        ship[name] = {"slug": slug, "files": hashes}
        ddir = ROOT / "kaggle_datasets" / slug
        if ddir.exists():
            shutil.rmtree(ddir)
        ddir.mkdir(parents=True)
        for f in parts:
            target = ddir / f
            try:
                os.link(src / "adapters" / name / f, target)       # no second copy of a large file
            except OSError:
                shutil.copy2(src / "adapters" / name / f, target)
        (ddir / "dataset-metadata.json").write_text(json.dumps(
            {"title": slug, "id": f"{USER}/{slug}", "licenses": [{"name": "CC0-1.0"}]}, indent=2))
        size = sum((ddir / f).stat().st_size for f in parts)
        print(f"adapter {name}: {size / 1e6:.0f} MB -> kaggle_datasets/{slug}/ (upload: kaggle datasets create -p kaggle_datasets/{slug})")

    code = (
        "import hashlib, json, zipfile\n"
        "from pathlib import Path\n\n"
        f"FILES = json.loads({json.dumps(json.dumps(texts, indent=1))})\n"
        f"ADAPTERS = json.loads({json.dumps(json.dumps(ship))})\n\n"
        "def sha256(p):\n"
        "    h = hashlib.sha256()\n"
        "    with open(p, 'rb') as f:\n"
        "        for b in iter(lambda: f.read(1 << 20), b''):\n"
        "            h.update(b)\n"
        "    return h.hexdigest()\n\n"
        "def find(slug, files):\n"
        "    # the attached dataset's folder: wherever Kaggle mounts it under /kaggle/input\n"
        "    for cfg in Path('/kaggle/input').rglob('adapter_config.json'):\n"
        "        d = cfg.parent\n"
        "        if slug in str(d) and all((d / f).is_file() for f in files):\n"
        "            return d\n"
        "    raise SystemExit(f'dataset {slug} not attached (Add Input -> Your Datasets)')\n\n"
        "out = Path('/kaggle/working/submission.zip')\n"
        "with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:\n"
        "    for name, text in FILES.items():\n"
        "        zf.writestr(name, text)\n"
        "    for name, a in ADAPTERS.items():\n"
        "        d = find(a['slug'], a['files'])\n"
        "        for f, h in a['files'].items():\n"
        "            assert sha256(d / f) == h, f'{d / f}: sha256 differs from the local adapter'\n"
        "            zf.write(d / f, f'adapters/{name}/{f}', compress_type=zipfile.ZIP_STORED)\n"
        "        print('adapter', name, 'from', d, 'sha256 ok')\n"
        "print(out, out.stat().st_size, 'bytes:', sorted(zipfile.ZipFile(out).namelist()))\n"
        "print(FILES['agent.yaml'])\n"
        "print(FILES['eval_config.yaml'])\n"
    )
    nb = {
        "cells": [
            {"cell_type": "markdown", "id": "intro", "metadata": {}, "source": [f"# {src.name}\n\nWrites `submission.zip` for the Gemma 4 Developer Agent competition. Run on CPU with internet off, then Submit."]},
            {"cell_type": "code", "id": "write-zip", "metadata": {}, "execution_count": None, "outputs": [], "source": [code]},
        ],
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}, "language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    nb_path = src.with_suffix(".ipynb")
    nb_path.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print(f"{zip_path.name}: {zip_path.stat().st_size / 1e6:.1f} MB, {len(files)} files")
    print(f"{nb_path.name}: notebook written")

    if args.kernel:
        kdir = ROOT / "kernels" / src.name
        kdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(nb_path, kdir / nb_path.name)
        meta = {"id": f"{USER}/gemma4-agent-{args.kernel}", "title": f"gemma4 agent {args.kernel.replace('-', ' ')}",
                "code_file": nb_path.name, "language": "python", "kernel_type": "notebook", "is_private": True,
                "enable_gpu": False, "enable_tpu": False, "enable_internet": False,
                "dataset_sources": [f"{USER}/{a['slug']}" for a in ship.values()],
                "competition_sources": ["gemma-4-developer-agent"], "kernel_sources": [], "model_sources": []}
        (kdir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2))
        print(f"kernels/{src.name}/: kernel {meta['id']} (datasets: {meta['dataset_sources'] or 'none'})")


if __name__ == "__main__":
    main()

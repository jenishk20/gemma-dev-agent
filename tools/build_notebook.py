"""Package a submission folder for the Gemma 4 Developer Agent competition.

  python3 tools/build_notebook.py submissions/e4b_baseline

Writes, next to the folder:
  <name>.zip    the submission archive (agent.yaml at the root), for local checks
  <name>.ipynb  a Kaggle notebook that recreates the files and writes
                /kaggle/working/submission.zip; run it on CPU with internet off, then Submit.
"""
import json
import pathlib
import sys
import zipfile

ALLOWED = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}


def main(folder: str) -> None:
    src = pathlib.Path(folder).resolve()
    files = {p.relative_to(src).as_posix(): p for p in sorted(src.rglob("*")) if p.is_file() and not p.name.startswith(".")}
    assert "agent.yaml" in files, "agent.yaml must be at the root"
    bad = [f for f in files if pathlib.Path(f).suffix.lower() not in ALLOWED]
    assert not bad, f"disallowed file types: {bad}"
    assert not any(f.endswith(".safetensors") for f in files), "adapters are too big to embed; upload them as a Kaggle dataset instead"

    zip_path = src.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, p in files.items():
            zf.write(p, rel)

    texts = {rel: p.read_text(encoding="utf-8") for rel, p in files.items()}
    code = (
        "import json, zipfile\n"
        "from pathlib import Path\n\n"
        f"FILES = json.loads({json.dumps(json.dumps(texts, indent=1))})\n\n"
        "out = Path('/kaggle/working/submission.zip')\n"
        "with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:\n"
        "    for name, text in FILES.items():\n"
        "        zf.writestr(name, text)\n"
        "print(out, out.stat().st_size, 'bytes:', sorted(FILES))\n"
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
    print(f"{zip_path.name}: {zip_path.stat().st_size} bytes, {len(files)} files")
    print(f"{nb_path.name}: notebook written")


if __name__ == "__main__":
    main(sys.argv[1])

"""Validate a submission zip with the competition's own harness code before spending a submission.

  <venv with swegemma, adk_submission, adk_eval_core, google_adk>/bin/python tools/validate_submission.py submissions/e4b_baseline.zip

Runs the same checks as the Kaggle notebook and scorer: archive layout, file types and size,
symlinks, validate_directory, the single-allowed-model rule, adapters, eval_config budgets,
and a full compile_submission() of the agent tree (catches YAML/schema/tool/model errors).
No model is called.
"""
import inspect
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import yaml
from adk_submission import validate_directory, discover_adapters, compile_submission
from adk_submission.discovery import discover_declared_models
from adk_submission.registry import ModelRegistry
from google.adk.models.lite_llm import LiteLlm
from swegemma.config import ALLOWED_SUBMISSION_EXTENSIONS, MAX_SUBMISSION_SIZE_BYTES, build_submission_limits

ALLOWED_MODELS = {
    "gemma-4-31b-it-qat-w4a16-ct",
    "gemma-4-12b-it-qat-w4a16-ct",
    "gemma-4-e4b-it-qat-w4a16-ct",
    "gemma-4-e2b-it-qat-w4a16-ct",
}
TOOL_NAMES = ["run_command", "submit_patch", "get_status", "read_file", "edit_file", "write_file",
              "get_code_neighbors", "search_similar_code", "get_code_subgraph"]


def stub_tools() -> dict:
    """Signature-correct stand-ins for the 9 harness tools (compile only needs names and signatures)."""
    def run_command(command: str) -> str: return ""
    def submit_patch() -> str: return ""
    def get_status() -> str: return ""
    def read_file(filepath: str, start_line: int | None = None, end_line: int | None = None) -> str: return ""
    def edit_file(filepath: str, old_string: str, new_string: str, allow_multiple: bool = False) -> str: return ""
    def write_file(filepath: str, content: str) -> str: return ""
    def get_code_neighbors(node: str, edge_type: str | None = None, max_neighbors: int = 50) -> str: return ""
    def search_similar_code(query: str, k: int = 10) -> str: return ""
    def get_code_subgraph(nodes: list[str]) -> str: return ""
    loc = locals()
    return {n: loc[n] for n in TOOL_NAMES}


def check(ok: bool, msg: str) -> None:
    print(("  PASS  " if ok else "  FAIL  ") + msg)
    if not ok:
        raise SystemExit(1)


def walk(agent, depth=0):
    model = getattr(agent, "model", None)
    model = getattr(model, "model", model)
    tools = [getattr(t, "name", type(t).__name__) for t in getattr(agent, "tools", []) or []]
    print(f"{'    ' * depth}  - {agent.name} [{type(agent).__name__}] model={model} tools={tools}")
    for t in getattr(agent, "tools", []) or []:
        if hasattr(t, "agent"):
            walk(t.agent, depth + 1)
    for s in getattr(agent, "sub_agents", []) or []:
        walk(s, depth + 1)


def main(zip_path: str) -> None:
    zp = Path(zip_path)
    print(f"Validating {zp}")
    with zipfile.ZipFile(zp) as zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        names = [i.filename for i in infos]
        check(zf.testzip() is None, "zip archive is readable (CRC ok)")
        check("agent.yaml" in names, "agent.yaml is at the archive root")
        check(sum(i.file_size for i in infos) <= MAX_SUBMISSION_SIZE_BYTES, f"unpacked size {sum(i.file_size for i in infos)} bytes <= 3 GiB")
        bad = [n for n in names if Path(n).suffix.lower() not in ALLOWED_SUBMISSION_EXTENSIONS]
        check(not bad, f"only allowed file types ({', '.join(sorted(ALLOWED_SUBMISSION_EXTENSIONS))})")
        check(not any(n.startswith("/") or ".." in Path(n).parts for n in names), "no absolute or .. paths")
        tmp = Path(tempfile.mkdtemp())
        zf.extractall(tmp)

    check(not any(p.is_symlink() for p in tmp.rglob("*")), "no symlinks")
    limits, gen_constraints = build_submission_limits()
    validate_directory(tmp, limits=limits)
    check(True, "validate_directory() (official structural limits)")

    models = discover_declared_models(tmp)
    check(len(models) == 1, f"exactly one base model declared: {sorted(models)}")
    model = next(iter(models))
    check(model in ALLOWED_MODELS, f"model {model} is an allowed competition model")

    adapters = discover_adapters(str(tmp))
    adapter_map = getattr(adapters, "adapters", None) or {}
    for p in [tmp / "agent.yaml", *sorted((tmp / "sub_agents").glob("*.yaml"))]:
        if p.is_file():
            ref = (yaml.safe_load(p.read_text().replace("!include", "")) or {}).get("adapter")
            check(ref is None or ref in adapter_map, f"{p.name}: adapter reference {ref!r} resolves")
    print(f"        adapters found: {sorted(adapter_map) or 'none'}")

    ec = tmp / "eval_config.yaml"
    if ec.is_file():
        ev = (yaml.safe_load(ec.read_text()) or {}).get("evaluation", {})
        print(f"        eval_config: {ev}")
        check(set(ev) <= {"timeout_seconds", "max_tool_calls", "max_time_minutes", "max_turns", "verification_timeout_seconds"}, "eval_config keys are recognised")
        check(1 <= float(ev.get("max_time_minutes", 60)) <= 60, "max_time_minutes in a sane range")

    registry = ModelRegistry()
    registry.register(model, LiteLlm(model=f"openai/{model}", api_base="http://127.0.0.1:8000/v1", api_key="EMPTY"))
    agent = compile_submission(submission_dir=tmp, tool_registry=stub_tools(), model_registry=registry,
                               limits=limits, generation_constraints=gen_constraints, adapter_manifest=adapters)
    check(True, "compile_submission() built the agent tree")
    walk(agent)
    gc = getattr(agent, "generate_content_config", None)
    if gc is not None:
        print(f"        root generate_content_config: temperature={gc.temperature} max_output_tokens={gc.max_output_tokens} thinking={gc.thinking_config}")
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    os.environ.setdefault("OPENAI_API_KEY", "EMPTY")
    main(sys.argv[1])

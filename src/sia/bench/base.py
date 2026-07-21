from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from pathlib import Path

import httpx

from sia.bench.extract import extract_code

DEFAULT_DATA_DIR = Path("data")


@dataclass(frozen=True)
class BenchTask:
    """One benchmark problem, normalized across benchmarks.

    ``instruction`` is the prompt shown to an instruct model. ``tests`` is an
    executable suffix: appended to solution code, it exits nonzero on failure.
    ``source_prompt`` keeps the original (e.g. HumanEval signature+docstring)
    for completion-style assembly fallback.
    """

    bench: str
    task_id: str
    instruction: str
    tests: str
    entry_point: str | None = None
    source_prompt: str = ""
    canonical_solution: str = ""


def build_execution(task: BenchTask, model_output: str) -> tuple[str, dict[str, str]]:
    """Return (program, auxiliary files) to execute for this task.

    Base benchmarks append their tests to the solution; EvalPlus benchmarks
    run differential testing against an oracle in separate modules.
    """
    if task.bench.endswith("+"):
        from sia.bench.evalplus import build_program

        return build_program(task, extract_code(model_output))
    return assemble_program(task, model_output), {}


def assemble_program(task: BenchTask, model_output: str) -> str:
    """Turn raw model output into an executable program ending in tests.

    Instruct models usually emit a complete function in a code fence; then the
    program is ``code + tests``. If the extracted code does not define the
    entry point (model emitted a bare body, completion-style), fall back to
    ``source_prompt + code + tests``.
    """
    code = extract_code(model_output)
    standalone = task.entry_point is None or re.search(
        rf"def\s+{re.escape(task.entry_point)}\s*\(", code
    )
    if standalone:
        solution = code
    else:
        # Bare body: keep as-is if already indented, otherwise indent one level.
        body = code if code[:1].isspace() else textwrap.indent(textwrap.dedent(code), "    ")
        solution = task.source_prompt + body
    return f"{solution}\n\n{task.tests}\n"


def fetch_cached(url: str, cache_path: Path) -> bytes:
    """Download ``url`` once; afterwards serve from ``cache_path``."""
    if cache_path.exists():
        return cache_path.read_bytes()
    response = httpx.get(url, follow_redirects=True, timeout=120)
    response.raise_for_status()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
    tmp.write_bytes(response.content)
    tmp.replace(cache_path)
    return response.content


def load_tasks(bench: str, data_dir: Path = DEFAULT_DATA_DIR) -> list[BenchTask]:
    if bench == "humaneval":
        from sia.bench.humaneval import load_humaneval

        return load_humaneval(data_dir)
    if bench == "mbpp":
        from sia.bench.mbpp import load_mbpp

        return load_mbpp(data_dir)
    if bench in ("humaneval+", "mbpp+"):
        from sia.bench.evalplus import load_evalplus

        return load_evalplus(bench, data_dir)
    raise ValueError(f"unknown benchmark: {bench!r}")

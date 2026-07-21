"""Run an experiment grid, resumably.

Cell → run_id mappings live in ``experiments/<id>/cells.json`` so an
interrupted grid resumes instead of re-spending compute, and so the report
can be rebuilt later without re-running anything.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from sia.experiments.spec import ExperimentSpec, GridCell
from sia.llm import LLMError, OpenAICompatClient
from sia.llm.openai_compat import OLLAMA_BASE_URL
from sia.runner import run_benchmark

DEFAULT_EXPERIMENTS_DIR = Path("experiments")


def _cells_path(spec: ExperimentSpec, experiments_dir: Path) -> Path:
    return experiments_dir / spec.id / "cells.json"


def load_cells(spec: ExperimentSpec, experiments_dir: Path = DEFAULT_EXPERIMENTS_DIR) -> dict:
    path = _cells_path(spec, experiments_dir)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_cells(
    spec: ExperimentSpec, cells: dict, experiments_dir: Path = DEFAULT_EXPERIMENTS_DIR
) -> None:
    path = _cells_path(spec, experiments_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cells, indent=2), encoding="utf-8")


def run_experiment(
    spec: ExperimentSpec,
    *,
    base_url: str = OLLAMA_BASE_URL,
    api_key: str | None = None,
    experiments_dir: Path = DEFAULT_EXPERIMENTS_DIR,
    runs_dir: Path = Path("runs"),
    progress: Callable[[str], None] | None = None,
    dry_run: bool = False,
) -> dict[str, str]:
    """Execute every cell not already recorded. Returns ``{label: run_id}``."""
    cells = load_cells(spec, experiments_dir)
    grid = spec.grid()
    say = progress or (lambda _: None)
    say(f"{spec.id}: {len(grid)} cells, {len(cells)} already complete")

    if dry_run:
        for cell in grid:
            state = "done" if cell.label() in cells else "pending"
            say(f"  [{state}] {cell.label()}")
        return cells

    # Preflight every distinct model before spending time on any cell, so a
    # typo or missing pull fails in seconds rather than mid-grid.
    for model in sorted({c.model for c in grid}):
        client = OpenAICompatClient(model, base_url=base_url, api_key=api_key)
        try:
            client.check_available()
        finally:
            client.close()

    for index, cell in enumerate(grid, start=1):
        label = cell.label()
        if label in cells:
            say(f"[{index}/{len(grid)}] skip (done): {label}")
            continue
        say(f"[{index}/{len(grid)}] running: {label}")
        run_id = _run_cell(
            spec, cell, base_url=base_url, api_key=api_key, runs_dir=runs_dir, progress=progress
        )
        if run_id:
            cells[label] = run_id
            _save_cells(spec, cells, experiments_dir)
    return cells


def _run_cell(
    spec: ExperimentSpec,
    cell: GridCell,
    *,
    base_url: str,
    api_key: str | None,
    runs_dir: Path,
    progress: Callable[[str], None] | None,
) -> str | None:
    if cell.condition != "none" or cell.repair_k:
        # M3 owns the repair conditions; the grid can already express them so
        # specs written now stay valid, but refuse to fabricate results.
        raise NotImplementedError(
            f"condition={cell.condition!r} repair_k={cell.repair_k} requires the M3 repair loop"
        )
    client = OpenAICompatClient(cell.model, base_url=base_url, api_key=api_key)
    try:
        kwargs = spec.run_kwargs()
        summary = run_benchmark(
            cell.bench,
            client,
            runs_dir=runs_dir,
            progress=None,
            **kwargs,
        )
    except LLMError as exc:
        if progress:
            progress(f"    failed: {exc}")
        return None
    finally:
        client.close()
    if progress:
        progress(f"    pass@1={summary.pass_rates.get('pass@1', 0):.3f}  run={summary.run_id}")
    return summary.run_id

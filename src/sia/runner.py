"""Benchmark run orchestration: tasks × samples → traced, scored, manifested runs."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from sia.agent import solve_single_shot
from sia.bench import BenchTask, assemble_program, load_tasks, pass_at_k, wilson_ci
from sia.bench.base import DEFAULT_DATA_DIR
from sia.llm import LLMClient, LLMError
from sia.sandbox import run_python
from sia.trace import RunManifest, TraceWriter
from sia.trace.writer import new_run_id


@dataclass
class RunSummary:
    run_id: str
    run_dir: Path
    bench: str
    model: str
    n_tasks: int
    samples: int
    pass_rates: dict[str, float]
    ci95: tuple[float, float] | None
    totals: dict[str, float] = field(default_factory=dict)


def run_benchmark(
    bench: str,
    llm: LLMClient,
    *,
    limit: int | None = None,
    samples: int = 1,
    temperature: float = 0.0,
    seed: int | None = None,
    max_tokens: int = 2048,
    exec_timeout_s: float = 10.0,
    runs_dir: Path = Path("runs"),
    data_dir: Path = DEFAULT_DATA_DIR,
    tasks: list[BenchTask] | None = None,
    progress: Callable[[str], None] | None = None,
) -> RunSummary:
    """Run one agent configuration over a benchmark, emitting trace + manifest + results.

    ``tasks`` overrides dataset loading (tests, subsets). Sequential by design
    for M1: a single local GPU serializes LLM calls anyway.
    """
    if tasks is None:
        tasks = load_tasks(bench, data_dir=data_dir)
    if limit is not None:
        tasks = tasks[:limit]

    run_id = new_run_id()
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "bench": bench,
        "model": llm.model,
        "limit": limit,
        "samples": samples,
        "temperature": temperature,
        "seed": seed,
        "max_tokens": max_tokens,
        "exec_timeout_s": exec_timeout_s,
        "agent": "single_shot",
    }
    manifest = RunManifest(run_id=run_id, config=config, model=llm.model, seed=seed)
    manifest.save(run_dir / "manifest.json")

    totals = {
        "llm_calls": 0,
        "llm_errors": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "llm_latency_ms": 0.0,
        "exec_ms": 0.0,
    }
    rows: list[dict[str, object]] = []
    started = time.perf_counter()

    with TraceWriter(run_dir / "trace.jsonl", run_id) as trace:
        for index, task in enumerate(tasks):
            trace.event("task_start", task_id=task.task_id)
            passed_count = 0
            for sample in range(samples):
                sample_seed = None if seed is None else seed + sample
                row: dict[str, object] = {"task_id": task.task_id, "sample": sample}
                try:
                    response = solve_single_shot(
                        task,
                        llm,
                        trace,
                        sample=sample,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        seed=sample_seed,
                    )
                except LLMError as exc:
                    totals["llm_errors"] += 1
                    trace.event("error", task_id=task.task_id, sample=sample, error=str(exc))
                    row.update(passed=False, error=str(exc))
                    rows.append(row)
                    continue
                totals["llm_calls"] += 1
                totals["prompt_tokens"] += response.prompt_tokens
                totals["completion_tokens"] += response.completion_tokens
                totals["llm_latency_ms"] += response.latency_ms

                program = assemble_program(task, response.content)
                result = run_python(program, timeout_s=exec_timeout_s)
                totals["exec_ms"] += result.duration_ms
                passed = result.ok
                passed_count += passed
                trace.event(
                    "verdict",
                    task_id=task.task_id,
                    sample=sample,
                    passed=passed,
                    exit_code=result.exit_code,
                    timed_out=result.timed_out,
                    stderr_tail=result.stderr[-2000:],
                )
                row.update(
                    passed=passed,
                    exit_code=result.exit_code,
                    timed_out=result.timed_out,
                    exec_ms=round(result.duration_ms, 1),
                    llm_latency_ms=round(response.latency_ms, 1),
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                )
                rows.append(row)
            if progress:
                progress(
                    f"[{index + 1}/{len(tasks)}] {task.task_id}: {passed_count}/{samples} passed"
                )

    totals["wall_s"] = round(time.perf_counter() - started, 2)
    (run_dir / "results.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )

    pass_rates = _pass_rates(rows, samples)
    n_passed_first = sum(1 for r in rows if r["sample"] == 0 and r.get("passed"))
    ci95 = wilson_ci(n_passed_first, len(tasks)) if samples == 1 and tasks else None

    manifest.totals = totals | {"tasks": len(tasks), **pass_rates}
    manifest.outcome = "completed"
    manifest.save(run_dir / "manifest.json")

    return RunSummary(
        run_id=run_id,
        run_dir=run_dir,
        bench=bench,
        model=llm.model,
        n_tasks=len(tasks),
        samples=samples,
        pass_rates=pass_rates,
        ci95=ci95,
        totals=totals,
    )


def _pass_rates(rows: list[dict[str, object]], samples: int) -> dict[str, float]:
    by_task: dict[object, list[bool]] = {}
    for row in rows:
        by_task.setdefault(row["task_id"], []).append(bool(row.get("passed")))
    ks = sorted({1, samples})
    rates: dict[str, float] = {}
    for k in ks:
        estimates = [
            pass_at_k(len(outcomes), sum(outcomes), k)
            for outcomes in by_task.values()
            if len(outcomes) >= k
        ]
        if estimates:
            rates[f"pass@{k}"] = sum(estimates) / len(estimates)
    return rates

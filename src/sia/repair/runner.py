"""Run a repair condition over a benchmark, starting from a baseline run.

Three compute savings, none of which cost rigour:

1. **Start from a baseline run.** First attempts are identical across
   conditions (same prompt, same greedy decode), so recomputing them per
   condition would burn compute to reproduce known outcomes — and makes the
   pairing between baseline and arm exact rather than merely statistical.
2. **Repair only failures.** Solved tasks need no iterations.
3. **Nested k.** One k_max trajectory records a verdict after every
   iteration, yielding pass rates for all k ≤ k_max from a single run.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from sia.bench import BenchTask, load_tasks
from sia.bench.base import DEFAULT_DATA_DIR
from sia.llm import LLMClient
from sia.parallel import default_workers, parallel_map
from sia.repair.loop import RepairOutcome, repair_task
from sia.sandbox import ExecResult
from sia.trace import RunManifest, TraceWriter
from sia.trace.writer import new_run_id


@dataclass
class BaselineTask:
    """One task's first-attempt result, replayed from a baseline trace."""

    task: BenchTask
    code: str
    passed: bool
    stdout: str
    stderr: str
    timed_out: bool

    def as_exec_result(self) -> ExecResult:
        return ExecResult(
            exit_code=0 if self.passed else 1,
            stdout=self.stdout,
            stderr=self.stderr,
            timed_out=self.timed_out,
            duration_ms=0.0,
        )


@dataclass
class RepairSummary:
    run_id: str
    run_dir: Path
    bench: str
    model: str
    condition: str
    k_max: int
    n_tasks: int
    pass_at_k: dict[int, float] = field(default_factory=dict)
    totals: dict[str, float] = field(default_factory=dict)


def load_baseline(
    baseline_run_id: str,
    bench: str,
    *,
    runs_dir: Path = Path("runs"),
    data_dir: Path = DEFAULT_DATA_DIR,
    tasks: list[BenchTask] | None = None,
) -> list[BaselineTask]:
    """Replay first attempts (code + execution output) from a baseline trace."""
    if tasks is None:
        tasks = load_tasks(bench, data_dir=data_dir)
    by_id = {t.task_id: t for t in tasks}

    responses: dict[str, str] = {}
    verdicts: dict[str, dict] = {}
    trace_path = runs_dir / baseline_run_id / "trace.jsonl"
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        data = event["data"]
        if data.get("sample") not in (0, None):
            continue
        task_id = data.get("task_id")
        if event["type"] == "llm_response":
            responses[task_id] = data["content"]
        elif event["type"] == "verdict":
            verdicts[task_id] = data

    out = []
    for task_id, verdict in verdicts.items():
        task = by_id.get(task_id)
        if task is None:
            continue
        from sia.bench import extract_code

        out.append(
            BaselineTask(
                task=task,
                code=extract_code(responses.get(task_id, "")),
                passed=bool(verdict["passed"]),
                stdout=verdict.get("stdout_tail", "") or "",
                stderr=verdict.get("stderr_tail", "") or "",
                timed_out=bool(verdict.get("timed_out", False)),
            )
        )
    out.sort(key=lambda b: b.task.task_id)
    return out


def run_repair(
    bench: str,
    llm: LLMClient,
    *,
    condition: str,
    k_max: int,
    baseline_run_id: str,
    temperature: float = 0.0,
    max_tokens: int = 2048,
    seed: int | None = 7,
    exec_timeout_s: float = 60.0,
    runs_dir: Path = Path("runs"),
    data_dir: Path = DEFAULT_DATA_DIR,
    tasks: list[BenchTask] | None = None,
    workers: int | None = None,
    progress: Callable[[str], None] | None = None,
) -> RepairSummary:
    baseline = load_baseline(
        baseline_run_id, bench, runs_dir=runs_dir, data_dir=data_dir, tasks=tasks
    )
    if not baseline:
        raise ValueError(f"baseline run {baseline_run_id!r} yielded no tasks")

    run_id = new_run_id()
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    n_workers = workers if workers is not None else default_workers()
    config = {
        "bench": bench,
        "model": llm.model,
        "agent": "repair",
        "condition": condition,
        "repair_k": k_max,
        "baseline_run_id": baseline_run_id,
        "samples": 1,
        "temperature": temperature,
        "seed": seed,
        "max_tokens": max_tokens,
        "exec_timeout_s": exec_timeout_s,
        "workers": n_workers,
    }
    manifest = RunManifest(run_id=run_id, config=config, model=llm.model, seed=seed)
    manifest.save(run_dir / "manifest.json")

    to_repair = [b for b in baseline if not b.passed]
    say = progress or (lambda _: None)
    say(
        f"{condition} k<={k_max}: {len(baseline)} tasks, {len(to_repair)} failed at baseline, "
        f"{n_workers} workers"
    )

    started = time.perf_counter()
    with TraceWriter(run_dir / "trace.jsonl", run_id) as trace:
        trace.event(
            "note",
            kind="repair_start",
            condition=condition,
            k_max=k_max,
            baseline_run_id=baseline_run_id,
            baseline_tasks=len(baseline),
            baseline_failures=len(to_repair),
        )

        done = [0]

        def work(item: BaselineTask) -> RepairOutcome:
            return repair_task(
                item.task,
                llm,
                trace,
                condition=condition,
                k_max=k_max,
                initial_code=item.code,
                initial_result=item.as_exec_result(),
                initial_passed=False,
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed,
                exec_timeout_s=exec_timeout_s,
            )

        def report(_index: int, item: BaselineTask, outcome: RepairOutcome) -> None:
            done[0] += 1
            solved = "solved" if outcome.passed_by(k_max) else "unsolved"
            say(f"  [{done[0]}/{len(to_repair)}] {item.task.task_id}: {solved}")

        outcomes = parallel_map(work, to_repair, workers=n_workers, on_result=report)

    # Tasks that passed at baseline are solved at every k.
    solved_at_baseline = len(baseline) - len(to_repair)
    pass_at_k = {}
    for k in range(k_max + 1):
        extra = sum(1 for o in outcomes if o.passed_by(k))
        pass_at_k[k] = (solved_at_baseline + extra) / len(baseline)

    totals = {
        "tasks": len(baseline),
        "baseline_failures": len(to_repair),
        "prompt_tokens": sum(o.prompt_tokens for o in outcomes),
        "completion_tokens": sum(o.completion_tokens for o in outcomes),
        "iterations": sum(o.iterations_used for o in outcomes),
        "wall_s": round(time.perf_counter() - started, 2),
        **{f"pass@k={k}": v for k, v in pass_at_k.items()},
    }
    manifest.totals = totals
    manifest.outcome = "completed"
    manifest.save(run_dir / "manifest.json")

    (run_dir / "results.jsonl").write_text(
        "".join(
            json.dumps(
                {
                    "task_id": o.task_id,
                    "condition": o.condition,
                    "passed_at": o.passed_at,
                    "iterations_used": o.iterations_used,
                    "prompt_tokens": o.prompt_tokens,
                    "completion_tokens": o.completion_tokens,
                }
            )
            + "\n"
            for o in outcomes
        ),
        encoding="utf-8",
    )

    return RepairSummary(
        run_id=run_id,
        run_dir=run_dir,
        bench=bench,
        model=llm.model,
        condition=condition,
        k_max=k_max,
        n_tasks=len(baseline),
        pass_at_k=pass_at_k,
        totals=totals,
    )

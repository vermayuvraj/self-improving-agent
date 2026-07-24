"""Failure taxonomy over run traces.

Promoted from ``scripts/analyze_failures.py`` (M2). The ``budget_exhausted``
class exists because EXP-001 showed a token budget that binds on one arm and
not another turns a configuration limit into an apparent capability gap; it
takes priority over every runtime signal, since a truncated response's
downstream error says nothing about the model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from sia.trace import read_jsonl

DEFAULT_RUNS_DIR = Path("runs")


def classify(output: str, timed_out: bool, *, budget_exhausted: bool = False) -> str:
    """Bucket one failure from the combined stdout+stderr of its execution.

    Order matters. ``budget_exhausted`` outranks everything (a truncated
    response's downstream error says nothing about the model). Crash signals
    are checked before wrong-answer signals, because the EvalPlus harness
    reports *both* — it prints ``input#N raised TypeError`` and then exits
    non-zero — and the crash is the more specific diagnosis.
    """
    if budget_exhausted:
        return "budget_exhausted"
    if timed_out:
        return "timeout"
    if not output.strip():
        return "no_output"
    if "SyntaxError" in output or "IndentationError" in output:
        return "syntax_error"
    if "does not define" in output:
        return "missing_entry_point"
    if "ImportError" in output or "ModuleNotFoundError" in output:
        return "import_error"
    if "RecursionError" in output:
        return "recursion_error"
    if "NameError" in output:
        return "name_error"
    if "TypeError" in output:
        return "type_error"
    if "IndexError" in output or "KeyError" in output:
        return "lookup_error"
    # EvalPlus differential failure, or a plain assertion from the base suites.
    if (
        "wrong answer" in output
        or "failing input" in output
        or "AssertionError" in output
        or "assert" in output
    ):
        return "wrong_answer"
    return "other_runtime_error"


def failure_output(verdict: dict) -> str:
    """Combined execution output for a verdict, stdout first.

    Traces written before M2 carry only ``stderr_tail``; ``stdout_tail`` is
    absent rather than empty, so this stays correct for older runs.
    """
    parts = [verdict.get("stdout_tail") or "", verdict.get("stderr_tail") or ""]
    return "\n".join(p for p in parts if p)


@dataclass
class FailureReport:
    run_id: str
    bench: str
    model: str
    tasks: int
    passed: int
    budget_exhausted: int
    taxonomy: dict[str, int] = field(default_factory=dict)
    outcomes: dict[str, bool] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.tasks if self.tasks else 0.0

    @property
    def conditional_pass(self) -> float | None:
        """Pass rate excluding responses that never produced code.

        ``None`` when nothing was truncated, in which case it equals
        ``pass_rate`` and reporting it separately would be noise.
        """
        scored = self.tasks - self.budget_exhausted
        return self.passed / scored if self.budget_exhausted and scored else None


def analyze_run(run_id: str, runs_dir: Path = DEFAULT_RUNS_DIR) -> FailureReport:
    run_dir = runs_dir / run_id
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8-sig"))
    max_tokens = manifest["config"].get("max_tokens", 0)

    verdicts: dict[tuple[str, int], dict] = {}
    responses: dict[tuple[str, int], dict] = {}
    for event in read_jsonl(run_dir / "trace.jsonl"):
        data = event["data"]
        key = (data.get("task_id"), data.get("sample"))
        if event["type"] == "verdict":
            verdicts[key] = data
        elif event["type"] == "llm_response":
            responses[key] = data

    def exhausted(key: tuple[str, int]) -> bool:
        r = responses.get(key)
        if not r or not max_tokens:
            return False
        return r["completion_tokens"] >= max_tokens - 8 or "```" not in r["content"]

    counts: dict[str, int] = {}
    n_exhausted = 0
    for key, verdict in verdicts.items():
        if verdict["passed"]:
            continue
        label = classify(
            failure_output(verdict),
            verdict.get("timed_out", False),
            budget_exhausted=exhausted(key),
        )
        counts[label] = counts.get(label, 0) + 1
        n_exhausted += label == "budget_exhausted"

    return FailureReport(
        run_id=run_id,
        bench=manifest["config"]["bench"],
        model=manifest["model"],
        tasks=len(verdicts),
        passed=sum(1 for v in verdicts.values() if v["passed"]),
        budget_exhausted=n_exhausted,
        taxonomy=dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        # Task-level outcomes keyed for paired tests across runs.
        outcomes={k[0]: v["passed"] for k, v in verdicts.items() if k[1] == 0},
    )

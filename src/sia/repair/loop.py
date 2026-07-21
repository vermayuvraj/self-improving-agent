from __future__ import annotations

from dataclasses import dataclass, field

from sia.bench import BenchTask, build_execution
from sia.llm import LLMClient, LLMError, Message
from sia.repair.conditions import build_retry_messages, summarize_failure
from sia.sandbox import ExecResult, run_python
from sia.trace import TraceWriter


@dataclass
class RepairOutcome:
    """Result of repairing one task, with the verdict after every iteration.

    ``passed_at`` is the nested k-curve for this task: ``passed_at[i]`` is the
    outcome after ``i`` repair iterations, so a single k_max trajectory yields
    pass rates for every k ≤ k_max. This is what makes the ablation affordable
    — and it is also *better* paired than independent runs per k, since the
    k=1 and k=8 arms share the identical prefix rather than merely the task.
    """

    task_id: str
    condition: str
    passed_at: list[bool] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    iterations_used: int = 0

    def passed_by(self, k: int) -> bool:
        """Solved within ``k`` repair iterations (k=0 means the first attempt)."""
        return any(self.passed_at[: k + 1])


def repair_task(
    task: BenchTask,
    llm: LLMClient,
    trace: TraceWriter,
    *,
    condition: str,
    k_max: int,
    initial_code: str,
    initial_result: ExecResult,
    initial_passed: bool,
    temperature: float = 0.0,
    max_tokens: int = 2048,
    seed: int | None = None,
    exec_timeout_s: float = 60.0,
) -> RepairOutcome:
    """Iteratively repair one task, recording the verdict after each attempt.

    Stops early on success — a solved task needs no further attempts, and
    continuing would inflate token cost without changing any pass rate.
    """
    outcome = RepairOutcome(task_id=task.task_id, condition=condition)
    outcome.passed_at.append(initial_passed)
    if initial_passed:
        return outcome

    code = initial_code
    failure = summarize_failure(
        initial_result.stdout, initial_result.stderr, timed_out=initial_result.timed_out
    )

    for iteration in range(1, k_max + 1):
        messages = build_retry_messages(task, condition, previous_code=code, failure=failure)
        trace.event(
            "llm_call",
            task_id=task.task_id,
            condition=condition,
            iteration=iteration,
            model=llm.model,
            messages=[m.as_dict() for m in messages],
        )
        try:
            response = llm.complete(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                # Vary the seed per iteration so `resample` genuinely redraws
                # instead of returning the identical greedy sample forever.
                seed=None if seed is None else seed + iteration,
            )
        except LLMError as exc:
            trace.event(
                "error",
                task_id=task.task_id,
                condition=condition,
                iteration=iteration,
                error=str(exc),
            )
            outcome.passed_at.append(False)
            break

        outcome.prompt_tokens += response.prompt_tokens
        outcome.completion_tokens += response.completion_tokens
        outcome.iterations_used = iteration
        trace.event(
            "llm_response",
            task_id=task.task_id,
            condition=condition,
            iteration=iteration,
            content=response.content,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            latency_ms=response.latency_ms,
        )

        program, aux = build_execution(task, response.content)
        result = run_python(program, timeout_s=exec_timeout_s, files=aux)
        passed = result.ok
        outcome.passed_at.append(passed)
        trace.event(
            "verdict",
            task_id=task.task_id,
            condition=condition,
            iteration=iteration,
            passed=passed,
            exit_code=result.exit_code,
            timed_out=result.timed_out,
            stdout_tail=result.stdout[-2000:],
            stderr_tail=result.stderr[-2000:],
        )
        if passed:
            break

        code = _extracted_or_previous(response.content, code)
        failure = summarize_failure(result.stdout, result.stderr, timed_out=result.timed_out)

    return outcome


def _extracted_or_previous(model_output: str, previous: str) -> str:
    """Carry forward the last real code if this attempt emitted none.

    Feeding an empty block back would silently degrade later iterations into
    a resample, quietly contaminating the condition.
    """
    from sia.bench import extract_code

    code = extract_code(model_output)
    return code if code.strip() else previous


def messages_for_baseline(task: BenchTask) -> list[Message]:
    from sia.agent import SYSTEM_PROMPT

    return [Message("system", SYSTEM_PROMPT), Message("user", task.instruction)]

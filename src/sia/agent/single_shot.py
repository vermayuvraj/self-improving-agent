from __future__ import annotations

from sia.bench import BenchTask
from sia.llm import LLMClient, LLMResponse, Message
from sia.trace import TraceWriter

SYSTEM_PROMPT = (
    "You are an expert Python programmer. Solve the given problem with a "
    "single, complete, correct Python solution inside one ```python code "
    "block. Do not explain."
)


def solve_single_shot(
    task: BenchTask,
    llm: LLMClient,
    trace: TraceWriter,
    *,
    sample: int = 0,
    temperature: float = 0.0,
    max_tokens: int = 2048,
    seed: int | None = None,
) -> LLMResponse:
    """One LLM call per task: instruction in, candidate solution out. Fully traced."""
    messages = [Message("system", SYSTEM_PROMPT), Message("user", task.instruction)]
    trace.event(
        "llm_call",
        task_id=task.task_id,
        sample=sample,
        model=llm.model,
        temperature=temperature,
        seed=seed,
        messages=[m.as_dict() for m in messages],
    )
    response = llm.complete(messages, temperature=temperature, max_tokens=max_tokens, seed=seed)
    trace.event(
        "llm_response",
        task_id=task.task_id,
        sample=sample,
        content=response.content,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        latency_ms=response.latency_ms,
    )
    return response

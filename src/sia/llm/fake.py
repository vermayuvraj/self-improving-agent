from __future__ import annotations

from sia.llm.base import LLMError, LLMResponse, Message


class FakeLLM:
    """Scripted client for tests and offline dry-runs.

    Returns queued responses in order; records every call's messages for
    assertions. Raises when the script runs out.
    """

    def __init__(self, responses: list[str], model: str = "fake") -> None:
        self.model = model
        self._responses = list(responses)
        self.calls: list[list[Message]] = []

    def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        stop: list[str] | None = None,
        seed: int | None = None,
    ) -> LLMResponse:
        self.calls.append(list(messages))
        if not self._responses:
            raise LLMError("FakeLLM script exhausted")
        content = self._responses.pop(0)
        return LLMResponse(
            content=content,
            model=self.model,
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(content.split()),
            latency_ms=0.0,
            raw={},
        )

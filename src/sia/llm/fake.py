from __future__ import annotations

import threading

from sia.llm.base import LLMError, LLMResponse, Message


class FakeLLM:
    """Scripted client for tests and offline dry-runs.

    Two modes. A ``list`` returns responses in call order — simple, but only
    meaningful when calls are sequential, so tests using it must pin
    ``workers=1``. A ``dict`` maps a substring of the prompt to a response,
    which stays deterministic under concurrency and is the better choice for
    anything exercising the parallel paths.
    """

    def __init__(self, responses: list[str] | dict[str, str], model: str = "fake") -> None:
        self.model = model
        self._by_prompt = dict(responses) if isinstance(responses, dict) else None
        self._responses = None if self._by_prompt is not None else list(responses)
        self.calls: list[list[Message]] = []
        self._lock = threading.Lock()

    def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        stop: list[str] | None = None,
        seed: int | None = None,
    ) -> LLMResponse:
        with self._lock:
            self.calls.append(list(messages))
            if self._by_prompt is not None:
                prompt = "\n".join(m.content for m in messages)
                match = next((v for k, v in self._by_prompt.items() if k in prompt), None)
                if match is None:
                    raise LLMError(f"FakeLLM has no response matching prompt: {prompt[:200]!r}")
                content = match
            else:
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

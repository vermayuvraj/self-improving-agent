from __future__ import annotations

import time

import httpx

from sia.llm.base import LLMError, LLMResponse, Message

OLLAMA_BASE_URL = "http://localhost:11434/v1"

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class OpenAICompatClient:
    """Chat-completions client for any OpenAI-compatible endpoint.

    Defaults target a local Ollama server (ADR-0006). ``transport`` is
    injectable for tests (httpx.MockTransport).
    """

    def __init__(
        self,
        model: str,
        *,
        base_url: str = OLLAMA_BASE_URL,
        api_key: str | None = None,
        timeout_s: float = 600.0,
        max_retries: int = 3,
        retry_base_delay_s: float = 1.0,
        max_backoff_s: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self._max_retries = max_retries
        self._retry_base_delay_s = retry_base_delay_s
        self._max_backoff_s = max_backoff_s
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(
            base_url=base_url,
            headers=headers,
            timeout=timeout_s,
            transport=transport,
        )

    def check_available(self) -> None:
        """Fail fast if the endpoint does not serve ``self.model``.

        A benchmark run against a missing model would otherwise record one
        error per task and still emit a manifest — a 0% score that looks like
        a result. Runs must never produce scored artifacts from a broken
        configuration.
        """
        try:
            response = self._client.get("/models")
            response.raise_for_status()
            served = {m.get("id") for m in response.json().get("data", [])}
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            raise LLMError(f"cannot reach model endpoint: {exc}") from exc
        if self.model not in served:
            raise LLMError(
                f"model {self.model!r} is not available at the endpoint. "
                f"Served models: {sorted(served) or '(none)'}"
            )

    def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        stop: list[str] | None = None,
        seed: int | None = None,
    ) -> LLMResponse:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [m.as_dict() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stop:
            payload["stop"] = stop
        if seed is not None:
            payload["seed"] = seed

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            if attempt:
                # Exponential backoff, capped: uncapped growth (e.g. base 4s,
                # 8 retries) reaches ~500s per call, which turns a throttled
                # free endpoint into a multi-minute-per-request stall.
                time.sleep(min(self._max_backoff_s, self._retry_base_delay_s * 2 ** (attempt - 1)))
            start = time.perf_counter()
            try:
                response = self._client.post("/chat/completions", json=payload)
            except httpx.TransportError as exc:
                last_error = exc
                continue
            if response.status_code in _RETRYABLE_STATUS:
                last_error = LLMError(f"HTTP {response.status_code}: {response.text[:500]}")
                continue
            if response.status_code != 200:
                raise LLMError(f"HTTP {response.status_code}: {response.text[:500]}")
            latency_ms = (time.perf_counter() - start) * 1000
            return self._parse(response.json(), latency_ms)

        raise LLMError(f"request failed after {self._max_retries + 1} attempts") from last_error

    def _parse(self, body: dict[str, object], latency_ms: float) -> LLMResponse:
        try:
            choices = body["choices"]
            content = choices[0]["message"]["content"]  # type: ignore[index]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"malformed response body: {str(body)[:500]}") from exc
        usage = body.get("usage") or {}
        return LLMResponse(
            content=content or "",
            model=str(body.get("model", self.model)),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),  # type: ignore[union-attr]
            completion_tokens=int(usage.get("completion_tokens", 0)),  # type: ignore[union-attr]
            latency_ms=latency_ms,
            raw=body,  # type: ignore[arg-type]
        )

    def close(self) -> None:
        self._client.close()

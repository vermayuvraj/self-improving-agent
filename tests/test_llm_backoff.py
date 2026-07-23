import time

import httpx

from sia.llm import OpenAICompatClient
from sia.llm.base import Message


def test_backoff_is_capped(monkeypatch):
    """A throttled endpoint must not produce multi-minute per-call stalls:
    exponential backoff is capped so total wait stays bounded."""
    slept: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))

    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] <= 6:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {}})

    client = OpenAICompatClient(
        "m",
        transport=httpx.MockTransport(handler),
        max_retries=8,
        retry_base_delay_s=4.0,
        max_backoff_s=30.0,
    )
    client.complete([Message("user", "hi")])

    # Uncapped, attempt 7 alone would sleep 4*2^6 = 256s; capped it is <= 30s.
    assert max(slept) <= 30.0
    assert sum(slept) < 8 * 30  # bounded total

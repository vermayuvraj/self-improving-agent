import httpx
import pytest

from sia.llm import FakeLLM, LLMClient, LLMError, Message, OpenAICompatClient


def _ok_body(content="hello"):
    return {
        "model": "test-model",
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 5},
    }


def make_client(handler, **kwargs) -> OpenAICompatClient:
    kwargs.setdefault("retry_base_delay_s", 0.0)
    return OpenAICompatClient("test-model", transport=httpx.MockTransport(handler), **kwargs)


def test_complete_success_and_payload():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen.update(json.loads(request.content))
        return httpx.Response(200, json=_ok_body())

    client = make_client(handler)
    resp = client.complete(
        [Message("system", "be brief"), Message("user", "hi")],
        temperature=0.2,
        max_tokens=64,
        seed=7,
        stop=["```"],
    )

    assert resp.content == "hello"
    assert resp.prompt_tokens == 12
    assert resp.completion_tokens == 5
    assert resp.latency_ms >= 0
    assert seen["model"] == "test-model"
    assert seen["messages"][0] == {"role": "system", "content": "be brief"}
    assert seen["temperature"] == 0.2
    assert seen["seed"] == 7
    assert seen["stop"] == ["```"]


def test_retries_then_success():
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(503, text="busy")
        return httpx.Response(200, json=_ok_body("recovered"))

    client = make_client(handler, max_retries=3)
    assert client.complete([Message("user", "hi")]).content == "recovered"
    assert attempts["n"] == 3


def test_exhausted_retries_raise():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="down")

    client = make_client(handler, max_retries=1)
    with pytest.raises(LLMError, match="after 2 attempts"):
        client.complete([Message("user", "hi")])


def test_non_retryable_status_raises_immediately():
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(404, text="no such model")

    client = make_client(handler, max_retries=3)
    with pytest.raises(LLMError, match="404"):
        client.complete([Message("user", "hi")])
    assert attempts["n"] == 1


def test_malformed_body_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    with pytest.raises(LLMError, match="malformed"):
        make_client(handler).complete([Message("user", "hi")])


def test_fake_llm_satisfies_protocol_and_scripts():
    fake = FakeLLM(["a", "b"])
    assert isinstance(fake, LLMClient)
    assert fake.complete([Message("user", "x")]).content == "a"
    assert fake.complete([Message("user", "y")]).content == "b"
    with pytest.raises(LLMError):
        fake.complete([Message("user", "z")])
    assert len(fake.calls) == 3

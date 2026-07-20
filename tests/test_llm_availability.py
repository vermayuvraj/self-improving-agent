import httpx
import pytest

from sia.llm import LLMError, OpenAICompatClient


def _client(handler):
    return OpenAICompatClient(
        "qwen3:8b", transport=httpx.MockTransport(handler), retry_base_delay_s=0.0
    )


def test_available_model_passes():
    def handler(request):
        return httpx.Response(200, json={"data": [{"id": "qwen3:8b"}, {"id": "other"}]})

    _client(handler).check_available()


def test_missing_model_raises_with_served_list():
    def handler(request):
        return httpx.Response(200, json={"data": [{"id": "qwen2.5-coder:7b"}]})

    with pytest.raises(LLMError, match="not available"):
        _client(handler).check_available()


def test_unreachable_endpoint_raises():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    with pytest.raises(LLMError, match="cannot reach"):
        _client(handler).check_available()

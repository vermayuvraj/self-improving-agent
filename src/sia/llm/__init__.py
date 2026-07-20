"""Provider-agnostic LLM access (ADR-0002, ADR-0006).

One protocol, thin adapters. The OpenAI-compatible adapter covers Ollama,
llama.cpp server, vLLM, OpenRouter, and OpenAI itself; an Anthropic adapter
can be added later without touching callers.
"""

from sia.llm.base import LLMClient, LLMError, LLMResponse, Message
from sia.llm.fake import FakeLLM
from sia.llm.openai_compat import OpenAICompatClient

__all__ = ["FakeLLM", "LLMClient", "LLMError", "LLMResponse", "Message", "OpenAICompatClient"]

"""LLM provider abstraction.

The rest of the backend (RAG chain, tool calling, guardrails) must only use
`get_llm_provider()` and the `LLMProvider` interface, never import a vendor SDK
directly. Switching Gemini -> OpenAI is then a single `LLM_PROVIDER` env change.
"""

from app.llm.base import LLMProvider, LLMProviderError
from app.llm.factory import get_llm_provider

__all__ = ["LLMProvider", "LLMProviderError", "get_llm_provider"]

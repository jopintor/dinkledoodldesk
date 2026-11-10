"""Picks the LLM provider named by the `LLM_PROVIDER` setting."""

from app.config import Settings, get_settings
from app.llm.base import LLMProvider, LLMProviderError
from app.llm.fake import FakeProvider
from app.llm.gemini import GeminiProvider
from app.llm.openai import OpenAIProvider

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "fake": FakeProvider,
}


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    try:
        provider_cls = _PROVIDERS[settings.llm_provider]
    except KeyError as exc:
        raise LLMProviderError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}") from exc
    return provider_cls(settings)

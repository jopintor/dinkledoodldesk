"""Provider-neutral interface that every LLM backend implements."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.language_models.chat_models import BaseChatModel


class LLMProviderError(RuntimeError):
    """Raised when a provider is misconfigured (e.g. missing API key or package)."""


class LLMProvider(ABC):
    """Hands out LangChain objects so callers stay vendor-agnostic.

    `chat_model()` returns a LangChain chat model, which already supports
    `.invoke()`, streaming and `.bind_tools()` for function calling.
    `embeddings()` returns a LangChain `Embeddings` used for ChromaDB ingestion and queries.
    """

    name: str

    @abstractmethod
    def chat_model(self) -> "BaseChatModel": ...

    @abstractmethod
    def embeddings(self) -> "Embeddings": ...

    @abstractmethod
    def is_configured(self) -> bool:
        """True when the credentials needed to call the provider are present."""

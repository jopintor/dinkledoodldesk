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
    Callers should go through `app.llm.gateway.LLMGateway`, which adds rate limiting,
    retries and model fallback on top of these objects.
    """

    name: str

    @abstractmethod
    def chat_model(self, *, fallback: bool = False) -> "BaseChatModel":
        """The primary chat model, or the fallback model (separate quota bucket)."""

    @abstractmethod
    def chat_model_name(self, *, fallback: bool = False) -> str: ...

    @property
    def has_fallback(self) -> bool:
        return self.chat_model_name(fallback=True) != self.chat_model_name()

    @abstractmethod
    def embeddings(self) -> "Embeddings": ...

    @abstractmethod
    def embedding_model_name(self) -> str:
        """Model id used in the Chroma collection name, so a model swap means a new collection."""

    @abstractmethod
    def is_configured(self) -> bool:
        """True when the credentials needed to call the provider are present."""

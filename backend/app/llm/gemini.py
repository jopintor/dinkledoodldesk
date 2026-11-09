"""Google Gemini (free tier) provider."""

from app.config import Settings
from app.llm.base import LLMProvider, LLMProviderError


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_configured(self) -> bool:
        return bool(self._settings.gemini_api_key.get_secret_value())

    def _api_key(self) -> str:
        if not self.is_configured():
            raise LLMProviderError("GEMINI_API_KEY is not set")
        return self._settings.gemini_api_key.get_secret_value()

    def chat_model_name(self, *, fallback: bool = False) -> str:
        s = self._settings
        return s.gemini_fallback_model if fallback else s.gemini_chat_model

    def chat_model(self, *, fallback: bool = False):
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = self.chat_model_name(fallback=fallback)
        # Thinking tokens count against max_output_tokens and the free-tier quota; grounded
        # answers from 5 chunks don't need them.
        extra = {}
        if model.startswith("gemini-2.5"):
            extra["thinking_budget"] = 0
        elif model.startswith("gemini-3") and self._settings.gemini_reasoning_effort:
            extra["reasoning_effort"] = self._settings.gemini_reasoning_effort
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=self._api_key(),
            temperature=self._settings.llm_temperature,
            max_output_tokens=self._settings.llm_max_output_tokens,
            timeout=self._settings.llm_request_timeout_s,
            # The gateway owns retries and backoff, so the SDK must not retry on its own.
            max_retries=0,
            **extra,
        )

    def embedding_model_name(self) -> str:
        return self._settings.gemini_embedding_model

    def embeddings(self):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        # Task types default to RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY in embed_documents /
        # embed_query. Truncated vectors are not unit length; the gateway normalises them.
        return GoogleGenerativeAIEmbeddings(
            model=self._settings.gemini_embedding_model,
            google_api_key=self._api_key(),
            output_dimensionality=self._settings.embedding_dim,
        )

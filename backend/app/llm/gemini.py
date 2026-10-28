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

    def chat_model(self):
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=self._settings.gemini_chat_model,
            google_api_key=self._api_key(),
            temperature=self._settings.llm_temperature,
        )

    def embeddings(self):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=self._settings.gemini_embedding_model,
            google_api_key=self._api_key(),
        )

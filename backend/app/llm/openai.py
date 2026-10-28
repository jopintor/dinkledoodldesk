"""OpenAI provider (fallback if the Gemini free tier is not enough).

Requires the optional extra: `pip install -e ".[openai]"`.
"""

from app.config import Settings
from app.llm.base import LLMProvider, LLMProviderError


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_configured(self) -> bool:
        return bool(self._settings.openai_api_key.get_secret_value())

    def _api_key(self) -> str:
        if not self.is_configured():
            raise LLMProviderError("OPENAI_API_KEY is not set")
        return self._settings.openai_api_key.get_secret_value()

    def _import(self):
        try:
            import langchain_openai
        except ImportError as exc:
            raise LLMProviderError(
                'langchain-openai is not installed; run: pip install -e ".[openai]"'
            ) from exc
        return langchain_openai

    def chat_model(self):
        return self._import().ChatOpenAI(
            model=self._settings.openai_chat_model,
            api_key=self._api_key(),
            temperature=self._settings.llm_temperature,
        )

    def embeddings(self):
        return self._import().OpenAIEmbeddings(
            model=self._settings.openai_embedding_model,
            api_key=self._api_key(),
        )

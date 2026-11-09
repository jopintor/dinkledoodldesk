import pytest

from app.config import Settings
from app.llm import LLMProviderError, get_llm_provider


def test_defaults_to_gemini():
    provider = get_llm_provider(Settings(_env_file=None))
    assert provider.name == "gemini"


def test_switch_to_openai_by_setting():
    provider = get_llm_provider(Settings(_env_file=None, llm_provider="openai"))
    assert provider.name == "openai"


def test_missing_key_is_reported_not_raised_until_used():
    provider = get_llm_provider(Settings(_env_file=None, gemini_api_key=""))
    assert provider.is_configured() is False
    with pytest.raises(LLMProviderError):
        provider.chat_model()


def test_gemini_builds_chat_model_with_key():
    provider = get_llm_provider(Settings(_env_file=None, gemini_api_key="test-key"))
    model = provider.chat_model()
    assert model.model.endswith("gemini-3.5-flash")

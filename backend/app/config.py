"""Application settings, loaded from environment variables (and `.env` when present).

Every setting has a safe default so the app and the tests start without a `.env`.
Secrets (API keys, tokens) default to empty and are only required by the code that uses them.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# The repo-root `.env` (backend/app/config.py -> repo root); also accept backend/.env.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: Literal["local", "ci", "demo"] = "local"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    # Data stores
    database_url: str = "postgresql+psycopg://dinkdesk:change-me@localhost:5432/dinkdesk"
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "picklehub-kb"

    # LLM
    llm_provider: Literal["gemini", "openai"] = "gemini"
    llm_temperature: float = 0.2
    gemini_api_key: SecretStr = SecretStr("")
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "models/gemini-embedding-001"
    openai_api_key: SecretStr = SecretStr("")
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Automation / ticketing
    n8n_webhook_base_url: str = "http://localhost:5678/webhook"
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: SecretStr = SecretStr("")
    jira_project_key: str = "DD"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

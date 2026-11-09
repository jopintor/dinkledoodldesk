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
    # http = the Chroma server (compose); persistent = embedded on disk (no Docker needed);
    # ephemeral = in memory (tests and quick experiments).
    chroma_mode: Literal["http", "persistent", "ephemeral"] = "http"
    chroma_persist_dir: str = ".chroma"

    # LLM
    # fake = deterministic offline provider for tests, CI and demos without a key.
    llm_provider: Literal["gemini", "openai", "fake"] = "gemini"
    llm_temperature: float = 0.2
    llm_max_output_tokens: int = 800
    gemini_api_key: SecretStr = SecretStr("")
    gemini_chat_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-3.1-flash-lite"
    # Gemini 3 thinking level. "minimal" keeps grounded answers fast and stops thinking tokens
    # eating the max_output_tokens budget; empty uses the model default.
    gemini_reasoning_effort: str = "minimal"
    gemini_embedding_model: str = "models/gemini-embedding-001"
    embedding_dim: int = 768
    openai_api_key: SecretStr = SecretStr("")
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # LLM gateway limits (docs/architecture.md §5). Set a bit below the published free-tier
    # quotas for your project; the code never hard-codes them.
    llm_rpm_limit: int = 8
    llm_rpd_limit: int = 200
    llm_max_concurrency: int = 2
    llm_queue_max_wait_s: float = 20
    llm_request_timeout_s: float = 25
    embedding_rpm_limit: int = 60

    # RAG (docs/ai-design.md §2-3)
    kb_dir: Path = _REPO_ROOT / "knowledge-base"
    rag_high_threshold: float = 0.70
    rag_medium_threshold: float = 0.50
    # Cosine similarities mapped to 0 and 1 in the confidence score; calibrated in Sprint 3.
    rag_cosine_floor: float = 0.45
    rag_cosine_ceiling: float = 0.85
    response_cache_path: str = ".cache/response_cache.json"
    response_cache_ttl_s: int = 24 * 3600

    # Automation / ticketing
    n8n_webhook_base_url: str = "http://localhost:5678/webhook"
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: SecretStr = SecretStr("")
    jira_project_key: str = "ITH"

    # Auth
    jwt_secret: SecretStr = SecretStr("dev-only-secret-change-me")
    jwt_expires_min: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

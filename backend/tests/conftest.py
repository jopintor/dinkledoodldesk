"""Shared fixtures: offline settings (fake provider, in-memory Chroma) and an indexed KB."""

import uuid

import pytest

from app.config import Settings
from app.llm import LLMGateway, get_llm_provider
from app.rag.ingest import ingest_knowledge_base
from app.rag.retriever import Retriever
from app.rag.store import KBStore, collection_name, make_client


def offline_settings(**overrides) -> Settings:
    values = {
        "llm_provider": "fake",
        "chroma_mode": "ephemeral",
        # The in-memory Chroma is shared within the process, so every test gets its own index.
        "chroma_collection": f"test-{uuid.uuid4().hex[:8]}",
        "embedding_rpm_limit": 100_000,
        "llm_rpm_limit": 100_000,
        "response_cache_path": "",
        "gemini_api_key": "",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def make_store(settings: Settings) -> KBStore:
    provider = get_llm_provider(settings)
    return KBStore(
        make_client(settings), collection_name(settings, provider.embedding_model_name())
    )


@pytest.fixture
def settings() -> Settings:
    return offline_settings()


@pytest.fixture
def store(settings) -> KBStore:
    return make_store(settings)


@pytest.fixture(scope="session")
def indexed_kb():
    """The real /knowledge-base, ingested once with fake embeddings."""
    settings = offline_settings()
    gateway = LLMGateway(get_llm_provider(settings), settings)
    store = make_store(settings)
    report = ingest_knowledge_base(settings.kb_dir, store, gateway.embed_documents)
    assert report.ok, report.summary()
    return settings, store, gateway


@pytest.fixture
def retriever(indexed_kb) -> Retriever:
    settings, store, gateway = indexed_kb
    return Retriever(store, gateway.embed_query, settings)

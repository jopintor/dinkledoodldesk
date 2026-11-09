import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.llm.fake import FakeChatModel
from app.main import app
from app.rag.cache import ResponseCache
from app.rag.retriever import Retriever
from app.rag.service import RagService, get_rag_service


@pytest.fixture
def client(indexed_kb, monkeypatch):
    settings, store, gateway = indexed_kb
    # Fake embeddings give low cosines; lower the thresholds so the generation path runs.
    tuned = settings.model_copy(update={"rag_high_threshold": 0.15, "rag_medium_threshold": 0.1})
    gateway._chat_models[False] = FakeChatModel()
    service = RagService(
        tuned, gateway, Retriever(store, gateway.embed_query, tuned), ResponseCache(None, 60)
    )
    app.dependency_overrides[get_rag_service] = lambda: service
    monkeypatch.setenv("RAG_DEV_AUTH", "true")
    get_settings.cache_clear()
    yield TestClient(app)
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_requires_dev_auth_until_jwt_lands(indexed_kb, monkeypatch):
    monkeypatch.setenv("RAG_DEV_AUTH", "false")
    get_settings.cache_clear()
    try:
        resp = TestClient(app).post("/rag/ask", json={"content": "hello"})
    finally:
        get_settings.cache_clear()
    assert resp.status_code == 401


def test_ask_returns_the_conversation_message_shape(client):
    resp = client.post(
        "/rag/ask",
        headers={"X-Dev-Role": "staff"},
        json={"content": "I typed my DinkPOS PIN wrong a few times and now it's locked"},
    )
    assert resp.status_code == 200
    body = resp.json()
    msg = body["assistant_message"]
    assert body["user_message"] == {
        "content": "I typed my DinkPOS PIN wrong a few times and now it's locked",
        "pii_detected": False,
    }
    assert msg["answer_mode"] == "generated" and msg["action"] == "answer"
    assert msg["citations"][0]["n"] == 1 and msg["citations"][0]["doc_id"] == "KB-007"
    assert msg["content"].endswith("[1]")
    assert body["tool_calls"] == [] and body["conversation_status"] == "active"


def test_ask_validates_input(client):
    assert (
        client.post("/rag/ask", headers={"X-Dev-Role": "staff"}, json={"content": ""}).status_code
        == 422
    )
    assert (
        client.post("/rag/ask", headers={"X-Dev-Role": "root"}, json={"content": "hi"}).status_code
        == 422
    )


def test_kb_search_is_for_agents_and_admins(client):
    query = {"query": "PickleHub-Staff Wi-Fi keeps asking for my password", "as_role": "member"}
    assert client.post("/kb/search", headers={"X-Dev-Role": "staff"}, json=query).status_code == 403
    resp = client.post("/kb/search", headers={"X-Dev-Role": "agent"}, json=query)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results and all(r["doc_id"] != "KB-011" for r in results)
    assert {
        "chunk_id",
        "vector_score",
        "bm25_score",
        "rrf_score",
        "is_current",
        "preview",
    } <= results[0].keys()

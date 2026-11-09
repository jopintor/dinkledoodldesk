"""RAG endpoints with the real JWT/permission dependencies and a fake signed-in user."""

import pytest
from fastapi.testclient import TestClient

from app import permissions
from app.deps import get_current_user, get_db
from app.llm.fake import FakeChatModel
from app.main import app
from app.models import Club, Role, User
from app.rag.cache import ResponseCache
from app.rag.retriever import Retriever
from app.rag.service import RagService, get_rag_service

ASK = "/api/v1/rag/ask"
SEARCH = "/api/v1/kb/search"
ROLE_IDS = {"member": 1, "staff": 2, "agent": 3, "admin": 4, "contractor": 5}


class FakeDB:
    """Just enough of a SQLAlchemy Session for `require()` and `caller_for()`."""

    def __init__(self) -> None:
        self.rows = {(Role, i): Role(id=i, name=name) for name, i in ROLE_IDS.items()}
        self.rows[(Club, 2)] = Club(id=2, code="IMS", name="Imus")

    def get(self, model, ident):
        return self.rows.get((model, ident))


@pytest.fixture
def service(indexed_kb):
    settings, store, gateway = indexed_kb
    # Fake embeddings give low cosines; lower the thresholds so the generation path runs.
    tuned = settings.model_copy(update={"rag_high_threshold": 0.15, "rag_medium_threshold": 0.1})
    gateway._chat_models[False] = FakeChatModel()
    return RagService(
        tuned, gateway, Retriever(store, gateway.embed_query, tuned), ResponseCache(None, 60)
    )


@pytest.fixture
def client_as(service):
    """`client_as("staff")` -> a TestClient signed in as a user with that role."""

    def make(role: str) -> TestClient:
        user = User(
            id=7, email="lia@picklehub.example", full_name="Lia Santos",
            role_id=ROLE_IDS[role], club_id=2, is_active=True,
        )  # fmt: skip
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_db] = FakeDB
        app.dependency_overrides[get_rag_service] = lambda: service
        return TestClient(app)

    yield make
    app.dependency_overrides.clear()


def test_requires_a_token(service):
    app.dependency_overrides[get_rag_service] = lambda: service
    try:
        client = TestClient(app)
        assert client.post(ASK, json={"content": "hello"}).status_code == 401
        assert client.post(SEARCH, json={"query": "vpn"}).status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_ask_returns_the_conversation_message_shape(client_as):
    question = "I typed my DinkPOS PIN wrong a few times and now it's locked"
    resp = client_as("staff").post(ASK, json={"content": question})
    assert resp.status_code == 200
    body = resp.json()
    msg = body["assistant_message"]
    assert body["user_message"] == {"content": question, "pii_detected": False}
    assert msg["answer_mode"] == "generated" and msg["action"] == "answer"
    assert msg["citations"][0]["n"] == 1 and msg["citations"][0]["doc_id"] == "KB-007"
    assert msg["content"].endswith("[1]")
    assert body["tool_calls"] == [] and body["conversation_status"] == "active"


def test_prompt_is_personalised_from_the_signed_in_user(client_as, service, monkeypatch):
    prompts = []
    real_generate = service.gateway.generate

    def spy(messages):
        prompts.append(messages[0].content)
        return real_generate(messages)

    monkeypatch.setattr(service.gateway, "generate", spy)
    client_as("staff").post(ASK, json={"content": "DinkPOS PIN locked after wrong tries"})
    assert "First name: Lia" in prompts[0]
    assert "Role: staff" in prompts[0] and "Branch: Imus" in prompts[0]


def test_role_from_the_token_filters_retrieval(client_as):
    query = {"content": "PickleHub-Staff Wi-Fi keeps asking for my password on my phone"}
    member = client_as("member").post(ASK, json=query).json()["assistant_message"]
    assert all(c["doc_id"] != "KB-011" for c in member["citations"])


def test_unknown_role_gets_the_member_view(client_as, service, monkeypatch):
    roles = []
    real_search = service.retriever.search

    def spy(query, role, **kwargs):
        roles.append(role)
        return real_search(query, role, **kwargs)

    monkeypatch.setattr(service.retriever, "search", spy)
    monkeypatch.setitem(permissions.ROLE_PERMISSIONS, "contractor", {"chat:use"})
    assert client_as("contractor").post(ASK, json={"content": "DinkPOS PIN locked"}).is_success
    assert roles == ["member"]


def test_ask_validates_input(client_as):
    client = client_as("staff")
    assert client.post(ASK, json={"content": ""}).status_code == 422
    assert client.post(ASK, json={"content": "x" * 2001}).status_code == 422


@pytest.mark.parametrize(
    ("role", "status"), [("member", 403), ("staff", 403), ("agent", 200), ("admin", 200)]
)
def test_kb_search_is_for_agents_and_admins(client_as, role, status):
    query = {"query": "PickleHub-Staff Wi-Fi keeps asking for my password", "as_role": "member"}
    resp = client_as(role).post(SEARCH, json=query)
    assert resp.status_code == status
    if status == 200:
        results = resp.json()["results"]
        assert results and all(r["doc_id"] != "KB-011" for r in results)
        assert {"chunk_id", "vector_score", "bm25_score", "rrf_score", "preview"} <= set(results[0])

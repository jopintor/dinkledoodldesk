from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every table)
from app.db import Base
from app.deps import get_current_user, get_db
from app.guardrails.events import GuardrailEventRecord, InMemoryGuardrailLog, get_guardrail_log
from app.models import Role, Ticket, User
from app.routers import admin


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def db(session_factory):
    with session_factory() as session:
        yield session


def make_user(name, role):
    return User(
        email=f"{name}@x.example",
        password_hash="x",  # noqa: S106
        full_name=name,
        role_id=role.id,
    )


@pytest.fixture
def users(db):
    roles = {n: Role(name=n) for n in ("member", "staff", "agent", "admin")}
    db.add_all(roles.values())
    db.flush()
    made = {n: make_user(n, roles[n]) for n in roles}
    db.add_all(made.values())
    db.commit()
    return made


@pytest.fixture
def events():
    """The guardrail log the dashboard reads. Tests record events into it."""
    return InMemoryGuardrailLog()


def event(action, type_, user_id=None, hour=8):
    return GuardrailEventRecord(
        stage="retrieval",
        type=type_,
        action=action,
        detector="confidence",
        user_id=user_id,
        user_role="staff",
        created_at=datetime(2026, 11, 3, hour, 0, tzinfo=UTC),
    )


@pytest.fixture
def client_as(session_factory, users, events):
    app = FastAPI()
    app.include_router(admin.router)
    app.include_router(admin.metrics_router)
    app.dependency_overrides[get_guardrail_log] = lambda: events

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db

    def make(name):
        app.dependency_overrides[get_current_user] = lambda: users[name]
        return TestClient(app)

    return make


def add_ticket(db, users, number, priority="P3", status="open", day=1):
    db.add(
        Ticket(
            ticket_number=number,
            summary=f"Ticket {number}",
            description="d",
            category="other",
            affected_system="other",
            priority=priority,
            status=status,
            requester_id=users["member"].id,
            created_at=datetime(2026, 11, day, 9, 0, tzinfo=UTC),
        )
    )
    db.commit()


@pytest.mark.parametrize("who", ["member", "staff"])
@pytest.mark.parametrize("path", ["/api/v1/escalations", "/api/v1/metrics/summary"])
def test_members_and_staff_are_refused(client_as, who, path):
    assert client_as(who).get(path).status_code == 403


@pytest.mark.parametrize("who", ["agent", "admin"])
@pytest.mark.parametrize("path", ["/api/v1/escalations", "/api/v1/metrics/summary"])
def test_agents_and_admins_may_read(client_as, who, path):
    assert client_as(who).get(path).status_code == 200


def test_escalations_list_urgent_and_escalated_tickets_only(db, users, client_as):
    add_ticket(db, users, "DD-000001", priority="P1", day=1)
    add_ticket(db, users, "DD-000002", priority="P2", day=2)
    add_ticket(db, users, "DD-000003", priority="P3", status="escalated", day=3)
    add_ticket(db, users, "DD-000004", priority="P3", day=4)
    add_ticket(db, users, "DD-000005", priority="P4", day=5)

    body = client_as("agent").get("/api/v1/escalations").json()
    numbers = [i["ticket_number"] for i in body["items"]]
    assert numbers == ["DD-000003", "DD-000002", "DD-000001"]  # newest first
    assert body["next_cursor"] is None
    assert body["items"][0]["reason"] == "escalated"
    assert body["items"][1]["reason"] == "P2 priority"
    assert all(i["source"] == "ticket" for i in body["items"])


def test_escalations_match_the_frontend_shape(db, users, client_as):
    add_ticket(db, users, "DD-000001", priority="P1")
    item = client_as("agent").get("/api/v1/escalations").json()["items"][0]
    for key in (
        "id",
        "conversation_id",
        "ticket_number",
        "reason",
        "urgency",
        "handoff_summary",
        "user",
        "status",
        "created_at",
        "waiting_s",
        "title",
        "priority",
    ):
        assert key in item
    assert item["user"] == {"full_name": "member", "role": "member", "club_code": None}
    assert item["status"] == "queued"
    assert item["urgency"] == "high"
    assert item["waiting_s"] > 0


def test_resolved_tickets_only_show_when_asked(db, users, client_as):
    add_ticket(db, users, "DD-000001", priority="P1", status="resolved")
    client = client_as("agent")
    assert client.get("/api/v1/escalations").json()["items"] == []
    resolved = client.get("/api/v1/escalations?status=resolved").json()["items"]
    assert [i["status"] for i in resolved] == ["resolved"]


def test_escalations_include_escalated_guardrail_events_only(db, users, client_as, events):
    add_ticket(db, users, "DD-000001", priority="P1", day=2)
    events.record(event("escalated", "low_confidence", user_id=users["staff"].id, hour=8))
    events.record(event("blocked", "prompt_injection", hour=9))
    items = client_as("admin").get("/api/v1/escalations").json()["items"]
    assert [i["source"] for i in items] == ["guardrail", "ticket"]
    assert items[0]["reason"] == "low_confidence"
    assert items[0]["user"]["full_name"] == "staff"
    assert all(i["reason"] != "prompt_injection" for i in items)


def test_metrics_are_real_counts_and_the_rest_is_null(db, users, client_as, events):
    add_ticket(db, users, "DD-000001", priority="P1")
    add_ticket(db, users, "DD-000002", priority="P3", status="escalated")
    add_ticket(db, users, "DD-000003", priority="P3")
    events.record(event("escalated", "user_requested_human"))
    events.record(event("blocked", "prompt_injection"))
    events.record(event("blocked", "prompt_injection"))
    events.record(event("allowed_redacted", "pii_redacted"))
    body = client_as("agent").get("/api/v1/metrics/summary").json()
    assert body["tickets_created"] == 3
    assert body["escalations"] == 3  # 2 tickets + 1 event
    assert body["guardrail_blocks"] == 2
    for name in admin.NOT_COMPUTED_YET:
        assert body[name] is None


def test_empty_database_gives_zeros_not_errors(client_as):
    metrics = client_as("admin").get("/api/v1/metrics/summary").json()
    assert metrics["tickets_created"] == 0
    assert metrics["escalations"] == 0
    assert metrics["guardrail_blocks"] == 0
    assert client_as("admin").get("/api/v1/escalations").json()["items"] == []


def test_the_dashboard_endpoints_are_read_only(client_as):
    client = client_as("admin")
    assert client.post("/api/v1/escalations").status_code == 405
    assert client.put("/api/v1/metrics/summary").status_code == 405

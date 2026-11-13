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
def events(monkeypatch):
    """The guardrail events the dashboard sees. Tests append to this list."""
    items = []
    monkeypatch.setattr(admin, "_raw_guardrail_events", lambda: list(items))
    return items


@pytest.fixture
def client_as(session_factory, users, events):
    app = FastAPI()
    app.include_router(admin.router)

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


def test_escalations_include_escalation_events_from_the_guardrail_log(db, users, client_as, events):
    add_ticket(db, users, "DD-000001", priority="P1", day=2)
    events += [
        {
            "id": 1,
            "kind": "human_escalation",
            "detail": "asked for a person",
            "created_at": "2026-11-03T08:00:00+00:00",
        },
        {
            "id": 2,
            "kind": "injection_blocked",
            "detail": "attack",
            "created_at": "2026-11-03T09:00:00+00:00",
        },
    ]
    items = client_as("admin").get("/api/v1/escalations").json()["items"]
    assert [i["source"] for i in items] == ["guardrail", "ticket"]
    assert items[0]["reason"] == "human_escalation"
    assert items[0]["summary"] == "asked for a person"
    assert all(i["reason"] != "injection_blocked" for i in items)


def test_metrics_are_real_counts_and_the_rest_is_null(db, users, client_as, events):
    add_ticket(db, users, "DD-000001", priority="P1")
    add_ticket(db, users, "DD-000002", priority="P3", status="escalated")
    add_ticket(db, users, "DD-000003", priority="P3")
    events += [
        {"id": 1, "kind": "human_escalation", "created_at": "2026-11-03T08:00:00+00:00"},
        {"id": 2, "kind": "injection_blocked", "created_at": "2026-11-03T09:00:00+00:00"},
        {"id": 3, "kind": "injection_blocked", "created_at": "2026-11-03T09:30:00+00:00"},
        {"id": 4, "kind": "pii_redacted", "created_at": "2026-11-03T10:00:00+00:00"},
    ]
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


def test_events_can_be_objects_too(client_as, events):
    class Event:
        id = 7
        event_type = "human_handoff"
        message = "wants a person"
        timestamp = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)

    events.append(Event())
    items = client_as("agent").get("/api/v1/escalations").json()["items"]
    assert items[0]["reason"] == "human_handoff"
    assert items[0]["created_at"].startswith("2026-11-03T08:00")


def test_the_dashboard_endpoints_are_read_only(client_as):
    client = client_as("admin")
    assert client.post("/api/v1/escalations").status_code == 405
    assert client.put("/api/v1/metrics/summary").status_code == 405

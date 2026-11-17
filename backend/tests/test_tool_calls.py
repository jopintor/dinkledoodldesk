import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every table)
from app.db import Base
from app.deps import get_current_user, get_db
from app.models import Role, Ticket, ToolCall, User
from app.routers import tickets, tool_calls
from app.tools.executor import ToolRefused, propose

GOOD = {
    "summary": "CourtBook shows Court 3 double-booked at 6 PM (Imus)",
    "description": "Two members booked Court 3 for 6 PM.",
    "category": "member_app_booking",
    "affected_system": "courtbook",
}


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
    roles = {name: Role(name=name) for name in ("member", "agent")}
    db.add_all(roles.values())
    db.flush()
    made = {
        "alice": make_user("alice", roles["member"]),
        "bob": make_user("bob", roles["member"]),
        "carol": make_user("carol", roles["agent"]),
    }
    db.add_all(made.values())
    db.commit()
    return made


@pytest.fixture
def client_as(session_factory, users):
    app = FastAPI()
    app.include_router(tool_calls.router)
    app.include_router(tickets.router)

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db

    def make(name):
        app.dependency_overrides[get_current_user] = lambda: users[name]
        return TestClient(app)

    return make


def test_propose_confirm_creates_a_ticket_that_the_list_returns(db, users, client_as):
    proposed = propose(db, users["alice"], "create_ticket", GOOD)
    assert proposed["status"] == "awaiting_confirmation"
    assert proposed["tool_name"] == "create_ticket"
    assert proposed["confirm_text"] == "Create this ticket for the IT Service Desk?"
    assert proposed["arguments"]["category"] == "member_app_booking"
    assert set(proposed) == {"id", "tool_name", "status", "arguments", "confirm_text"}

    client = client_as("alice")
    resp = client.post(f"/api/v1/tool-calls/{proposed['id']}/confirm")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "succeeded"
    assert body["message"] == "Ticket DD-000001 created."
    assert body["result"] == {
        "ticket_number": "DD-000001",
        "jira_key": None,
        "jira_sync_status": "pending",
    }

    items = client.get("/api/v1/tickets").json()
    assert items["next_cursor"] is None
    assert [t["ticket_number"] for t in items["items"]] == ["DD-000001"]
    assert items["items"][0]["status"] == "open"
    assert items["items"][0]["priority"] == "P3"


def test_ticket_numbers_count_up(db, users, client_as):
    client = client_as("alice")
    for _ in range(2):
        tc = propose(db, users["alice"], "create_ticket", GOOD)
        client.post(f"/api/v1/tool-calls/{tc['id']}/confirm")
    numbers = [t["ticket_number"] for t in client.get("/api/v1/tickets").json()["items"]]
    assert numbers == ["DD-000002", "DD-000001"]


def test_another_users_tool_call_is_a_404(db, users, client_as):
    tc = propose(db, users["alice"], "create_ticket", GOOD)
    bob = client_as("bob")
    assert bob.post(f"/api/v1/tool-calls/{tc['id']}/confirm").status_code == 404
    assert bob.post(f"/api/v1/tool-calls/{tc['id']}/cancel").status_code == 404
    assert bob.post("/api/v1/tool-calls/9999/confirm").status_code == 404
    assert db.scalars(select(Ticket)).all() == []


def test_cancel_works_and_blocks_confirm(db, users, client_as):
    tc = propose(db, users["alice"], "create_ticket", GOOD)
    client = client_as("alice")
    resp = client.post(f"/api/v1/tool-calls/{tc['id']}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert resp.json()["message"] == "Okay, I didn't change anything."
    assert client.post(f"/api/v1/tool-calls/{tc['id']}/confirm").status_code == 409
    assert client.get("/api/v1/tickets").json()["items"] == []


def test_confirm_twice_is_refused(db, users, client_as):
    tc = propose(db, users["alice"], "create_ticket", GOOD)
    client = client_as("alice")
    assert client.post(f"/api/v1/tool-calls/{tc['id']}/confirm").status_code == 200
    assert client.post(f"/api/v1/tool-calls/{tc['id']}/confirm").status_code == 409
    assert len(client.get("/api/v1/tickets").json()["items"]) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"category": "security"},
        {"category": "pos_payments"},
        {"category": "accounts_access"},
        {"priority": "P1"},
        {"priority": "P2"},
    ],
)
def test_member_with_a_disallowed_request_is_refused(db, users, changes):
    with pytest.raises(ToolRefused):
        propose(db, users["alice"], "create_ticket", {**GOOD, **changes})
    assert db.scalars(select(ToolCall)).all() == []


@pytest.mark.parametrize("category", ["member_app_booking", "network", "other"])
def test_member_may_use_the_allowed_categories(db, users, category):
    out = propose(
        db,
        users["alice"],
        "create_ticket",
        {**GOOD, "category": category, "priority": "P3"},
    )
    assert out["status"] == "awaiting_confirmation"


def test_agent_is_not_limited_by_the_member_rules(db, users):
    out = propose(
        db,
        users["carol"],
        "create_ticket",
        {**GOOD, "category": "security", "priority": "P1"},
    )
    assert out["arguments"]["priority"] == "P1"


def test_invalid_arguments_and_unknown_tools_are_refused(db, users):
    with pytest.raises(ToolRefused):
        propose(db, users["alice"], "create_ticket", {**GOOD, "category": "nonsense"})
    with pytest.raises(ToolRefused):
        propose(db, users["alice"], "launch_rocket", {})


def test_members_see_their_own_tickets_and_agents_see_all(db, users, client_as):
    for name in ("alice", "bob"):
        tc = propose(db, users[name], "create_ticket", GOOD)
        client_as(name).post(f"/api/v1/tool-calls/{tc['id']}/confirm")
    assert len(client_as("alice").get("/api/v1/tickets").json()["items"]) == 1
    assert len(client_as("bob").get("/api/v1/tickets").json()["items"]) == 1
    assert len(client_as("carol").get("/api/v1/tickets").json()["items"]) == 2

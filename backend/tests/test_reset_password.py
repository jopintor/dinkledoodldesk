"""reset_password: who may ask for it (propose step).

The confirm step (send a code through the mock directory) and /verify are not built
yet; until then confirm answers 409 and nothing is changed.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every table)
from app.db import Base
from app.deps import get_current_user, get_db
from app.models import Role, ToolCall, User
from app.routers import tool_calls
from app.tools.executor import ToolRefused, propose

ARGS = {"system": "staffid", "reason": "forgot_password"}


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


@pytest.fixture
def users(db):
    roles = {n: Role(name=n) for n in ("member", "staff", "agent", "admin")}
    db.add_all(roles.values())
    db.flush()

    def make(name, role, username=None):
        return User(
            email=f"{name}@x.example",
            password_hash="x",  # noqa: S106
            full_name=name,
            role_id=roles[role].id,
            directory_username=username,
        )

    made = {
        "staff": make("staff", "staff", "demo.staff"),
        "staff_no_dir": make("staff_no_dir", "staff"),
        "member": make("member", "member"),
        "agent": make("agent", "agent", "demo.agent"),
        "admin": make("admin", "admin", "demo.admin"),
    }
    db.add_all(made.values())
    db.commit()
    return made


def test_staff_with_a_directory_account_gets_a_confirmation(db, users):
    out = propose(db, users["staff"], "reset_password", ARGS)
    assert out["status"] == "awaiting_confirmation"
    assert out["tool_name"] == "reset_password"
    assert "verification code" in out["confirm_text"]


@pytest.mark.parametrize("who", ["agent", "admin"])
def test_privileged_accounts_are_refused(db, users, who):
    with pytest.raises(ToolRefused, match="privileged"):
        propose(db, users[who], "reset_password", ARGS)
    assert db.scalars(select(ToolCall)).all() == []


def test_members_are_refused(db, users):
    with pytest.raises(ToolRefused, match="only available to staff"):
        propose(db, users["member"], "reset_password", ARGS)


def test_staff_without_a_directory_account_is_refused(db, users):
    with pytest.raises(ToolRefused, match="directory account"):
        propose(db, users["staff_no_dir"], "reset_password", ARGS)


def test_other_systems_are_refused(db, users):
    with pytest.raises(ToolRefused):
        propose(db, users["staff"], "reset_password", {**ARGS, "system": "hubmail"})


def test_confirm_does_not_run_a_reset_yet(db, users, session_factory):
    tc = propose(db, users["staff"], "reset_password", ARGS)
    app = FastAPI()
    app.include_router(tool_calls.router)

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: users["staff"]
    res = TestClient(app).post(f"/api/v1/tool-calls/{tc['id']}/confirm")
    assert res.status_code == 409
    assert db.get(ToolCall, tc["id"]).status == "awaiting_confirmation"

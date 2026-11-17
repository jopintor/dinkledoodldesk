"""reset_password: who may ask (propose), then confirm -> code -> verify -> reset."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every table)
from app.db import Base
from app.deps import get_current_user, get_db
from app.errors import register_error_handlers
from app.models import AuditLog, Role, ToolCall, User
from app.routers import tool_calls
from app.tools.directory import DirectoryError, get_directory
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
            employee_no="PH-10021" if username else None,
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


class FakeDirectory:
    """Stands in for mock-directory. The right code is 123456."""

    def __init__(self, privileged=False, send_error=None, attempts=3):
        self.privileged = privileged
        self.send_error = send_error
        self.attempts = attempts
        self.calls = []

    def send_otp(self, username, employee_no):
        self.calls.append(("send_otp", username, employee_no))
        if self.send_error:
            raise self.send_error
        return {"challenge_id": "ch-1", "sent_to": "+63 9** *** **21", "attempts_left": 3}

    def verify_otp(self, username, challenge_id, code):
        self.calls.append(("verify_otp", username, challenge_id))
        if code != "123456":
            self.attempts -= 1
            if self.attempts == 0:
                raise DirectoryError(423, "OTP_LOCKED", "locked")
            raise DirectoryError(400, "OTP_INVALID", "bad", {"attempts_left": self.attempts})
        return {"verified": True, "privileged": self.privileged, "reset_token": "tok-secret"}

    def reset(self, username, reset_token):
        self.calls.append(("reset", username, reset_token))
        return {
            "status": "reset",
            "sent_to": "d***@mail.example",
            "temp_password_expires_at": "2026-11-18T10:00:00Z",
        }


@pytest.fixture
def client_for(session_factory, users):
    def make(who, directory):
        app = FastAPI()
        app.include_router(tool_calls.router)
        register_error_handlers(app)

        def override_db():
            with session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: users[who]
        app.dependency_overrides[get_directory] = lambda: directory
        return TestClient(app)

    return make


def start(db, users, client_for, directory):
    tc = propose(db, users["staff"], "reset_password", ARGS)
    client = client_for("staff", directory)
    return tc["id"], client, client.post(f"/api/v1/tool-calls/{tc['id']}/confirm")


def test_confirm_sends_a_code_and_never_returns_the_challenge(db, users, client_for):
    directory = FakeDirectory()
    _, _, res = start(db, users, client_for, directory)
    body = res.json()
    assert res.status_code == 200
    assert body["status"] == "awaiting_verification"
    assert "+63 9** *** **21" in body["message"]
    assert body["result"] == {"sent_to": "+63 9** *** **21"}  # no _challenge_id
    assert directory.calls == [("send_otp", "demo.staff", "PH-10021")]


def test_right_code_resets_and_never_shows_the_token(db, users, client_for):
    directory = FakeDirectory()
    tc_id, client, _ = start(db, users, client_for, directory)
    res = client.post(f"/api/v1/tool-calls/{tc_id}/verify", json={"otp": "123456"})
    body = res.json()
    assert res.status_code == 200
    assert body["status"] == "succeeded"
    assert "d***@mail.example" in body["message"]
    assert "tok-secret" not in res.text
    assert ("reset", "demo.staff", "tok-secret") in directory.calls
    stored = db.get(ToolCall, tc_id)
    db.refresh(stored)
    assert "tok-secret" not in str(stored.result)
    actions = [a.action for a in db.query(AuditLog).all()]
    assert actions == ["password_reset_code_sent", "password_reset_succeeded"]


def test_wrong_code_says_attempts_left_then_locks(db, users, client_for):
    tc_id, client, _ = start(db, users, client_for, FakeDirectory())
    first = client.post(f"/api/v1/tool-calls/{tc_id}/verify", json={"otp": "000000"})
    assert first.status_code == 400
    assert first.json()["error"]["message"] == "That code didn't match. 2 attempts left."
    client.post(f"/api/v1/tool-calls/{tc_id}/verify", json={"otp": "000000"})
    third = client.post(f"/api/v1/tool-calls/{tc_id}/verify", json={"otp": "000000"})
    assert third.status_code == 200
    assert third.json()["status"] == "failed"
    assert "IT was notified" in third.json()["message"]
    again = client.post(f"/api/v1/tool-calls/{tc_id}/verify", json={"otp": "123456"})
    assert again.status_code == 409


def test_code_must_be_six_digits(db, users, client_for):
    tc_id, client, _ = start(db, users, client_for, FakeDirectory())
    assert (
        client.post(f"/api/v1/tool-calls/{tc_id}/verify", json={"otp": "12ab"}).status_code == 422
    )


def test_verify_before_confirm_is_refused(db, users, client_for):
    tc = propose(db, users["staff"], "reset_password", ARGS)
    client = client_for("staff", FakeDirectory())
    res = client.post(f"/api/v1/tool-calls/{tc['id']}/verify", json={"otp": "123456"})
    assert res.status_code == 409


def test_privileged_account_is_stopped_after_the_code(db, users, client_for):
    directory = FakeDirectory(privileged=True)
    tc_id, client, _ = start(db, users, client_for, directory)
    body = client.post(f"/api/v1/tool-calls/{tc_id}/verify", json={"otp": "123456"}).json()
    assert body["status"] == "failed"
    assert not any(call[0] == "reset" for call in directory.calls)


def test_directory_down_keeps_the_card_so_the_user_can_retry(db, users, client_for):
    down = FakeDirectory(send_error=DirectoryError(503, "UNREACHABLE", "down"))
    tc_id, _, res = start(db, users, client_for, down)
    assert res.status_code == 503
    assert db.get(ToolCall, tc_id).status == "awaiting_confirmation"
    retry = client_for("staff", FakeDirectory()).post(f"/api/v1/tool-calls/{tc_id}/confirm")
    assert retry.json()["status"] == "awaiting_verification"


def test_no_mobile_on_file_fails_with_a_clear_message(db, users, client_for):
    error = DirectoryError(409, "NO_MOBILE_ON_FILE", "no mobile")
    _, _, res = start(db, users, client_for, FakeDirectory(send_error=error))
    assert res.json()["status"] == "failed"
    assert "no mobile number" in res.json()["message"]


def test_someone_elses_reset_is_a_404(db, users, client_for):
    tc = propose(db, users["staff"], "reset_password", ARGS)
    other = client_for("member", FakeDirectory())
    assert other.post(f"/api/v1/tool-calls/{tc['id']}/confirm").status_code == 404

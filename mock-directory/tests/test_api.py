import re
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.mailer import DeliveryError
from app.main import create_app
from app.settings import load_settings

KEY = {"X-API-Key": "test-key"}


class FakeMailer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self.fail = False

    def send(self, to: str, subject: str, body: str) -> None:
        if self.fail:
            raise DeliveryError("smtp down")
        self.sent.append((to, subject, body))

    def last_code(self) -> str:
        return re.search(r"code: (\d{6})", self.sent[-1][2]).group(1)


class Clock:
    def __init__(self) -> None:
        self.now = 1_800_000_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def env():
    mailer, clock = FakeMailer(), Clock()
    settings = replace(load_settings(), api_key="test-key")
    client = TestClient(create_app(settings, mailer, clock))
    return client, mailer, clock


def send_code(client, username="demo.staff", employee_no="PH-10021"):
    return client.post(f"/accounts/{username}/otp", json={"employee_no": employee_no}, headers=KEY)


def test_health_needs_no_key(env):
    client, _, _ = env
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["accounts"] >= 4


def test_api_key_required(env):
    client, _, _ = env
    assert client.get("/accounts/demo.staff").status_code == 401
    r = client.get("/accounts/demo.staff", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_lookup_masks_contact_details(env):
    client, _, _ = env
    r = client.get("/accounts/Demo.Staff", headers=KEY)
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "demo.staff"
    assert body["privileged"] is False
    assert body["mobile_masked"].endswith("0021")
    assert "917" not in body["mobile_masked"]
    assert body["recovery_email_masked"] == "d***@mail.example"
    assert "employee_no" not in body


def test_lookup_unknown_account(env):
    client, _, _ = env
    r = client.get("/accounts/nobody.here", headers=KEY)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


def test_full_reset_flow(env):
    client, mailer, _ = env
    r = send_code(client)
    assert r.status_code == 201
    body = r.json()
    assert body["attempts_left"] == 3
    assert "code" not in body
    to, _, sms = mailer.sent[-1]
    assert to == "639170000021@sms.picklehub.example"

    r = client.post(
        "/accounts/demo.staff/otp/verify",
        json={"challenge_id": body["challenge_id"], "code": mailer.last_code()},
        headers=KEY,
    )
    assert r.status_code == 200
    verified = r.json()
    assert verified["verified"] is True
    assert verified["privileged"] is False

    r = client.post(
        "/accounts/demo.staff/reset", json={"reset_token": verified["reset_token"]}, headers=KEY
    )
    assert r.status_code == 200
    assert r.json()["must_change_password"] is True
    assert "password" not in {k for k in r.json() if k != "must_change_password"}
    to, subject, mail = mailer.sent[-1]
    assert to == "demo.staff.personal@mail.example"
    assert "Temporary password:" in mail

    # The token is single use.
    r = client.post(
        "/accounts/demo.staff/reset", json={"reset_token": verified["reset_token"]}, headers=KEY
    )
    assert r.json()["error"]["code"] == "RESET_TOKEN_INVALID"


def test_wrong_employee_number(env):
    client, mailer, _ = env
    r = send_code(client, employee_no="PH-99999")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VERIFICATION_FAILED"
    assert mailer.sent == []


def test_three_wrong_codes_lock_the_challenge_and_flag_account(env):
    client, mailer, _ = env
    cid = send_code(client).json()["challenge_id"]
    wrong = "000000" if mailer.last_code() != "000000" else "111111"
    codes = []
    for _ in range(3):
        r = client.post(
            "/accounts/demo.staff/otp/verify",
            json={"challenge_id": cid, "code": wrong},
            headers=KEY,
        )
        codes.append((r.status_code, r.json()["error"]["code"], r.json()["error"]["attempts_left"]))
    assert codes == [(400, "OTP_INVALID", 2), (400, "OTP_INVALID", 1), (423, "OTP_LOCKED", 0)]
    # Even the right code no longer works.
    r = client.post(
        "/accounts/demo.staff/otp/verify",
        json={"challenge_id": cid, "code": mailer.last_code()},
        headers=KEY,
    )
    assert r.json()["error"]["code"] == "OTP_LOCKED"
    assert client.get("/accounts/demo.staff", headers=KEY).json()["flagged"] is True


def test_code_expires_after_ten_minutes(env):
    client, mailer, clock = env
    cid = send_code(client).json()["challenge_id"]
    clock.now += 601
    r = client.post(
        "/accounts/demo.staff/otp/verify",
        json={"challenge_id": cid, "code": mailer.last_code()},
        headers=KEY,
    )
    assert r.json()["error"]["code"] == "OTP_EXPIRED"


def test_send_rate_limit(env):
    client, _, clock = env
    for _ in range(3):
        assert send_code(client).status_code == 201
    r = send_code(client)
    assert r.status_code == 429
    assert r.json()["error"]["retry_after_s"] > 0
    clock.now += 601
    assert send_code(client).status_code == 201


def test_privileged_account_reported(env):
    client, mailer, _ = env
    cid = send_code(client, "demo.agent", "PH-10031").json()["challenge_id"]
    r = client.post(
        "/accounts/demo.agent/otp/verify",
        json={"challenge_id": cid, "code": mailer.last_code()},
        headers=KEY,
    )
    assert r.json()["privileged"] is True


def test_reset_token_cannot_be_used_for_another_account(env):
    client, mailer, _ = env
    cid = send_code(client).json()["challenge_id"]
    token = client.post(
        "/accounts/demo.staff/otp/verify",
        json={"challenge_id": cid, "code": mailer.last_code()},
        headers=KEY,
    ).json()["reset_token"]
    r = client.post("/accounts/demo.agent/reset", json={"reset_token": token}, headers=KEY)
    assert r.json()["error"]["code"] == "RESET_TOKEN_INVALID"


def test_delivery_failure_returns_503_and_keeps_token(env):
    client, mailer, _ = env
    cid = send_code(client).json()["challenge_id"]
    token = client.post(
        "/accounts/demo.staff/otp/verify",
        json={"challenge_id": cid, "code": mailer.last_code()},
        headers=KEY,
    ).json()["reset_token"]
    mailer.fail = True
    r = client.post("/accounts/demo.staff/reset", json={"reset_token": token}, headers=KEY)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "DELIVERY_FAILED"
    mailer.fail = False
    r = client.post("/accounts/demo.staff/reset", json={"reset_token": token}, headers=KEY)
    assert r.status_code == 200


def test_no_mobile_on_file(env):
    client, _, _ = env
    r = send_code(client, "nomobile.staff", "PH-10199")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "NO_MOBILE_ON_FILE"


def test_reset_unlocks_and_unlock_endpoint(env):
    client, _, _ = env
    assert client.get("/accounts/maria.santos", headers=KEY).json()["locked"] is True
    r = client.post("/accounts/maria.santos/unlock", headers=KEY)
    assert r.json()["locked"] is False


def test_reload_restores_seed(env):
    client, _, _ = env
    client.post("/accounts/maria.santos/unlock", headers=KEY)
    client.post("/admin/reload", headers=KEY)
    assert client.get("/accounts/maria.santos", headers=KEY).json()["locked"] is True

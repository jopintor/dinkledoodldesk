"""In-memory StaffID directory: accounts from the seed file, one-time codes and reset tokens.

State lives only in memory, so restarting the container restores the seed (handy between demo
rehearsals; `POST /admin/reload` does the same without a restart). Codes and tokens are stored
as SHA-256 hashes and are never returned by the API or logged.
"""

import hashlib
import json
import secrets
import string
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.mailer import Mailer, sms_address
from app.settings import Settings


class DirectoryError(Exception):
    def __init__(self, status: int, code: str, message: str, **extra: object) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.extra = extra


@dataclass
class Account:
    username: str
    display_name: str
    employee_no: str
    mobile: str
    recovery_email: str
    privileged: bool = False
    locked: bool = False
    must_change_password: bool = False
    flagged: bool = False  # set after too many wrong codes (docs/architecture.md §6)
    temp_password_expires_at: float | None = None


@dataclass
class Challenge:
    challenge_id: str
    username: str
    code_hash: str
    expires_at: float
    attempts_left: int
    used: bool = False


@dataclass
class ResetToken:
    username: str
    expires_at: float


@dataclass
class _State:
    accounts: dict[str, Account] = field(default_factory=dict)
    challenges: dict[str, Challenge] = field(default_factory=dict)
    reset_tokens: dict[str, ResetToken] = field(default_factory=dict)  # sha256(token) -> token
    sends: dict[str, list[float]] = field(default_factory=dict)  # username -> send times


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:1]}***@{domain}" if domain else "***"


def mask_mobile(mobile: str) -> str:
    digits = "".join(ch for ch in mobile if ch.isdigit())
    return f"+{'*' * max(len(digits) - 4, 0)}{digits[-4:]}" if digits else ""


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def load_seed(path: Path) -> dict[str, Account]:
    data = json.loads(path.read_text(encoding="utf-8"))
    accounts = {}
    for raw in data["accounts"]:
        acc = Account(**raw)
        accounts[acc.username.lower()] = acc
    return accounts


def _temp_password() -> str:
    # 12 chars with upper, lower, digit and symbol so it meets the KB-001 password rules.
    alphabet = string.ascii_letters + string.digits
    core = "".join(secrets.choice(alphabet) for _ in range(8))
    return (
        secrets.choice(string.ascii_uppercase)
        + core
        + secrets.choice(string.digits)
        + secrets.choice("!#$%&*?")
        + secrets.choice(string.ascii_lowercase)
    )


class Directory:
    def __init__(
        self, settings: Settings, mailer: Mailer, clock: Callable[[], float] = time.time
    ) -> None:
        self.settings = settings
        self.mailer = mailer
        self.clock = clock
        self._lock = threading.Lock()
        self._state = _State()
        self.reload()

    # --- admin ---------------------------------------------------------------
    def reload(self) -> int:
        with self._lock:
            self._state = _State(accounts=load_seed(self.settings.seed_file))
            return len(self._state.accounts)

    def count(self) -> int:
        return len(self._state.accounts)

    # --- lookups -------------------------------------------------------------
    def _get(self, username: str) -> Account:
        acc = self._state.accounts.get(username.strip().lower())
        if acc is None:
            raise DirectoryError(404, "ACCOUNT_NOT_FOUND", "No StaffID account with that username.")
        return acc

    def public_view(self, acc: Account) -> dict:
        return {
            "username": acc.username,
            "display_name": acc.display_name,
            "privileged": acc.privileged,
            "locked": acc.locked,
            "flagged": acc.flagged,
            "must_change_password": acc.must_change_password,
            "has_mobile": bool(acc.mobile),
            "mobile_masked": mask_mobile(acc.mobile),
            "recovery_email_masked": mask_email(acc.recovery_email),
        }

    def lookup(self, username: str) -> dict:
        with self._lock:
            return self.public_view(self._get(username))

    # --- one-time codes ------------------------------------------------------
    def send_otp(self, username: str, employee_no: str) -> dict:
        s = self.settings
        with self._lock:
            now = self.clock()
            acc = self._get(username)
            if not secrets.compare_digest(
                acc.employee_no.strip().upper(), employee_no.strip().upper()
            ):
                raise DirectoryError(
                    400, "VERIFICATION_FAILED", "The employee number does not match this account."
                )
            if not acc.mobile:
                raise DirectoryError(
                    409, "NO_MOBILE_ON_FILE", "No mobile number on file; contact the Service Desk."
                )
            recent = [
                t for t in self._state.sends.get(acc.username, []) if now - t < s.otp_send_window_s
            ]
            if len(recent) >= s.otp_sends_per_window:
                retry = int(s.otp_send_window_s - (now - recent[0])) + 1
                raise DirectoryError(
                    429,
                    "OTP_RATE_LIMITED",
                    "Too many codes requested. Try again later.",
                    retry_after_s=retry,
                )
            code = f"{secrets.randbelow(1_000_000):06d}"
            challenge = Challenge(
                challenge_id=secrets.token_urlsafe(12),
                username=acc.username,
                code_hash=_hash(code),
                expires_at=now + s.otp_ttl_s,
                attempts_left=s.otp_max_attempts,
            )
            minutes = max(s.otp_ttl_s // 60, 1)
            # Send before storing: if delivery fails, no challenge exists and no send is counted.
            self.mailer.send(
                sms_address(acc.mobile),
                f"SMS to {mask_mobile(acc.mobile)}",
                f"PickleHub StaffID code: {code}\n"
                f"Valid for {minutes} minutes. Enter it only in DinkDesk's code box. "
                "IT staff will never ask you for it.",
            )
            self._state.challenges[challenge.challenge_id] = challenge
            self._state.sends[acc.username] = [*recent, now]
            return {
                "challenge_id": challenge.challenge_id,
                "expires_at": _iso(challenge.expires_at),
                "sent_to": mask_mobile(acc.mobile),
                "attempts_left": challenge.attempts_left,
            }

    def verify_otp(self, username: str, challenge_id: str, code: str) -> dict:
        s = self.settings
        with self._lock:
            now = self.clock()
            acc = self._get(username)
            ch = self._state.challenges.get(challenge_id)
            if ch is None or ch.username != acc.username:
                raise DirectoryError(
                    404, "CHALLENGE_NOT_FOUND", "Unknown or finished code request."
                )
            if ch.used:
                raise DirectoryError(409, "OTP_ALREADY_USED", "This code was already used.")
            if now > ch.expires_at:
                raise DirectoryError(400, "OTP_EXPIRED", "The code has expired. Request a new one.")
            if ch.attempts_left <= 0:
                raise DirectoryError(423, "OTP_LOCKED", "Too many wrong codes.", attempts_left=0)
            if not secrets.compare_digest(ch.code_hash, _hash(code.strip())):
                ch.attempts_left -= 1
                if ch.attempts_left <= 0:
                    acc.flagged = True
                    raise DirectoryError(
                        423,
                        "OTP_LOCKED",
                        "Too many wrong codes. Contact the Service Desk.",
                        attempts_left=0,
                    )
                raise DirectoryError(
                    400,
                    "OTP_INVALID",
                    f"That code didn't match. {ch.attempts_left} attempts left.",
                    attempts_left=ch.attempts_left,
                )
            ch.used = True
            token = secrets.token_urlsafe(24)
            expires_at = now + s.reset_token_ttl_s
            self._state.reset_tokens[_hash(token)] = ResetToken(acc.username, expires_at)
            return {
                "verified": True,
                "privileged": acc.privileged,
                "reset_token": token,
                "reset_token_expires_at": _iso(expires_at),
            }

    # --- reset / unlock ------------------------------------------------------
    def reset_password(self, username: str, reset_token: str) -> dict:
        s = self.settings
        with self._lock:
            now = self.clock()
            acc = self._get(username)
            key = _hash(reset_token)
            tok = self._state.reset_tokens.get(key)
            if tok is None or tok.username != acc.username or now > tok.expires_at:
                raise DirectoryError(
                    400, "RESET_TOKEN_INVALID", "The reset token is invalid or has expired."
                )
            temp = _temp_password()
            expires_at = now + s.temp_password_ttl_h * 3600
            # Send before consuming the token so a mail outage can be retried.
            self.mailer.send(
                acc.recovery_email,
                "Your temporary StaffID password",
                f"Hi {acc.display_name},\n\n"
                f"Your StaffID password was reset. Temporary password: {temp}\n"
                f"It is valid for {s.temp_password_ttl_h} hours. You will be asked to choose a new "
                "password when you sign in.\n\n"
                "Not you? Contact security@picklehub.example straight away.\n",
            )
            del self._state.reset_tokens[key]
            acc.locked = False
            acc.must_change_password = True
            acc.temp_password_expires_at = expires_at
            return {
                "status": "reset",
                "username": acc.username,
                "sent_to": mask_email(acc.recovery_email),
                "temp_password_expires_at": _iso(expires_at),
                "must_change_password": True,
            }

    def unlock(self, username: str) -> dict:
        with self._lock:
            acc = self._get(username)
            acc.locked = False
            return self.public_view(acc)

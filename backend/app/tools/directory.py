"""Client for the StaffID directory (mock-directory/ in this repo, port 8090).

Only the reset_password tool uses it. Codes and temporary passwords never pass through
DinkDesk: the directory sends them itself (to Mailpit in the demo).
"""

import httpx

from app.config import Settings, get_settings

TIMEOUT_S = 10


class DirectoryError(Exception):
    """The directory refused the request or could not be reached.

    `code` is the directory's error code (e.g. OTP_INVALID), or UNREACHABLE.
    """

    def __init__(self, status: int, code: str, message: str, extra: dict | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.extra = extra or {}


class DirectoryClient:
    def __init__(self, settings: Settings | None = None, transport=None) -> None:
        s = settings or get_settings()
        self._client = httpx.Client(
            base_url=s.directory_base_url,
            headers={"X-API-Key": s.directory_api_key.get_secret_value()},
            timeout=TIMEOUT_S,
            transport=transport,
        )

    def _post(self, path: str, body: dict | None = None) -> dict:
        try:
            res = self._client.post(path, json=body or {})
        except httpx.HTTPError as exc:
            raise DirectoryError(503, "UNREACHABLE", "Directory not reachable") from exc
        data = res.json() if res.content else {}
        if res.is_success:
            return data
        error = dict(data.get("error") or {})
        code = error.pop("code", "ERROR")
        message = error.pop("message", res.text)
        raise DirectoryError(res.status_code, code, message, error)

    def send_otp(self, username: str, employee_no: str) -> dict:
        """{challenge_id, expires_at, sent_to, attempts_left}"""
        return self._post(f"/accounts/{username}/otp", {"employee_no": employee_no})

    def verify_otp(self, username: str, challenge_id: str, code: str) -> dict:
        """{verified, privileged, reset_token, reset_token_expires_at}"""
        return self._post(
            f"/accounts/{username}/otp/verify", {"challenge_id": challenge_id, "code": code}
        )

    def reset(self, username: str, reset_token: str) -> dict:
        """{status, username, sent_to, temp_password_expires_at, must_change_password}"""
        return self._post(f"/accounts/{username}/reset", {"reset_token": reset_token})


def get_directory() -> DirectoryClient:
    """FastAPI dependency; tests override it with a fake."""
    return DirectoryClient()

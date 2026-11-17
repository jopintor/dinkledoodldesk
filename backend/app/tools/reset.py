"""reset_password after the user confirms: send a code, check it, reset (docs/api.md §4).

1. confirm -> the directory texts a 6-digit code -> status `awaiting_verification`.
2. verify  -> the directory checks the code and returns a short-lived reset token, which is
   used at once to reset the account; the temporary password goes to the recovery email.

The code and the reset token are never stored, logged or shown. Only the challenge id is
kept on the tool call (under a `_` key, which the API never returns).
"""

from sqlalchemy.orm import Session

from app.models import AuditLog, ToolCall, User
from app.tools.directory import DirectoryClient, DirectoryError

CHALLENGE_KEY = "_challenge_id"


class TryAgain(Exception):
    """A temporary problem: the tool call keeps its status and the user can retry.

    `status` is the HTTP status to answer with; str(exc) is safe to show the user.
    """

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def public_result(result: dict | None) -> dict | None:
    if result is None:
        return None
    return {k: v for k, v in result.items() if not k.startswith("_")}


def _audit(db: Session, user: User, action: str, tool_call: ToolCall, **details) -> None:
    db.add(
        AuditLog(
            user_id=user.id,
            action=action,
            details={"tool_call_id": tool_call.id, "username": user.directory_username, **details},
        )
    )


def _fail(db: Session, user: User, tool_call: ToolCall, code: str, message: str) -> str:
    tool_call.status = "failed"
    tool_call.result = {"error": code}
    _audit(db, user, "password_reset_failed", tool_call, code=code)
    db.commit()
    return message


def start_reset(db: Session, user: User, tool_call: ToolCall, directory: DirectoryClient) -> str:
    """Send the code. Returns the message for the user."""
    if not user.directory_username or not user.employee_no:
        return _fail(
            db, user, tool_call, "NO_DIRECTORY_ACCOUNT",
            "I can't find your StaffID record. Please contact the IT Service Desk.",
        )  # fmt: skip
    try:
        sent = directory.send_otp(user.directory_username, user.employee_no)
    except DirectoryError as exc:
        if exc.code == "OTP_RATE_LIMITED":
            minutes = max(1, round(int(exc.extra.get("retry_after_s", 600)) / 60))
            raise TryAgain(429, f"Too many codes were sent. Try again in {minutes} min.") from exc
        if exc.code in ("UNREACHABLE", "DELIVERY_FAILED") or exc.status >= 500:
            raise TryAgain(
                503, "The password reset service isn't reachable right now. Try again in a minute."
            ) from exc
        if exc.code == "NO_MOBILE_ON_FILE":
            return _fail(
                db, user, tool_call, exc.code,
                "There's no mobile number on your StaffID record, so I can't send a code. "
                "Please contact the IT Service Desk.",
            )  # fmt: skip
        return _fail(
            db, user, tool_call, exc.code,
            "I couldn't verify your StaffID record. Please contact the IT Service Desk.",
        )  # fmt: skip

    tool_call.status = "awaiting_verification"
    tool_call.result = {CHALLENGE_KEY: sent["challenge_id"], "sent_to": sent.get("sent_to")}
    _audit(db, user, "password_reset_code_sent", tool_call)
    db.commit()
    return f"I sent a 6-digit code by text to {sent.get('sent_to') or 'your mobile on file'}."


def finish_reset(
    db: Session, user: User, tool_call: ToolCall, code: str, directory: DirectoryClient
) -> str:
    """Check the code and reset. Returns the message for the user."""
    challenge_id = (tool_call.result or {}).get(CHALLENGE_KEY)
    username = user.directory_username
    try:
        verified = directory.verify_otp(username, challenge_id, code)
    except DirectoryError as exc:
        if exc.code == "OTP_INVALID":
            left = exc.extra.get("attempts_left")
            more = f" {left} attempt{'s' if left != 1 else ''} left." if left is not None else ""
            raise TryAgain(400, f"That code didn't match.{more}") from exc
        if exc.code in ("UNREACHABLE",) or exc.status >= 500:
            raise TryAgain(
                503, "The password reset service isn't reachable right now. Try again in a minute."
            ) from exc
        if exc.code == "OTP_LOCKED":
            return _fail(
                db, user, tool_call, exc.code,
                "Too many wrong codes. For your safety the reset was stopped and IT was "
                "notified. Please contact the IT Service Desk.",
            )  # fmt: skip
        if exc.code == "OTP_EXPIRED":
            return _fail(
                db, user, tool_call, exc.code,
                "That code expired. Ask me to reset your password again for a new code.",
            )  # fmt: skip
        return _fail(
            db, user, tool_call, exc.code,
            "That code can't be used any more. Ask me to reset your password again.",
        )  # fmt: skip

    if verified.get("privileged"):
        # The executor never proposes a reset for agents/admins; this is a second check.
        return _fail(
            db, user, tool_call, "PRIVILEGED_ACCOUNT",
            "This account has admin rights, so IT has to reset it. Please contact the IT "
            "Service Desk.",
        )  # fmt: skip

    try:
        done = directory.reset(username, verified["reset_token"])
    except DirectoryError as exc:
        return _fail(
            db, user, tool_call, exc.code,
            "Your code was right, but the reset didn't go through. Please contact the IT "
            "Service Desk.",
        )  # fmt: skip

    tool_call.status = "succeeded"
    tool_call.result = {
        "sent_to": done.get("sent_to"),
        "temp_password_expires_at": done.get("temp_password_expires_at"),
    }
    _audit(db, user, "password_reset_succeeded", tool_call)
    db.commit()
    return (
        f"Done. A temporary password was sent to {done.get('sent_to') or 'your recovery email'}. "
        "It works for 24 hours, and you'll be asked to change it when you first sign in."
    )

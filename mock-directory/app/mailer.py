"""Sends the directory's messages to Mailpit (or any SMTP server).

One-time codes are "SMS" messages: they go to `<digits>@sms.picklehub.example` so they show
up in the Mailpit inbox next to the emails. Nothing here logs a code or a password.
"""

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

log = logging.getLogger("mock_directory.mailer")


class DeliveryError(Exception):
    """The message could not be handed to the SMTP server."""


class Mailer(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class SmtpMailer:
    def __init__(self, host: str, port: int, sender: str, timeout_s: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.sender = sender
        self.timeout_s = timeout_s

    def send(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout_s) as smtp:
                smtp.send_message(msg)
        except (OSError, smtplib.SMTPException) as exc:
            log.warning(
                "SMTP delivery to %s:%s failed: %s", self.host, self.port, type(exc).__name__
            )
            raise DeliveryError(str(exc)) from exc


def sms_address(mobile: str) -> str:
    digits = "".join(ch for ch in mobile if ch.isdigit())
    return f"{digits}@sms.picklehub.example"

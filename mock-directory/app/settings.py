"""Settings from environment variables. Every value has a safe local default."""

import os
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_SEED = Path(__file__).with_name("seed.json")


@dataclass(frozen=True)
class Settings:
    api_key: str
    smtp_host: str
    smtp_port: int
    mail_from: str
    seed_file: Path
    otp_ttl_s: int
    otp_max_attempts: int
    otp_sends_per_window: int
    otp_send_window_s: int
    reset_token_ttl_s: int
    temp_password_ttl_h: int


def load_settings() -> Settings:
    env = os.environ.get
    return Settings(
        api_key=env("DIRECTORY_API_KEY", "dev-directory-key"),
        smtp_host=env("SMTP_HOST", "localhost"),
        smtp_port=int(env("SMTP_PORT", "1025")),
        mail_from=env("DIRECTORY_MAIL_FROM", "StaffID <no-reply@id.picklehub.example>"),
        seed_file=Path(env("DIRECTORY_SEED_FILE", str(_DEFAULT_SEED))),
        otp_ttl_s=int(env("DIRECTORY_OTP_TTL_S", "600")),  # 10 min (docs/architecture.md §6)
        otp_max_attempts=int(env("DIRECTORY_OTP_MAX_ATTEMPTS", "3")),
        otp_sends_per_window=int(env("DIRECTORY_OTP_SENDS_PER_WINDOW", "3")),
        otp_send_window_s=int(env("DIRECTORY_OTP_SEND_WINDOW_S", "600")),
        # Long enough to cover the 30-minute admin approval of privileged resets.
        reset_token_ttl_s=int(env("DIRECTORY_RESET_TOKEN_TTL_S", "2700")),
        temp_password_ttl_h=int(env("DIRECTORY_TEMP_PASSWORD_TTL_H", "24")),  # KB-001
    )

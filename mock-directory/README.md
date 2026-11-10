# mock-directory — fake StaffID directory

A tiny FastAPI service that stands in for PickleHub's real StaffID directory during development and the demo
(component C14 in [docs/architecture.md](../docs/architecture.md)). The backend's `reset_password` tool calls it;
nothing else should.

- Runs in Docker Compose as `mock-directory` on port **8090** (`http://mock-directory:8090` from other containers).
- One-time codes ("SMS") and temporary passwords are **emailed to Mailpit**, never returned by the API. Open
  <http://localhost:8025> to read them during a demo.
- State is in memory. Restarting the container (or `POST /admin/reload`) restores [app/seed.json](app/seed.json).

## Auth

Every endpoint except `/health` needs the header `X-API-Key: <DIRECTORY_API_KEY>` (default `dev-directory-key`;
compose passes the value from the root `.env` to both the backend and this service).

## Endpoints

Errors use the same shape as the DinkDesk API: `{"error": {"code": "…", "message": "…"}}` (some add
`attempts_left` or `retry_after_s`).

| Method & path | Body | Success | Errors |
|---|---|---|---|
| `GET /health` | — | `{status, version, accounts}` | — |
| `GET /accounts/{username}` | — | account with masked contacts: `username, display_name, privileged, locked, flagged, must_change_password, has_mobile, mobile_masked, recovery_email_masked` | 404 `ACCOUNT_NOT_FOUND` |
| `POST /accounts/{username}/otp` | `{"employee_no": "PH-10021"}` | 201 `{challenge_id, expires_at, sent_to, attempts_left}`; 6-digit code sent to Mailpit as an "SMS" | 400 `VERIFICATION_FAILED` (employee no. mismatch), 409 `NO_MOBILE_ON_FILE`, 429 `OTP_RATE_LIMITED` (3 codes / 10 min), 503 `DELIVERY_FAILED` |
| `POST /accounts/{username}/otp/verify` | `{"challenge_id": "…", "code": "482913"}` | `{verified: true, privileged, reset_token, reset_token_expires_at}` | 400 `OTP_INVALID` (+`attempts_left`), 423 `OTP_LOCKED` after 3 wrong codes (account `flagged`), 400 `OTP_EXPIRED` (10 min), 409 `OTP_ALREADY_USED`, 404 `CHALLENGE_NOT_FOUND` |
| `POST /accounts/{username}/reset` | `{"reset_token": "…"}` | `{status: "reset", username, sent_to, temp_password_expires_at, must_change_password: true}`; temp password (valid 24 h) emailed to the recovery address; account unlocked | 400 `RESET_TOKEN_INVALID` (wrong account, used or older than 45 min), 503 `DELIVERY_FAILED` (token kept, safe to retry) |
| `POST /accounts/{username}/unlock` | — | account view | 404 |
| `POST /admin/reload` | — | `{status, accounts}` — back to the seed | — |

Usernames are case-insensitive. The reset token lives 45 minutes so a privileged reset can wait for the 30-minute
admin approval (WF-03) before the backend calls `/reset`. The backend should keep the token in memory or encrypted,
never in logs or the chat.

## Demo accounts (`app/seed.json`)

| Username | Employee no. | Privileged | Notes |
|---|---|---|---|
| `demo.staff` | PH-10021 | no | normal staff reset, no approval |
| `demo.agent` | PH-10031 | yes | needs admin approval |
| `demo.admin1` / `demo.admin2` | PH-10041 / PH-10042 | yes | two admins so self-approval can be blocked |
| `paolo.reyes` | PH-10055 | yes | the "Paolo R." in docs/automation.md |
| `maria.santos` | PH-10107 | no | starts **locked** |
| `nomobile.staff` | PH-10199 | no | no mobile on file → `NO_MOBILE_ON_FILE` |

Link a DinkDesk user to one of these with `users.directory_username`.

## Settings (env vars)

`DIRECTORY_API_KEY`, `SMTP_HOST` (default `localhost`), `SMTP_PORT` (`1025`), and optional
`DIRECTORY_MAIL_FROM`, `DIRECTORY_SEED_FILE`, `DIRECTORY_OTP_TTL_S` (600), `DIRECTORY_OTP_MAX_ATTEMPTS` (3),
`DIRECTORY_OTP_SENDS_PER_WINDOW` (3), `DIRECTORY_OTP_SEND_WINDOW_S` (600), `DIRECTORY_RESET_TOKEN_TTL_S` (2700),
`DIRECTORY_TEMP_PASSWORD_TTL_H` (24).

## Run and test without Docker

```bash
cd mock-directory
py -3.12 -m venv .venv && .venv/Scripts/activate     # macOS/Linux: python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check . && pytest
uvicorn app.main:app --port 8090                     # emails need Mailpit on localhost:1025
```

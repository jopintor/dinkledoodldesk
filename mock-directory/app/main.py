"""HTTP API of the mock StaffID directory. See ../README.md for the contract."""

import logging
import secrets

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import __version__
from app.mailer import DeliveryError, Mailer, SmtpMailer
from app.settings import Settings, load_settings
from app.store import Directory, DirectoryError

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


class OtpRequest(BaseModel):
    employee_no: str = Field(min_length=1, max_length=32)


class OtpVerify(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=64)
    code: str = Field(pattern=r"^\s*\d{4,8}\s*$")


class ResetRequest(BaseModel):
    reset_token: str = Field(min_length=1, max_length=128)


def _error(status: int, code: str, message: str, **extra: object) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": {"code": code, "message": message, **extra}}
    )


def create_app(
    settings: Settings | None = None, mailer: Mailer | None = None, clock=None
) -> FastAPI:
    settings = settings or load_settings()
    mailer = mailer or SmtpMailer(settings.smtp_host, settings.smtp_port, settings.mail_from)
    directory = Directory(settings, mailer, clock) if clock else Directory(settings, mailer)

    app = FastAPI(title="DinkDesk mock StaffID directory", version=__version__)
    app.state.directory = directory

    @app.exception_handler(DirectoryError)
    async def _directory_error(_: Request, exc: DirectoryError) -> JSONResponse:
        return _error(exc.status, exc.code, exc.message, **exc.extra)

    @app.exception_handler(DeliveryError)
    async def _delivery_error(_: Request, exc: DeliveryError) -> JSONResponse:
        return _error(503, "DELIVERY_FAILED", "Could not send the message; try again shortly.")

    def require_key(x_api_key: str = Header(default="")) -> None:
        if not settings.api_key or not secrets.compare_digest(x_api_key, settings.api_key):
            raise DirectoryError(401, "UNAUTHORIZED", "Missing or wrong X-API-Key.")

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "version": __version__, "accounts": directory.count()}

    @app.get("/accounts/{username}", dependencies=[Depends(require_key)])
    def lookup(username: str) -> dict:
        return directory.lookup(username)

    @app.post("/accounts/{username}/otp", status_code=201, dependencies=[Depends(require_key)])
    def send_otp(username: str, body: OtpRequest) -> dict:
        return directory.send_otp(username, body.employee_no)

    @app.post("/accounts/{username}/otp/verify", dependencies=[Depends(require_key)])
    def verify_otp(username: str, body: OtpVerify) -> dict:
        return directory.verify_otp(username, body.challenge_id, body.code)

    @app.post("/accounts/{username}/reset", dependencies=[Depends(require_key)])
    def reset(username: str, body: ResetRequest) -> dict:
        return directory.reset_password(username, body.reset_token)

    @app.post("/accounts/{username}/unlock", dependencies=[Depends(require_key)])
    def unlock(username: str) -> dict:
        return directory.unlock(username)

    @app.post("/admin/reload", dependencies=[Depends(require_key)])
    def reload() -> dict:
        return {"status": "reloaded", "accounts": directory.reload()}

    return app


app = create_app()

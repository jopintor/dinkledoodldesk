from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

# TODO: match the error format in API doc section 1.4.
CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
}


def error_response(
    status_code: int,
    code: str,
    message: str,
    details=None,
    headers: dict | None = None,
) -> JSONResponse:
    body: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(body, status_code=status_code, headers=headers)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return error_response(
        exc.status_code,
        CODES.get(exc.status_code, "error"),
        str(exc.detail),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [
        {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]} for e in exc.errors()
    ]
    return error_response(422, "validation_error", "Request validation failed", details)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return error_response(
        429,
        "rate_limited",
        "Too many requests. Slow down and try again.",
        headers={"Retry-After": "60"},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

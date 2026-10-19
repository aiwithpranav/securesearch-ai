"""Problem Details (RFC 9457 style) errors: type, title, status, detail, request_id.

Rule: error bodies never echo what the user sent (passwords, tokens, emails)."""
import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Raise this from services/routes to return a clean Problem Details response."""

    def __init__(
        self,
        status: int,
        title: str,
        detail: str,
        headers: dict[str, str] | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.title = title
        self.detail = detail
        self.headers = headers or {}
        self.extra = extra or {}


def _problem(
    request: Request,
    status: int,
    title: str,
    detail: str,
    headers: dict[str, str] | None = None,
    extra: dict[str, object] | None = None,
) -> JSONResponse:
    body: dict[str, object] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
        "request_id": getattr(request.state, "request_id", None),
    }
    if extra:
        body.update(extra)
    return JSONResponse(status_code=status, content=body, headers=headers)


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return _problem(request, exc.status, exc.title, exc.detail, exc.headers, exc.extra)


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    title = {404: "Not Found", 405: "Method Not Allowed"}.get(exc.status_code, "Request Error")
    return _problem(request, exc.status_code, title, str(exc.detail), dict(exc.headers or {}))


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Only field names and rule messages. Never the submitted values.
    errors = [
        {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
        for e in exc.errors()
    ]
    return _problem(
        request, 422, "Validation failed", "Some fields are invalid.", extra={"errors": errors}
    )


async def problem_details_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last resort for unexpected errors. Logs the error type only (no message,
    which could contain user data) and returns a safe 500."""
    request_id = getattr(request.state, "request_id", None)
    logger.error("unhandled_exception type=%s", type(exc).__name__, extra={"request_id": request_id})
    return _problem(request, 500, "Internal Server Error", "An unexpected error occurred.")

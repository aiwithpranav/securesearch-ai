import socket

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.core import rate_limit, status
from app.core.config import settings
from app.core.errors import AppError

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/ready")
async def ready(request: Request):
    status = {"postgres": "ok", "redis": "ok"}
    is_ready = True

    # check postgres
    try:
        if settings.database_url != "CHANGE_ME":
            url_part = settings.database_url.split("@")[1].split("/")[0]
            host, port = url_part.split(":") if ":" in url_part else (url_part, 5432)
            with socket.create_connection((host, int(port)), timeout=2):
                pass
        else:
            status["postgres"] = "down"
            is_ready = False
    except Exception:
        status["postgres"] = "down"
        is_ready = False

    # check redis
    try:
        if settings.redis_url != "CHANGE_ME":
            url = settings.redis_url.split("://")[1].split("/")[0]
            host, port = url.split(":") if ":" in url else (url, 6379)
            with socket.create_connection((host, int(port)), timeout=2):
                pass
        else:
            status["redis"] = "down"
            is_ready = False
    except Exception:
        status["redis"] = "down"
        is_ready = False

    if is_ready:
        return status
    else:
        return JSONResponse(
            status_code=503,
            content={
                "type": "about:blank",
                "title": "Service Unavailable",
                "status": 503,
                "detail": "One or more dependent services are down",
                "request_id": getattr(request.state, "request_id", None),
                "services": status
            }
        )


@router.get("/status")
async def service_status(request: Request, response: Response):
    """The public status page's data: a name and up or down for each part, and one overall word. Nothing else (see app/core/status.py)."""
    ip = request.client.host if request.client else "unknown"
    allowed, retry = await rate_limit.hit(rate_limit.key_for("status", ip), 60, 60)
    if not allowed:
        raise AppError(429, "Too many attempts", "Too many requests. Try again shortly.", headers={"Retry-After": str(retry)}, extra={"retry_after_seconds": retry})
    response.headers["Cache-Control"] = "no-store"
    return await status.collect()

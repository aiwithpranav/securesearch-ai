"""Simple service numbers (Phase 9B, NFR-06): how many requests, how many server errors, how many "too many requests" answers.

Counted per hour in Redis and kept for two days; the Overview shows the last 24 hours (administrators only). Only numbers are
stored: no path, no user, no address. Counting can never break a request: any failure here is ignored.
Health checks and the status page are not counted, so monitoring does not drown the real traffic."""
import logging
from datetime import datetime, timedelta, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

PREFIX = "ss:metrics:"
KEEP_SECONDS = 48 * 3600
SKIP_PATHS = ("/api/v1/health", "/api/v1/ready", "/api/v1/status")
FIELDS = ("requests", "errors_5xx", "rate_limited")


def _bucket(now: datetime) -> str:
    return f"{PREFIX}{now:%Y%m%d%H}"


async def record(status_code: int, now: datetime | None = None) -> None:
    try:
        key = _bucket(now or datetime.now(timezone.utc))
        pipe = get_redis().pipeline(transaction=False)
        pipe.hincrby(key, "requests", 1)
        if status_code >= 500:
            pipe.hincrby(key, "errors_5xx", 1)
        elif status_code == 429:
            pipe.hincrby(key, "rate_limited", 1)
        pipe.expire(key, KEEP_SECONDS)
        await pipe.execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("metrics.record_failed type=%s", type(exc).__name__)


async def last_24_hours(now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    totals = dict.fromkeys(FIELDS, 0)
    try:
        pipe = get_redis().pipeline(transaction=False)
        for h in range(24):
            pipe.hgetall(_bucket(now - timedelta(hours=h)))
        for row in await pipe.execute():
            for f in FIELDS:
                totals[f] += int(row.get(f, 0))
    except Exception as exc:  # noqa: BLE001
        logger.warning("metrics.read_failed type=%s", type(exc).__name__)
    return totals


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        if request.url.path not in SKIP_PATHS:
            await record(response.status_code)
        return response

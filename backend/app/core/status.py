"""Is everything running? (Phase 9B, FR-37.) Real checks, not just "the port is open".

The answer is deliberately plain: a name and up or down for each part, plus one overall word. It never contains a host name,
a version, an error text or a count, so it is safe to show to anyone who can reach the server.
- Database: a real query. Redis: a real PING. File store: a real (cheap) listing.
- Background worker: it writes a heartbeat to Redis every minute; no heartbeat for 3 minutes means it is down.
- Overall: `down` if the database, Redis or the file store is down (nothing works); `degraded` if only the worker is down
  (searching and answering still work, new documents are not processed); otherwise `operational`."""
import asyncio
import logging
import time
from datetime import datetime, timezone

import redis as redis_sync
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.redis import get_redis
from app.db.session import async_session
from app.storage import get_storage

logger = logging.getLogger(__name__)

HEARTBEAT_KEY = "ss:worker:heartbeat"
HEARTBEAT_TTL = 180  # seconds
CHECK_TIMEOUT = 3.0


def record_heartbeat() -> None:
    """Called by the worker every minute (plain, not async: the worker runs plain functions)."""
    client = redis_sync.Redis.from_url(settings.redis_url)
    try:
        client.set(HEARTBEAT_KEY, int(time.time()), ex=HEARTBEAT_TTL)
    finally:
        client.close()


async def _database() -> bool:
    async with async_session() as db:
        await db.execute(text("select 1"))
    return True


async def _redis() -> bool:
    return bool(await get_redis().ping())


async def _storage() -> bool:
    await run_in_threadpool(get_storage().list_keys, "status-check/", 1)
    return True


async def _worker() -> bool:
    return await get_redis().get(HEARTBEAT_KEY) is not None


CHECKS = (("Database", _database), ("Redis", _redis), ("File storage", _storage), ("Background worker", _worker))
CRITICAL = {"Database", "Redis", "File storage"}


async def _run(check) -> bool:  # type: ignore[no-untyped-def]
    try:
        return bool(await asyncio.wait_for(check(), timeout=CHECK_TIMEOUT))
    except Exception as exc:  # noqa: BLE001  any failure, including a timeout, means "down"; the reason is not shown
        logger.warning("status.check_failed type=%s", type(exc).__name__)
        return False


async def collect() -> dict[str, object]:
    results = await asyncio.gather(*(_run(check) for _, check in CHECKS))
    components = [{"name": name, "status": "up" if ok else "down"} for (name, _), ok in zip(CHECKS, results)]
    down = {c["name"] for c in components if c["status"] == "down"}
    overall = "down" if down & CRITICAL else "degraded" if down else "operational"
    return {"status": overall, "components": components, "checked_at": datetime.now(timezone.utc).isoformat()}

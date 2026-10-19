"""Small Redis counters for rate limits and login lockout (NFR-03).

All keys start with "ss:" so tests and operators can find them."""
import hashlib

from app.core.redis import get_redis

PREFIX = "ss:"


def key_for(kind: str, raw: str) -> str:
    """Hash the raw value (email, IP) so Redis never stores readable emails."""
    return f"{PREFIX}{kind}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]}"


async def hit(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Count one event. Returns (allowed, seconds_until_window_resets)."""
    r = get_redis()
    async with r.pipeline(transaction=True) as pipe:
        pipe.set(key, 0, ex=window_seconds, nx=True)  # start a window if none
        pipe.incr(key)
        pipe.ttl(key)
        _, count, ttl = await pipe.execute()
    return int(count) <= limit, max(int(ttl), 1)


async def failure_count(key: str) -> int:
    return int(await get_redis().get(key) or 0)


async def seconds_left(key: str) -> int:
    return max(int(await get_redis().ttl(key)), 1)


async def add_failure(key: str, max_failures: int, window_seconds: int, lockout_seconds: int) -> int:
    """Record one failed login. When the limit is reached the counter's lifetime
    becomes the lockout duration, so the account stays locked for that long."""
    r = get_redis()
    async with r.pipeline(transaction=True) as pipe:
        pipe.set(key, 0, ex=window_seconds, nx=True)
        pipe.incr(key)
        _, count = await pipe.execute()
    if int(count) >= max_failures:
        await r.expire(key, lockout_seconds)
    return int(count)


async def clear(key: str) -> None:
    await get_redis().delete(key)

"""Login, refresh-token rotation, logout, and password reset/change.

Security rules implemented here (blueprint Sections 7.5, 9, ADR-018):
- One generic message for every login failure (no hint which field was wrong).
- Temporary lockout after repeated failures, also for emails that do not exist.
- Refresh tokens rotate on every use. Re-using an old one revokes the whole session family.
- Reset tokens are single-use, expire, and are stored only as hashes.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core import rate_limit
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import security_event
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    hash_password,
    hash_token,
    needs_rehash,
    new_opaque_token,
    verify_password,
)
from app.models import AuthToken, User

REFRESH = "REFRESH"
RESET = "RESET"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def invalid_credentials() -> AppError:
    return AppError(
        401,
        "Invalid credentials",
        "Email or password is incorrect.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def invalid_session() -> AppError:
    return AppError(
        401, "Session expired", "Please sign in again.", headers={"WWW-Authenticate": "Bearer"}
    )


def invalid_reset_link() -> AppError:
    return AppError(400, "Invalid link", "This link is invalid or has expired.")


@dataclass
class SessionResult:
    access_token: str
    expires_in: int
    refresh_token: str
    cookie_max_age: int | None  # None = browser-session cookie
    user: User


# ---------------------------------------------------------------- helpers

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email))


async def revoke_all_refresh_tokens(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(AuthToken)
        .where(AuthToken.user_id == user_id, AuthToken.type == REFRESH, AuthToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


async def revoke_all_sessions(db: AsyncSession, user: User) -> None:
    """Sign the user out everywhere: kill refresh tokens AND old access tokens."""
    await revoke_all_refresh_tokens(db, user.id)
    user.auth_valid_after = _now()


async def _revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    await db.execute(
        update(AuthToken)
        .where(AuthToken.family_id == family_id, AuthToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


async def _issue_session(
    db: AsyncSession,
    user: User,
    remember_me: bool,
    family_id: uuid.UUID | None = None,
    expires_at: datetime | None = None,
) -> SessionResult:
    now = _now()
    if expires_at is None:
        expires_at = now + (
            timedelta(days=settings.refresh_remember_days)
            if remember_me
            else timedelta(hours=settings.refresh_session_hours)
        )
    raw = new_opaque_token()
    db.add(
        AuthToken(
            user_id=user.id,
            type=REFRESH,
            token_hash=hash_token(raw),
            family_id=family_id or uuid.uuid4(),
            remember_me=remember_me,
            expires_at=expires_at,
        )
    )
    access, expires_in = create_access_token(user.id, now)
    max_age = max(int((expires_at - now).total_seconds()), 1) if remember_me else None
    return SessionResult(access, expires_in, raw, max_age, user)


# ------------------------------------------------------------------ login

async def login(
    db: AsyncSession, email: str, password: str, remember_me: bool, ip: str, request_id: str | None
) -> SessionResult:
    allowed, retry = await rate_limit.hit(
        rate_limit.key_for("login-ip", ip), settings.login_ip_limit_per_minute, 60
    )
    if not allowed:
        raise _too_many(retry)

    fail_key = rate_limit.key_for("login-fail", email)
    if await rate_limit.failure_count(fail_key) >= settings.login_max_failures:
        security_event("auth.login_locked", request_id)
        raise _too_many(await rate_limit.seconds_left(fail_key))

    user = await get_user_by_email(db, email)
    # Always run one Argon2 check (against a dummy hash if needed) so timing is similar.
    hash_to_check = user.password_hash if user else DUMMY_HASH
    password_ok = await run_in_threadpool(verify_password, hash_to_check, password)

    if not (user and password_ok and user.is_active):
        await rate_limit.add_failure(
            fail_key,
            settings.login_max_failures,
            settings.login_lockout_minutes * 60,
            settings.login_lockout_minutes * 60,
        )
        security_event(
            "auth.login_failed", request_id, user_id=str(user.id) if user else None
        )
        raise invalid_credentials()

    await rate_limit.clear(fail_key)
    if await run_in_threadpool(needs_rehash, user.password_hash):
        user.password_hash = await run_in_threadpool(hash_password, password)
    user.last_login_at = _now()
    result = await _issue_session(db, user, remember_me)
    await db.commit()
    security_event("auth.login_ok", request_id, user_id=str(user.id))
    return result


def _too_many(retry_after: int) -> AppError:
    minutes = max(1, (retry_after + 59) // 60)
    return AppError(
        429,
        "Too many attempts",
        f"Too many attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.",
        headers={"Retry-After": str(retry_after)},
        extra={"retry_after_seconds": retry_after},
    )


# ---------------------------------------------------------------- refresh

async def refresh(db: AsyncSession, raw_token: str | None, request_id: str | None) -> SessionResult:
    if not raw_token:
        raise invalid_session()
    row = await db.scalar(
        select(AuthToken).where(AuthToken.token_hash == hash_token(raw_token), AuthToken.type == REFRESH)
    )
    now = _now()
    if row is None or row.revoked_at is not None or row.expires_at <= now:
        raise invalid_session()

    # Atomic "use once": only one request can flip used_at from NULL.
    claimed = await db.execute(
        update(AuthToken)
        .where(AuthToken.id == row.id, AuthToken.used_at.is_(None), AuthToken.revoked_at.is_(None))
        .values(used_at=now)
        .returning(AuthToken.id)
    )
    if claimed.first() is None:
        # Token was already used: treat as theft and kill the whole family.
        assert row.family_id is not None
        await _revoke_family(db, row.family_id)
        await db.commit()
        security_event("auth.refresh_reuse_detected", request_id, user_id=str(row.user_id))
        raise invalid_session()

    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        assert row.family_id is not None
        await _revoke_family(db, row.family_id)
        await db.commit()
        raise invalid_session()

    # New token keeps the same family and the same absolute end time.
    result = await _issue_session(
        db, user, row.remember_me, family_id=row.family_id, expires_at=row.expires_at
    )
    await db.commit()
    return result


# ----------------------------------------------------------------- logout

async def logout(db: AsyncSession, raw_token: str | None) -> None:
    """Ends this browser's session. Always succeeds (idempotent)."""
    if not raw_token:
        return
    row = await db.scalar(
        select(AuthToken).where(AuthToken.token_hash == hash_token(raw_token), AuthToken.type == REFRESH)
    )
    if row is not None and row.family_id is not None:
        await _revoke_family(db, row.family_id)
        await db.commit()


async def logout_all(db: AsyncSession, user: User, request_id: str | None) -> None:
    await revoke_all_sessions(db, user)
    await db.commit()
    security_event("auth.logout_all", request_id, user_id=str(user.id))


# --------------------------------------------------------- reset / invite

async def create_reset_token(db: AsyncSession, user: User, lifetime: timedelta) -> str:
    """Creates a single-use token and returns the RAW value (to email). Only the hash is stored.
    Older unused reset tokens for this user are cancelled, so only the newest link works."""
    await db.execute(
        update(AuthToken)
        .where(
            AuthToken.user_id == user.id,
            AuthToken.type == RESET,
            AuthToken.used_at.is_(None),
            AuthToken.revoked_at.is_(None),
        )
        .values(revoked_at=_now())
    )
    raw = new_opaque_token()
    db.add(
        AuthToken(
            user_id=user.id,
            type=RESET,
            token_hash=hash_token(raw),
            expires_at=_now() + lifetime,
        )
    )
    return raw


async def forgot_password(
    db: AsyncSession, email: str, ip: str, request_id: str | None
) -> tuple[User, str] | None:
    """Returns (user, raw_token) when an email should be sent, otherwise None.
    The caller returns the SAME response either way (no account enumeration)."""
    allowed, retry = await rate_limit.hit(
        rate_limit.key_for("forgot-ip", ip), settings.forgot_ip_limit_per_15min, 15 * 60
    )
    if not allowed:
        raise _too_many(retry)

    user = await get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None
    # Quietly limit emails per account so nobody can spam a mailbox.
    ok, _ = await rate_limit.hit(rate_limit.key_for("forgot-email", email), 3, 3600)
    if not ok:
        return None
    raw = await create_reset_token(db, user, timedelta(minutes=settings.reset_token_minutes))
    await db.commit()
    security_event("auth.reset_requested", request_id, user_id=str(user.id))
    return user, raw


async def reset_password(
    db: AsyncSession, raw_token: str, new_password: str, request_id: str | None
) -> None:
    now = _now()
    claimed = await db.execute(
        update(AuthToken)
        .where(
            AuthToken.token_hash == hash_token(raw_token),
            AuthToken.type == RESET,
            AuthToken.used_at.is_(None),
            AuthToken.revoked_at.is_(None),
            AuthToken.expires_at > now,
        )
        .values(used_at=now)
        .returning(AuthToken.user_id)
    )
    row = claimed.first()
    if row is None:
        raise invalid_reset_link()
    user = await db.get(User, row[0])
    if user is None or not user.is_active:
        await db.rollback()
        raise invalid_reset_link()

    user.password_hash = await run_in_threadpool(hash_password, new_password)
    await revoke_all_sessions(db, user)
    await db.commit()
    await rate_limit.clear(rate_limit.key_for("login-fail", user.email))
    security_event("auth.password_reset", request_id, user_id=str(user.id))


async def change_password(
    db: AsyncSession, user: User, current: str, new: str, request_id: str | None
) -> None:
    allowed, retry = await rate_limit.hit(rate_limit.key_for("chpw", str(user.id)), 5, 15 * 60)
    if not allowed:
        raise _too_many(retry)
    if not await run_in_threadpool(verify_password, user.password_hash, current):
        security_event("auth.change_password_failed", request_id, user_id=str(user.id))
        raise AppError(400, "Wrong password", "Current password is incorrect.")
    user.password_hash = await run_in_threadpool(hash_password, new)
    await revoke_all_sessions(db, user)
    await db.commit()
    security_event("auth.password_changed", request_id, user_id=str(user.id))

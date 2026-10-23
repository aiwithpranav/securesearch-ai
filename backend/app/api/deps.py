"""Shared FastAPI dependencies: who is calling, and are they an admin?

The server decides. Roles are read from the database on EVERY request, never
from the token (ADR-018)."""
import uuid

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User
from app.services.auth_service import invalid_session
from app.services.user_service import ADMIN_ROLE

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise invalid_session()
    claims = decode_access_token(creds.credentials)
    if claims is None:
        raise invalid_session()
    try:
        user_id = uuid.UUID(str(claims["sub"]))
    except ValueError:
        raise invalid_session() from None

    user = await db.get(User, user_id)
    # Deactivated users are rejected immediately (FR-03).
    if user is None or not user.is_active:
        raise invalid_session()
    # "Sign out everywhere" / password change cut off older access tokens too.
    if int(str(claims["iat"])) < int(user.auth_valid_after.timestamp()):
        raise invalid_session()
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if ADMIN_ROLE not in user.role_names:
        raise AppError(403, "Forbidden", "You do not have permission to do this.")
    return user


def require_trusted_origin(request: Request) -> None:
    """Cookie-based endpoints (refresh, logout): if the browser says which site
    sent the request, it must be our frontend. Extra CSRF protection on top of SameSite."""
    origin = request.headers.get("origin")
    if origin is not None and origin != settings.frontend_origin:
        raise AppError(403, "Forbidden", "Request origin is not allowed.")

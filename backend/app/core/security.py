"""Password hashing (Argon2id), opaque tokens, and access-token (JWT) helpers.

The access token carries ONLY the user id and timing claims. Roles, department
and clearance are read from the database on every request (ADR-018)."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

# argon2-cffi defaults are Argon2id with the RFC 9106 low-memory profile.
_hasher = PasswordHasher()

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# Verified against when the email is unknown, so "no such user" takes about as
# long as "wrong password" (stops attackers timing which emails exist).
DUMMY_HASH = _hasher.hash("not-a-real-password-for-timing-only")


def new_opaque_token() -> str:
    """A random token for refresh cookies and reset links (384 bits)."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user_id: uuid.UUID, now: datetime | None = None) -> tuple[str, int]:
    """Returns (jwt, expires_in_seconds)."""
    now = now or datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_minutes)
    claims = {
        "sub": str(user_id),
        "jti": uuid.uuid4().hex,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    token = jwt.encode(claims, settings.jwt_secret_key, algorithm=ALGORITHM)
    return token, settings.access_token_minutes * 60


def decode_access_token(token: str) -> dict[str, object] | None:
    """Returns the claims, or None if the token is invalid, expired or the wrong kind."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[ALGORITHM],  # fixed list: never trust the token's own "alg"
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    if claims.get("type") != "access":
        return None
    return claims

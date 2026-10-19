"""Pure unit tests: no database needed for the logic, but conftest still prepares one."""
import time
import uuid

import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    new_opaque_token,
    verify_password,
)


def test_password_is_hashed_with_argon2id_and_verifies():
    h = hash_password("a-long-test-password")
    assert h.startswith("$argon2id$")
    assert "a-long-test-password" not in h
    assert verify_password(h, "a-long-test-password")
    assert not verify_password(h, "wrong")
    assert not verify_password("not-a-hash", "anything")


def test_opaque_tokens_are_random_and_hash_is_stable():
    a, b = new_opaque_token(), new_opaque_token()
    assert a != b and len(a) >= 60
    assert hash_token(a) == hash_token(a) != hash_token(b)
    assert a not in hash_token(a)


def test_access_token_round_trip_has_no_roles():
    uid = uuid.uuid4()
    token, expires_in = create_access_token(uid)
    claims = decode_access_token(token)
    assert claims is not None and claims["sub"] == str(uid)
    assert expires_in == settings.access_token_minutes * 60
    assert set(claims) == {"sub", "jti", "type", "iat", "exp"}  # ADR-018: no roles in token


def test_bad_access_tokens_are_rejected():
    uid = str(uuid.uuid4())
    now = int(time.time())
    good = {"sub": uid, "type": "access", "iat": now, "exp": now + 60}
    assert decode_access_token(jwt.encode(good, settings.jwt_secret_key, "HS256")) is not None
    # wrong signing key
    assert decode_access_token(jwt.encode(good, "x" * 40, "HS256")) is None
    # expired
    expired = {**good, "iat": now - 120, "exp": now - 60}
    assert decode_access_token(jwt.encode(expired, settings.jwt_secret_key, "HS256")) is None
    # "alg: none" trick
    assert decode_access_token(jwt.encode(good, None, algorithm="none")) is None
    # wrong token type
    wrong = {**good, "type": "refresh"}
    assert decode_access_token(jwt.encode(wrong, settings.jwt_secret_key, "HS256")) is None
    assert decode_access_token("garbage") is None

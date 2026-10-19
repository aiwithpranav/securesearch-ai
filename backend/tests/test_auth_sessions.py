"""Refresh-token rotation, reuse detection, logout, logout-all, origin check."""
import time

from app.core.config import settings


def test_refresh_rotates_the_cookie_and_returns_new_access_token(api, make_user):
    make_user("aisha@demo")
    _, rt1 = api.signed_in("aisha@demo")
    resp = api.request("POST", "/auth/refresh", refresh=rt1)
    assert resp.status_code == 200
    rt2 = api.refresh_cookie(resp)
    assert rt2 != rt1
    assert api.request("GET", "/auth/me", token=resp.json()["access_token"]).status_code == 200


def test_reusing_an_old_refresh_token_kills_the_whole_session_family(api, make_user):
    make_user("aisha@demo")
    _, rt1 = api.signed_in("aisha@demo")
    rt2 = api.refresh_cookie(api.request("POST", "/auth/refresh", refresh=rt1))
    # attacker replays the OLD token
    assert api.request("POST", "/auth/refresh", refresh=rt1).status_code == 401
    # the legitimate newer token is now dead too (family revoked)
    assert api.request("POST", "/auth/refresh", refresh=rt2).status_code == 401


def test_other_devices_are_not_affected_by_reuse_on_one_family(api, make_user):
    make_user("aisha@demo")
    _, laptop = api.signed_in("aisha@demo")
    _, phone = api.signed_in("aisha@demo")
    api.request("POST", "/auth/refresh", refresh=laptop)
    api.request("POST", "/auth/refresh", refresh=laptop)  # reuse -> laptop family dead
    assert api.request("POST", "/auth/refresh", refresh=phone).status_code == 200


def test_refresh_without_or_with_garbage_cookie_is_401(api):
    assert api.request("POST", "/auth/refresh").status_code == 401
    assert api.request("POST", "/auth/refresh", refresh="garbage").status_code == 401


def test_expired_refresh_token_is_rejected(api, make_user, pg):
    make_user("aisha@demo")
    _, rt = api.signed_in("aisha@demo")
    pg.execute("UPDATE auth_tokens SET expires_at = now() - interval '1 minute'")
    assert api.request("POST", "/auth/refresh", refresh=rt).status_code == 401


def test_rotation_keeps_the_original_absolute_expiry(api, make_user, pg):
    make_user("aisha@demo")
    _, rt = api.signed_in("aisha@demo", remember=True)
    api.request("POST", "/auth/refresh", refresh=rt)
    rows = pg.execute("SELECT count(DISTINCT expires_at), count(*) FROM auth_tokens").fetchone()
    assert rows == (1, 2)


def test_refresh_token_is_stored_hashed(api, make_user, pg):
    make_user("aisha@demo")
    _, rt = api.signed_in("aisha@demo")
    stored = pg.execute("SELECT token_hash FROM auth_tokens").fetchone()[0]
    assert stored != rt and rt not in stored and len(stored) == 64


def test_refresh_for_deactivated_user_is_rejected(api, make_user, pg):
    make_user("aisha@demo")
    _, rt = api.signed_in("aisha@demo")
    pg.execute("UPDATE users SET is_active=false")
    assert api.request("POST", "/auth/refresh", refresh=rt).status_code == 401


def test_logout_revokes_the_refresh_token(api, make_user):
    make_user("aisha@demo")
    _, rt = api.signed_in("aisha@demo")
    assert api.request("POST", "/auth/logout", refresh=rt).status_code == 204
    assert api.request("POST", "/auth/logout", refresh=rt).status_code == 204  # idempotent
    assert api.request("POST", "/auth/refresh", refresh=rt).status_code == 401


def test_logout_all_ends_every_device_and_old_access_tokens(api, make_user):
    make_user("aisha@demo")
    token1, rt1 = api.signed_in("aisha@demo")
    _, rt2 = api.signed_in("aisha@demo")
    time.sleep(1.1)  # access tokens carry whole-second timestamps
    assert api.request("POST", "/auth/logout-all", token=token1).status_code == 204
    assert api.request("POST", "/auth/refresh", refresh=rt1).status_code == 401
    assert api.request("POST", "/auth/refresh", refresh=rt2).status_code == 401
    assert api.request("GET", "/auth/me", token=token1).status_code == 401
    assert api.signed_in("aisha@demo")  # logging in again works


def test_logout_all_requires_sign_in(api):
    assert api.request("POST", "/auth/logout-all").status_code == 401


def test_cookie_endpoints_reject_foreign_origins(api, make_user):
    make_user("aisha@demo")
    _, rt = api.signed_in("aisha@demo")
    evil = api.request("POST", "/auth/refresh", refresh=rt, headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403
    ok = api.request("POST", "/auth/refresh", refresh=rt, headers={"Origin": settings.frontend_origin})
    assert ok.status_code == 200
    assert api.request("POST", "/auth/logout", headers={"Origin": "https://evil.example"}).status_code == 403

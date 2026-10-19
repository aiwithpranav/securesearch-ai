import time

import jwt

from app.core.config import settings
from tests.constants import TEST_PASSWORD


def test_login_success_returns_token_user_and_safe_cookie(api, make_user):
    make_user("aisha@demo", roles=("employee",), clearance=1)
    resp = api.login("aisha@demo")
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 900
    assert body["user"]["email"] == "aisha@demo"
    assert body["user"]["roles"] == ["employee"]
    assert body["user"]["department"]["name"] == "Engineering"
    assert body["user"]["clearance_level"] == 1
    assert "password" not in resp.text
    cookie = [h for h in resp.headers.get_list("set-cookie") if h.startswith("refresh_token=")][0]
    low = cookie.lower()
    assert "httponly" in low and "samesite=lax" in low and "path=/api/v1/auth" in low
    assert "max-age" not in low  # "remember me" unchecked: session cookie
    assert "refresh_token" not in resp.text  # the refresh token is never in the JSON body


def test_access_token_contains_no_roles(api, make_user):
    make_user("dev@demo", roles=("employee", "system_admin"))
    token, _ = api.signed_in("dev@demo")
    claims = jwt.decode(token, options={"verify_signature": False})
    assert set(claims) == {"sub", "jti", "type", "iat", "exp"}


def test_remember_me_sets_persistent_cookie(api, make_user):
    make_user("aisha@demo")
    resp = api.login("aisha@demo", remember=True)
    cookie = [h for h in resp.headers.get_list("set-cookie") if h.startswith("refresh_token=")][0]
    assert f"Max-Age={settings.refresh_remember_days * 86400}" in cookie


def test_email_is_trimmed_and_case_insensitive(api, make_user):
    make_user("aisha@demo")
    assert api.request("POST", "/auth/login",
                       json={"email": "  AISHA@Demo ", "password": TEST_PASSWORD}).status_code == 200


def test_wrong_password_and_unknown_email_look_identical(api, make_user):
    make_user("aisha@demo")
    wrong = api.login("aisha@demo", password="wrong-password-123")
    unknown = api.login("nobody@demo", password="wrong-password-123")
    assert wrong.status_code == unknown.status_code == 401
    a, b = wrong.json(), unknown.json()
    a.pop("request_id"), b.pop("request_id")
    assert a == b
    assert a["detail"] == "Email or password is incorrect."


def test_deactivated_user_cannot_login_and_gets_same_message(api, make_user):
    make_user("gone@demo", active=False)
    resp = api.login("gone@demo")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Email or password is incorrect."


def test_lockout_after_five_wrong_passwords_even_with_correct_password(api, make_user):
    make_user("aisha@demo")
    for _ in range(5):
        assert api.login("aisha@demo", password="wrong-password-123").status_code == 401
    locked = api.login("aisha@demo")  # correct password, but locked
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0
    assert "Too many attempts" in locked.json()["detail"]


def test_lockout_also_applies_to_unknown_emails(api):
    for _ in range(5):
        assert api.login("ghost@demo", password="wrong-password-123").status_code == 401
    assert api.login("ghost@demo", password="wrong-password-123").status_code == 429


def test_successful_login_resets_failure_counter(api, make_user):
    make_user("aisha@demo")
    for _ in range(4):
        api.login("aisha@demo", password="wrong-password-123")
    assert api.login("aisha@demo").status_code == 200
    for _ in range(4):
        assert api.login("aisha@demo", password="wrong-password-123").status_code == 401
    assert api.login("aisha@demo").status_code == 200


def test_ip_rate_limit(api):
    codes = [api.login(f"user{i}@demo", password="wrong-password-123").status_code
             for i in range(settings.login_ip_limit_per_minute + 2)]
    assert codes[: settings.login_ip_limit_per_minute] == [401] * settings.login_ip_limit_per_minute
    assert codes[-1] == 429


def test_validation_errors_never_echo_the_password(api):
    resp = api.request("POST", "/auth/login", json={"email": "not-an-email", "password": "secret-value-xyz"})
    assert resp.status_code == 422
    assert "secret-value-xyz" not in resp.text
    assert resp.json()["title"] == "Validation failed"
    empty = api.request("POST", "/auth/login", json={"email": "a@b", "password": ""})
    assert empty.status_code == 422


def test_me_requires_a_valid_token(api, make_user):
    make_user("aisha@demo")
    assert api.request("GET", "/auth/me").status_code == 401
    assert api.request("GET", "/auth/me", token="garbage").status_code == 401
    token, _ = api.signed_in("aisha@demo")
    resp = api.request("GET", "/auth/me", token=token)
    assert resp.status_code == 200 and resp.json()["email"] == "aisha@demo"


def test_roles_are_read_from_database_not_token(api, make_user, pg):
    make_user("aisha@demo", roles=("employee",))
    token, _ = api.signed_in("aisha@demo")
    assert api.request("GET", "/auth/me", token=token).json()["roles"] == ["employee"]
    pg.execute("INSERT INTO user_roles SELECT u.id, r.id FROM users u, roles r "
               "WHERE u.email='aisha@demo' AND r.name='auditor'")
    # same token, new role shows up immediately
    assert api.request("GET", "/auth/me", token=token).json()["roles"] == ["auditor", "employee"]


def test_expired_and_forged_tokens_are_rejected(api, make_user):
    uid = make_user("aisha@demo")
    now = int(time.time())
    expired = jwt.encode({"sub": uid, "type": "access", "iat": now - 1000, "exp": now - 10},
                         settings.jwt_secret_key, "HS256")
    forged = jwt.encode({"sub": uid, "type": "access", "iat": now, "exp": now + 600},
                        "attacker-key-" + "x" * 30, "HS256")
    assert api.request("GET", "/auth/me", token=expired).status_code == 401
    assert api.request("GET", "/auth/me", token=forged).status_code == 401


def test_deactivated_user_with_valid_token_is_rejected_immediately(api, make_user, pg):
    make_user("aisha@demo")
    token, _ = api.signed_in("aisha@demo")
    assert api.request("GET", "/auth/me", token=token).status_code == 200
    pg.execute("UPDATE users SET is_active=false WHERE email='aisha@demo'")
    assert api.request("GET", "/auth/me", token=token).status_code == 401


def test_all_seed_style_users_can_log_in(api, make_user):
    emails = [f"{n}@demo" for n in ("aisha", "rahul", "priya", "arjun", "meera", "vikram", "dev", "nina")]
    for e in emails:
        make_user(e)
    for e in emails:
        assert api.login(e).status_code == 200, e


def test_error_responses_use_problem_details_and_request_id(api):
    resp = api.request("GET", "/does-not-exist")
    body = resp.json()
    assert resp.status_code == 404
    assert {"type", "title", "status", "detail", "request_id"} <= set(body)
    assert resp.headers["X-Request-ID"] == body["request_id"]

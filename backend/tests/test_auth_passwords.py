"""Forgot / reset / change password, with real emails captured by Mailpit."""
import re

from tests.constants import TEST_PASSWORD

NEW_PASSWORD = "brand-new-password-42"


def _token_from(mail_text: str) -> str:
    m = re.search(r"#token=([A-Za-z0-9_\-]+)", mail_text)
    assert m, "no reset link in email"
    return m.group(1)


def test_forgot_password_answers_the_same_for_known_and_unknown_emails(api, make_user):
    make_user("aisha@demo")
    known = api.request("POST", "/auth/forgot-password", json={"email": "aisha@demo"})
    unknown = api.request("POST", "/auth/forgot-password", json={"email": "ghost@demo"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    api.get_mail("aisha@demo")
    assert api.mail_count() == 1  # nothing was sent for the unknown address


def test_deactivated_users_get_no_reset_email(api, make_user):
    make_user("gone@demo", active=False)
    assert api.request("POST", "/auth/forgot-password", json={"email": "gone@demo"}).status_code == 202
    assert api.mail_count() == 0


def test_full_reset_flow_and_token_is_single_use(api, make_user, pg):
    make_user("aisha@demo")
    _, old_refresh = api.signed_in("aisha@demo")
    api.request("POST", "/auth/forgot-password", json={"email": "aisha@demo"})
    token = _token_from(api.get_mail("aisha@demo"))
    stored = pg.execute("SELECT token_hash FROM auth_tokens WHERE type='RESET'").fetchone()[0]
    assert stored != token  # only the hash is stored

    done = api.request("POST", "/auth/reset-password", json={"token": token, "new_password": NEW_PASSWORD})
    assert done.status_code == 204
    again = api.request("POST", "/auth/reset-password", json={"token": token, "new_password": NEW_PASSWORD})
    assert again.status_code == 400  # single use

    assert api.login("aisha@demo", password=TEST_PASSWORD).status_code == 401
    assert api.login("aisha@demo", password=NEW_PASSWORD).status_code == 200
    # the reset signed out the old session
    assert api.request("POST", "/auth/refresh", refresh=old_refresh).status_code == 401


def test_expired_or_garbage_reset_token_is_rejected(api, make_user, pg):
    make_user("aisha@demo")
    api.request("POST", "/auth/forgot-password", json={"email": "aisha@demo"})
    token = _token_from(api.get_mail("aisha@demo"))
    pg.execute("UPDATE auth_tokens SET expires_at = now() - interval '1 minute'")
    for t in (token, "garbage"):
        r = api.request("POST", "/auth/reset-password", json={"token": t, "new_password": NEW_PASSWORD})
        assert r.status_code == 400
        assert r.json()["detail"] == "This link is invalid or has expired."


def test_a_newer_reset_link_cancels_the_older_one(api, make_user):
    make_user("aisha@demo")
    api.request("POST", "/auth/forgot-password", json={"email": "aisha@demo"})
    first = _token_from(api.get_mail("aisha@demo"))
    api.clear_mail()
    api.request("POST", "/auth/forgot-password", json={"email": "aisha@demo"})
    second = _token_from(api.get_mail("aisha@demo"))
    assert first != second
    bad = api.request("POST", "/auth/reset-password", json={"token": first, "new_password": NEW_PASSWORD})
    good = api.request("POST", "/auth/reset-password", json={"token": second, "new_password": NEW_PASSWORD})
    assert (bad.status_code, good.status_code) == (400, 204)


def test_weak_new_password_is_rejected(api, make_user):
    make_user("aisha@demo")
    api.request("POST", "/auth/forgot-password", json={"email": "aisha@demo"})
    token = _token_from(api.get_mail("aisha@demo"))
    r = api.request("POST", "/auth/reset-password", json={"token": token, "new_password": "short"})
    assert r.status_code == 422 and "at least 12" in r.text


def test_reset_clears_a_lockout(api, make_user):
    make_user("aisha@demo")
    for _ in range(5):
        api.login("aisha@demo", password="wrong-password-123")
    assert api.login("aisha@demo").status_code == 429
    api.request("POST", "/auth/forgot-password", json={"email": "aisha@demo"})
    token = _token_from(api.get_mail("aisha@demo"))
    api.request("POST", "/auth/reset-password", json={"token": token, "new_password": NEW_PASSWORD})
    assert api.login("aisha@demo", password=NEW_PASSWORD).status_code == 200


def test_forgot_password_is_rate_limited_per_ip(api):
    codes = [api.request("POST", "/auth/forgot-password", json={"email": f"u{i}@demo"}).status_code
             for i in range(7)]
    assert codes[:5] == [202] * 5 and codes[-1] == 429


def test_change_password_flow(api, make_user):
    make_user("aisha@demo")
    token, rt = api.signed_in("aisha@demo")
    wrong = api.request("POST", "/auth/change-password", token=token,
                        json={"current_password": "not-my-password", "new_password": NEW_PASSWORD})
    assert wrong.status_code == 400
    ok = api.request("POST", "/auth/change-password", token=token,
                     json={"current_password": TEST_PASSWORD, "new_password": NEW_PASSWORD})
    assert ok.status_code == 204
    assert api.request("POST", "/auth/refresh", refresh=rt).status_code == 401
    assert api.login("aisha@demo", password=TEST_PASSWORD).status_code == 401
    assert api.login("aisha@demo", password=NEW_PASSWORD).status_code == 200


def test_change_password_requires_sign_in_and_is_rate_limited(api, make_user):
    make_user("aisha@demo")
    body = {"current_password": "not-my-password", "new_password": NEW_PASSWORD}
    assert api.request("POST", "/auth/change-password", json=body).status_code == 401
    token, _ = api.signed_in("aisha@demo")
    codes = [api.request("POST", "/auth/change-password", token=token, json=body).status_code
             for _ in range(6)]
    assert codes[:5] == [400] * 5 and codes[5] == 429

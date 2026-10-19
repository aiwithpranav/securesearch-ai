"""Admin endpoints: who may call them, and what they do."""
import re
import time

import jwt

from app.core.config import settings
from tests.constants import TEST_PASSWORD


def _ids(pg):
    dept = pg.execute("SELECT id FROM departments WHERE name='Finance'").fetchone()[0]
    roles = dict(pg.execute("SELECT name, id FROM roles").fetchall())
    return dept, roles


def _admin(api, make_user, email="dev@demo"):
    make_user(email, roles=("employee", "system_admin"))
    token, _ = api.signed_in(email)
    return token


def test_user_management_requires_sign_in_and_the_admin_role(api, make_user):
    make_user("aisha@demo", roles=("employee",))
    make_user("nina@demo", roles=("employee", "auditor"))
    for path in ("/users", "/roles", "/departments"):
        assert api.request("GET", path).status_code == 401
    for email in ("aisha@demo", "nina@demo"):
        token, _ = api.signed_in(email)
        for path in ("/users", "/roles", "/departments"):
            assert api.request("GET", path, token=token).status_code == 403, (email, path)
        assert api.request("POST", "/users", token=token, json={}).status_code == 403


def test_forged_role_claim_in_token_does_not_grant_admin(api, make_user):
    uid = make_user("aisha@demo", roles=("employee",))
    now = int(time.time())
    forged = jwt.encode(
        {"sub": uid, "type": "access", "iat": now, "exp": now + 600, "roles": ["system_admin"]},
        settings.jwt_secret_key, "HS256",
    )
    assert api.request("GET", "/users", token=forged).status_code == 403


def test_admin_can_list_users_without_password_data(api, make_user):
    token = _admin(api, make_user)
    make_user("aisha@demo")
    resp = api.request("GET", "/users", token=token)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2 and {u["email"] for u in body["items"]} == {"dev@demo", "aisha@demo"}
    assert "password" not in resp.text and "hash" not in resp.text
    assert api.request("GET", "/users?limit=1&offset=1", token=token).json()["items"].__len__() == 1


def test_create_user_sends_invite_and_new_user_sets_password(api, make_user, pg):
    token = _admin(api, make_user)
    dept, roles = _ids(pg)
    resp = api.request("POST", "/users", token=token, json={
        "email": "  New.Person@Demo ", "full_name": "New Person", "department_id": dept,
        "clearance_level": 2, "country": "in", "employment_type": "contractor"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "new.person@demo" and body["country"] == "IN"
    assert body["roles"] == ["employee"]  # default role
    mail = api.get_mail("new.person@demo")
    link_token = re.search(r"#token=([A-Za-z0-9_\-]+)", mail).group(1)
    # cannot log in until they set a password
    assert api.login("new.person@demo", password="anything-at-all-123").status_code == 401
    done = api.request("POST", "/auth/reset-password",
                       json={"token": link_token, "new_password": "my-own-new-password-1"})
    assert done.status_code == 204
    assert api.login("new.person@demo", password="my-own-new-password-1").status_code == 200


def test_create_user_validation_and_duplicates(api, make_user, pg):
    token = _admin(api, make_user)
    dept, _ = _ids(pg)
    base = {"email": "x@demo", "full_name": "X", "department_id": dept, "country": "IN"}
    assert api.request("POST", "/users", token=token, json=base).status_code == 201
    assert api.request("POST", "/users", token=token, json=base).status_code == 409
    assert api.request("POST", "/users", token=token, json={**base, "email": "y@demo", "department_id": 9999}).status_code == 422
    assert api.request("POST", "/users", token=token, json={**base, "email": "y@demo", "clearance_level": 9}).status_code == 422
    assert api.request("POST", "/users", token=token, json={**base, "email": "y@demo", "country": "India"}).status_code == 422
    assert api.request("POST", "/users", token=token, json={**base, "email": "y@demo", "role_ids": [9999]}).status_code == 422


def test_get_and_patch_user(api, make_user, pg):
    token = _admin(api, make_user)
    uid = make_user("aisha@demo")
    dept, _ = _ids(pg)
    resp = api.request("PATCH", f"/users/{uid}", token=token,
                       json={"clearance_level": 3, "department_id": dept, "full_name": "Aisha K"})
    assert resp.status_code == 200
    got = api.request("GET", f"/users/{uid}", token=token).json()
    assert got["clearance_level"] == 3 and got["department"]["name"] == "Finance" and got["full_name"] == "Aisha K"
    missing = api.request("GET", "/users/00000000-0000-0000-0000-000000000000", token=token)
    assert missing.status_code == 404
    assert api.request("GET", "/users/not-a-uuid", token=token).status_code == 422


def test_deactivate_takes_effect_immediately_and_can_be_reversed(api, make_user):
    token = _admin(api, make_user)
    uid = make_user("aisha@demo")
    user_token, user_refresh = api.signed_in("aisha@demo")
    assert api.request("POST", f"/users/{uid}/deactivate", token=token).status_code == 200
    assert api.request("GET", "/auth/me", token=user_token).status_code == 401
    assert api.request("POST", "/auth/refresh", refresh=user_refresh).status_code == 401
    assert api.login("aisha@demo").status_code == 401
    assert api.request("PATCH", f"/users/{uid}", token=token, json={"is_active": True}).status_code == 200
    assert api.login("aisha@demo").status_code == 200


def test_admin_cannot_deactivate_self_or_drop_own_admin_role(api, make_user, pg):
    make_user("dev@demo", roles=("employee", "system_admin"))
    token, _ = api.signed_in("dev@demo")
    me = api.request("GET", "/auth/me", token=token).json()["id"]
    assert api.request("POST", f"/users/{me}/deactivate", token=token).status_code == 400
    assert api.request("PATCH", f"/users/{me}", token=token, json={"is_active": False}).status_code == 400
    _, roles = _ids(pg)
    assert api.request("POST", f"/users/{me}/roles", token=token,
                       json={"role_ids": [roles["employee"]]}).status_code == 400


def test_set_roles_replaces_the_list_and_applies_immediately(api, make_user, pg):
    token = _admin(api, make_user)
    uid = make_user("aisha@demo", roles=("employee",))
    user_token, _ = api.signed_in("aisha@demo")
    _, roles = _ids(pg)
    assert api.request("GET", "/users", token=user_token).status_code == 403
    r = api.request("POST", f"/users/{uid}/roles", token=token,
                    json={"role_ids": [roles["employee"], roles["system_admin"]]})
    assert r.status_code == 200 and r.json()["roles"] == ["employee", "system_admin"]
    assert api.request("GET", "/users", token=user_token).status_code == 200  # same token
    r2 = api.request("POST", f"/users/{uid}/roles", token=token, json={"role_ids": [roles["employee"]]})
    assert r2.json()["roles"] == ["employee"]
    assert api.request("GET", "/users", token=user_token).status_code == 403
    assert api.request("POST", f"/users/{uid}/roles", token=token, json={"role_ids": [9999]}).status_code == 422


def test_roles_and_departments_endpoints(api, make_user):
    token = _admin(api, make_user)
    names = [r["name"] for r in api.request("GET", "/roles", token=token).json()]
    assert names == sorted(names) and "system_admin" in names
    created = api.request("POST", "/roles", token=token, json={"name": "legal_reviewer", "description": "Reviews"})
    assert created.status_code == 201 and created.json()["name"] == "legal_reviewer"
    assert api.request("POST", "/roles", token=token, json={"name": "legal_reviewer"}).status_code == 409
    assert api.request("POST", "/roles", token=token, json={"name": "Bad Name!"}).status_code == 422
    depts = api.request("GET", "/departments", token=token).json()
    assert {d["name"] for d in depts} == {"Engineering", "Finance", "HR"}


def test_demo_password_is_not_hardcoded_in_responses(api, make_user):
    token = _admin(api, make_user)
    assert TEST_PASSWORD not in api.request("GET", "/users", token=token).text

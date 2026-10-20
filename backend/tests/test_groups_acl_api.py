"""Groups, access rules, rule history, access preview, and who may call them."""
import uuid

NOBODY = "00000000-0000-0000-0000-000000000000"


def _doc(api, admin, name="a.txt", body=b"some document text for the tests"):
    r = api.upload(admin, name, body)
    assert r.status_code == 202, r.text
    return r.json()["id"]


def _ready(pg, doc_id):
    pg.execute("update documents set status='READY' where id=%s", (doc_id,))


def _rule(api, token, doc, ptype, pid=None, effect="ALLOW", permission="READ", expires_at=None):
    body = {"principal_type": ptype, "effect": effect, "permission": permission}
    if pid is not None:
        body["principal_id"] = str(pid)
    if expires_at:
        body["expires_at"] = expires_at
    return api.request("POST", f"/documents/{doc}/acl", token=token, json=body)


def _future(hours=24):
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _past():
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()


# ------------------------------------------------------------------ groups

def test_group_routes_are_admin_only(api, make_user, enqueued):
    make_user("aisha@demo")
    token, _ = api.signed_in("aisha@demo")
    calls = [("GET", "/groups"), ("POST", "/groups"), ("GET", "/groups/1"), ("POST", "/groups/1/members"),
             ("DELETE", f"/groups/1/members?user_id={NOBODY}")]
    for method, path in calls:
        assert api.request(method, path).status_code == 401, path
        assert api.request(method, path, token=token, json={} if method == "POST" else None).status_code == 403, path


def test_create_list_and_read_groups(api, admin, make_user):
    r = api.request("POST", "/groups", token=admin, json={"name": "Finance Managers", "description": "demo"})
    assert r.status_code == 201 and r.json()["member_count"] == 0
    assert api.request("POST", "/groups", token=admin, json={"name": "Finance Managers"}).status_code == 409
    assert api.request("POST", "/groups", token=admin, json={"name": "x"}).status_code == 422
    gid = r.json()["id"]
    uid = make_user("pranav@demo")
    added = api.request("POST", f"/groups/{gid}/members", token=admin, json={"user_id": str(uid)})
    assert added.status_code == 200 and [m["email"] for m in added.json()["members"]] == ["pranav@demo"]
    again = api.request("POST", f"/groups/{gid}/members", token=admin, json={"user_id": str(uid)})
    assert again.json()["member_count"] == 1  # adding twice changes nothing
    listing = api.request("GET", "/groups", token=admin).json()
    assert [(g["name"], g["member_count"]) for g in listing] == [("Finance Managers", 1)]
    assert api.request("GET", f"/groups/{gid}", token=admin).json()["members"][0]["full_name"]
    assert api.request("DELETE", f"/groups/{gid}/members?user_id={uid}", token=admin).status_code == 204
    assert api.request("DELETE", f"/groups/{gid}/members?user_id={uid}", token=admin).status_code == 204  # idempotent
    assert api.request("GET", f"/groups/{gid}", token=admin).json()["member_count"] == 0


def test_group_membership_errors(api, admin):
    gid = api.request("POST", "/groups", token=admin, json={"name": "SRE team"}).json()["id"]
    assert api.request("POST", f"/groups/{gid}/members", token=admin, json={"user_id": NOBODY}).status_code == 422
    assert api.request("POST", "/groups/9999/members", token=admin, json={"user_id": NOBODY}).status_code == 404
    assert api.request("GET", "/groups/9999", token=admin).status_code == 404
    assert api.request("DELETE", f"/groups/9999/members?user_id={NOBODY}", token=admin).status_code == 404


# ------------------------------------------------------------------ rules: creating

def test_rules_for_every_principal_type(api, admin, make_user, enqueued):
    doc = _doc(api, admin)
    uid = make_user("pranav@demo")
    gid = api.request("POST", "/groups", token=admin, json={"name": "HR Team"}).json()["id"]
    made = {
        "USER": _rule(api, admin, doc, "USER", uid),
        "ROLE": _rule(api, admin, doc, "ROLE", 1),
        "GROUP": _rule(api, admin, doc, "GROUP", gid),
        "DEPARTMENT": _rule(api, admin, doc, "DEPARTMENT", 2),
        "COMPANY": _rule(api, admin, doc, "COMPANY"),
    }
    assert {k: v.status_code for k, v in made.items()} == {k: 201 for k in made}
    names = {k: v.json()["principal_name"] for k, v in made.items()}
    assert names["USER"].startswith("pranav@demo".split("@")[0].title()) or "pranav@demo" in names["USER"]
    assert names["GROUP"] == "HR Team" and names["COMPANY"] == "Everyone" and names["ROLE"] and names["DEPARTMENT"]
    listed = api.request("GET", f"/documents/{doc}/acl", token=admin).json()
    assert len(listed) == 5 and all(not x["expired"] for x in listed)


def test_bad_principals_are_refused(api, admin, enqueued):
    doc = _doc(api, admin)
    assert _rule(api, admin, doc, "USER", NOBODY).status_code == 422          # no such user
    assert _rule(api, admin, doc, "USER", "not-a-uuid").status_code == 422
    assert _rule(api, admin, doc, "ROLE", 9999).status_code == 422
    assert _rule(api, admin, doc, "GROUP", "abc").status_code == 422
    assert _rule(api, admin, doc, "DEPARTMENT", 9999).status_code == 422
    assert _rule(api, admin, doc, "USER").status_code == 422                  # missing id
    assert _rule(api, admin, doc, "COMPANY", 1).status_code == 422            # COMPANY names nobody
    bad = api.request("POST", f"/documents/{doc}/acl", token=admin,
                      json={"principal_type": "TEAM", "effect": "ALLOW", "permission": "READ"})
    assert bad.status_code == 422
    assert api.request("POST", f"/documents/{doc}/acl", token=admin,
                       json={"principal_type": "COMPANY", "effect": "ALLOW", "permission": "SEARCH"}).status_code == 422
    assert api.request("GET", f"/documents/{doc}/acl", token=admin).json() == []


def test_expiry_must_be_in_the_future_and_duplicates_are_refused(api, admin, enqueued, pg):
    doc = _doc(api, admin)
    assert _rule(api, admin, doc, "COMPANY", expires_at=_past()).status_code == 422
    ok = _rule(api, admin, doc, "COMPANY", expires_at=_future())
    assert ok.status_code == 201 and ok.json()["expires_at"] is not None
    assert _rule(api, admin, doc, "COMPANY", expires_at=_future(2)).status_code == 409  # same rule (expiry is not part of identity)
    assert _rule(api, admin, doc, "COMPANY", effect="DENY").status_code == 201          # a different effect is a different rule
    assert pg.execute("select count(*) from permission_change_events").fetchone()[0] == 2  # the refused ones left no history


# ------------------------------------------------------------------ rules: editing and deleting

def test_patch_and_delete_rules(api, admin, enqueued):
    doc, other = _doc(api, admin, "a.txt"), _doc(api, admin, "b.txt", b"another document body")
    rule = _rule(api, admin, doc, "COMPANY").json()
    patched = api.request("PATCH", f"/documents/{doc}/acl/{rule['id']}", token=admin,
                          json={"effect": "DENY", "expires_at": _future()})
    assert patched.status_code == 200 and patched.json()["effect"] == "DENY" and patched.json()["expires_at"]
    cleared = api.request("PATCH", f"/documents/{doc}/acl/{rule['id']}", token=admin, json={"expires_at": None})
    assert cleared.json()["expires_at"] is None
    assert api.request("PATCH", f"/documents/{doc}/acl/{rule['id']}", token=admin, json={"expires_at": _past()}).status_code == 422
    assert api.request("PATCH", f"/documents/{doc}/acl/{rule['id']}", token=admin, json={"effect": None}).status_code == 422
    other_rule = _rule(api, admin, doc, "COMPANY").json()  # ALLOW COMPANY next to the DENY COMPANY
    assert api.request("PATCH", f"/documents/{doc}/acl/{other_rule['id']}", token=admin, json={"effect": "DENY"}).status_code == 409
    # a rule can only be reached through its own document
    assert api.request("PATCH", f"/documents/{other}/acl/{rule['id']}", token=admin, json={"effect": "ALLOW"}).status_code == 404
    assert api.request("DELETE", f"/documents/{other}/acl/{rule['id']}", token=admin).status_code == 404
    assert api.request("DELETE", f"/documents/{doc}/acl/{rule['id']}", token=admin).status_code == 204
    assert api.request("DELETE", f"/documents/{doc}/acl/{rule['id']}", token=admin).status_code == 404
    assert api.request("PATCH", f"/documents/{doc}/acl/{uuid.uuid4()}", token=admin, json={"effect": "ALLOW"}).status_code == 404


def test_expired_rules_are_flagged_in_the_list(api, admin, enqueued, pg):
    doc = _doc(api, admin)
    _rule(api, admin, doc, "COMPANY")
    pg.execute("update document_acl set expires_at = now() - interval '1 minute'")
    assert api.request("GET", f"/documents/{doc}/acl", token=admin).json()[0]["expired"] is True


# ------------------------------------------------------------------ history

def test_every_change_is_recorded_with_before_and_after(api, admin, make_user, enqueued, pg):
    doc = _doc(api, admin)
    r1 = _rule(api, admin, doc, "COMPANY").json()
    r2 = _rule(api, admin, doc, "DEPARTMENT", 2).json()
    api.request("PATCH", f"/documents/{doc}/acl/{r1['id']}", token=admin, json={"effect": "DENY"})
    api.request("DELETE", f"/documents/{doc}/acl/{r2['id']}", token=admin)
    events = api.request("GET", f"/documents/{doc}/acl/history", token=admin).json()
    assert len(events) == 4
    newest, oldest = events[0], events[-1]
    assert oldest["prev_acl"] == [] and len(oldest["new_acl"]) == 1 and oldest["new_acl"][0]["principal_name"] == "Everyone"
    assert len(newest["prev_acl"]) == 2 and len(newest["new_acl"]) == 1  # the delete
    assert newest["changed_by"]["email"] == "admin@demo"
    assert [e["changed_at"] for e in events] == sorted((e["changed_at"] for e in events), reverse=True)
    assert api.request("GET", f"/documents/{doc}/acl/history?limit=2", token=admin).json().__len__() == 2


def test_rule_and_history_are_saved_together_or_not_at_all(api, admin, enqueued, pg, monkeypatch):
    from app.services import access_service

    doc = _doc(api, admin)

    async def boom(*args, **kwargs):
        raise RuntimeError("history failed")

    monkeypatch.setattr(access_service, "_record", boom)
    try:
        r = _rule(api, admin, doc, "COMPANY")
        assert r.status_code == 500
    except RuntimeError:
        pass  # the test client may re-raise the error instead of answering 500
    assert pg.execute("select count(*) from document_acl").fetchone()[0] == 0  # no rule without its history row


# ------------------------------------------------------------------ who may manage

def test_people_without_manage_get_the_same_404_as_for_a_missing_document(api, admin, make_user, enqueued):
    doc = _doc(api, admin)
    make_user("aisha@demo")
    token, _ = api.signed_in("aisha@demo")
    for method, path, body in [
        ("GET", f"/documents/{doc}/acl", None), ("GET", f"/documents/{NOBODY}/acl", None),
        ("POST", f"/documents/{doc}/acl", {"principal_type": "COMPANY", "effect": "ALLOW", "permission": "READ"}),
        ("POST", f"/documents/{NOBODY}/acl", {"principal_type": "COMPANY", "effect": "ALLOW", "permission": "READ"}),
        ("GET", f"/documents/{doc}/acl/history", None), ("GET", f"/documents/{doc}/access-preview?user_id={NOBODY}", None),
        ("PATCH", f"/documents/{doc}", {"title": "x"}), ("PATCH", f"/documents/{NOBODY}", {"title": "x"}),
    ]:
        resp = api.request(method, path, token=token, json=body)
        assert resp.status_code == 404 and resp.json()["detail"] == "Document not found.", (method, path)
        assert api.request(method, path, json=body).status_code == 401


def test_a_manage_holder_manages_only_that_document_and_cannot_read_it(api, admin, make_user, enqueued, pg):
    doc, other = _doc(api, admin, "a.txt"), _doc(api, admin, "b.txt", b"different document body")
    uid = make_user("manager@demo")
    token, _ = api.signed_in("manager@demo")
    assert api.request("GET", f"/documents/{doc}/acl", token=token).status_code == 404  # not yet
    assert _rule(api, admin, doc, "USER", uid, permission="MANAGE").status_code == 201
    assert api.request("GET", f"/documents/{doc}/acl", token=token).status_code == 200
    assert _rule(api, token, doc, "COMPANY").status_code == 201                          # may add rules
    assert api.request("PATCH", f"/documents/{doc}", token=token, json={"title": "Edited by manager"}).json()["title"] == "Edited by manager"
    assert api.request("GET", f"/documents/{other}/acl", token=token).status_code == 404  # another document
    assert api.request("PATCH", f"/documents/{other}", token=token, json={"title": "x"}).status_code == 404
    for method, path in [("GET", "/documents"), ("GET", f"/documents/{doc}"), ("DELETE", f"/documents/{doc}"),
                         ("POST", f"/documents/{doc}/reindex"), ("GET", "/groups"), ("GET", "/users")]:
        assert api.request(method, path, token=token).status_code == 403, path           # still not an admin
    _ready(pg, doc)
    preview = api.request("GET", f"/documents/{doc}/access-preview?user_id={uid}", token=token).json()
    assert preview["manage"]["allowed"] is True and preview["read"]["allowed"] is True  # COMPANY rule gave READ, not MANAGE
    only_manage = api.request("GET", f"/documents/{doc}/access-preview?user_id={uid}", token=token)
    assert only_manage.status_code == 200


def test_manage_holders_do_not_read_through_manage(api, admin, make_user, enqueued, pg):
    doc = _doc(api, admin)
    _ready(pg, doc)
    uid = make_user("manager@demo")
    _rule(api, admin, doc, "USER", uid, permission="MANAGE")
    p = api.request("GET", f"/documents/{doc}/access-preview?user_id={uid}", token=admin).json()
    assert p["manage"] == {"allowed": True, "code": "ALLOWED"}
    assert p["read"] == {"allowed": False, "code": "NO_ALLOW_RULE"}


def test_deny_manage_stops_a_manager_but_never_the_admin(api, admin, make_user, enqueued):
    doc = _doc(api, admin)
    uid = make_user("manager@demo")
    token, _ = api.signed_in("manager@demo")
    _rule(api, admin, doc, "USER", uid, permission="MANAGE")
    assert api.request("GET", f"/documents/{doc}/acl", token=token).status_code == 200
    _rule(api, admin, doc, "COMPANY", effect="DENY", permission="MANAGE")
    assert api.request("GET", f"/documents/{doc}/acl", token=token).status_code == 404
    assert api.request("GET", f"/documents/{doc}/acl", token=admin).status_code == 200  # the admin can always repair the rules


# ------------------------------------------------------------------ preview and revocation

def test_preview_explains_the_decision_and_revocation_is_instant(api, admin, make_user, enqueued, pg):
    doc = _doc(api, admin)
    _ready(pg, doc)
    uid = make_user("pranav@demo", clearance=2)
    gid = api.request("POST", "/groups", token=admin, json={"name": "Finance Managers"}).json()["id"]
    api.request("POST", f"/groups/{gid}/members", token=admin, json={"user_id": str(uid)})
    url = f"/documents/{doc}/access-preview?user_id={uid}"

    before = api.request("GET", url, token=admin).json()
    assert before["read"] == {"allowed": False, "code": "NO_ALLOW_RULE"} and before["matching_rules"] == []
    assert before["user"]["email"] == "pranav@demo" and "password" not in str(before)

    _rule(api, admin, doc, "GROUP", gid)
    granted = api.request("GET", url, token=admin).json()
    assert granted["read"]["allowed"] is True and len(granted["matching_rules"]) == 1
    assert granted["matching_rules"][0]["principal_name"] == "Finance Managers"

    api.request("DELETE", f"/groups/{gid}/members?user_id={uid}", token=admin)   # revoke
    assert api.request("GET", url, token=admin).json()["read"] == {"allowed": False, "code": "NO_ALLOW_RULE"}

    api.request("POST", f"/groups/{gid}/members", token=admin, json={"user_id": str(uid)})
    pg.execute("update documents set sensitivity_level=3 where id=%s", (doc,))   # clearance gate
    assert api.request("GET", url, token=admin).json()["read"]["code"] == "CLEARANCE_TOO_LOW"
    _rule(api, admin, doc, "USER", uid, effect="DENY")
    assert api.request("GET", url, token=admin).json()["read"]["code"] == "DENIED_BY_RULE"

    assert api.request("GET", f"/documents/{doc}/access-preview?user_id={NOBODY}", token=admin).status_code == 404
    assert api.request("GET", f"/documents/{doc}/access-preview", token=admin).status_code == 422


def test_system_admin_is_not_a_reader_in_the_preview(api, admin, enqueued, pg):
    doc = _doc(api, admin)
    _ready(pg, doc)
    _rule(api, admin, doc, "COMPANY")  # everybody may read
    admin_id = pg.execute("select id from users where email='admin@demo'").fetchone()[0]
    p = api.request("GET", f"/documents/{doc}/access-preview?user_id={admin_id}", token=admin).json()
    assert p["manage"]["allowed"] is True and p["manage"]["code"] == "ALLOWED"
    assert p["read"]["allowed"] is True          # allowed only because of the COMPANY rule and clearance...
    pg.execute("delete from document_acl")
    p2 = api.request("GET", f"/documents/{doc}/access-preview?user_id={admin_id}", token=admin).json()
    assert p2["read"] == {"allowed": False, "code": "NO_ALLOW_RULE"} and p2["manage"]["allowed"] is True


# ------------------------------------------------------------------ nothing leaks

def test_access_responses_never_carry_document_text(api, admin, enqueued, pg):
    from app.scripts import synthetic_docs as sd

    s = next(x for x in sd.SAMPLES if x.filename == "salary-bands-2026.docx")
    doc = api.upload(admin, s.filename, sd.build(s), sensitivity_level=3).json()["id"]
    _ready(pg, doc)
    _rule(api, admin, doc, "COMPANY")
    admin_id = pg.execute("select id from users where email='admin@demo'").fetchone()[0]
    for path in (f"/documents/{doc}/acl", f"/documents/{doc}/acl/history", f"/documents/{doc}/access-preview?user_id={admin_id}"):
        body = api.request("GET", path, token=admin).text
        assert s.canary not in body and "Band L1" not in body


def test_openapi_schemas_for_access_have_no_text_fields(client):
    schemas = client.get("/api/openapi.json").json()["components"]["schemas"]
    for name in ("AclOut", "HistoryOut", "PreviewOut", "GroupDetail", "DecisionOut"):
        assert not (set(schemas[name]["properties"]) & {"content", "text", "chunks", "preview", "snippet"}), name

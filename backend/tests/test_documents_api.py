"""Admin documents API: who may call it, what upload accepts and rejects, and what is never returned."""
import json

from app.scripts import synthetic_docs as sd
from app.core.config import settings


def _sample(name):
    return next(s for s in sd.SAMPLES if s.filename == name)


def _upload(api, admin, name="leave-policy.md", **fields):
    s = _sample(name)
    return api.upload(admin, s.filename, sd.build(s), **fields)


# ---------------------------------------------------------------- who may call

def test_every_document_route_needs_sign_in_and_the_admin_role(api, make_user):
    make_user("aisha@demo", roles=("employee",))
    make_user("nina@demo", roles=("employee", "auditor"))
    routes = [
        ("GET", "/documents"), ("GET", "/documents/00000000-0000-0000-0000-000000000000"),
        ("PATCH", "/documents/00000000-0000-0000-0000-000000000000"),
        ("DELETE", "/documents/00000000-0000-0000-0000-000000000000"),
        ("GET", "/documents/00000000-0000-0000-0000-000000000000/versions"),
        ("POST", "/documents/00000000-0000-0000-0000-000000000000/reindex"),
        ("GET", "/ingestion/jobs"), ("GET", "/ingestion/jobs/00000000-0000-0000-0000-000000000000"),
    ]
    for method, path in routes:
        assert api.request(method, path).status_code == 401, (method, path)
    for email in ("aisha@demo", "nina@demo"):
        token, _ = api.signed_in(email)
        for method, path in routes:
            # Editing metadata needs MANAGE on the document (Phase 4B): without it the answer is the same
            # "Document not found" as for a missing document. Every other route needs the admin role.
            expected = 404 if method == "PATCH" else 403
            assert api.request(method, path, token=token, json={} if method == "PATCH" else None).status_code == expected, (email, method, path)
        assert api.upload(token, "a.txt", b"hello").status_code == 403
    assert api.upload(None, "a.txt", b"hello").status_code == 401


# ---------------------------------------------------------------- upload happy path

def test_upload_creates_document_version_and_queued_job(api, admin, enqueued, pg):
    resp = _upload(api, admin, title="  Leave policy  ", sensitivity_level=2, allowed_countries="in, us")
    assert resp.status_code == 202, resp.text
    d = resp.json()
    assert d["title"] == "Leave policy" and d["status"] == "QUEUED"
    assert d["sensitivity_level"] == 2 and d["sensitivity_name"] == "CONFIDENTIAL"
    assert d["allowed_countries"] == ["IN", "US"]
    assert d["chunk_count"] == 0 and d["version_count"] == 1 and d["current_version_no"] is None
    assert d["latest_job"]["status"] == "QUEUED" and d["uploaded_by"]["full_name"]
    assert enqueued == [__import__("uuid").UUID(d["latest_job"]["id"])]
    assert pg.execute("select count(*) from documents").fetchone()[0] == 1
    assert pg.execute("select count(*) from document_versions").fetchone()[0] == 1


def test_original_is_stored_under_an_id_and_hash_key_not_the_file_name(api, admin, enqueued, pg):
    from app.storage import get_storage

    resp = _upload(api, admin, name="salary-bands-2026.docx")
    doc_id = resp.json()["id"]
    keys = get_storage().list_keys("documents/")
    assert len(keys) == 1 and keys[0].startswith(f"documents/{doc_id}/v1/")
    assert "salary" not in keys[0] and ".docx" not in keys[0]
    row = pg.execute("select storage_path, content_hash, size_bytes from document_versions").fetchone()
    assert row[0] == keys[0] and keys[0].endswith(row[1])


def test_upload_response_and_list_never_contain_document_text(api, admin, enqueued):
    s = _sample("salary-bands-2026.docx")
    resp = api.upload(admin, s.filename, sd.build(s), sensitivity_level=3)
    listing = api.request("GET", "/documents", token=admin)
    for body in (resp.text, listing.text):
        assert s.canary not in body and "Band L1" not in body
    assert "content" not in json.dumps(listing.json()["items"][0]).replace("content_type", "")


def test_openapi_has_no_field_that_could_carry_document_text(client):
    spec = client.get("/api/openapi.json").json()
    for name, schema in spec["components"]["schemas"].items():
        if name in ("DocumentOut", "DocumentPage", "JobOut", "VersionOut"):
            props = set(schema.get("properties", {}))
            assert not (props & {"content", "text", "chunks", "preview", "snippet", "download_url", "storage_path"}), name


def test_no_route_returns_the_original_file_or_chunks(client):
    paths = client.get("/api/openapi.json").json()["paths"]
    for p in paths:
        if p.endswith("/access-preview"):  # explains an ACCESS decision (codes and rules); carries no content (own test)
            continue
        assert "chunk" not in p and "download" not in p and "preview" not in p, p


# ---------------------------------------------------------------- upload rejections

def test_wrong_files_are_rejected_with_a_code_and_nothing_is_stored(api, admin, enqueued, pg):
    from app.storage import get_storage

    cases = [
        ("virus.exe", b"MZ....", "UNSUPPORTED_TYPE"),
        ("report.pdf.exe", b"%PDF-1.4 x", "UNSUPPORTED_TYPE"),
        ("fake.pdf", b"plain text", "UNSUPPORTED_TYPE"),
        ("fake.docx", sd.fake_docx(), "UNSUPPORTED_TYPE"),
        ("binary.txt", b"a\x00b", "UNSUPPORTED_TYPE"),
        ("empty.txt", b"", "EMPTY"),
        ("bomb.docx", sd.zip_bomb_docx(20), "TOO_LARGE"),
    ]
    for name, data, code in cases:
        r = api.upload(admin, name, data)
        assert r.status_code in (413, 422), (name, r.status_code)
        assert r.json()["error_code"] == code, name
    assert pg.execute("select count(*) from documents").fetchone()[0] == 0
    assert get_storage().list_keys("documents/") == [] and enqueued == []


def test_oversize_upload_is_rejected_with_413(api, admin, enqueued, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 2048)
    r = api.upload(admin, "big.txt", b"x" * 5000)
    assert r.status_code == 413 and r.json()["error_code"] == "TOO_LARGE"


def test_hostile_file_name_is_cleaned(api, admin, enqueued):
    # (control characters in names are covered by the clean_filename unit test; HTTP clients escape them)
    r = api.upload(admin, "../../etc/passwd.txt", b"hello world")
    assert r.status_code == 202 and r.json()["original_filename"] == "passwd.txt"
    r2 = api.upload(admin, "..\\..\\windows\\evil.txt", b"another text body")
    assert r2.status_code == 202 and r2.json()["original_filename"] == "evil.txt"


def test_invalid_metadata_is_rejected(api, admin, enqueued):
    ok = b"hello world text"
    assert api.upload(admin, "a.txt", ok, department_id=999).status_code == 422
    assert api.upload(admin, "a.txt", ok, document_type="MEMO").status_code == 422
    assert api.upload(admin, "a.txt", ok, sensitivity_level=9).status_code == 422
    assert api.upload(admin, "a.txt", ok, allowed_countries="India").status_code == 422
    assert api.request("POST", "/documents/upload", token=admin, files={"file": ("a.txt", ok)}).status_code == 422  # no metadata


def test_identical_content_is_refused_as_a_duplicate(api, admin, enqueued):
    first = _upload(api, admin)
    second = _upload(api, admin, title="Same file again")
    assert second.status_code == 409 and second.json()["existing_document_id"] == first.json()["id"]
    assert len(enqueued) == 1


def test_uploads_are_rate_limited(api, admin, enqueued, monkeypatch):
    monkeypatch.setattr(settings, "upload_limit_per_minute", 3)
    codes = [api.upload(admin, f"f{i}.txt", f"text number {i}".encode()).status_code for i in range(5)]
    assert codes == [202, 202, 202, 429, 429]


# ---------------------------------------------------------------- read, edit, delete

def test_list_get_filter_and_pagination(api, admin, enqueued):
    for i in range(3):
        api.upload(admin, f"d{i}.txt", f"document body {i}".encode(), department_id=1 + (i % 2))
    page = api.request("GET", "/documents?limit=2&offset=0", token=admin).json()
    assert page["total"] == 3 and len(page["items"]) == 2 and page["limit"] == 2
    only_dept = api.request("GET", "/documents?department_id=1", token=admin).json()
    assert only_dept["total"] == 2
    assert api.request("GET", "/documents?status=READY", token=admin).json()["total"] == 0
    assert api.request("GET", "/documents?status=NOPE", token=admin).status_code == 422
    one = api.request("GET", f"/documents/{page['items'][0]['id']}", token=admin)
    assert one.status_code == 200 and one.json()["id"] == page["items"][0]["id"]
    assert api.request("GET", "/documents/not-a-uuid", token=admin).status_code == 422


def test_patch_changes_metadata_only(api, admin, enqueued):
    d = _upload(api, admin).json()
    r = api.request("PATCH", f"/documents/{d['id']}", token=admin, json={
        "title": "New title", "sensitivity_level": 3, "document_type": "report", "department_id": 2,
        "allowed_countries": ["in"]})
    assert r.status_code == 200, r.text
    b = r.json()
    assert (b["title"], b["sensitivity_level"], b["document_type"], b["department"]["id"], b["allowed_countries"]) == (
        "New title", 3, "REPORT", 2, ["IN"])
    assert api.request("PATCH", f"/documents/{d['id']}", token=admin, json={"department_id": 999}).status_code == 422
    assert api.request("PATCH", f"/documents/{d['id']}", token=admin, json={"sensitivity_level": 7}).status_code == 422
    cleared = api.request("PATCH", f"/documents/{d['id']}", token=admin, json={"allowed_countries": None}).json()
    assert cleared["allowed_countries"] is None


def test_soft_delete_hides_the_document_and_keeps_the_row(api, admin, enqueued, pg):
    d = _upload(api, admin).json()
    assert api.request("DELETE", f"/documents/{d['id']}", token=admin).status_code == 204
    assert api.request("GET", f"/documents/{d['id']}", token=admin).status_code == 404
    assert api.request("GET", "/documents", token=admin).json()["total"] == 0
    assert pg.execute("select deleted_at is not null from documents").fetchone()[0] is True
    assert api.request("DELETE", f"/documents/{d['id']}", token=admin).status_code == 404
    again = _upload(api, admin)  # same content can be uploaded again after deleting
    assert again.status_code == 202


def test_versions_and_jobs_endpoints(api, admin, enqueued):
    d = _upload(api, admin).json()
    versions = api.request("GET", f"/documents/{d['id']}/versions", token=admin).json()
    assert len(versions) == 1 and versions[0]["version_no"] == 1 and "storage_path" not in versions[0]
    jobs = api.request("GET", "/ingestion/jobs", token=admin).json()
    assert jobs["total"] == 1 and jobs["items"][0]["status"] == "QUEUED"
    assert api.request("GET", f"/ingestion/jobs/{jobs['items'][0]['id']}", token=admin).status_code == 200
    assert api.request("GET", "/ingestion/jobs?status=FAILED", token=admin).json()["total"] == 0
    assert api.request("GET", "/ingestion/jobs/00000000-0000-0000-0000-000000000000", token=admin).status_code == 404


def test_jobs_can_be_filtered_by_document(api, admin, enqueued):
    a = api.upload(admin, "a.txt", b"first document text").json()
    b = api.upload(admin, "b.txt", b"second document text").json()
    all_jobs = api.request("GET", "/ingestion/jobs", token=admin).json()
    assert all_jobs["total"] == 2
    only_a = api.request("GET", f"/ingestion/jobs?document_id={a['id']}", token=admin).json()
    assert only_a["total"] == 1 and only_a["items"][0]["document_id"] == a["id"]
    assert b["id"] != a["id"]
    assert api.request("GET", "/ingestion/jobs?document_id=not-a-uuid", token=admin).status_code == 422


def test_reindex_is_refused_while_a_job_is_unfinished(api, admin, enqueued):
    d = _upload(api, admin).json()
    r = api.request("POST", f"/documents/{d['id']}/reindex", token=admin)
    assert r.status_code == 409  # the first job is still QUEUED
    assert len(enqueued) == 1


# ---------------------------------------------------------------- notifications

def test_notifications_are_private_to_their_owner(api, admin, make_user, pg):
    other_id = make_user("other@demo", roles=("employee",))
    admin_id = pg.execute("select id from users where email='admin@demo'").fetchone()[0]
    pg.execute("insert into notifications (user_id, kind, payload) values (%s, 'INGESTION_FAILED', '{}')", (admin_id,))
    pg.execute("insert into notifications (user_id, kind, payload) values (%s, 'INGESTION_FAILED', '{}')", (other_id,))
    mine = api.request("GET", "/notifications", token=admin).json()
    assert len(mine) == 1
    nid = mine[0]["id"]
    other_token, _ = api.signed_in("other@demo")
    theirs = api.request("GET", "/notifications", token=other_token).json()
    assert len(theirs) == 1 and theirs[0]["id"] != nid
    assert api.request("POST", f"/notifications/{nid}/read", token=other_token).status_code == 404  # not theirs
    assert api.request("POST", f"/notifications/{nid}/read", token=admin).json()["read_at"] is not None
    assert api.request("GET", "/notifications?unread_only=true", token=admin).json() == []
    assert api.request("GET", "/notifications").status_code == 401

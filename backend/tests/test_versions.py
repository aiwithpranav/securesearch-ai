"""Phase 8A: new versions of a document, "same content means nothing to do", and restoring a deleted document.

Proven here: a new version is stored and indexed without touching access rules; the old version keeps answering
until the new one is complete, then the swap is whole; identical content is skipped; duplicates of other documents,
busy documents, deleted documents and bad files are refused with nothing stored; a restored document comes back with
the same rules but is not searchable until it has been re-indexed; and the date shown with a passage is the date
of the version it came from."""
import uuid

import pytest

from app.ingest.pipeline import run_ingestion
from app.llm import set_llm
from app.retrieval.reranker import set_reranker
from app.storage import get_storage
from tests.access_world import World
from tests.test_answers import FakeLlm, OverlapReranker

V1 = b"Leave policy, version one. Employees receive 24 days of paid annual leave every year.\n"
V2 = b"Leave policy, version two. Employees receive 26 days of paid annual leave every year.\n"
V3 = b"Another document altogether about the office canteen opening hours and menu choices.\n"


def upload(api, admin, data=V1, name="leave.txt"):
    r = api.upload(admin, name, data)
    assert r.status_code == 202, r.text
    d = r.json()
    return d["id"], uuid.UUID(d["latest_job"]["id"])


def new_version(api, admin, doc_id, data, name="leave.txt"):
    return api.request("POST", f"/documents/{doc_id}/versions", token=admin, files={"file": (name, data, "application/octet-stream")})


def chunks(pg, doc_id):
    rows = pg.execute(
        "select v.version_no, c.is_active, count(*) from document_chunks c join document_versions v on v.id = c.document_version_id "
        "where c.document_id = %s group by 1, 2 order by 1, 2", (doc_id,)
    ).fetchall()
    return {(v, a): n for v, a, n in rows}


@pytest.fixture(autouse=True)
def fakes():
    set_reranker(OverlapReranker())
    set_llm(FakeLlm())
    yield
    set_reranker(None)
    set_llm(None)


@pytest.fixture
def ready(api, admin, enqueued):
    doc_id, job = upload(api, admin)
    assert run_ingestion(job) == "READY"
    return doc_id


# ---------------------------------------------------------------- who may call

def test_new_version_and_restore_need_sign_in_and_the_admin_role(api, make_user):
    make_user("aisha@demo", roles=("employee",))
    make_user("nina@demo", roles=("employee", "auditor"))
    nil = "00000000-0000-0000-0000-000000000000"
    for email in (None, "aisha@demo", "nina@demo"):
        token = api.signed_in(email)[0] if email else None
        for path in (f"/documents/{nil}/versions", f"/documents/{nil}/restore"):
            kw = {"files": {"file": ("a.txt", b"hello", "text/plain")}} if path.endswith("versions") else {}
            assert api.request("POST", path, token=token, **kw).status_code == (403 if email else 401), (email, path)


# ---------------------------------------------------------------- a new version

def test_a_new_version_is_stored_and_queued_and_the_old_one_keeps_answering(api, admin, enqueued, pg, ready):
    r = new_version(api, admin, ready, V2)
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["result"] == "CREATED" and body["version_no"] == 2
    d = body["document"]
    assert d["status"] == "READY" and d["version_count"] == 2 and d["current_version_no"] == 1  # still serving version 1
    assert d["latest_job"]["status"] == "QUEUED" and len(enqueued) == 2
    old = chunks(pg, ready)
    assert old.get((1, True), 0) >= 1 and (2, True) not in old  # nothing of version 2 is searchable yet
    assert len(get_storage().list_keys(f"documents/{ready}/")) == 2


def test_when_the_new_version_is_ready_the_swap_is_whole(api, admin, enqueued, pg, ready):
    new_version(api, admin, ready, V2)
    assert run_ingestion(enqueued[-1]) == "READY"
    c = chunks(pg, ready)
    assert c.get((2, True), 0) >= 1 and (1, True) not in c and c.get((1, False), 0) >= 1  # old passages switched off, kept for history
    d = api.request("GET", f"/documents/{ready}", token=admin).json()
    assert d["current_version_no"] == 2 and d["version_count"] == 2 and d["status"] == "READY"
    assert pg.execute("select count(*) from document_chunks where is_active and content like '%24 days%'").fetchone()[0] == 0
    assert pg.execute("select count(*) from document_chunks where is_active and content like '%26 days%'").fetchone()[0] >= 1


def test_the_same_content_as_the_newest_version_does_nothing(api, admin, enqueued, pg, ready):
    r = new_version(api, admin, ready, V1)
    assert r.status_code == 200 and r.json()["result"] == "UNCHANGED" and r.json()["version_no"] == 1
    assert pg.execute("select count(*) from document_versions").fetchone()[0] == 1
    assert pg.execute("select count(*) from ingestion_jobs").fetchone()[0] == 1 and len(enqueued) == 1
    assert len(get_storage().list_keys(f"documents/{ready}/")) == 1


def test_going_back_to_older_content_is_a_new_version(api, admin, enqueued, pg, ready):
    new_version(api, admin, ready, V2)
    run_ingestion(enqueued[-1])
    r = new_version(api, admin, ready, V1)  # V1 is no longer the newest content
    assert r.status_code == 202 and r.json()["version_no"] == 3
    run_ingestion(enqueued[-1])
    assert pg.execute("select count(*) from document_chunks where is_active and content like '%24 days%'").fetchone()[0] >= 1


def test_a_new_version_does_not_touch_the_access_rules_or_metadata(api, admin, enqueued, pg, ready):
    w = World(pg)
    w.acl(ready, ("ROLE", "employee"))
    before = pg.execute("select principal_type, principal_id, effect, permission from document_acl order by 1,2,3,4").fetchall()
    meta = pg.execute("select title, department_id, sensitivity_level, document_type from documents").fetchone()
    new_version(api, admin, ready, V2, name="leave-2027.txt")
    run_ingestion(enqueued[-1])
    assert pg.execute("select principal_type, principal_id, effect, permission from document_acl order by 1,2,3,4").fetchall() == before
    assert pg.execute("select title, department_id, sensitivity_level, document_type from documents").fetchone() == meta
    assert pg.execute("select count(*) from permission_change_events").fetchone()[0] == 0


# ---------------------------------------------------------------- refusals

def test_content_that_belongs_to_another_document_is_refused(api, admin, enqueued, pg, ready):
    other, job = upload(api, admin, V3, "canteen.txt")
    r = new_version(api, admin, ready, V3)
    assert r.status_code == 409 and r.json()["existing_document_id"] == other
    assert pg.execute("select count(*) from document_versions where document_id = %s", (ready,)).fetchone()[0] == 1


def test_a_document_that_is_still_being_processed_refuses_a_new_version(api, admin, enqueued, pg):
    doc_id, _ = upload(api, admin)  # its first job is still QUEUED
    assert new_version(api, admin, doc_id, V2).status_code == 409
    assert pg.execute("select count(*) from document_versions").fetchone()[0] == 1 and len(get_storage().list_keys("documents/")) == 1


def test_missing_deleted_and_bad_files_are_refused_and_nothing_is_stored(api, admin, enqueued, pg, ready):
    keys = get_storage().list_keys("documents/")
    assert new_version(api, admin, str(uuid.uuid4()), V2).status_code == 404
    assert new_version(api, admin, ready, b"MZ....", "virus.exe").status_code == 422
    assert new_version(api, admin, ready, b"", "empty.txt").status_code == 422
    assert api.request("DELETE", f"/documents/{ready}", token=admin).status_code == 204
    assert new_version(api, admin, ready, V2).status_code == 404
    assert get_storage().list_keys("documents/") == keys
    assert pg.execute("select count(*) from document_versions").fetchone()[0] == 1


def test_a_failed_database_step_leaves_no_orphan_file(api, admin, enqueued, pg, ready, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    async def failing_commit(self):
        raise RuntimeError("commit failed")

    keys = get_storage().list_keys("documents/")
    monkeypatch.setattr(AsyncSession, "commit", failing_commit)
    with pytest.raises(RuntimeError):
        new_version(api, admin, ready, V2)
    monkeypatch.undo()
    assert get_storage().list_keys("documents/") == keys


# ---------------------------------------------------------------- restore

def test_a_deleted_document_can_be_listed_and_restored_with_its_rules(api, admin, enqueued, pg, ready):
    World(pg).acl(ready, ("ROLE", "employee"))
    rules = pg.execute("select count(*) from document_acl").fetchone()[0]
    assert api.request("DELETE", f"/documents/{ready}", token=admin).status_code == 204
    assert api.request("GET", "/documents", token=admin).json()["total"] == 0
    gone = api.request("GET", "/documents?deleted=true", token=admin).json()
    assert gone["total"] == 1 and gone["items"][0]["id"] == ready and gone["items"][0]["deleted_at"] is not None

    r = api.request("POST", f"/documents/{ready}/restore", token=admin)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["deleted_at"] is None and d["status"] == "QUEUED" and d["latest_job"]["status"] == "QUEUED"
    assert pg.execute("select count(*) from document_acl").fetchone()[0] == rules  # same rules as before
    assert api.request("GET", "/documents?deleted=true", token=admin).json()["total"] == 0
    assert chunks(pg, ready).get((1, True), 0) == 0  # not searchable until it is indexed again
    assert run_ingestion(enqueued[-1]) == "READY"
    assert chunks(pg, ready).get((1, True), 0) >= 1
    assert api.request("GET", f"/documents/{ready}", token=admin).json()["status"] == "READY"


def test_restore_refuses_a_live_document_an_unknown_one_and_duplicate_content(api, admin, enqueued, pg, ready):
    assert api.request("POST", f"/documents/{ready}/restore", token=admin).status_code == 409  # not deleted
    assert api.request("POST", f"/documents/{uuid.uuid4()}/restore", token=admin).status_code == 404
    api.request("DELETE", f"/documents/{ready}", token=admin)
    upload(api, admin, V1, "copy.txt")  # the same content is now live in another document
    r = api.request("POST", f"/documents/{ready}/restore", token=admin)
    assert r.status_code == 409 and "identical" in r.json()["detail"]
    assert pg.execute("select deleted_at is not null from documents where id = %s", (ready,)).fetchone()[0] is True


def test_a_deleted_document_stays_out_of_search_even_with_rules(api, admin, enqueued, pg, make_user, ready):
    make_user("reader@demo")
    reader = api.signed_in("reader@demo")[0]
    World(pg).acl(ready, ("ROLE", "employee"))
    found = lambda: api.request("POST", "/search", token=reader, json={"query": "annual leave"}).json()["count"]  # noqa: E731
    assert found() >= 1
    api.request("DELETE", f"/documents/{ready}", token=admin)
    assert found() == 0


# ---------------------------------------------------------------- the date shown with a passage

def test_the_date_of_a_passage_is_the_date_of_its_version(api, admin, enqueued, pg, make_user, ready):
    make_user("reader@demo")
    reader = api.signed_in("reader@demo")[0]
    World(pg).acl(ready, ("ROLE", "employee"))
    new_version(api, admin, ready, V2)
    run_ingestion(enqueued[-1])
    pg.execute("update document_versions set created_at = '2020-01-01T00:00:00Z' where version_no = 2")
    body = api.request("POST", "/chat", token=reader, json={"question": "How many days of annual leave do employees receive?"}).json()
    cite = body["citations"][0]
    assert cite["document_updated_at"].startswith("2020-01-01")  # not the (recent) time the document row last changed
    preview = api.request("GET", f"/chunks/{cite['chunk_id']}/preview", token=reader).json()
    assert preview["document_updated_at"].startswith("2020-01-01") and "26 days" in preview["content"]

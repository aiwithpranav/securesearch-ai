"""Phase 7A: the audit trail. Who asked what, what happened, what administrators changed, and who may read it.

Proven here: every search and answer leaves one row (ids and code words, never an answer or document text); the
rows cannot be changed or deleted; no audit means no answer; only the security_admin and auditor roles can read the
trail (not the system_admin); filters, paging and a spreadsheet-safe CSV export work; security events are recorded
with ids only; and forbidden text never reaches any audit table."""
import csv
import io
import re
import json
import uuid

import psycopg
import pytest

from app.answers.service import REFUSAL_TEXT
from app.audit import service as audit_service
from app.audit.service import csv_safe
from app.core.config import settings
from app.llm import set_llm
from app.retrieval.reranker import set_reranker
from tests.access_world import World
from tests.retrieval_world import add_chunks
from tests.test_answers import LEAVE, SECRET, VPN, FakeLlm, OverlapReranker

QUESTION = "How many days of annual leave do employees receive?"
ANSWER_TEXT = "Answer based on the first source [S1]."


@pytest.fixture(autouse=True)
def fakes():
    set_reranker(OverlapReranker())
    set_llm(FakeLlm())
    yield
    set_reranker(None)
    set_llm(None)


@pytest.fixture
def world(pg):
    w = World(pg)
    docs, chunks = {}, {}
    for name, text in (("leave", LEAVE), ("vpn", VPN)):
        d = w.doc(filename=f"{name}.txt")
        w.acl(d, ("ROLE", "employee"))
        chunks[name] = add_chunks(pg, d, [text])[0]
        docs[name] = d
    hidden = w.doc(filename="salary.txt")
    chunks["hidden"] = add_chunks(pg, hidden, [SECRET])[0]
    docs["hidden"] = hidden
    return w, docs, chunks


@pytest.fixture
def people(api, make_user):
    ids = {
        "reader": make_user("reader@demo"),
        "security": make_user("sec@demo", roles=("employee", "security_admin")),
        "auditor": make_user("aud@demo", roles=("employee", "auditor")),
        "admin": make_user("boss@demo", roles=("employee", "system_admin")),
    }
    tokens = {name: api.signed_in(f"{email}@demo" if "@" not in email else email)[0] for name, email in
              (("reader", "reader"), ("security", "sec"), ("auditor", "aud"), ("admin", "boss"))}
    return ids, tokens


def search(api, token, query="annual leave days"):
    return api.request("POST", "/search", token=token, json={"query": query})


def chat(api, token, question=QUESTION):
    return api.request("POST", "/chat", token=token, json={"question": question})


def rows(pg, table):
    cur = pg.execute(f"select * from {table}")
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


# ---------------------------------------------------------------- csv safety (pure)

@pytest.mark.parametrize("value, expected", [
    ("=SUM(A1)", "'=SUM(A1)"), ("+1", "'+1"), ("-1", "'-1"), ("@cmd", "'@cmd"), ("\tx", "'\tx"), ("\rx", "'\rx"),
    ("normal", "normal"), ("", ""), (None, ""), (7, "7"),
])
def test_csv_cells_that_could_run_as_formulas_are_defused(value, expected):
    assert csv_safe(value) == expected


# ---------------------------------------------------------------- the trail is written

def test_a_search_leaves_one_audit_row_with_ids_and_counts(api, people, world, pg):
    ids, tokens = people
    _, docs, chunks = world
    body = search(api, tokens["reader"]).json()
    (row,) = rows(pg, "query_audit_logs")
    assert str(row["user_id"]) == ids["reader"] and row["kind"] == "SEARCH" and row["query_text"] == "annual leave days"
    assert row["filters"] == {"mode": settings.retrieval_mode} and row["response_status"] == "OK"
    assert row["allowed_doc_count"] == 2  # leave and vpn; the salary document is not readable
    assert {str(c) for c in row["retrieved_chunk_ids"]} == {h["chunk_id"] for h in body["hits"]}
    assert str(chunks["hidden"]) not in {str(c) for c in row["retrieved_chunk_ids"]}
    assert row["latency_ms"] >= 0 and row["request_id"]


def test_a_search_with_no_results_is_audited_as_no_results(api, people, world, pg):
    _, tokens = people
    assert search(api, tokens["reader"], "zzzqqq").json()["count"] >= 0
    pg.execute("delete from document_chunks")  # nothing left to find
    search(api, tokens["reader"], "annual leave days")
    assert [r["response_status"] for r in rows(pg, "query_audit_logs")][-1] == "NO_RESULTS"


def test_an_answer_leaves_a_query_row_and_an_answer_row_without_the_answer_text(api, people, world, pg):
    ids, tokens = people
    body = chat(api, tokens["reader"]).json()
    (q,) = rows(pg, "query_audit_logs")
    (a,) = rows(pg, "answer_audit_logs")
    assert q["kind"] == "CHAT" and q["response_status"] == "ANSWERED" and q["query_text"] == QUESTION and q["allowed_doc_count"] == 2
    assert a["query_audit_id"] == q["id"] and {str(c) for c in a["citation_chunk_ids"]} == {c["chunk_id"] for c in body["citations"]}
    assert a["model"] == settings.llm_model and len(a["prompt_version"]) == 8
    assert (a["llm_calls"], a["input_tokens"], a["output_tokens"]) == (1, 100, 20) and a["answer_chars"] == len(body["answer"])
    assert a["refusal_reason"] is None
    assert q["retrieved_chunk_ids"] and {str(c) for c in a["citation_chunk_ids"]} <= {str(c) for c in q["retrieved_chunk_ids"]}  # cited passages were retrieved
    everything = json.dumps([q, a], default=str)
    assert ANSWER_TEXT not in everything and body["answer"] not in everything and "24 days" not in everything


def test_a_refusal_is_audited_with_a_code_word_and_no_text(api, people, world, pg):
    _, tokens = people
    body = chat(api, tokens["reader"], "quantum teleportation laboratory schedule").json()
    assert body["refusal"] == REFUSAL_TEXT
    (q,) = rows(pg, "query_audit_logs")
    (a,) = rows(pg, "answer_audit_logs")
    assert q["response_status"] == "REFUSED_LOW_CONFIDENCE" and a["refusal_reason"] == "WEAK_EVIDENCE"
    assert a["answer_chars"] == 0 and a["citation_chunk_ids"] == [] and a["llm_calls"] == 0
    assert REFUSAL_TEXT not in json.dumps([q, a], default=str)


def test_a_question_the_model_could_not_answer_is_still_audited(api, people, world, pg):
    from app.llm import LlmError

    class Down:
        def complete(self, *a):
            raise LlmError("unavailable")

    _, tokens = people
    set_llm(Down())
    assert chat(api, tokens["reader"]).status_code == 503
    (q,) = rows(pg, "query_audit_logs")
    assert q["response_status"] == "UNAVAILABLE" and q["allowed_doc_count"] == 2 and q["retrieved_chunk_ids"]
    assert rows(pg, "answer_audit_logs") == []


def test_the_stream_is_audited_too(api, people, world, pg):
    _, tokens = people
    r = api.request("POST", "/chat/stream", token=tokens["reader"], json={"question": QUESTION})
    assert r.status_code == 200 and "event: result" in r.text
    assert [q["kind"] for q in rows(pg, "query_audit_logs")] == ["CHAT"] and len(rows(pg, "answer_audit_logs")) == 1


def test_deleting_a_history_item_does_not_touch_the_audit_trail(api, people, world, pg):
    _, tokens = people
    hid = chat(api, tokens["reader"]).json()["history_id"]
    assert api.request("DELETE", f"/me/search-history/{hid}", token=tokens["reader"]).status_code == 204
    assert len(rows(pg, "query_audit_logs")) == 1 and len(rows(pg, "answer_audit_logs")) == 1


# ---------------------------------------------------------------- append-only and fail-closed

@pytest.mark.parametrize("table, sql", [
    ("query_audit_logs", "update query_audit_logs set query_text='changed'"),
    ("query_audit_logs", "delete from query_audit_logs"),
    ("answer_audit_logs", "update answer_audit_logs set model='x'"),
    ("answer_audit_logs", "delete from answer_audit_logs"),
    ("access_events", "update access_events set event='x'"),
    ("access_events", "delete from access_events"),
])
def test_audit_rows_cannot_be_changed_or_deleted_even_by_the_database_user(api, people, world, pg, table, sql):
    _, tokens = people
    chat(api, tokens["reader"])
    assert rows(pg, table), table
    with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        pg.execute(sql)
    assert rows(pg, table)  # still there


@pytest.mark.parametrize("path, body", [("/search", {"query": "annual leave days"}), ("/chat", {"question": QUESTION})])
def test_no_audit_no_answer(api, people, world, monkeypatch, path, body):
    _, tokens = people

    def boom(*a, **k):
        raise RuntimeError("audit store down")

    monkeypatch.setattr(audit_service.QueryAuditLog, "__init__", boom)
    with pytest.raises(RuntimeError, match="audit store down"):  # the test client re-raises; a real server answers 500
        api.request("POST", path, token=tokens["reader"], json=body)
    set_llm(None)  # nothing was returned to the person; and nothing was written



def test_no_audit_no_answer_on_the_stream(api, people, world, monkeypatch):
    _, tokens = people

    def boom(*a, **k):
        raise RuntimeError("audit store down")

    monkeypatch.setattr(audit_service.QueryAuditLog, "__init__", boom)
    r = api.request("POST", "/chat/stream", token=tokens["reader"], json={"question": QUESTION})
    assert "event: result" not in r.text and "24 days" not in r.text and "event: error" in r.text


# ---------------------------------------------------------------- who may read the trail

ROUTES = ["/audit/queries", "/audit/answers", "/audit/access-events", "/audit/export"]


@pytest.mark.parametrize("path", ROUTES)
def test_only_the_audit_roles_may_read_and_the_system_admin_may_not(api, people, world, path):
    _, tokens = people
    search(api, tokens["reader"])
    assert api.request("GET", path).status_code == 401
    assert api.request("GET", path, token="bad").status_code == 401
    assert api.request("GET", path, token=tokens["reader"]).status_code == 403
    assert api.request("GET", path, token=tokens["admin"]).status_code == 403  # admin is not auditor
    assert api.request("GET", path, token=tokens["security"]).status_code == 200
    assert api.request("GET", path, token=tokens["auditor"]).status_code == 200


def test_the_query_list_shows_who_what_when_and_ids_but_no_text_of_documents_or_answers(api, people, world):
    ids, tokens = people
    search(api, tokens["reader"], "annual leave days")
    chat(api, tokens["reader"])
    page = api.request("GET", "/audit/queries", token=tokens["auditor"]).json()
    assert page["total"] == 2 and set(page) == {"items", "total", "limit", "offset"}
    item = page["items"][0]
    assert set(item) == {"id", "created_at", "user", "kind", "query_text", "filters", "allowed_doc_count", "retrieved_chunk_ids", "response_status", "latency_ms", "request_id"}
    assert item["user"] == {"id": ids["reader"], "full_name": "Reader", "email": "reader@demo"}
    text = json.dumps(page)
    assert "24 days" not in text and ANSWER_TEXT not in text and "Employees receive" not in text


def test_filters_paging_and_the_page_cap(api, people, world):
    ids, tokens = people
    for q in ("annual leave days", "vpn login phone", "leave carried over"):
        search(api, tokens["reader"], q)
    chat(api, tokens["reader"])
    search(api, tokens["security"], "company network")
    get = lambda qs: api.request("GET", "/audit/queries" + qs, token=tokens["auditor"]).json()  # noqa: E731
    assert get("")["total"] == 5
    assert get(f"?user_id={ids['security']}")["total"] == 1
    assert get("?kind=CHAT")["total"] == 1 and get("?kind=SEARCH")["total"] == 4
    assert get("?status=ANSWERED")["total"] == 1
    assert [i["query_text"] for i in get("?q=VPN")["items"]] == ["vpn login phone"]  # not case sensitive
    assert get("?q=%25")["total"] == 0  # a percent sign is text, not a wildcard
    assert get("?since=2999-01-01T00:00:00Z")["total"] == 0 and get("?until=2000-01-01T00:00:00Z")["total"] == 0
    page = get("?limit=2&offset=1")
    assert len(page["items"]) == 2 and page["total"] == 5
    assert get("?limit=100000")["limit"] == 200
    assert api.request("GET", "/audit/queries?kind=OTHER", token=tokens["auditor"]).status_code == 422
    assert api.request("GET", "/audit/queries?limit=0", token=tokens["auditor"]).status_code == 422


def test_the_answers_list_links_to_the_query_and_carries_no_answer_text(api, people, world):
    _, tokens = people
    chat(api, tokens["reader"])
    qid = api.request("GET", "/audit/queries?kind=CHAT", token=tokens["auditor"]).json()["items"][0]["id"]
    page = api.request("GET", f"/audit/answers?query_audit_id={qid}", token=tokens["auditor"]).json()
    assert page["total"] == 1
    item = page["items"][0]
    assert item["query_audit_id"] == qid and item["model"] == settings.llm_model and len(item["citation_chunk_ids"]) == 1
    assert set(item) == {"id", "query_audit_id", "created_at", "citation_chunk_ids", "model", "prompt_version", "llm_calls", "input_tokens", "output_tokens", "answer_chars", "refusal_reason"}
    assert ANSWER_TEXT not in json.dumps(page)
    assert api.request("GET", f"/audit/answers?query_audit_id={uuid.uuid4()}", token=tokens["auditor"]).json()["total"] == 0


# ---------------------------------------------------------------- security events

def events(api, token, qs=""):
    return api.request("GET", "/audit/access-events" + qs, token=token).json()


def test_sign_ins_and_failures_are_recorded_without_the_email_or_password(api, make_user, people, pg):
    _, tokens = people
    make_user("lockme@demo")
    api.login("lockme@demo", "WrongPassword123!x")
    api.login("nobody-at-all@demo", "WrongPassword123!x")
    names = [e["event"] for e in events(api, tokens["auditor"])["items"]]
    assert "auth.login_ok" in names and names.count("auth.login_failed") == 2
    text = json.dumps(events(api, tokens["auditor"]))
    assert "WrongPassword" not in text and "nobody-at-all" not in text
    failed = events(api, tokens["auditor"], "?event=auth.login_failed")["items"]
    assert all(e["detail"] == {} for e in failed)
    unknown = [e for e in failed if e["actor"] is None]
    assert len(unknown) == 1  # the unknown address is recorded as nobody, never as the typed text


def test_administrator_changes_are_recorded_with_who_did_it_and_to_whom(api, people, world, make_user):
    ids, tokens = people
    _, docs, _ = world
    rule = api.request("POST", f"/documents/{docs['leave']}/acl", token=tokens["admin"], json={"principal_type": "COMPANY", "effect": "ALLOW", "permission": "DOWNLOAD"})
    assert rule.status_code in (200, 201), rule.text
    group = api.request("POST", "/groups", token=tokens["admin"], json={"name": "Audit Team"}).json()
    api.request("POST", f"/groups/{group['id']}/members", token=tokens["admin"], json={"user_id": ids["reader"]})
    got = {e["event"]: e for e in events(api, tokens["auditor"], "?limit=200")["items"] if e["event"].startswith("admin.")}
    assert {"admin.acl_rule_added", "admin.group_created", "admin.group_member_added"} <= set(got)
    added = got["admin.acl_rule_added"]
    assert added["actor"]["email"] == "boss@demo" and added["detail"]["document_id"] == str(docs["leave"])
    assert added["detail"]["permission"] == "DOWNLOAD" and added["detail"]["effect"] == "ALLOW"
    member = got["admin.group_member_added"]
    assert member["actor"]["email"] == "boss@demo" and member["subject"]["email"] == "reader@demo"


def test_events_can_be_filtered_by_name_and_person(api, people, world):
    ids, tokens = people
    api.login("reader@demo", "bad-password-for-test")
    only = events(api, tokens["auditor"], "?event=auth.login_failed")
    assert only["total"] >= 1 and {e["event"] for e in only["items"]} == {"auth.login_failed"}
    mine = events(api, tokens["auditor"], f"?actor_id={ids['auditor']}")
    assert mine["total"] >= 1 and all(e["actor"]["id"] == ids["auditor"] for e in mine["items"])


def test_only_ids_and_fixed_words_are_ever_stored_in_an_event(pg):
    from app.audit.service import persist_access_event

    persist_access_event(
        "admin.user_updated", "req-1",
        {"actor_id": str(uuid.uuid4()), "user_id": str(uuid.uuid4()), "fields": ["department"], "email": "secret@example.com",
         "password": "hunter2", "note": "free text must not be kept"},
    )
    (row,) = rows(pg, "access_events")
    assert row["detail"] == {"fields": ["department"]}
    assert "secret@example.com" not in json.dumps(row, default=str) and "hunter2" not in json.dumps(row, default=str)
    persist_access_event("search", "req-2", {"user_id": str(uuid.uuid4())})  # the query trail owns searches: not an access event
    assert len(rows(pg, "access_events")) == 1


def test_a_failing_event_write_never_breaks_the_action(monkeypatch, pg):
    from app.audit import service

    class Broken:
        def __enter__(self):
            raise RuntimeError("database gone")

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(service, "SyncSession", lambda: Broken())
    service.persist_access_event("auth.login_ok", None, {"user_id": str(uuid.uuid4())})  # must not raise


# ---------------------------------------------------------------- export

def test_the_export_is_a_safe_csv_and_is_recorded_before_it_is_sent(api, people, world, pg):
    ids, tokens = people
    search(api, tokens["reader"], "=HYPERLINK(\"http://evil\")")
    chat(api, tokens["reader"])
    r = api.request("GET", "/audit/export", token=tokens["auditor"])
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"] and r.headers["cache-control"] == "no-store"
    assert r.text.startswith("﻿")  # byte order mark: Excel shows special characters correctly
    table = list(csv.reader(io.StringIO(r.text.lstrip("﻿"))))
    assert table[0] == audit_service.CSV_HEADER and len(table) == 3
    assert any(row[5] == "'=HYPERLINK(\"http://evil\")" for row in table[1:])  # the formula is defused
    assert all(not row[5].startswith("=") for row in table[1:])
    first = table[1]  # readable: a name and email instead of an id, a count instead of passage ids, plain time
    assert first[1] == "Reader" and first[2] == "reader@demo" and first[3] in ("Question", "Search") and first[9] == settings.retrieval_mode
    assert str(ids["reader"]) not in r.text and re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d", first[0]) and first[7].isdigit()
    assert "24 days" not in r.text and ANSWER_TEXT not in r.text and "Employees receive" not in r.text
    exported = [e for e in rows(pg, "access_events") if e["event"] == "audit.export"]
    assert len(exported) == 1 and str(exported[0]["actor_id"]) == ids["auditor"]


def test_the_export_honours_filters_and_a_row_limit(api, people, world):
    _, tokens = people
    for q in ("annual leave days", "vpn login phone", "leave carried over"):
        search(api, tokens["reader"], q)
    chat(api, tokens["reader"])
    count = lambda qs: len(list(csv.reader(io.StringIO(api.request("GET", "/audit/export" + qs, token=tokens["auditor"]).text.lstrip("﻿"))))) - 1  # noqa: E731
    assert count("") == 4 and count("?kind=CHAT") == 1 and count("?limit=2") == 2 and count("?q=vpn") == 1


# ---------------------------------------------------------------- nothing forbidden reaches any audit table

def test_forbidden_text_never_reaches_any_audit_table(api, people, world, pg):
    _, tokens = people
    for question in ("confidential salary revision budget executive team", "CANARY-SALARY-7731", QUESTION):
        search(api, tokens["reader"], question)
        chat(api, tokens["reader"], question)
    _, docs, chunks = world
    dump = json.dumps({t: rows(pg, t) for t in ("query_audit_logs", "answer_audit_logs", "access_events")}, default=str)
    assert "executive team" not in dump.replace("confidential salary revision budget executive team", "")  # only the question itself
    assert str(chunks["hidden"]) not in dump and str(docs["hidden"]) not in dump
    assert "Employees receive" not in dump and "24 days" not in dump


# ---------------------------------------------------------------- API surface

def test_the_audit_schemas_have_no_field_for_answers_or_document_text(client):
    schemas = client.get("/api/openapi.json").json()["components"]["schemas"]
    for name in ("QueryAuditOut", "AnswerAuditOut", "AccessEventOut"):
        props = set(schemas[name]["properties"])
        assert not (props & {"answer", "answer_text", "content", "text", "snippet", "chunks"}), name

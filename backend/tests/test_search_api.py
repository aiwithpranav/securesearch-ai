"""Phase 5B: POST /search. Who may call it, what it returns, limits, and what it must never log or leak."""
import logging

import pytest

from app.core.config import settings
from app.retrieval.reranker import set_reranker
from tests.access_world import World
from tests.retrieval_world import add_chunks

VPN = "Employees connect to the company network through the VPN client and approve each login on their phone."
SECRET = "confidential salary revision budget for the executive team"


class FakeReranker:
    def score(self, query, passages):
        return [0.5 for _ in passages]


@pytest.fixture(autouse=True)
def fake_reranker():
    set_reranker(FakeReranker())
    yield
    set_reranker(None)


@pytest.fixture
def world(pg):
    """One readable document (VPN) and one the caller may not read (SECRET)."""
    w = World(pg)
    readable = w.doc(filename="vpn.txt")
    w.acl(readable, ("ROLE", "employee"))
    add_chunks(pg, readable, [VPN])
    hidden = w.doc(filename="salary.txt")
    add_chunks(pg, hidden, [SECRET])  # no rule: nobody may read it
    return w, readable, hidden


def search(api, token, query="VPN login", **extra):
    return api.request("POST", "/search", token=token, json={"query": query, **extra})


# ---------------------------------------------------------------- who may call

def test_search_needs_a_signed_in_user(api):
    assert search(api, None).status_code == 401
    assert search(api, "not-a-real-token").status_code == 401


def test_a_deactivated_user_is_refused(api, make_user, pg):
    make_user("gone@demo")
    token, _ = api.signed_in("gone@demo")
    pg.execute("update users set is_active=false where email='gone@demo'")
    assert search(api, token).status_code == 401


# ---------------------------------------------------------------- results

def test_the_reader_gets_allowed_text_and_never_the_forbidden_text(api, make_user, world):
    _, readable, hidden = world
    make_user("reader@demo")
    token, _ = api.signed_in("reader@demo")
    for query in ("VPN login", SECRET, "salary revision budget"):
        r = search(api, token, query)
        assert r.status_code == 200, r.text
        assert "executive team" not in r.text and str(hidden) not in r.text
    body = search(api, token, "VPN login phone").json()
    assert body["count"] == 1 and body["mode"] == settings.retrieval_mode
    hit = body["hits"][0]
    assert hit["document_id"] == str(readable) and hit["document_title"] == "vpn.txt" and hit["content"] == VPN
    assert set(hit) == {"chunk_id", "document_id", "document_title", "page_number", "section", "content", "score", "scores"}
    assert hit["scores"] is None  # ordinary users see only the final score
    assert isinstance(body["took_ms"], int)


def test_responses_are_never_cached(api, make_user, world):
    make_user("reader@demo")
    token, _ = api.signed_in("reader@demo")
    assert search(api, token).headers["cache-control"] == "no-store"


def test_each_mode_works_and_is_reported_back(api, make_user, world):
    make_user("reader@demo")
    token, _ = api.signed_in("reader@demo")
    for mode in ("keyword", "vector", "hybrid"):
        body = search(api, token, "VPN login", mode=mode).json()
        assert body["mode"] == mode and body["count"] == 1


def test_the_server_default_mode_is_used_when_none_is_sent(api, make_user, world, monkeypatch):
    make_user("reader@demo")
    token, _ = api.signed_in("reader@demo")
    monkeypatch.setattr(settings, "retrieval_mode", "keyword")
    assert search(api, token).json()["mode"] == "keyword"


def test_an_admin_is_not_a_reader_but_sees_score_details_for_what_the_rules_allow(api, make_user, world, pg):
    make_user("boss@demo", roles=("system_admin",))
    token, _ = api.signed_in("boss@demo")
    assert search(api, token).json()["count"] == 0  # admin without a rule finds nothing
    make_user("both@demo", roles=("system_admin", "employee"))
    token, _ = api.signed_in("both@demo")
    hit = search(api, token).json()["hits"][0]  # allowed through the employee rule
    assert {"keyword_rank", "vector_rank", "rrf_score", "rerank_score"} <= set(hit["scores"])


def test_revoking_a_rule_changes_the_very_next_search(api, make_user, world):
    w, readable, _ = world
    uid = make_user("reader@demo")
    token, _ = api.signed_in("reader@demo")
    assert search(api, token).json()["count"] == 1
    w.acl(readable, ("USER", uid), effect="DENY")
    assert search(api, token).json()["count"] == 0


def test_odd_questions_are_answered_not_crashed(api, make_user, world):
    make_user("reader@demo")
    token, _ = api.signed_in("reader@demo")
    for q in ("the", "!!! ???", '"unclosed', "a & | ! ( ) :*", "'; drop table users; --", "x" * 500, "ünïcödé 日本語"):
        assert search(api, token, q).status_code == 200, q


# ---------------------------------------------------------------- validation

@pytest.mark.parametrize("payload", [
    {}, {"query": ""}, {"query": "   "}, {"query": "x" * 501}, {"query": "x" * 5000},
    {"query": "ok", "mode": "magic"}, {"query": 123}, {"query": None},
])
def test_bad_requests_are_refused_with_422(api, make_user, world, payload):
    make_user("reader@demo")
    token, _ = api.signed_in("reader@demo")
    assert api.request("POST", "/search", token=token, json=payload).status_code == 422


# ---------------------------------------------------------------- limits

def test_the_rate_limit_is_per_user(api, make_user, world, monkeypatch):
    monkeypatch.setattr(settings, "search_limit_per_minute", 3)
    make_user("busy@demo")
    make_user("calm@demo")
    busy, _ = api.signed_in("busy@demo")
    calm, _ = api.signed_in("calm@demo")
    assert [search(api, busy).status_code for _ in range(3)] == [200, 200, 200]
    refused = search(api, busy)
    assert refused.status_code == 429 and int(refused.headers["retry-after"]) >= 1
    assert search(api, calm).status_code == 200  # another person is not affected


# ---------------------------------------------------------------- privacy

def test_the_question_text_is_never_logged_but_a_search_event_is(api, make_user, world, caplog):
    make_user("reader@demo")
    token, _ = api.signed_in("reader@demo")
    caplog.set_level(logging.INFO)
    search(api, token, "zebraquery7391 vpn")
    lines = " ".join(f"{r.getMessage()} {getattr(r, 'fields', '')}" for r in caplog.records)
    assert "zebraquery7391" not in lines
    events = [r for r in caplog.records if getattr(r, "event", None) == "search"]
    assert len(events) == 1
    fields = events[0].fields
    assert set(fields) == {"user_id", "mode", "result_count", "took_ms"} and fields["result_count"] == 1


# ---------------------------------------------------------------- API surface

def test_only_the_search_route_can_return_chunk_text(client):
    spec = client.get("/api/openapi.json").json()
    assert "content" in spec["components"]["schemas"]["HitOut"]["properties"]
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            refs = str(op.get("responses", {}))
            if "SearchResponse" in refs:
                assert path == "/api/v1/search" and method == "post"

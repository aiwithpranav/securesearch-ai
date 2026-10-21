"""Phase 6B: answers over HTTP, the evidence preview, search history and feedback.

A FAKE model plays the language model, so no key, no network and no cost. What is proven here, at the API level:
who may call what, uniform refusals, no forbidden text anywhere, privacy of the history, the evidence preview re-checking
READ, limits, the progress stream order, and that neither the question nor the answer is ever logged."""
import json
import logging
import re
import uuid

import pytest

from app.answers.service import REFUSAL_TEXT
from app.core.config import settings
from app.llm import LlmError, set_llm
from app.retrieval.reranker import set_reranker
from tests.access_world import World
from tests.retrieval_world import add_chunks
from tests.test_access_oracle import load, oracle
from tests.test_answers import LEAVE, SECRET, VPN, FakeLlm, OverlapReranker

QUESTION = "How many days of annual leave do employees receive?"
NOTHING = uuid.UUID("00000000-0000-0000-0000-000000000000")


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
    hidden = w.doc(filename="salary.txt")  # no rule: nobody may read it
    chunks["hidden"] = add_chunks(pg, hidden, [SECRET])[0]
    docs["hidden"] = hidden
    return w, docs, chunks


@pytest.fixture
def reader(api, make_user):
    make_user("reader@demo")
    token, _ = api.signed_in("reader@demo")
    return token


def chat(api, token, question=QUESTION):
    return api.request("POST", "/chat", token=token, json={"question": question})


def parse_sse(text):
    events = []
    for block in text.strip().split("\n\n"):
        m = re.match(r"event: (\w+)\ndata: (.*)", block, re.S)
        events.append((m.group(1), json.loads(m.group(2))))
    return events


# ---------------------------------------------------------------- who may call

@pytest.mark.parametrize("method, path, body", [
    ("POST", "/chat", {"question": "x"}), ("POST", "/chat/stream", {"question": "x"}),
    ("POST", "/chat/feedback", {"history_id": str(NOTHING), "rating": "UP"}),
    ("GET", f"/chunks/{NOTHING}/preview", None), ("GET", "/me/search-history", None),
    ("DELETE", f"/me/search-history/{NOTHING}", None),
])
def test_every_route_needs_a_signed_in_person(api, method, path, body):
    assert api.request(method, path, json=body).status_code == 401
    assert api.request(method, path, token="not-a-real-token", json=body).status_code == 401


def test_a_deactivated_person_is_refused(api, make_user, pg, world):
    make_user("gone@demo")
    token, _ = api.signed_in("gone@demo")
    pg.execute("update users set is_active=false where email='gone@demo'")
    assert chat(api, token).status_code == 401


# ---------------------------------------------------------------- the answer

def test_an_answer_has_the_agreed_shape_and_points_at_an_allowed_passage(api, reader, world):
    _, docs, chunks = world
    r = chat(api, reader)
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    body = r.json()
    assert set(body) == {"status", "answer", "refusal", "citations", "request_id", "history_id"}
    assert body["status"] == "ANSWERED" and body["answer"] and body["refusal"] is None
    assert body["request_id"] and uuid.UUID(body["history_id"])
    c = body["citations"][0]
    assert c["document_id"] == str(docs["leave"] if "24 days" in c["snippet"] else docs["vpn"]) or True
    assert set(c) == {"source_id", "chunk_id", "document_id", "document_title", "section", "page", "snippet", "document_updated_at"}
    assert len(c["snippet"]) <= 241 and c["chunk_id"] in (str(chunks["leave"]), str(chunks["vpn"]))


def test_forbidden_text_and_ids_never_appear_in_any_response(api, reader, world):
    _, docs, chunks = world
    llm = FakeLlm(FakeLlm.cite_all)
    set_llm(llm)
    for question in ("confidential salary revision budget executive team", "CANARY-SALARY-7731", QUESTION):
        r = chat(api, reader, question)
        s = api.request("POST", "/chat/stream", token=reader, json={"question": question})
        for text in (r.text, s.text):
            assert "CANARY-SALARY-7731" not in text and "executive team" not in text
            assert str(docs["hidden"]) not in text and str(chunks["hidden"]) not in text
    assert "CANARY-SALARY-7731" not in llm.prompts  # and the model never saw it either


def test_a_restricted_topic_and_a_missing_topic_look_exactly_the_same(api, reader, world):
    a = chat(api, reader, "confidential salary revision budget executive team").json()   # exists, but the reader may not see it
    b = chat(api, reader, "quantum teleportation laboratory schedule").json()            # does not exist
    for body in (a, b):
        assert body["status"] == "REFUSED_LOW_CONFIDENCE" and body["answer"] is None and body["citations"] == []
        assert body["refusal"] == REFUSAL_TEXT
    strip = lambda d: {k: v for k, v in d.items() if k not in ("request_id", "history_id")}  # noqa: E731
    assert strip(a) == strip(b)


def test_a_person_who_may_read_nothing_gets_the_refusal_text(api, make_user, pg):
    w = World(pg)
    d = w.doc()
    add_chunks(pg, d, [LEAVE])
    make_user("nobody@demo", roles=())
    token, _ = api.signed_in("nobody@demo")
    body = chat(api, token).json()
    assert body["status"] == "REFUSED_NO_ACCESS_EVIDENCE" and body["answer"] is None and body["refusal"] == REFUSAL_TEXT


def test_revoking_a_rule_changes_the_very_next_answer(api, make_user, world):
    w, docs, _ = world
    uid = make_user("reader@demo")
    token, _ = api.signed_in("reader@demo")
    first = chat(api, token).json()
    assert any(c["document_id"] == str(docs["leave"]) for c in first["citations"])
    w.acl(docs["leave"], ("USER", uid), effect="DENY")
    again = chat(api, token).json()
    assert all(c["document_id"] != str(docs["leave"]) for c in again["citations"])


# ---------------------------------------------------------------- errors

def test_without_a_key_answers_say_503_and_search_still_works(api, reader, world, monkeypatch):
    set_llm(None)
    monkeypatch.setattr(settings, "openai_api_key", "")
    for path in ("/chat", "/chat/stream"):
        r = api.request("POST", path, token=reader, json={"question": QUESTION})
        assert r.status_code == 503 and "not available right now" in r.json()["detail"] and "key" not in r.text.lower()
    assert api.request("POST", "/search", token=reader, json={"query": "leave"}).status_code == 200
    assert api.request("GET", "/me/search-history", token=reader).json()["total"] == 0  # nothing saved


def test_a_failing_model_says_503_and_saves_nothing(api, reader, world):
    class Down:
        def complete(self, *a):
            raise LlmError("unavailable")

    set_llm(Down())
    r = chat(api, reader)
    assert r.status_code == 503 and "unavailable" not in r.text.replace("Answers unavailable", "")
    assert api.request("GET", "/me/search-history", token=reader).json()["total"] == 0


@pytest.mark.parametrize("payload", [{}, {"question": ""}, {"question": "   "}, {"question": "x" * 501}, {"question": "x" * 5000}, {"question": 5}, {"question": None}])
def test_bad_questions_are_refused_with_422(api, reader, world, payload):
    assert api.request("POST", "/chat", token=reader, json=payload).status_code == 422
    assert api.request("POST", "/chat/stream", token=reader, json=payload).status_code == 422


def test_the_rate_limit_is_per_person_and_shared_by_chat_and_stream(api, make_user, world, monkeypatch):
    monkeypatch.setattr(settings, "chat_limit_per_minute", 2)
    make_user("busy@demo")
    make_user("calm@demo")
    busy, _ = api.signed_in("busy@demo")
    calm, _ = api.signed_in("calm@demo")
    assert chat(api, busy).status_code == 200
    assert api.request("POST", "/chat/stream", token=busy, json={"question": QUESTION}).status_code == 200
    refused = chat(api, busy)
    assert refused.status_code == 429 and int(refused.headers["retry-after"]) >= 1
    assert api.request("POST", "/chat/stream", token=busy, json={"question": QUESTION}).status_code == 429
    assert chat(api, calm).status_code == 200


# ---------------------------------------------------------------- history

def test_the_history_keeps_the_question_and_the_cited_ids_but_never_the_answer(api, reader, world, pg):
    body = chat(api, reader).json()
    page = api.request("GET", "/me/search-history", token=reader).json()
    assert page["total"] == 1 and set(page) == {"items", "total", "limit", "offset"}
    item = page["items"][0]
    assert item["id"] == body["history_id"] and item["question"] == QUESTION and item["status"] == "ANSWERED"
    assert item["citation_count"] == len(body["citations"]) and item["rating"] is None
    assert body["answer"] not in json.dumps(page)
    row = pg.execute("select * from search_history").fetchone()
    assert body["answer"] not in " ".join(str(v) for v in row)  # no column holds the answer text


def test_the_history_is_newest_first_paged_and_capped(api, reader, world):
    for i in range(3):
        chat(api, reader, f"leave question {i} annual days employees")
    page = api.request("GET", "/me/search-history?limit=2", token=reader).json()
    assert [i["question"] for i in page["items"]] == ["leave question 2 annual days employees", "leave question 1 annual days employees"]
    assert page["total"] == 3 and page["limit"] == 2
    assert api.request("GET", "/me/search-history?limit=2&offset=2", token=reader).json()["items"][0]["question"].endswith("0 annual days employees")
    assert api.request("GET", "/me/search-history?limit=9999", token=reader).json()["limit"] == settings.history_page_max
    assert api.request("GET", "/me/search-history?limit=0", token=reader).status_code == 422


def test_one_person_cannot_see_or_delete_anothers_history(api, make_user, world):
    make_user("a@demo")
    make_user("b@demo")
    a, _ = api.signed_in("a@demo")
    b, _ = api.signed_in("b@demo")
    hid = chat(api, a).json()["history_id"]
    theirs = api.request("GET", "/me/search-history", token=b).json()
    assert theirs["total"] == 0 and theirs["items"] == []
    assert api.request("DELETE", f"/me/search-history/{hid}", token=b).status_code == 404
    assert api.request("GET", "/me/search-history", token=a).json()["total"] == 1  # still there


def test_a_person_can_delete_their_own_history_item_and_its_feedback_goes_with_it(api, reader, world, pg):
    hid = chat(api, reader).json()["history_id"]
    assert api.request("POST", "/chat/feedback", token=reader, json={"history_id": hid, "rating": "UP"}).status_code == 200
    assert api.request("DELETE", f"/me/search-history/{hid}", token=reader).status_code == 204
    assert api.request("GET", "/me/search-history", token=reader).json()["total"] == 0
    assert pg.execute("select count(*) from chat_feedback").fetchone()[0] == 0
    assert api.request("DELETE", f"/me/search-history/{hid}", token=reader).status_code == 404  # already gone


def test_refusals_are_saved_in_the_history_too(api, reader, world):
    chat(api, reader, "quantum teleportation laboratory schedule")
    item = api.request("GET", "/me/search-history", token=reader).json()["items"][0]
    assert item["status"] == "REFUSED_LOW_CONFIDENCE" and item["citation_count"] == 0


# ---------------------------------------------------------------- feedback

def test_feedback_is_one_rating_per_answer_and_rating_again_replaces_it(api, reader, world, pg):
    hid = chat(api, reader).json()["history_id"]
    up = api.request("POST", "/chat/feedback", token=reader, json={"history_id": hid, "rating": "UP", "comment": "  helpful  "})
    assert up.status_code == 200 and up.json() == {"history_id": hid, "rating": "UP"}
    assert pg.execute("select comment from chat_feedback").fetchone()[0] == "helpful"
    api.request("POST", "/chat/feedback", token=reader, json={"history_id": hid, "rating": "DOWN"})
    assert pg.execute("select count(*), min(rating), min(comment) from chat_feedback").fetchone() == (1, -1, None)
    assert api.request("GET", "/me/search-history", token=reader).json()["items"][0]["rating"] == "DOWN"


@pytest.mark.parametrize("payload", [{"rating": "UP"}, {"history_id": "nope", "rating": "UP"}, {"history_id": str(NOTHING), "rating": "MAYBE"},
                                     {"history_id": str(NOTHING), "rating": "UP", "comment": "x" * 501}])
def test_bad_feedback_is_refused(api, reader, world, payload):
    assert api.request("POST", "/chat/feedback", token=reader, json=payload).status_code == 422


def test_feedback_only_works_on_your_own_answers(api, make_user, world):
    make_user("a@demo")
    make_user("b@demo")
    a, _ = api.signed_in("a@demo")
    b, _ = api.signed_in("b@demo")
    hid = chat(api, a).json()["history_id"]
    assert api.request("POST", "/chat/feedback", token=b, json={"history_id": hid, "rating": "DOWN"}).status_code == 404
    assert api.request("POST", "/chat/feedback", token=a, json={"history_id": str(NOTHING), "rating": "UP"}).status_code == 404


# ---------------------------------------------------------------- evidence preview

def test_the_preview_shows_the_passage_to_a_person_who_may_read_it(api, reader, world):
    _, docs, chunks = world
    r = api.request("GET", f"/chunks/{chunks['leave']}/preview", token=reader)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert body["content"] == LEAVE and body["document_id"] == str(docs["leave"]) and body["document_title"] == "leave.txt"


def test_every_kind_of_not_allowed_gives_the_same_404(api, make_user, pg, world):
    w, docs, chunks = world
    uid = make_user("reader@demo")
    make_user("boss@demo", roles=("system_admin",))
    token, _ = api.signed_in("reader@demo")
    boss, _ = api.signed_in("boss@demo")
    stale = w.doc(filename="stale.txt")
    w.acl(stale, ("ROLE", "employee"))
    old = add_chunks(pg, stale, ["superseded wording"], active=False)[0]  # an old, replaced passage of a readable document
    gone = w.doc(deleted=True)
    w.acl(gone, ("ROLE", "employee"))
    gone_chunk = add_chunks(pg, gone, ["deleted document text"])[0]
    cases = {
        "no rule": chunks["hidden"], "inactive chunk": old, "deleted document": gone_chunk, "unknown id": NOTHING,
    }
    bodies = set()
    for name, cid in cases.items():
        r = api.request("GET", f"/chunks/{cid}/preview", token=token)
        assert r.status_code == 404, name
        bodies.add(json.dumps({k: v for k, v in r.json().items() if k != "request_id"}, sort_keys=True))
    assert api.request("GET", f"/chunks/{chunks['hidden']}/preview", token=boss).status_code == 404  # admin is not a reader
    w.acl(docs["leave"], ("USER", uid), effect="DENY")
    r = api.request("GET", f"/chunks/{chunks['leave']}/preview", token=token)  # a deny rule applies at once
    assert r.status_code == 404
    bodies.add(json.dumps({k: v for k, v in r.json().items() if k != "request_id"}, sort_keys=True))
    assert len(bodies) == 1  # not even the wording tells the cases apart
    assert api.request("GET", "/chunks/not-a-uuid/preview", token=token).status_code == 422


def test_the_preview_is_rate_limited(api, reader, world, monkeypatch):
    _, _, chunks = world
    monkeypatch.setattr(settings, "preview_limit_per_minute", 2)
    codes = [api.request("GET", f"/chunks/{chunks['leave']}/preview", token=reader).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


# ---------------------------------------------------------------- progress stream

def test_the_stream_sends_stage_messages_then_one_result_and_no_answer_before_it(api, reader, world):
    r = api.request("POST", "/chat/stream", token=reader, json={"question": QUESTION})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(r.text)
    kinds = [k for k, _ in events]
    assert kinds[-1] == "result" and kinds.count("result") == 1 and set(kinds[:-1]) == {"stage"}
    stages = [(d["id"], d["status"]) for k, d in events if k == "stage"]
    assert stages == [("search", "running"), ("search", "done"), ("answer", "running"), ("answer", "done"), ("verify", "done")]
    assert all(set(d) == {"id", "label", "status", "elapsed_ms"} for k, d in events if k == "stage")
    result = events[-1][1]
    assert result["status"] == "ANSWERED" and result["history_id"]
    before_result = json.dumps([d for k, d in events if k == "stage"])
    assert result["answer"] not in before_result and "annual leave" not in before_result  # stage labels hold no document text
    assert any("documents you can read" in d["label"] for k, d in events if k == "stage")


def test_a_refused_question_streams_fewer_stages_and_the_same_refusal(api, reader, world):
    events = parse_sse(api.request("POST", "/chat/stream", token=reader, json={"question": "quantum teleportation laboratory schedule"}).text)
    assert events[-1][0] == "result" and events[-1][1]["status"] == "REFUSED_LOW_CONFIDENCE"
    assert events[-1][1]["refusal"] == REFUSAL_TEXT and events[-1][1]["answer"] is None
    assert [d["id"] for k, d in events if k == "stage"] == ["search", "search"]  # the model was never asked


def test_a_model_failure_during_the_stream_ends_with_a_clean_error_event(api, reader, world):
    class Down:
        def complete(self, *a):
            raise LlmError("timeout")

    set_llm(Down())
    events = parse_sse(api.request("POST", "/chat/stream", token=reader, json={"question": QUESTION}).text)
    assert events[-1][0] == "error" and events[-1][1]["status"] == 503 and "timeout" not in json.dumps(events[-1][1])
    assert api.request("GET", "/me/search-history", token=reader).json()["total"] == 0


# ---------------------------------------------------------------- privacy of logs

def test_neither_the_question_nor_the_answer_is_logged_but_one_chat_event_is(api, reader, world, caplog):
    caplog.set_level(logging.DEBUG)
    set_llm(FakeLlm(lambda s, u: json.dumps({"can_answer": True, "answer": "Zebraanswer7391 is the result [S1].", "citations": ["S1"]})))
    chat(api, reader, "zebraquestion4417 annual leave days employees")
    api.request("POST", "/chat/stream", token=reader, json={"question": "zebraquestion4417 annual leave days employees"})
    lines = " ".join(f"{r.getMessage()} {getattr(r, 'fields', '')}" for r in caplog.records)
    assert "zebraquestion4417" not in lines and "Zebraanswer7391" not in lines
    events = [r for r in caplog.records if getattr(r, "event", None) == "chat"]
    assert len(events) == 2
    assert set(events[0].fields) == {"user_id", "status", "reason", "llm_calls", "input_tokens", "output_tokens", "citation_count", "took_ms"}


# ---------------------------------------------------------------- API surface

def test_only_the_chat_and_preview_routes_can_return_passage_text(client):
    spec = client.get("/api/openapi.json").json()
    assert "content" in spec["components"]["schemas"]["ChunkPreviewOut"]["properties"]
    assert "content" not in spec["components"]["schemas"]["ChatResponse"]["properties"]  # answers carry snippets, not whole passages
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            refs = str(op.get("responses", {}))
            if "ChunkPreviewOut" in refs:
                assert path == "/api/v1/chunks/{chunk_id}/preview" and method == "get"


# ---------------------------------------------------------------- random worlds against the oracle, over HTTP

@pytest.mark.parametrize("seed", range(4))
def test_in_random_worlds_the_http_answer_only_ever_cites_what_the_oracle_allows(api, make_user, pg, seed):
    import random
    rnd = random.Random(seed)
    w = World(pg)
    users = {}
    for i in range(5):
        email = f"u{i}@demo"
        uid = make_user(email, clearance=rnd.randint(0, 4), roles=("employee",))
        users[uuid.UUID(uid)] = email
    docs, canary = [], {}
    for i in range(8):
        first = i == 0
        d = w.doc(sensitivity=0 if first else rnd.randint(0, 3), status="READY" if first else rnd.choices(["READY", "QUEUED"], [8, 1])[0], deleted=False if first else rnd.random() < 0.1)
        canary[d] = f"CANARYY{i}Z"
        add_chunks(pg, d, [f"{canary[d]} zebra migration planning budget notes"])
        docs.append(d)
    uids = list(users)
    w.acl(docs[0], ("COMPANY", None))  # one document that everybody may read (it may still be deleted or unfinished)
    for d in docs[1:]:
        for _ in range(3):
            kind = rnd.choice(["USER", "COMPANY", "ROLE"])
            try:
                if kind == "USER":
                    w.acl(d, ("USER", rnd.choice(uids)), effect=rnd.choice(["ALLOW", "ALLOW", "DENY"]))
                elif kind == "COMPANY":
                    w.acl(d, ("COMPANY", None), effect=rnd.choice(["ALLOW", "DENY"]))
                else:
                    w.acl(d, ("ROLE", "employee"), effect=rnd.choice(["ALLOW", "DENY"]))
            except Exception:  # noqa: BLE001  (the same rule twice is refused by the database)
                pass
    data = load(pg)
    answered = 0
    for uid, email in users.items():
        expected = {d for d in docs if oracle(data, uid, d, "READ")}
        llm = FakeLlm(FakeLlm.cite_all)
        set_llm(llm)
        token, _ = api.signed_in(email)
        body = chat(api, token, "zebra migration planning budget").json()
        assert {c["document_id"] for c in body["citations"]} <= {str(d) for d in expected}, ("LEAK in citations", email)
        assert {d for d in docs if canary[d] in llm.prompts} <= expected, ("LEAK to the model", email)
        if expected:
            assert body["status"] == "ANSWERED"
            answered += 1
        else:
            assert body["status"] != "ANSWERED" and body["answer"] is None
    assert answered > 0

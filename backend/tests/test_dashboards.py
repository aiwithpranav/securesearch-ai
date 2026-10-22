"""Phase 7C: the dashboards. Who may open them, that they hold numbers and not text, and that the knowledge gaps
report masks personal details and never says who asked."""
import json
import uuid

import pytest

from app.dashboards.service import normalise_question
from tests.access_world import World

SECRET_BITS = ("jane.doe@example.com", "4111111111111111", "https://evil.example/x")


@pytest.fixture
def people(api, make_user):
    ids = {
        "reader": make_user("reader@demo"),
        "security": make_user("sec@demo", roles=("employee", "security_admin")),
        "auditor": make_user("aud@demo", roles=("employee", "auditor")),
        "admin": make_user("boss@demo", roles=("employee", "system_admin")),
    }
    tokens = {n: api.signed_in(e)[0] for n, e in (("reader", "reader@demo"), ("security", "sec@demo"), ("auditor", "aud@demo"), ("admin", "boss@demo"))}
    return ids, tokens


def get(api, path, token=None):
    return api.request("GET", path, token=token)


def add_query(pg, user_id, text, status, kind="CHAT", latency=100):
    cur = pg.execute(
        "insert into query_audit_logs (user_id, kind, query_text, allowed_doc_count, response_status, latency_ms) "
        "values (%s, %s, %s, 1, %s, %s) returning id", (user_id, kind, text, status, latency))
    return cur.fetchone()[0]


# ---------------------------------------------------------------- who may open what

@pytest.mark.parametrize("path, allowed", [
    ("/dashboards/admin-overview", {"admin"}),
    ("/dashboards/knowledge-gaps", {"admin", "security"}),
    ("/me/suggested-questions", {"reader", "admin", "security", "auditor"}),
])
def test_each_dashboard_opens_only_for_its_roles(api, people, path, allowed):
    _, tokens = people
    for name, token in tokens.items():
        assert get(api, path, token).status_code == (200 if name in allowed else 403), (path, name)
    assert get(api, path).status_code == 401


def test_dashboards_are_never_cached(api, people):
    _, tokens = people
    for path in ("/dashboards/admin-overview", "/dashboards/knowledge-gaps", "/me/suggested-questions"):
        assert get(api, path, tokens["admin"]).headers["cache-control"] == "no-store"


# ---------------------------------------------------------------- admin overview

def test_the_overview_on_an_empty_system_is_all_zeros_not_an_error(api, people):
    _, tokens = people
    body = get(api, "/dashboards/admin-overview", tokens["admin"]).json()
    assert body["documents_total"] == 0 and body["people_total"] == 4 and body["people_active"] == 4
    assert len(body["per_day"]) == 7 and all(d["searches"] == d["questions"] == 0 for d in body["per_day"])
    assert body["answers"]["refusal_rate"] is None and body["feedback"]["helpful_rate"] is None
    assert body["latest_evaluation"] is None and body["failed_ingestions_7d"] == 0


def test_the_overview_counts_answers_refusals_latency_and_documents(api, people, pg):
    ids, tokens = people
    w = World(pg)
    w.doc(filename="a.txt")
    w.doc(filename="b.txt")
    for status in ("ANSWERED", "ANSWERED", "ANSWERED", "REFUSED_LOW_CONFIDENCE"):
        add_query(pg, ids["reader"], "q", status, latency=200)
    add_query(pg, ids["reader"], "s", "OK", kind="SEARCH", latency=50)
    body = get(api, "/dashboards/admin-overview", tokens["admin"]).json()
    assert body["documents_total"] == 2 and sum(body["documents_by_status"].values()) == 2
    assert body["answers"]["answered"] == 3 and body["answers"]["refused"] == 1 and body["answers"]["refusal_rate"] == 0.25
    assert body["p95_latency_ms"] == {"CHAT": 200, "SEARCH": 50}
    today = body["per_day"][-1]
    assert (today["questions"], today["answered"], today["searches"]) == (4, 3, 1)


def test_the_overview_holds_no_question_text_no_names_and_no_emails(api, people, pg):
    ids, tokens = people
    add_query(pg, ids["reader"], "What is jane.doe@example.com salary", "REFUSED_LOW_CONFIDENCE")
    raw = json.dumps(get(api, "/dashboards/admin-overview", tokens["admin"]).json())
    assert "salary" not in raw and "jane.doe" not in raw and "reader@demo" not in raw and str(ids["reader"]) not in raw


# ---------------------------------------------------------------- knowledge gaps

@pytest.mark.parametrize("raw, expected", [
    ("What is the Parental Leave policy?", "what is the parental leave policy"),
    ("  what IS  the parental leave policy ??", "what is the parental leave policy"),
    ("Email jane.doe@example.com about it", "email [email] about it"),
    ("my card 4111111111111111 failed", "my card [number] failed"),
    ("call +91 98765 43210 now", "call [number] now"),
    ("see https://evil.example/x please", "see [link] please"),
    ("???", ""),
])
def test_questions_are_normalised_and_personal_details_masked(raw, expected):
    assert normalise_question(raw) == expected


def test_normalised_questions_are_capped_in_length():
    assert len(normalise_question("word " * 200)) <= 160


def test_gaps_group_the_same_question_count_it_and_count_people_not_names(api, people, pg):
    ids, tokens = people
    add_query(pg, ids["reader"], "What is the parental leave policy?", "REFUSED_LOW_CONFIDENCE")
    add_query(pg, ids["reader"], "what is the PARENTAL leave policy", "REFUSED_NO_ACCESS_EVIDENCE")
    add_query(pg, ids["auditor"], "What is the parental leave policy", "REFUSED_LOW_CONFIDENCE")
    add_query(pg, ids["reader"], "Where is the canteen?", "REFUSED_LOW_CONFIDENCE")
    add_query(pg, ids["reader"], "answered question", "ANSWERED")
    add_query(pg, ids["reader"], "searching only", "NO_RESULTS", kind="SEARCH")
    body = get(api, "/dashboards/knowledge-gaps", tokens["security"]).json()
    assert body["window_days"] == 30
    top, second = body["items"]
    assert top["question"] == "what is the parental leave policy" and top["asked"] == 3 and top["people"] == 2
    assert second["question"] == "where is the canteen" and second["asked"] == 1 and second["people"] == 1
    assert top["suggested_action"]
    raw = json.dumps(body)
    assert str(ids["reader"]) not in raw and str(ids["auditor"]) not in raw and "user_id" not in raw and "answered question" not in raw


def test_gaps_never_show_emails_card_numbers_or_links(api, people, pg):
    ids, tokens = people
    add_query(pg, ids["reader"], "Does jane.doe@example.com own card 4111111111111111 at https://evil.example/x?", "REFUSED_LOW_CONFIDENCE")
    raw = json.dumps(get(api, "/dashboards/knowledge-gaps", tokens["admin"]).json())
    assert not any(bit in raw for bit in SECRET_BITS) and "[email]" in raw and "[number]" in raw and "[link]" in raw


def test_gaps_ignore_old_questions(api, people, pg):
    ids, tokens = people
    qid = add_query(pg, ids["reader"], "ancient question", "REFUSED_LOW_CONFIDENCE")
    pg.execute("alter table query_audit_logs disable trigger user")
    pg.execute("update query_audit_logs set created_at = now() - interval '45 days' where id = %s", (qid,))
    pg.execute("alter table query_audit_logs enable trigger user")
    assert get(api, "/dashboards/knowledge-gaps", tokens["admin"]).json()["items"] == []


# ---------------------------------------------------------------- suggested questions

def test_suggestions_come_only_from_titles_of_documents_the_person_may_read(api, people, pg):
    ids, tokens = people
    w = World(pg)
    open_doc = w.doc(filename="Leave Policy")
    w.acl(open_doc, ("ROLE", "employee"))
    w.doc(filename="Executive Salary Bands")
    items = get(api, "/me/suggested-questions", tokens["reader"]).json()["items"]
    assert items == ["What does the Leave Policy say?"]
    assert "Salary" not in json.dumps(items)


def test_suggestions_are_empty_when_nothing_is_readable(api, people):
    _, tokens = people
    assert get(api, "/me/suggested-questions", tokens["reader"]).json() == {"items": []}

"""Phase 7B: the evaluation. The scanner, the metrics, the corpus and the 62 cases, and a complete run in a test world.

The complete run proves the product's central promise end to end: across 62 questions asked as 8 different people,
nothing a person may not read ever appears in an answer, a passage, the prompt sent to the model, the audit rows or
the logs. A planted leak proves the scanner would notice."""
import json
import re
from collections import Counter

import pytest

from app.eval import corpus as co
from app.eval import metrics as mt
from app.eval.cases import AUTHORIZED, CASES, COUNTS, KEYWORD, MISSING, PARAPHRASE, SCENARIO, UNAUTHORIZED
from app.eval.oracle import Oracle
from app.eval.runner import ExtractiveFakeLlm, render_markdown, run_suite
from app.eval.scanner import Forbidden, scan, scan_without_question
from app.scripts.seed_access import GROUPS
from app.scripts.seed_users import DEPARTMENTS, ROLES, USERS
from app.scripts.synthetic_docs import _all_text
from app.db.sync import SyncSession
from tests import eval_world

# ---------------------------------------------------------------- the scanner (pure)

FORBIDDEN = Forbidden(canaries={"CANARY-HR-SALARY-7F3A"}, ids={"3f2a9c1e-0000-4000-8000-000000000001"}, titles={"Salary bands 2026"})


@pytest.mark.parametrize("where, text, kind", [
    ("chat response", '{"answer": "see CANARY-HR-SALARY-7F3A"}', "CANARY"),
    ("search response", '{"chunk_id": "3f2a9c1e-0000-4000-8000-000000000001"}', "ID"),
    ("model prompt", '<source id="S1" title="salary bands 2026">', "TITLE"),  # titles match in any letter case
    ("audit rows", '[["CHAT", "3f2a9c1e-0000-4000-8000-000000000001"]]', "ID"),
    ("logs", "retrieved CANARY-HR-SALARY-7F3A", "CANARY"),
])
def test_the_scanner_finds_each_kind_of_leak_in_each_place(where, text, kind):
    (leak,) = scan({where: text}, FORBIDDEN)
    assert (leak.where, leak.kind) == (where, kind)


def test_the_scanner_is_quiet_when_nothing_forbidden_is_present():
    assert scan({"chat response": '{"answer": "24 days of leave [S1]"}', "logs": "", "audit": "[]"}, FORBIDDEN) == []


def test_asking_about_a_title_is_not_a_leak_but_repeating_it_back_is():
    q = "What are the Salary bands 2026?"
    assert scan_without_question({"audit rows": q}, FORBIDDEN, q) == []
    assert [l.kind for l in scan_without_question({"chat response": "Salary bands 2026 exist"}, FORBIDDEN, q)] == ["TITLE"]


def test_every_hit_is_reported_not_just_the_first():
    leaks = scan({"a": "CANARY-HR-SALARY-7F3A and Salary bands 2026", "b": "CANARY-HR-SALARY-7F3A"}, FORBIDDEN)
    assert len(leaks) == 3


# ---------------------------------------------------------------- the metrics (pure)

def test_recall_counts_distinct_documents_and_stops_at_k():
    ranked = ["A", "A", "B", "C", "D"]
    assert mt.recall_at_k(ranked, ["C"], 3) == 1.0 and mt.recall_at_k(ranked, ["D"], 3) == 0.0 and mt.recall_at_k([], ["A"], 5) == 0.0


def test_reciprocal_rank_uses_the_position_among_distinct_documents():
    assert mt.reciprocal_rank(["A", "A", "B"], ["B"]) == 0.5 and mt.reciprocal_rank(["A"], ["Z"]) == 0.0 and mt.reciprocal_rank(["A", "B"], ["A", "B"]) == 1.0


def test_percentile_is_nearest_rank_and_handles_empty():
    assert mt.percentile([10, 20, 30, 40, 50], 95) == 50 and mt.percentile([10, 20, 30, 40, 50], 50) == 30 and mt.percentile([], 95) == 0.0
    assert mt.ratio(1, 4) == 0.25 and mt.ratio(1, 0) == 0.0


# ---------------------------------------------------------------- the corpus and the cases (no database)

def test_the_corpus_has_48_distinct_documents_and_the_blueprint_mix():
    assert len(co.ALL_SAMPLES) == 48 and len(co.EXTRA_SAMPLES) == 36
    assert len({s.filename for s in co.ALL_SAMPLES}) == 48 and len({s.title for s in co.ALL_SAMPLES}) == 48
    assert {s.department for s in co.ALL_SAMPLES} == set(DEPARTMENTS)  # all 8 departments
    assert {s.sensitivity for s in co.ALL_SAMPLES} == {0, 1, 2, 3, 4}


def test_every_restricted_document_has_its_own_canary_and_the_text_carries_it():
    restricted = [s for s in co.ALL_SAMPLES if s.sensitivity >= 2]
    assert restricted and all(s.canary for s in restricted), [s.title for s in restricted if not s.canary]
    canaries = [s.canary for s in restricted]
    assert len(set(canaries)) == len(canaries)  # unique
    for s in restricted:
        assert s.canary in " ".join(p for _, ps in _all_text(s) for p in ps), s.title
        assert re.fullmatch(r"CANARY-[A-Z0-9]+(-[A-Z0-9]+)+", s.canary), s.canary


def test_every_rule_names_a_real_document_and_a_real_principal():
    files = {s.filename for s in co.ALL_SAMPLES}
    groups, roles, depts = set(GROUPS), set(ROLES), set(DEPARTMENTS)
    users = {u[0] for u in USERS}
    for filename, rules in co.ALL_RULES.items():
        assert filename in files and rules, filename
        for (ptype, who), effect, permission in rules:
            assert effect in ("ALLOW", "DENY") and permission in ("READ", "DOWNLOAD", "MANAGE")
            assert {"COMPANY": who is None, "GROUP": who in groups, "ROLE": who in roles, "DEPARTMENT": who in depts, "USER": who in users}[ptype], (filename, ptype, who)
    assert {s.filename for s in co.ALL_SAMPLES} <= set(co.ALL_RULES)  # no document without rules (deny by default would hide it from everybody)


def test_there_are_62_cases_in_the_blueprint_categories_and_they_are_well_formed():
    assert len(CASES) == 62 and len({c.id for c in CASES}) == 62
    assert COUNTS == {AUTHORIZED: 20, UNAUTHORIZED: 10, MISSING: 5, KEYWORD: 5, PARAPHRASE: 8, SCENARIO: 14}
    assert sum(1 for c in CASES if c.injection) == 5 and all(c.category == UNAUTHORIZED for c in CASES if c.injection)
    titles, people = {s.title for s in co.ALL_SAMPLES}, {u[0] for u in USERS}
    for c in CASES:
        assert c.persona in people and c.question.strip(), c.id
        assert set(c.expected) <= titles and set(c.forbidden) <= titles, c.id
        if c.category in (AUTHORIZED, KEYWORD, PARAPHRASE):
            assert c.expected, c.id
        if c.category == UNAUTHORIZED:
            assert c.forbidden and not c.expected, c.id
        if c.category == MISSING:
            assert not c.expected and not c.forbidden, c.id
    plain = [c for c in CASES if c.category != SCENARIO]
    assert len({(c.persona, c.question) for c in plain}) == len(plain)  # no repeated pair (the same question by two people is a deliberate contrast)


# ---------------------------------------------------------------- a complete run in the test world

def snapshot(pg):
    """Everything the scenarios change, so we can prove each one put it back."""
    return {
        "acl": pg.execute("select document_id, principal_type, principal_id, effect, permission, expires_at from document_acl order by 1,2,3,4,5").fetchall(),
        "users": pg.execute("select email, department_id, clearance_level, country, is_active from users order by 1").fetchall(),
        "docs": pg.execute("select title, status, deleted_at, allowed_countries from documents order by 1").fetchall(),
        "groups": pg.execute("select user_id, group_id from user_groups order by 1,2").fetchall(),
        "chunks": pg.execute("select document_id, chunk_index, is_active, left(content, 40) from document_chunks order by 1,2").fetchall(),
    }


@pytest.fixture
def world(pg):
    return eval_world.build(pg)


def test_the_oracle_agrees_with_the_designed_access(pg, world):
    with SyncSession() as s:
        o = Oracle(s)
        assert not o.can_read("swara@demo", "Salary bands 2026") and not o.can_read("shivam@demo", "Salary bands 2026")  # even the CEO: a personal deny
        assert o.can_read("dhanashree@demo", "Salary bands 2026") and o.can_read("shivam@demo", "Executive compensation plan")
        assert not o.can_read("prashant@demo", "Board meeting minutes Q2") and not o.can_read("prashant@demo", "Executive compensation plan")  # admin is not reader
        assert not o.can_read("pranav@demo", "Q3 revenue report FY2026") and o.can_read("pranav@demo", "Expense reimbursement policy")  # clearance gate
        assert not o.can_read("former@demo", "Leave policy")  # inactive
        assert "Salary bands 2026" in o.forbidden_titles("swara@demo") and "Leave policy" not in o.forbidden_titles("swara@demo")


def test_the_whole_suite_runs_clean_with_zero_leakage_and_puts_everything_back(pg, world, client):
    before = snapshot(pg)
    report = run_suite(live=False, reranker=eval_world.StrictOverlapReranker(), client=client)
    failed = [(r.case.id, r.detail, [(l.where, l.kind) for l in r.leaks]) for r in report.results if not r.passed]
    assert report.leak_count == 0, [(r.case.id, [(l.where, l.kind, l.token) for l in r.leaks]) for r in report.results if r.leaks]
    assert not failed, failed
    assert len(report.results) == 62 and report.passed == 62
    m = report.metrics
    assert m["leakage_cases"] == 0 and m["leakage_hits"] == 0
    assert m["recall_at_5"] >= 0.85 and m["citation_correctness"] >= 0.9 and m["refusal_accuracy"] >= 0.9
    assert m["scenarios_passed"] == "14/14" and all(v.split("/")[0] == v.split("/")[1] for v in m["by_category"].values())
    assert [t["set_up"] for t in report.mode_table] == ["keyword", "vector", "hybrid", "hybrid + reranker"]
    assert all(0.0 <= t["recall_at_5"] <= 1.0 and t["p95_ms"] >= 0 for t in report.mode_table)
    assert snapshot(pg) == before  # every scenario undid its changes
    text = render_markdown(report)
    assert "Unauthorized leakage" in text and "Failed cases" not in text


def test_a_planted_leak_is_caught_by_the_scanner_and_fails_the_run(pg, world, monkeypatch, client):
    original = ExtractiveFakeLlm.complete

    def leaky(self, system, user, max_output_tokens):
        result = original(self, system, user, max_output_tokens)
        data = json.loads(result.text)
        if data["can_answer"]:
            data["answer"] = data["answer"].replace(" [S1]", " CANARY-HR-SALARY-7F3A [S1]")  # a model that blurts out a forbidden marker
            result.text = json.dumps(data)
        return result

    monkeypatch.setattr(ExtractiveFakeLlm, "complete", leaky)
    report = run_suite(live=False, reranker=eval_world.StrictOverlapReranker(), categories={AUTHORIZED}, with_modes=False, client=client)
    swara = [r for r in report.results if r.case.persona == "swara@demo"]  # swara may not read the salary bands
    assert swara and all(r.leaked and not r.passed for r in swara)
    assert {(l.where, l.kind, l.token) for r in swara for l in r.leaks} >= {("chat response", "CANARY", "CANARY-HR-SALARY-7F3A")}
    shivam = [r for r in report.results if r.case.persona == "shivam@demo"]  # a personal deny: the CEO may not read them either
    assert all(r.leaked for r in shivam)
    assert report.metrics["leakage_cases"] > 0 and report.leak_count > 0


def test_a_scenario_undoes_its_changes_even_when_a_step_fails(pg, world, monkeypatch, client):
    from app.eval import runner

    before = snapshot(pg)

    def boom(*a, **k):
        def step():
            raise RuntimeError("step failed")
        return step

    monkeypatch.setattr(runner, "_not_from", boom)
    case = next(c for c in CASES if c.scenario == "REVOCATION")
    with runner._Run(False, eval_world.StrictOverlapReranker(), client) as run, pytest.raises(RuntimeError):
        runner._scn_revocation(run, case)
    assert snapshot(pg) == before  # the deny rule that the scenario added is gone again


def test_the_fake_model_cites_the_first_passage_and_declines_without_one():
    llm = ExtractiveFakeLlm()
    out = json.loads(llm.complete("s", '<question>\nq\n</question>\n<sources>\n<source id="S1" title="T">\nKey facts\n\nLeave is 24 days. More text.\n</source>\n</sources>', 100).text)
    assert out == {"can_answer": True, "answer": "Leave is 24 days. [S1]", "citations": ["S1"]}
    assert json.loads(llm.complete("s", "<sources>\n</sources>", 100).text)["can_answer"] is False
    assert sorted(Counter(c.category for c in CASES)) == sorted(COUNTS)


# ---------------------------------------------------------------- a leak in ANY place the scanner covers is found

CANARY = "CANARY-HR-SALARY-7F3A"  # the salary bands document: swara may not read it


@pytest.mark.parametrize("place", ["model prompt", "logs", "audit rows", "search response"])
def test_a_leak_planted_in_each_place_is_found_in_that_place(pg, world, monkeypatch, client, place):
    import logging

    from app.answers import service as answers_service
    from app.audit import service as audit_service
    from app.api.v1 import search as search_route

    if place == "model prompt":
        real = answers_service.build_user_message
        monkeypatch.setattr(answers_service, "build_user_message", lambda q, hits: real(q, hits) + " " + CANARY)
    elif place == "logs":
        original = ExtractiveFakeLlm.complete

        def noisy(self, system, user, max_output_tokens):
            logging.getLogger("leaky").warning("retrieved %s", CANARY)
            return original(self, system, user, max_output_tokens)

        monkeypatch.setattr(ExtractiveFakeLlm, "complete", noisy)
    elif place == "audit rows":
        real_row = audit_service.add_answer_row

        def tainted(db, query_row, result):
            row = real_row(db, query_row, result)
            row.refusal_reason = CANARY
            return row

        monkeypatch.setattr("app.api.v1.chat.add_answer_row", tainted)
    else:
        original_run = search_route._run

        def leaky_search(user_id, query, mode):
            hits, count = original_run(user_id, query, mode)
            if hits:
                hits[0].document_title = "Salary bands 2026"  # a forbidden title in the search results
            return hits, count

        monkeypatch.setattr(search_route, "_run", leaky_search)
    report = run_suite(live=False, reranker=eval_world.StrictOverlapReranker(), case_ids={"A01"}, with_modes=False, client=client)
    (result,) = report.results
    assert result.leaked and not result.passed
    assert place in {leak.where for leak in result.leaks}, [(l.where, l.kind) for l in result.leaks]


def test_a_forbidden_id_in_the_audit_rows_or_a_logged_question_is_found(pg, world, monkeypatch, client):
    import logging

    original = ExtractiveFakeLlm.complete

    def chatty(self, system, user, max_output_tokens):
        logging.getLogger("leaky").warning("question was: %s", "When must I acknowledge a page when I am on call?")  # the question text in a log
        return original(self, system, user, max_output_tokens)

    monkeypatch.setattr(ExtractiveFakeLlm, "complete", chatty)
    (result,) = run_suite(live=False, reranker=eval_world.StrictOverlapReranker(), case_ids={"A01"}, with_modes=False, client=client).results
    assert result.leaked and ("logs", "QUESTION") in {(l.where, l.kind) for l in result.leaks}


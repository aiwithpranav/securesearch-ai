"""Phase 7B: the evaluation API, the command line and how runs are saved. Starting a run needs a system administrator;
a live (paid) run needs an explicit confirmation; results never hold an answer or a document text."""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.eval import runner
from app.eval.cases import AUTHORIZED, CASES
from app.eval.runner import CaseResult, ExtractiveFakeLlm, RunReport
from app.llm import LlmNotConfigured
from app.scripts import run_eval
from tests import eval_world

NOTHING = uuid.UUID("00000000-0000-0000-0000-000000000000")


@pytest.fixture
def people(api, make_user):
    make_user("boss@demo", roles=("employee", "system_admin"))
    make_user("sec@demo", roles=("employee", "security_admin"))
    make_user("aud@demo", roles=("employee", "auditor"))
    make_user("emp@demo")
    return {name: api.signed_in(email)[0] for name, email in (("admin", "boss@demo"), ("security", "sec@demo"), ("auditor", "aud@demo"), ("employee", "emp@demo"))}


class FakePopen:
    calls: list[list[str]] = []

    def __init__(self, command, **kwargs):
        FakePopen.calls.append(command)
        assert kwargs.get("start_new_session") is True


@pytest.fixture(autouse=True)
def popen(monkeypatch):
    FakePopen.calls = []
    monkeypatch.setattr("app.api.v1.evaluation.subprocess.Popen", FakePopen)
    return FakePopen


def start(api, token, **body):
    return api.request("POST", "/evaluation/runs", token=token, json=body)


# ---------------------------------------------------------------- who may use it

@pytest.mark.parametrize("method, path", [
    ("POST", "/evaluation/runs"), ("GET", "/evaluation/runs"), ("GET", f"/evaluation/runs/{NOTHING}"), ("GET", f"/evaluation/runs/{NOTHING}/failures"),
])
def test_only_a_system_administrator_may_use_the_evaluation(api, people, popen, method, path):
    kw = {"json": {}} if method == "POST" else {}
    assert api.request(method, path, **kw).status_code == 401
    for who in ("employee", "security", "auditor"):
        assert api.request(method, path, token=people[who], **kw).status_code == 403, who
    assert api.request(method, path, token=people["admin"], **kw).status_code in (200, 202, 404)
    assert popen.calls == [] or method == "POST"


# ---------------------------------------------------------------- starting a run

def test_a_free_run_is_started_in_its_own_process_and_recorded(api, people, popen, pg):
    r = start(api, people["admin"], label="nightly check")
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "RUNNING" and body["model_mode"] == "FAKE_MODEL" and body["label"] == "nightly check" and body["total"] == 0
    (command,) = popen.calls
    assert command[1:4] == ["-m", "app.scripts.run_eval", "--run-id"] and command[4] == body["id"] and "--live" not in command
    assert pg.execute("select status, model_mode from eval_runs").fetchone() == ("RUNNING", "FAKE_MODEL")


def test_only_one_run_at_a_time_and_a_stale_one_does_not_block(api, people, popen, pg):
    assert start(api, people["admin"]).status_code == 202
    assert start(api, people["admin"]).status_code == 409 and len(popen.calls) == 1
    pg.execute("update eval_runs set started_at = %s", (datetime.now(timezone.utc) - timedelta(minutes=31),))
    assert start(api, people["admin"]).status_code == 202


def test_a_live_run_needs_confirmation_a_key_and_says_what_it_costs(api, people, popen, monkeypatch):
    r = start(api, people["admin"], live=True)
    assert r.status_code == 422 and r.json()["estimated_usd"] > 0 and r.json()["questions"] > 60 and popen.calls == []
    monkeypatch.setattr("app.api.v1.evaluation.get_llm", lambda: (_ for _ in ()).throw(LlmNotConfigured("not_configured")))
    r = start(api, people["admin"], live=True, confirm_cost=True)
    assert r.status_code == 503 and "key" in r.json()["detail"] and popen.calls == []
    monkeypatch.setattr("app.api.v1.evaluation.get_llm", lambda: object())
    r = start(api, people["admin"], live=True, confirm_cost=True)
    assert r.status_code == 202 and r.json()["model_mode"] == "LIVE_MODEL"
    assert popen.calls[0][-2:] == ["--live", "--yes"]


def test_the_evaluation_does_not_run_in_production(api, people, popen, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    assert start(api, people["admin"]).status_code == 403 and popen.calls == []


def test_a_start_that_fails_is_recorded_as_failed(api, people, monkeypatch, pg):
    def broken(*a, **k):
        raise OSError("no process")

    monkeypatch.setattr("app.api.v1.evaluation.subprocess.Popen", broken)
    assert start(api, people["admin"]).status_code == 503
    assert pg.execute("select status, summary from eval_runs").fetchone() == ("FAILED", {"error": "COULD_NOT_START"})


@pytest.mark.parametrize("body", [{"label": "x" * 81}, {"live": "yes"}, {"confirm_cost": 3}])
def test_bad_start_requests_are_refused(api, people, popen, body):
    assert start(api, people["admin"], **body).status_code == 422 and popen.calls == []


# ---------------------------------------------------------------- reading runs

def insert_run(pg):
    rid = pg.execute(
        "insert into eval_runs (label, model_mode, status, finished_at, total, passed, leak_count, summary) values ('seeded','FAKE_MODEL','DONE', now(), 2, 1, 0, %s) returning id",
        (json.dumps({"metrics": {"recall_at_5": 0.9}, "mode_table": []}),),
    ).fetchone()[0]
    pg.execute("insert into eval_cases (id, category, persona, question, definition) values ('A01','AUTHORIZED','swara@demo','How many days?','{}'),('U01','UNAUTHORIZED','swara@demo','Secret?','{}')")
    pg.execute("insert into eval_results (run_id, case_id, category, passed, leaked, latency_ms, detail) values (%s,'A01','AUTHORIZED',true,false,120,'{}'),(%s,'U01','UNAUTHORIZED',false,true,80,%s)",
               (rid, rid, json.dumps({"leaks": [{"where": "chat response", "kind": "CANARY"}]})))
    return rid


def test_runs_can_be_listed_opened_and_filtered_to_their_failures(api, people, pg):
    rid = insert_run(pg)
    runs = api.request("GET", "/evaluation/runs", token=people["admin"]).json()
    assert [r["id"] for r in runs] == [str(rid)] and runs[0]["summary"]["metrics"]["recall_at_5"] == 0.9
    detail = api.request("GET", f"/evaluation/runs/{rid}", token=people["admin"]).json()
    assert detail["total"] == 2 and [r["case_id"] for r in detail["results"]] == ["A01", "U01"]
    assert detail["results"][0] == {"case_id": "A01", "category": "AUTHORIZED", "persona": "swara@demo", "question": "How many days?", "passed": True, "leaked": False, "latency_ms": 120, "detail": {}}
    failures = api.request("GET", f"/evaluation/runs/{rid}/failures", token=people["admin"]).json()
    assert [f["case_id"] for f in failures] == ["U01"] and failures[0]["leaked"] and failures[0]["detail"]["leaks"] == [{"where": "chat response", "kind": "CANARY"}]
    assert api.request("GET", f"/evaluation/runs/{uuid.uuid4()}", token=people["admin"]).status_code == 404
    assert api.request("GET", f"/evaluation/runs/{uuid.uuid4()}/failures", token=people["admin"]).status_code == 404
    assert api.request("GET", "/evaluation/runs?limit=0", token=people["admin"]).status_code == 422


def test_the_evaluation_schemas_have_no_field_for_answers_or_document_text(client):
    schemas = client.get("/api/openapi.json").json()["components"]["schemas"]
    for name in ("RunOut", "ResultOut", "RunDetail"):
        assert not (set(schemas[name]["properties"]) & {"answer", "answer_text", "content", "text", "snippet", "chunks"}), name


# ---------------------------------------------------------------- saving a run

def test_a_saved_run_keeps_ids_and_places_but_never_the_leaked_text(pg, client, monkeypatch):
    eval_world.build(pg)
    original = ExtractiveFakeLlm.complete

    def leaky(self, system, user, max_output_tokens):
        result = original(self, system, user, max_output_tokens)
        data = json.loads(result.text)
        if data["can_answer"]:
            data["answer"] = data["answer"].replace(" [S1]", " CANARY-HR-SALARY-7F3A [S1]")
            result.text = json.dumps(data)
        return result

    monkeypatch.setattr(ExtractiveFakeLlm, "complete", leaky)
    report = runner.run_suite(live=False, reranker=eval_world.StrictOverlapReranker(), categories={AUTHORIZED}, with_modes=False, client=client)
    run_id = runner.create_run_row("saved", report.model_mode, None)
    runner.finish_run_row(run_id, report)
    row = pg.execute("select status, total, passed, leak_count from eval_runs where id = %s", (run_id,)).fetchone()
    assert row[0] == "DONE" and row[1] == 20 and row[3] > 0
    dump = json.dumps([list(r) for r in pg.execute("select detail, case_id from eval_results where run_id = %s", (run_id,)).fetchall()], default=str)
    assert "CANARY-HR-SALARY-7F3A" not in dump and "chat response" in dump  # where it leaked is kept, what leaked is not
    assert pg.execute("select count(*) from eval_cases").fetchone()[0] == len(CASES)
    runner.fail_run_row(run_id, "ValueError")
    assert pg.execute("select status, summary from eval_runs where id = %s", (run_id,)).fetchone() == ("FAILED", {"error": "ValueError"})


# ---------------------------------------------------------------- the command line

def stub_report(leaks=0, failed=0):
    case = CASES[0]
    from app.eval.scanner import Leak

    results = [CaseResult(case, True)] * (3 - failed) + [CaseResult(case, False, [Leak("chat response", "CANARY", "x")] * leaks)] * failed
    return RunReport("FAKE_MODEL", results, {"leakage_cases": leaks, "leakage_hits": leaks, "recall_at_5": 1.0, "mrr": 1.0, "citation_correctness": 1.0,
                                            "refusal_accuracy": 1.0, "answer_rate": 1.0, "answer_rate_by_category": {}, "scenarios_passed": "0/0", "p95_answer_ms": 1, "p95_search_ms": 1, "by_category": {}},
                     [], datetime.now(timezone.utc), datetime.now(timezone.utc))


@pytest.mark.parametrize("report, code", [(stub_report(), 0), (stub_report(failed=1), 2), (stub_report(leaks=1, failed=1), 1)])
def test_the_command_line_exit_code_tells_pass_failure_or_leak(monkeypatch, report, code, capsys):
    monkeypatch.setattr(run_eval, "run_suite", lambda **k: report)
    assert run_eval.main([]) == code
    assert "Unauthorized leakage" in capsys.readouterr().out


def test_a_live_run_from_the_command_line_needs_a_key_and_a_yes(monkeypatch, capsys):
    monkeypatch.setattr(run_eval, "run_suite", lambda **k: (_ for _ in ()).throw(AssertionError("must not run")))
    monkeypatch.setattr(run_eval, "get_llm", lambda: (_ for _ in ()).throw(LlmNotConfigured("not_configured")))
    assert run_eval.main(["--live", "--yes"]) == 3 and "No OPENAI_API_KEY" in capsys.readouterr().out
    monkeypatch.setattr(run_eval, "get_llm", lambda: object())
    assert run_eval.main(["--live"]) == 3 and "Add --yes" in capsys.readouterr().out


def test_the_command_line_refuses_to_run_in_production(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    assert run_eval.main([]) == 1


def test_a_crash_is_reported_and_recorded_not_hidden(monkeypatch, pg, capsys):
    monkeypatch.setattr(run_eval, "run_suite", lambda **k: (_ for _ in ()).throw(LookupError("the demo people are missing")))
    assert run_eval.main(["--save"]) == 4 and "could not run" in capsys.readouterr().out
    assert pg.execute("select status, summary from eval_runs").fetchone() == ("FAILED", {"error": "LookupError"})

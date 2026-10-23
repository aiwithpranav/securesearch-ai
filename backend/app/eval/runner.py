"""The evaluation runner (Phase 7B).

It asks the 62 cases of `cases.py` through the real HTTP API in-process (so routes, the access resolver, the retrieval
engine, the answer engine, the audit trail and the logs are all the real ones), as each demo person in turn, and
checks three kinds of things:

1. LEAKAGE (must be zero): for every question, everything the person could receive or that is recorded about the
   request is scanned for the canary strings, ids and titles of every document that person may NOT read.
2. QUALITY: Recall@5, MRR, citation correctness, refusal accuracy and speed, plus a comparison of keyword, vector,
   hybrid and hybrid plus reranker search.
3. SCENARIOS: the system changes under a person's feet (a rule is revoked, a group membership ends, a document is
   deleted ...) and the very next question must reflect it. Every change is undone afterwards.

By default a FAKE model writes the answers (free, repeatable, used in CI). A live run uses the real model: the caller
must ask for it on purpose, and the cost is estimated first. The fake model measures the pipeline (retrieval,
confidence gate, validation, refusals, leakage); only a live run measures the real model's wording.

Safety: results hold ids, code words, numbers and the (synthetic) question. Never an answer text, never document text."""
import json
import logging
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select, text

from app.answers.service import ANSWERED, REFUSAL_TEXT
from app.api.deps import get_current_user
from app.core.config import settings
from app.db.sync import SyncSession
from app.eval import metrics as mt
from app.eval.cases import (
    AUTHORIZED,
    CASES,
    KEYWORD,
    MISSING,
    PARAPHRASE,
    RETRIEVAL_CATEGORIES,
    SCENARIO,
    UNAUTHORIZED,
    Case,
)
from app.eval.corpus import CANARIES
from app.eval.oracle import Oracle
from app.eval.scanner import Forbidden, Leak, scan_without_question
from app.llm import LlmResult, get_llm, set_llm
from app.models import DocumentChunk, EvalCase, EvalResult, EvalRun, User
from app.retrieval.search import retrieve

CONFIGS = [("keyword", "keyword", False), ("vector", "vector", False), ("hybrid", "hybrid", False), ("hybrid + reranker", "hybrid", True)]
COST_PER_CHAT_USD = 650 * 0.15e-6 + 60 * 0.6e-6  # GPT-4o mini: about 650 tokens in, 60 out per answer


def estimate_live_cost() -> dict[str, float]:
    """An upper estimate for a live run (every chat question might reach the model)."""
    chats = len(CASES) + 12  # the cases plus the extra questions inside scenarios
    return {"questions": chats, "estimated_usd": round(chats * COST_PER_CHAT_USD, 4)}


# --------------------------------------------------------------------------------------------- the fake model

class ExtractiveFakeLlm:
    """Plays the model without any cost: answers with the first sentence of the first passage and cites it."""

    def complete(self, system: str, user: str, max_output_tokens: int) -> LlmResult:
        m = re.search(r'<source id="S1"[^>]*>\n(.*?)\n</source>', user, re.S)
        if not m:
            return LlmResult(json.dumps({"can_answer": False, "answer": "", "citations": []}), 0, 0)
        body = [line for line in m.group(1).splitlines() if line.strip() and not line.startswith("Key facts")]
        sentence = re.split(r"(?<=[.!?])\s", " ".join(body))[0][:200].replace("<", "").replace(">", "")
        return LlmResult(json.dumps({"can_answer": True, "answer": f"{sentence} [S1]", "citations": ["S1"]}), 0, 0)


class RecordingLlm:
    def __init__(self, inner) -> None:  # noqa: ANN001
        self.inner = inner
        self.prompts: list[str] = []

    def complete(self, system: str, user: str, max_output_tokens: int) -> LlmResult:
        self.prompts.append(user)
        return self.inner.complete(system, user, max_output_tokens)


class _LogCatcher(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(f"{record.getMessage()} {getattr(record, 'fields', '')}")


# --------------------------------------------------------------------------------------------- results

@dataclass
class Exchange:
    status: str = ""  # chat status, or "HTTP 503" and so on
    chat: dict = field(default_factory=dict)  # type: ignore[type-arg]
    search: dict = field(default_factory=dict)  # type: ignore[type-arg]
    prompts: list[str] = field(default_factory=list)
    audit: str = ""
    logs: str = ""
    chat_ms: int = 0
    search_ms: int = 0

    def cited_titles(self) -> list[str]:
        return [c["document_title"] for c in self.chat.get("citations", [])]

    def refused_uniformly(self) -> bool:
        return self.status != ANSWERED and self.chat.get("answer") is None and self.chat.get("refusal") == REFUSAL_TEXT and not self.chat.get("citations")


@dataclass
class CaseResult:
    case: Case
    passed: bool
    leaks: list[Leak] = field(default_factory=list)
    latency_ms: int = 0
    detail: dict = field(default_factory=dict)  # type: ignore[type-arg]

    @property
    def leaked(self) -> bool:
        return bool(self.leaks)


@dataclass
class RunReport:
    model_mode: str
    results: list[CaseResult]
    metrics: dict  # type: ignore[type-arg]
    mode_table: list[dict]  # type: ignore[type-arg]
    started_at: datetime
    finished_at: datetime

    @property
    def leak_count(self) -> int:
        return sum(len(r.leaks) for r in self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)


# --------------------------------------------------------------------------------------------- the session of one run

class _Run:
    def __init__(self, live: bool, reranker, client=None) -> None:  # noqa: ANN001
        from fastapi.testclient import TestClient

        from app.main import app

        self.app = app
        self._owned = None
        if client is None:  # one client for the whole run keeps one event loop (the database and Redis connections live in it)
            self._owned = TestClient(app)
            client = self._owned.__enter__()
        self.client = client
        self.live = live
        self.reranker = reranker
        self.current: dict[str, User] = {}
        self.llm = RecordingLlm(get_llm() if live else ExtractiveFakeLlm())
        self.catcher = _LogCatcher()
        self.counter = 0
        self._saved: dict[str, object] = {}

    # -- setup and teardown
    def __enter__(self) -> "_Run":
        for name in ("chat_limit_per_minute", "search_limit_per_minute", "preview_limit_per_minute"):
            self._saved[name] = getattr(settings, name)
            setattr(settings, name, 10**9)  # the evaluation asks many questions quickly
        set_llm(self.llm)
        if self.reranker is not None:
            from app.retrieval.reranker import set_reranker

            set_reranker(self.reranker)
        logging.getLogger().addHandler(self.catcher)
        self.app.dependency_overrides[get_current_user] = lambda: self.current["user"]
        return self

    def __exit__(self, *exc: object) -> None:
        self.app.dependency_overrides.pop(get_current_user, None)
        logging.getLogger().removeHandler(self.catcher)
        set_llm(None)
        if self.reranker is not None:
            from app.retrieval.reranker import set_reranker

            set_reranker(None)
        for name, value in self._saved.items():
            setattr(settings, name, value)
        if self._owned is not None:
            self._owned.__exit__(None, None, None)

    # -- helpers
    def user(self, email: str) -> User:
        with SyncSession() as s:
            u = s.scalar(select(User).where(User.email == email))
            if u is None:
                raise LookupError(f"The person {email} does not exist; load the demo people first.")
            _ = u.role_names
            return u

    def sql(self, statement: str, **params: object) -> bool:
        """Runs one statement and saves it. Returns True so a scenario step can use it inside an expression."""
        with SyncSession() as s:
            s.execute(text(statement), params)
            s.commit()
        return True

    def user_group(self, name: str) -> int:
        with SyncSession() as s:
            return int(s.scalar(text("select id from groups where name = :n"), {"n": name}) or 0)

    def forbidden_for(self, email: str) -> Forbidden:
        with SyncSession() as s:
            titles = Oracle(s).forbidden_titles(email)
            ids = {str(i) for (i,) in s.execute(text("select id from documents where title = any(:t)"), {"t": list(titles)})}
            ids |= {str(i) for (i,) in s.execute(text("select c.id from document_chunks c join documents d on d.id = c.document_id where d.title = any(:t)"), {"t": list(titles)})}
        return Forbidden({CANARIES[t] for t in titles if t in CANARIES}, ids, titles)

    def ask(self, email: str, question: str, extra: dict | None = None, search: bool = True) -> Exchange:  # type: ignore[type-arg]
        self.counter += 1
        self.current["user"] = self.user(email)
        rid = f"eval-{uuid.uuid4().hex[:12]}"
        mark = len(self.llm.prompts)
        mark_logs = len(self.catcher.lines)
        ex = Exchange()
        t = time.perf_counter()
        r = self.client.post("/api/v1/chat", json={"question": question, **(extra or {})}, headers={"X-Request-ID": rid})
        ex.chat_ms = int((time.perf_counter() - t) * 1000)
        ex.chat = r.json() if r.headers.get("content-type", "").startswith("application/") else {}
        ex.status = ex.chat.get("status", f"HTTP {r.status_code}") if r.status_code == 200 else f"HTTP {r.status_code}"
        if search:
            t = time.perf_counter()
            r2 = self.client.post("/api/v1/search", json={"query": question}, headers={"X-Request-ID": rid + "s"})
            ex.search_ms = int((time.perf_counter() - t) * 1000)
            ex.search = r2.json() if r2.status_code == 200 else {}
        ex.prompts = self.llm.prompts[mark:]
        ex.logs = "\n".join(self.catcher.lines[mark_logs:])
        with SyncSession() as s:
            rows = s.execute(text(
                "select q.kind, q.filters, q.allowed_doc_count, q.retrieved_chunk_ids, q.response_status, a.citation_chunk_ids, a.refusal_reason "
                "from query_audit_logs q left join answer_audit_logs a on a.query_audit_id = q.id where q.request_id in (:a, :b)"
            ), {"a": rid, "b": rid + "s"}).all()  # (the question text column is left out on purpose: it is the person's own words)
            ex.audit = json.dumps([[str(c) for c in row] for row in rows])
        return ex

    def leaks(self, email: str, ex: Exchange, question: str, forbidden: Forbidden | None = None) -> list[Leak]:
        blobs = {
            "chat response": json.dumps(ex.chat), "search response": json.dumps(ex.search), "model prompt": "\n".join(ex.prompts),
            "audit rows": ex.audit, "logs": ex.logs,
        }
        found = scan_without_question(blobs, forbidden or self.forbidden_for(email), question)
        if question.strip() and len(question) > 12 and question in ex.logs:  # the question text must not be logged
            found.append(Leak("logs", "QUESTION", "the question text itself"))
        return found

    def titles(self, email: str, question: str, mode: str, rerank: bool) -> tuple[list[str], int]:
        uid = self.user(email).id
        t = time.perf_counter()
        with SyncSession() as s:
            hits = retrieve(s, uid, question, mode=mode, rerank=rerank, final_k=10)
        return [h.document_title for h in hits], int((time.perf_counter() - t) * 1000)


# --------------------------------------------------------------------------------------------- one case

def _run_case(run: _Run, case: Case) -> CaseResult:
    if case.category == SCENARIO:
        return SCENARIOS[case.scenario](run, case)
    ex = run.ask(case.persona, case.question)
    leaks = run.leaks(case.persona, ex, case.question)
    detail: dict = {"status": ex.status, "cited": ex.cited_titles()}  # type: ignore[type-arg]
    if case.category == AUTHORIZED:
        ok = ex.status == ANSWERED and any(t in case.expected for t in ex.cited_titles())
    elif case.category in (UNAUTHORIZED, MISSING):
        ok = ex.refused_uniformly()
        if case.category == UNAUTHORIZED:
            with SyncSession() as s:
                oracle = Oracle(s)
                assert all(not oracle.can_read(case.persona, t) for t in case.forbidden), f"{case.id}: the case is not set up as unauthorized"
    else:  # KEYWORD and PARAPHRASE: the right document must be in the top k of the hybrid search
        ranked, _ = run.titles(case.persona, case.question, "hybrid", True)
        ok = mt.recall_at_k(ranked, case.expected, case.top_k) == 1.0
        detail["top"] = ranked[: case.top_k]
    return CaseResult(case, ok and not leaks, leaks, ex.chat_ms, detail)


# --------------------------------------------------------------------------------------------- scenarios

def _steps(run: _Run, case: Case, steps: list[tuple[str, Callable[[], tuple[bool, list[Leak]]]]]) -> CaseResult:
    """Runs named steps in order; every step must pass. Leaks of any step are collected."""
    all_leaks: list[Leak] = []
    detail: dict[str, bool] = {}
    ok = True
    t = time.perf_counter()
    for name, step in steps:
        passed, leaks = step()
        detail[name] = passed
        all_leaks += leaks
        ok = ok and passed
    return CaseResult(case, ok and not all_leaks, all_leaks, int((time.perf_counter() - t) * 1000), {"steps": detail})


def _answered(run: _Run, case: Case, email: str, question: str, expected: str, extra: dict | None = None):  # type: ignore[no-untyped-def]
    def step() -> tuple[bool, list[Leak]]:
        ex = run.ask(email, question, extra, search=False)
        return ex.status == ANSWERED and expected in ex.cited_titles(), run.leaks(email, ex, question)
    return step


def _refused(run: _Run, case: Case, email: str, question: str, extra: dict | None = None):  # type: ignore[no-untyped-def]
    def step() -> tuple[bool, list[Leak]]:
        ex = run.ask(email, question, extra, search=True)
        return ex.refused_uniformly(), run.leaks(email, ex, question)  # (the search may still show passages of documents the person CAN read)
    return step


def _not_from(run: _Run, case: Case, email: str, question: str, title: str):  # type: ignore[no-untyped-def]
    """After a revocation: the document must not be cited or shown any more. Another document the person may still read
    can legitimately answer a similar question, so a refusal is not required here."""
    def step() -> tuple[bool, list[Leak]]:
        ex = run.ask(email, question, None, search=True)
        shown = [h["document_title"] for h in ex.search.get("hits", [])]
        return title not in ex.cited_titles() and title not in shown, run.leaks(email, ex, question)
    return step


def _doc_id(title: str) -> str:
    with SyncSession() as s:
        return str(s.scalar(text("select id from documents where title = :t"), {"t": title}))


def _user_id(email: str) -> str:
    with SyncSession() as s:
        return str(s.scalar(text("select id from users where email = :e"), {"e": email}))


def _scn_revocation(run: _Run, case: Case) -> CaseResult:
    doc, uid = _doc_id("Sales commission plan"), _user_id(case.persona)
    q = case.question
    try:
        return _steps(run, case, [
            ("allowed first", _answered(run, case, case.persona, q, "Sales commission plan")),
            ("deny added", lambda: (run.sql("insert into document_acl (document_id, principal_type, principal_id, effect, permission) values (:d,'USER',:u,'DENY','READ')", d=doc, u=uid), (True, []))[1]),
            ("no longer used or shown", _not_from(run, case, case.persona, q, "Sales commission plan")),
        ])
    finally:
        run.sql("delete from document_acl where document_id = :d and principal_type = 'USER' and principal_id = :u and effect = 'DENY'", d=doc, u=uid)


def _scn_group_removal(run: _Run, case: Case) -> CaseResult:
    uid = _user_id(case.persona)
    gid = run.user_group("SRE")
    try:
        return _steps(run, case, [
            ("allowed through the group", _answered(run, case, case.persona, case.question, "Support SLA by plan")),
            ("removed", lambda: (run.sql("delete from user_groups where user_id = :u and group_id = :g", u=uid, g=gid), (True, []))[1]),
            ("no longer used or shown", _not_from(run, case, case.persona, case.question, "Support SLA by plan")),
        ])
    finally:
        run.sql("insert into user_groups (user_id, group_id) values (:u, :g) on conflict do nothing", u=uid, g=gid)


def _scn_department_change(run: _Run, case: Case) -> CaseResult:
    with SyncSession() as s:
        old = s.scalar(text("select department_id from users where email = :e"), {"e": case.persona})
        finance = s.scalar(text("select id from departments where name = 'Finance'"))
    try:
        return _steps(run, case, [
            ("allowed in Sales", _answered(run, case, case.persona, case.question, "Sales onboarding guide")),
            ("moved to Finance", lambda: (run.sql("update users set department_id = :d where email = :e", d=finance, e=case.persona), (True, []))[1]),
            ("refused at once", _refused(run, case, case.persona, case.question)),
        ])
    finally:
        run.sql("update users set department_id = :d where email = :e", d=old, e=case.persona)


def _scn_expired_acl(run: _Run, case: Case) -> CaseResult:
    doc, uid = _doc_id("Intellectual property register"), _user_id(case.persona)
    insert = ("insert into document_acl (document_id, principal_type, principal_id, effect, permission, expires_at) "
              "values (:d,'USER',:u,'ALLOW','READ', now() + (:i)::interval)")
    try:
        return _steps(run, case, [
            ("expired allow added", lambda: (run.sql(insert, d=doc, u=uid, i="-1 hour"), (True, []))[1]),
            ("refused", _refused(run, case, case.persona, case.question)),
            ("live allow added", lambda: (run.sql("update document_acl set expires_at = now() + interval '1 hour' where document_id = :d and principal_id = :u", d=doc, u=uid), (True, []))[1]),
            ("answered", _answered(run, case, case.persona, case.question, "Intellectual property register")),
        ])
    finally:
        run.sql("delete from document_acl where document_id = :d and principal_type = 'USER' and principal_id = :u", d=doc, u=uid)


def _scn_deny_beats_allow(run: _Run, case: Case) -> CaseResult:
    doc, uid = _doc_id("Disciplinary case log 2026"), _user_id(case.persona)
    try:
        return _steps(run, case, [
            ("allowed through the HR group", _answered(run, case, case.persona, case.question, "Disciplinary case log 2026")),
            ("company allow and personal deny added", lambda: (run.sql(
                "insert into document_acl (document_id, principal_type, principal_id, effect, permission) values (:d,'COMPANY',null,'ALLOW','READ'),(:d,'USER',:u,'DENY','READ')", d=doc, u=uid), (True, []))[1]),
            ("refused: deny wins", _refused(run, case, case.persona, case.question)),
        ])
    finally:
        run.sql("delete from document_acl where document_id = :d and ((principal_type = 'COMPANY') or (principal_type = 'USER' and principal_id = :u))", d=doc, u=uid)


def _scn_deleted_document(run: _Run, case: Case) -> CaseResult:
    doc = _doc_id("Remote work policy")
    try:
        return _steps(run, case, [
            ("answered first", _answered(run, case, case.persona, case.question, "Remote work policy")),
            ("document deleted", lambda: (run.sql("update documents set deleted_at = now() where id = :d", d=doc), (True, []))[1]),
            ("refused", _refused(run, case, case.persona, case.question)),
        ])
    finally:
        run.sql("update documents set deleted_at = null where id = :d", d=doc)


def _scn_new_version(run: _Run, case: Case) -> CaseResult:
    doc = _doc_id("Travel policy")
    with SyncSession() as s:
        old = s.execute(text("select id, document_version_id, ingestion_job_id, chunk_index from document_chunks where document_id = :d and is_active"), {"d": doc}).all()
    new_text = "Key facts The hotel limit is 12000 units per night in metro cities. Book hotels through the travel desk."
    from app.embeddings import embed_documents, model_label

    vec = "[" + ",".join(f"{x:.7f}" for x in embed_documents([new_text])[0]) + "]"
    new_ids: list[str] = []

    def switch() -> tuple[bool, list[Leak]]:
        with SyncSession() as s:
            s.execute(text("update document_chunks set is_active = false where document_id = :d"), {"d": doc})
            row = old[0]
            new_id = s.scalar(text(
                "insert into document_chunks (document_id, document_version_id, ingestion_job_id, is_active, chunk_index, content, token_count, embedding, embedding_model) "
                "values (:d, :v, :j, true, 99, :c, 20, (:e)::vector, :m) returning id"), {"d": doc, "v": row.document_version_id, "j": row.ingestion_job_id, "c": new_text, "e": vec, "m": model_label()})
            new_ids.append(str(new_id))
            s.commit()
        return True, []

    def newest_only() -> tuple[bool, list[Leak]]:
        ex = run.ask(case.persona, case.question, None, search=False)
        snippets = " ".join(c["snippet"] for c in ex.chat.get("citations", []))
        return ex.status == ANSWERED and "12000" in snippets and "9000" not in snippets and "9000" not in "\n".join(ex.prompts), run.leaks(case.persona, ex, case.question)

    try:
        return _steps(run, case, [
            ("old version answers first", lambda: (_old_has_9000(run, case), [])),
            ("new version switched on", switch),
            ("only the new version is used", newest_only),
        ])
    finally:
        with SyncSession() as s:
            if new_ids:
                s.execute(text("delete from document_chunks where id = :i"), {"i": new_ids[0]})
            s.execute(text("update document_chunks set is_active = true where document_id = :d and id = any(:ids)"), {"d": doc, "ids": [r.id for r in old]})
            s.commit()


def _old_has_9000(run: _Run, case: Case) -> bool:
    ex = run.ask(case.persona, case.question, None, search=False)
    return ex.status == ANSWERED and "9000" in " ".join(c["snippet"] for c in ex.chat.get("citations", []))


def _scn_weak_confidence(run: _Run, case: Case) -> CaseResult:
    def step() -> tuple[bool, list[Leak]]:
        ex = run.ask(case.persona, case.question)
        return ex.refused_uniformly() and not ex.prompts, run.leaks(case.persona, ex, case.question)  # the model was not even asked
    return _steps(run, case, [("refused without asking the model", step)])


def _scn_tampered_request(run: _Run, case: Case) -> CaseResult:
    forged = {"user_id": _user_id("shivam@demo"), "roles": ["system_admin", "executive"], "clearance_level": 4, "department": "HR", "is_admin": True}
    return _steps(run, case, [("forged fields ignored", _refused(run, case, case.persona, case.question, forged))])


def _scn_admin_is_not_reader(run: _Run, case: Case) -> CaseResult:
    return _steps(run, case, [
        ("board minutes not used or shown", _not_from(run, case, case.persona, case.question, "Board meeting minutes Q2")),
        ("compensation refused", _refused(run, case, case.persona, "How big is the chief executive bonus pool?")),
    ])


def _scn_clearance_change(run: _Run, case: Case) -> CaseResult:
    try:
        return _steps(run, case, [
            ("refused at clearance 2", _refused(run, case, case.persona, case.question)),
            ("clearance raised", lambda: (run.sql("update users set clearance_level = 3 where email = :e", e=case.persona), (True, []))[1]),
            ("answered at clearance 3", _answered(run, case, case.persona, case.question, "Q3 revenue report FY2026")),
            ("clearance lowered", lambda: (run.sql("update users set clearance_level = 2 where email = :e", e=case.persona), (True, []))[1]),
            ("refused again", _refused(run, case, case.persona, case.question)),
        ])
    finally:
        run.sql("update users set clearance_level = 2 where email = :e", e=case.persona)


def _scn_country_gate(run: _Run, case: Case) -> CaseResult:
    doc = _doc_id("Remote work policy")
    try:
        return _steps(run, case, [
            ("limited to the US", lambda: (run.sql("update documents set allowed_countries = array['US'] where id = :d", d=doc), (True, []))[1]),
            ("Indian employee refused", _refused(run, case, case.persona, case.question)),
            ("US employee answered", _answered(run, case, "akshay@demo", case.question, "Remote work policy")),
        ])
    finally:
        run.sql("update documents set allowed_countries = null where id = :d", d=doc)


def _scn_inactive_user(run: _Run, case: Case) -> CaseResult:
    try:
        return _steps(run, case, [
            ("deactivated", lambda: (run.sql("update users set is_active = false where email = :e", e=case.persona), (True, []))[1]),
            ("finds nothing", _refused(run, case, case.persona, case.question)),
        ])
    finally:
        run.sql("update users set is_active = true where email = :e", e=case.persona)


def _scn_not_ready(run: _Run, case: Case) -> CaseResult:
    doc = _doc_id("Refund policy")
    try:
        return _steps(run, case, [
            ("answered when ready", _answered(run, case, case.persona, case.question, "Refund policy")),
            ("back to processing", lambda: (run.sql("update documents set status = 'PROCESSING' where id = :d", d=doc), (True, []))[1]),
            ("not used or shown", _not_from(run, case, case.persona, case.question, "Refund policy")),
        ])
    finally:
        run.sql("update documents set status = 'READY' where id = :d", d=doc)


SCENARIOS: dict[str, Callable[[_Run, Case], CaseResult]] = {
    "REVOCATION": _scn_revocation, "GROUP_REMOVAL": _scn_group_removal, "DEPARTMENT_CHANGE": _scn_department_change,
    "EXPIRED_ACL": _scn_expired_acl, "DENY_BEATS_ALLOW": _scn_deny_beats_allow, "DELETED_DOCUMENT": _scn_deleted_document,
    "NEW_VERSION": _scn_new_version, "WEAK_CONFIDENCE": _scn_weak_confidence, "TAMPERED_REQUEST": _scn_tampered_request,
    "ADMIN_IS_NOT_READER": _scn_admin_is_not_reader, "CLEARANCE_CHANGE": _scn_clearance_change, "COUNTRY_GATE": _scn_country_gate,
    "INACTIVE_USER": _scn_inactive_user, "NOT_READY_DOCUMENT": _scn_not_ready,
}


# --------------------------------------------------------------------------------------------- metrics and the whole run

def _metrics(run: _Run, results: list[CaseResult], with_modes: bool) -> tuple[dict, list[dict]]:  # type: ignore[type-arg]
    retrieval = [r for r in results if r.case.category in RETRIEVAL_CATEGORIES]
    table: list[dict] = []  # type: ignore[type-arg]
    if with_modes:
        for label, mode, rerank in CONFIGS:
            recall, rr, times = [], [], []
            for r in retrieval:
                ranked, ms = run.titles(r.case.persona, r.case.question, mode, rerank)
                recall.append(mt.recall_at_k(ranked, r.case.expected, 5))
                rr.append(mt.reciprocal_rank(ranked, r.case.expected))
                times.append(ms)
            table.append({"set_up": label, "recall_at_5": round(sum(recall) / len(recall), 3) if recall else 0.0,
                          "mrr": round(sum(rr) / len(rr), 3) if rr else 0.0, "p95_ms": mt.percentile(times, 95)})
    hybrid = next((t for t in table if t["set_up"] == "hybrid + reranker"), None)
    authorized = [r for r in results if r.case.category == AUTHORIZED]
    decision_cases = [r for r in results if r.case.category in (AUTHORIZED, UNAUTHORIZED, MISSING)]
    chat_ms = [r.latency_ms for r in results if r.case.category != SCENARIO]
    answerable = [r for r in results if r.case.category in RETRIEVAL_CATEGORIES]  # questions that a document can answer
    metrics = {
        "leakage_cases": sum(1 for r in results if r.leaked), "leakage_hits": sum(len(r.leaks) for r in results),
        "recall_at_5": hybrid["recall_at_5"] if hybrid else None, "mrr": hybrid["mrr"] if hybrid else None,
        "citation_correctness": round(mt.ratio(sum(1 for r in authorized if r.passed), len(authorized)), 3),
        "refusal_accuracy": round(mt.ratio(sum(1 for r in decision_cases if r.passed), len(decision_cases)), 3),
        "answer_rate": round(mt.ratio(sum(1 for r in answerable if r.detail.get("status") == ANSWERED), len(answerable)), 3),
        "answer_rate_by_category": {c: f"{sum(1 for r in answerable if r.case.category == c and r.detail.get('status') == ANSWERED)}/{sum(1 for r in answerable if r.case.category == c)}" for c in RETRIEVAL_CATEGORIES},
        "scenarios_passed": f"{sum(1 for r in results if r.case.category == SCENARIO and r.passed)}/{sum(1 for r in results if r.case.category == SCENARIO)}",
        "p95_answer_ms": mt.percentile(chat_ms, 95),
        "p95_search_ms": hybrid["p95_ms"] if hybrid else None,
        "by_category": {c: f"{sum(1 for r in results if r.case.category == c and r.passed)}/{sum(1 for r in results if r.case.category == c)}"
                        for c in (AUTHORIZED, UNAUTHORIZED, MISSING, KEYWORD, PARAPHRASE, SCENARIO)},
    }
    return metrics, table


def run_suite(
    *, live: bool = False, reranker=None, categories: set[str] | None = None, with_modes: bool = True,  # noqa: ANN001
    progress: Callable[[int, int, str], None] | None = None, client=None, case_ids: set[str] | None = None,
) -> RunReport:
    """Runs the cases and returns the report (nothing is saved here; see `save_report`)."""
    started = datetime.now(timezone.utc)
    cases = [c for c in CASES if (categories is None or c.category in categories) and (case_ids is None or c.id in case_ids)]
    results: list[CaseResult] = []
    with _Run(live, reranker, client) as run:
        for i, case in enumerate(cases, 1):
            results.append(_run_case(run, case))
            if progress:
                progress(i, len(cases), case.id)
        metrics, table = _metrics(run, results, with_modes and categories is None and case_ids is None)
    return RunReport("LIVE_MODEL" if live else "FAKE_MODEL", results, metrics, table, started, datetime.now(timezone.utc))


# --------------------------------------------------------------------------------------------- saving

def create_run_row(label: str, model_mode: str, started_by: uuid.UUID | None) -> uuid.UUID:
    with SyncSession() as s:
        row = EvalRun(label=label, model_mode=model_mode, status="RUNNING", started_by=started_by)
        s.add(row)
        s.commit()
        return row.id


def finish_run_row(run_id: uuid.UUID, report: RunReport) -> None:
    with SyncSession() as s:
        for c in CASES:
            s.merge(EvalCase(id=c.id, category=c.category, persona=c.persona, question=c.question,
                             definition={"expected": list(c.expected), "forbidden": list(c.forbidden), "injection": c.injection, "top_k": c.top_k, "scenario": c.scenario}))
        for r in report.results:
            s.add(EvalResult(run_id=run_id, case_id=r.case.id, category=r.case.category, passed=r.passed, leaked=r.leaked, latency_ms=r.latency_ms,
                             detail={**r.detail, "leaks": [{"where": x.where, "kind": x.kind} for x in r.leaks]}))  # where and what kind, never the text
        row = s.get(EvalRun, run_id)
        assert row is not None
        row.status, row.finished_at, row.total, row.passed, row.leak_count = "DONE", report.finished_at, len(report.results), report.passed, report.leak_count
        row.summary = {"metrics": report.metrics, "mode_table": report.mode_table}
        s.commit()


def fail_run_row(run_id: uuid.UUID, code: str) -> None:
    with SyncSession() as s:
        row = s.get(EvalRun, run_id)
        assert row is not None
        row.status, row.finished_at, row.summary = "FAILED", datetime.now(timezone.utc), {"error": code}
        s.commit()


def render_markdown(report: RunReport) -> str:
    """A readable summary of a run (used by the command line and the evaluation report)."""
    m = report.metrics
    lines = [
        f"Model: {report.model_mode}. Cases: {len(report.results)}, passed {report.passed}. Leakage hits: {report.leak_count}.",
        "", "| Measure | Result | Target |", "|---|---|---|",
        f"| Unauthorized leakage (cases) | {m['leakage_cases']} | 0 |",
        f"| Recall@5 (hybrid + reranker) | {m['recall_at_5']} | 0.85 or better |",
        f"| MRR | {m['mrr']} | |",
        f"| Citation correctness | {m['citation_correctness']} | 0.90 or better |",
        f"| Appropriate refusal accuracy | {m['refusal_accuracy']} | 0.90 or better |",
        f"| Answered when a document can answer (authorized, keyword, paraphrase) | {m['answer_rate']} | higher is better; {m['answer_rate_by_category']} |",
        f"| Scenarios passed | {m['scenarios_passed']} | all |",
        f"| P95 search latency (ms) | {m['p95_search_ms']} | under 5000 |",
        f"| P95 answer latency (ms) | {m['p95_answer_ms']} | |",
    ]
    if report.mode_table:
        lines += ["", "| Search set-up | Recall@5 | MRR | P95 ms |", "|---|---|---|---|"]
        lines += [f"| {t['set_up']} | {t['recall_at_5']} | {t['mrr']} | {t['p95_ms']} |" for t in report.mode_table]
    failed = [r for r in report.results if not r.passed]
    if failed:
        lines += ["", "Failed cases:"] + [f"- {r.case.id} ({r.case.category}): {r.detail}" for r in failed]
    return "\n".join(lines)


__all__ = [
    "CaseResult", "CONFIGS", "RunReport", "SCENARIOS", "create_run_row", "estimate_live_cost", "fail_run_row", "finish_run_row",
    "render_markdown", "run_suite", "ExtractiveFakeLlm", "DocumentChunk", "KEYWORD", "PARAPHRASE",
]

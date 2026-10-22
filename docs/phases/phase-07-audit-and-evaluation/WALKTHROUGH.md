# Phase 7 Walkthrough: Audit and evaluation

## Layer 7A: the audit trail (backend)

### 1. What we built
A tamper-resistant record of who asked what and what happened, readable only by security staff. There is no screen yet (7C). It answers the auditor's questions: who asked, when, which question, how many documents they could read, which passages were retrieved and cited, how it ended, how long it took, and what administrators changed.

### 2. How it works, step by step
1. **Every search and every answer** writes a row in `query_audit_logs`; every answer or refusal also writes a row in `answer_audit_logs` (cited passage ids, model, a fingerprint of the system prompt, tokens, the answer length and a refusal code word). The answer text is never stored.
2. **No audit, no answer:** the rows are saved in the same request and the same database transaction as the person's history. If saving fails, the request fails and nothing is returned, including on the progress stream.
3. **Model trouble:** if the model cannot answer, the question is still audited with status `UNAVAILABLE`.
4. **Security events** (sign-ins, failures, lockouts, token reuse, password changes, and every administrator change to people, groups, documents and rules) are saved in `access_events` from the one place that already logs them. Only ids and fixed words are kept.
5. **Append-only:** a database trigger refuses UPDATE and DELETE on all three tables, whoever connects. Deleting your history or an account does not touch the trail.
6. **Reading:** `GET /audit/queries` (filters by person, kind, status, dates and a text search; paged, at most 200), `GET /audit/answers`, `GET /audit/access-events`, `GET /audit/export` (CSV). Only the roles `security_admin` and `auditor`; the `system_admin` is refused.
7. **Export:** at most 10,000 rows; cells that could run as spreadsheet formulas get a leading quote; the export itself is recorded (who, when) before any data is sent.

### 3. Important files
`backend/app/models/audit.py`, `backend/migrations/versions/2026_10_22_1500-0006_audit_tables.py`, `backend/app/audit/service.py` (writing, filters, CSV, event saving), `backend/app/api/v1/audit.py`, `backend/app/schemas/audit.py`, audit calls in `backend/app/api/v1/search.py` and `chat.py`, `backend/app/core/logging.py` (`security_event`), audit facts in `backend/app/answers/service.py`. Tests: `backend/tests/test_audit.py`. Decision record: `docs/adr/031-audit-trail.md`.

### 4. Tools: why we chose them
Existing building blocks only: PostgreSQL (a trigger makes the log append-only), FastAPI, the existing security event hook. Nothing new to install.

### 5. How to run it
`docker compose build backend && docker compose up -d`, then `docker compose exec backend alembic upgrade head`. Sign in as `sanjana@demo` (security_admin) or `karunesh@demo` (auditor) and open `/api/docs`, or wait for the 7C screens.

### 6. How to test it
`docker compose exec backend python -m pytest -q` (526 tests; 42 are new for 7A).

### 7. Actual results (checked by me)
- 526 backend tests pass; `alembic check` clean after migration `0006`.
- Tests: see ADR 031 (rows and ids, no answer or document text, append-only, no audit no answer, roles, filters, events, export, no forbidden text in any table).
- Mutation check: 14 deliberate mistakes, all caught.
- Live, through the running API with three temporary people (removed afterwards, with their audit rows): the security_admin saw the searches (who, 4 readable documents, 8 retrieved passages, latency); an employee and a system_admin were refused (403); sign-ins appeared as events; the CSV export held the rows and no answer text. The live model was not available (no key in `.env` at that moment), so the answer rows were covered by tests only.

### 8. Limitations and open issues
- No screens yet (7C). No retention rule (backlog 32).
- The audit rows from a live answer with the real model (tokens, model, prompt fingerprint) were proven with a fake model in tests; they will be seen with real data in 7B.
- See `docs/CHALLENGES.md` entries 95 to 99.

## Layer 7B: the evaluation (backend, data and report)

### 1. What we built
A test that proves the product's central promise. 36 more synthetic documents (48 with the old 12), 62 questions to ask as 8 different people, a scanner that looks for forbidden text everywhere, and a runner that reports leakage, answer quality and speed and compares the four search set-ups. The full result and the reasoning are in `docs/evaluation-report.md`. No screen yet (7C).

### 2. How it works, step by step
1. **People and documents:** the demo people, 48 documents (23 carry a unique canary string) and their access rules.
2. **Each question** is asked through the real application as the person it belongs to (only the sign-in check is replaced).
3. **Forbidden list:** an independent plain-Python check decides which documents this person may not read. Their canary strings, ids and titles are the forbidden tokens.
4. **Scan:** the API answers, search results, the exact prompt sent to the model, the audit rows and the logs are searched for those tokens (and for the question text in the logs). One hit fails the whole run.
5. **Quality:** authorized questions must be answered with the right source; unauthorized ones and questions nothing covers must get the one uniform refusal; keyword and paraphrase questions must find the right document in the top 3.
6. **Scenarios:** 14 situations where the system changes (a rule revoked, a group left, a document deleted, a new version, a forged request, a deactivated account ...). The very next question must reflect it, and every change is undone.
7. **Report:** metrics, and a table of keyword, vector, hybrid and hybrid plus reranker search. By default a fake model writes the answers (free); `--live --yes` uses the real model after showing the cost.
8. **Saved:** runs are stored (ids, code words, numbers, the synthetic question; never an answer). `POST /evaluation/runs` starts one in a separate process (system administrator only).

### 3. Important files
`backend/app/eval/` (`corpus.py`, `cases.py`, `scanner.py`, `oracle.py`, `metrics.py`, `runner.py`, `loader.py`), `backend/app/scripts/load_eval_corpus.py` and `run_eval.py`, `backend/app/api/v1/evaluation.py`, migration `0007`, `docs/evaluation-report.md`, `docs/adr/032-evaluation-design.md`. Tests: `tests/test_eval.py`, `tests/test_eval_api.py`, `tests/eval_world.py`.

### 4. Tools: why we chose them
Existing building blocks: the real application, the real database, the real local models. A fake model keeps the run free and repeatable; the scanner is plain text search so it cannot be talked out of finding a canary.

### 5. How to run it
See the end of `docs/evaluation-report.md`: load the 36 extra documents (`load_eval_corpus`), wait until they are READY, then `docker compose exec backend python -m app.scripts.run_eval --save`.

### 6. How to test it
`docker compose exec backend python -m pytest -q` (572 tests; 46 are new for 7B). The full evaluation runs inside the test suite, so any leak breaks the build.

### 7. Actual results (checked by me)
- 572 backend tests pass; `alembic check` clean after migration `0007`.
- Real stack (real embeddings and reranker, fake answer writer): 62 of 62 cases pass, **0 leaks**, Recall@5 1.00, MRR 1.00, citation correctness 1.00, refusal accuracy 1.00 (after tuning the threshold from 0.03 to 0.30; before it was 0.886), 14 of 14 scenarios, P95 search 2.0 s.
- Hybrid plus reranker beats keyword, vector and plain hybrid (MRR 1.00 against 0.91, 0.98 and 0.98); plain hybrid only ties vector on this set.
- Mutation check: 14 deliberate mistakes, 13 caught, 1 equivalent.

### 8. Limitations and open issues
- Paraphrase questions are answered only 4 of 8 times (the right document is always found, but the confidence gate refuses when the reranker score is low). Backlog 34.
- The real model was not measured (no key was set). Backlog 35.
- 62 cases and 48 short synthetic documents: a result for this set, not a promise for a real corpus.
- See `docs/CHALLENGES.md` entries 100 to 106.

## Layer 7C: the dashboards (screens)

### 1. What we built
The screens on top of 7A and 7B, so a person can actually see the work. A **Manage** menu (only the links your role allows), an **Audit** screen, an admin **Overview**, a **Knowledge gaps** report, an **Evaluation** dashboard and a better **Home** for employees (recent questions and ideas to ask).

### 2. How it works, step by step
1. **Menu:** roles decide the links. system_admin: Overview, Documents, Users, Groups, Knowledge gaps, Evaluation. security_admin: Knowledge gaps, Audit. auditor: Audit. A plain employee sees no Manage menu. The server checks the role again on every request.
2. **Audit** (`/audit`, security_admin and auditor, not the system administrator): filter by type, result, dates and words; page through the records; open Details; switch to Security events; Export CSV (downloaded through the signed-in request, and the export itself is recorded first). The file has one readable line per question: time (UTC), name, email, type, result, question, documents readable, passages returned, speed, search mode, reranked, request id; it starts with a byte order mark so Excel shows special characters correctly. No answer text and no document text exists there.
3. **Overview** (`/admin/overview`, system_admin): counts and times only: documents by status, people, refusal rate, helpful answers, P95 times, a 7-day chart, why answers were refused, permission changes, failed uploads and the latest evaluation. No question text, no names.
4. **Knowledge gaps** (`/gaps`, system_admin and security_admin): the questions nobody could get an answer to in the last 30 days, grouped (case and punctuation ignored), counted, with emails, links and long numbers replaced by `[email]`, `[link]` and `[number]`. It shows how many different people asked, never who.
5. **Evaluation** (`/admin/evaluation`, system_admin): run history, a free **Run evaluation** button (the built-in stand-in model; the page refreshes by itself while it runs, about three minutes), per-run metrics, the search set-up comparison and every failed case. A leak is shown as "Leak found" and wins over everything else. A real-model run costs money and stays on the command line.
6. **Employee Home:** ideas to ask (built from the titles of documents you may read) and your own recent questions. Picking one fills the Ask box through memory (never the address bar) and does not ask by itself.
7. **Find passages** now calls a match weak below 0.30, the same level answers use to refuse (backlog 33 closed).

### 3. Important files
Backend: `backend/app/dashboards/service.py`, `backend/app/api/v1/dashboards.py` (`GET /dashboards/admin-overview`, `/dashboards/knowledge-gaps`, `/me/suggested-questions`). Frontend: `frontend/lib/{roles,dashboards,audit,evaluation,pendingQuestion}.ts`, `frontend/app/(portal)/(app)/{audit,gaps,admin/overview,admin/evaluation,home}/`, `PortalHeader.tsx`.

### 4. Tools: why we chose them
No chart library: the 7-day chart is a few lines of SVG with text labels, so it is small, accessible and needs nothing new. Aggregates are plain SQL.

### 5. How to run it
`docker compose build backend && docker compose up -d`, then `cd frontend; npm run dev` and open http://localhost:3000. Sign in as `prashant@demo` (Overview, Evaluation), `sanjana@demo` (Audit, Knowledge gaps) or `karunesh@demo` (Audit).

### 6. How to test it
`docker compose exec backend python -m pytest tests/test_dashboards.py -q` (20 tests); `cd frontend; npx vitest run` (96 tests); `npm run build`.

### 7. Actual results (checked by me)
- 592 backend tests and 96 frontend tests pass; the production build passes; type check clean.
- 6 deliberate mistakes (no email masking, ignoring the readable-documents rule, counting user ids as people, opening gaps to the auditor, opening the overview to everyone, ignoring the 30-day window) were all caught.
- In a real browser with temporary people (security_admin, auditor, system_admin, employee; all deleted afterwards): each role saw exactly its own menu links; employees and the wrong roles got "You don't have access"; the audit table, details, security events and CSV export worked; the overview and gaps showed real numbers; a free evaluation started from the screen finished with 62 of 62 and 0 leaks; a suggested question filled the Ask box without asking and without touching the address; no page scrolled sideways at 360 px.

### 8. Limitations and open issues
- Evaluation runs write ordinary audit rows, so their questions also appear in the audit trail and in Knowledge gaps. In a real company the evaluation would run against a test copy (backlog 36).
- The 7-day chart and tables are simple on purpose; no export of the overview (backlog 37).
- See `docs/CHALLENGES.md` entries 107 to 113.

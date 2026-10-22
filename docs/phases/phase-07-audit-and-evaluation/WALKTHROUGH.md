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

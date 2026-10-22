# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.7] - 2026-10-22
Phase 7 (audit and evaluation) complete: append-only audit trail (7A), evaluation with canary scanner and 0 leaks on 62 cases (7B), dashboards and screens (7C). 592 backend and 96 frontend tests.
### Added (Phase 7C, merged)
- Dashboards API: `GET /dashboards/admin-overview` (system administrator), `GET /dashboards/knowledge-gaps` (system and security administrator; questions normalised, counted and masked, nobody named) and `GET /me/suggested-questions` (built from documents the person may read).
- Screens: role-based **Manage** menu, **Audit** (filters, details, security events, CSV export), **Overview**, **Knowledge gaps**, **Evaluation** (run history, free Run button with live refresh, metrics, failed cases) and an employee **Home** with ideas to ask and recent questions.
- 20 backend tests (592 total), 37 frontend tests (96 total), 6 mutation checks all caught. Challenges 107 to 113.

### Changed (Phase 7C)
- The audit CSV export is readable: name and email instead of an id, a plain UTC time, a passage count instead of long ids, separate search mode and reranked columns, and a byte order mark for Excel.
- The weak-match note on Find passages now uses 0.30, the same level answers refuse at.

### Added (Phase 7B, merged)
- Evaluation: 36 extra synthetic documents (48 total, a unique canary in every one of sensitivity 2 or higher), 62 cases (authorized, unauthorized with prompt injection, missing, keyword, paraphrase, 14 scenarios), a canary scanner over answers, search results, the model prompt, audit rows and logs, an independent oracle, a runner with metrics and a keyword / vector / hybrid / hybrid + reranker comparison, saved runs (migration `0007`), `POST /evaluation/runs` and friends (system administrator), `load_eval_corpus` and `run_eval` scripts. `docs/evaluation-report.md`, ADR 032.
- Real-stack result: 62 of 62 cases, 0 leaks, Recall@5 1.00, MRR 1.00, citation correctness 1.00, refusal accuracy 1.00, P95 search 2.0 s.

### Changed (Phase 7B)
- Refusal threshold raised from 0.03 to 0.30 (measured on 48 answer-or-refuse cases). Refusal accuracy rose from 0.886 to 1.00; paraphrased questions are answered 4 of 8 times.
- 46 new tests (572 total), 14 mutation checks (13 caught, 1 equivalent). Challenges 100 to 106.

### Added (Phase 7A, merged)
- Append-only audit trail (migration `0006`): one row for every search and answer (who, question, how many documents they could read, retrieved and cited passage ids, outcome, speed), answer facts without the answer text, and security events with ids only. The database refuses changes and deletes.
- "No audit, no answer": if the trail cannot be written the person gets nothing.
- `GET /audit/queries`, `/audit/answers`, `/audit/access-events`, `/audit/export` (formula-safe CSV) for `security_admin` and `auditor` only; the `system_admin` cannot read the audit. ADR 031.
- 42 new tests (526 total), 14 mutation checks. Challenges 95 to 99.


## [v0.6] - 2026-10-22
Phase 6 (answers and citations) complete: answer engine with validated citations and uniform refusals (6A), answer API with evidence preview, history and feedback (6B), the Ask screen (6C). Details in the three Phase 6 sections below. 484 backend and 59 frontend tests.

### Added (Phase 6C, branch `feat/answers-ui-6c`, awaiting owner review)
- Ask screen: ask a question and get a short answer with sources, or find passages; progress stages; evidence panel for the passage behind a citation; thumbs up or down with an optional comment; your recent questions with Ask again and Remove; plain messages for no answer, answers off and too many questions. Menu link is now **Ask**.
- The model client retries a dropped connection once. 59 frontend tests, 484 backend tests. Challenges 91 to 94.

### Added (Phase 6B, branch `feat/chat-api-6b`, awaiting owner review)
- Answer API: `POST /chat` (blueprint shape), `POST /chat/stream` (progress events then one result), `POST /chat/feedback`, `GET /chunks/{id}/preview` (re-checks READ), `GET /me/search-history`, `DELETE /me/search-history/{id}`. Migration `0005` (tables `search_history`, `chat_feedback`).
- Private, deletable history (question and cited ids, never the answer); 10 answers per minute per person; one friendly 503 when answers are unavailable; no question or answer text in logs.
- 45 new tests (483 total), 12 mutation checks, live check with the real model. Challenges 86 to 90.

### Added (Phase 6A, branch `feat/answers-6a`, awaiting owner review)
- Answer engine (`app/llm`, `app/answers`): GPT-4o mini behind one interface, prompt that marks passages as untrusted data, validator (JSON shape, citations only to given passages, no links or HTML), confidence gate, second access check, one uniform refusal. ADR 030.
- The OpenAI key is optional, read from `.env` only, never logged, and given to the backend container only.
- 83 new tests (438 total), 11 mutation checks, a live check with the real model on the demo documents. Challenges 81 to 85.

### Changed (design refresh, branch `feat/design-refresh`, awaiting owner review)
- New look everywhere through the theme tokens: violet-black base and purple accent (contrast checked). Soft 150 ms hover and focus transitions on controls.
- Animated dots sphere on the landing hero and the sign-in, forgot-password and reset-password pages: dots fly in from both sides, then it turns slowly. Still picture for reduced motion, fewer dots on phones. No background animation after sign-in.
- No change to text, API, database, permissions or search. 7 new frontend tests (48 total); backend 355 tests unchanged. ADR 029, challenges 77 to 80.


## [v0.5] - 2026-10-21
Phase 5 (hybrid retrieval) complete: search engine with indexes, allow-list first, RRF and local reranker (5A), `POST /search` (5B), search screen (5C). Details in the three Phase 5 sections below. 355 backend and 41 frontend tests.

### Added (Phase 5C, branch `feat/search-ui-5c`, awaiting owner review)
- Search screen `/search` for everyone: question box, results with document, page or section, passage and a relevance bar with words, weak-match note, no-results, error and rate-limit messages, administrator score details. Menu link, Home and tour wording updated. The question is never put in the web address.
- 41 frontend tests (13 new). Challenges 74 to 76.

### Added (Phase 5B, branch `feat/search-api-5b`, awaiting owner review)
- `POST /api/v1/search`: question in, best permitted passages out; modes keyword, vector, hybrid; validation, rate limit 30 per minute per person, no-store, no question text in logs, score details for administrators only; models warmed at start-up.
- 20 new tests (355 total), 6 mutation checks. Challenges 71 to 73.

### Added (Phase 5A, branch `feat/retrieval-5a`, awaiting owner review)
- Migration `0004`: GIN index on the full-text column and HNSW index on the vectors.
- Retrieval engine (`app/retrieval`): allow-list first, keyword (any word) and vector search inside it, RRF fusion (k=60), cross-encoder reranker (`BAAI/bge-reranker-base`, baked into the image), three modes, final allow-list guard. ADR 028.
- 52 new tests (335 total): random worlds against the Phase 4 oracle, 5 mutation checks. `app/scripts/retrieval_check.py` measures Recall@5 and MRR on the demo data. Challenges 65 to 70.


## [v0.4] - 2026-10-20
Phase 4 (permissions and ACL) complete: access tables and resolver (4A), groups, rules, history, preview and demo data API (4B), admin screens (4C). Details in the three Phase 4 sections below. 283 backend and 28 frontend tests.

### Added (Phase 4C, branch `feat/access-4c`, awaiting owner review)
- Admin Users page (invite, edit, roles, deactivate and reactivate), Groups page (create, members), and an Access section on the document page: rules add, edit, remove, Deny confirmation, expiry, rule history and the "who can read this" preview with plain-English reasons. Menu links Users and Groups.
- 28 frontend tests. Fixed sideways scrolling at 360 px caused by screen-reader text outside scroll boxes (also in the Phase 3 history table). Challenges 61 to 64.

### Added (Phase 4B, branch `feat/access-4b`, awaiting owner review)
- Groups API (admin only), access rule API (list, add, edit, delete) enforcing MANAGE, rule history saved in the same transaction, access preview with reason codes (CR-003).
- `seed_access` script: 6 demo groups and rules for the 12 demo documents following the personas; the sales executive gets clearance 2.
- `PATCH /documents/{id}` now needs MANAGE on the document (admin role no longer enough by itself, but admins always manage).
- 22 new tests (283 total). Challenges 57 to 60.

### Added (Phase 4A, branch `feat/access-4a`, awaiting owner review)
- Migration `0003`: groups, user_groups, document_acl, permission_change_events, with database constraints.
- Access resolver (`app/access/resolver.py`): READ rules A to E in SQL, DOWNLOAD, MANAGE, explanations; deny by default, deny beats allow, admin is not reader.
- 92 new tests (261 total): table-driven rules, independent Python oracle in 8 random worlds, mutation check (8 deliberate mistakes all caught). ADR 027, Phase 4 docs.

## [v0.3] - 2026-10-20
Phase 3 (documents and ingestion) signed off by the owner. Tag created after the Phase 3 close-out PR.
### Added (3C: admin screens)
- Admin screens: documents list (filters, paging, auto-refresh while processing), upload page, document page (edit, re-index, delete, processing history, versions), notification bell for failed processing, "no access" page for non-admins.
- `GET /ingestion/jobs?document_id=` filter; frontend API client sends files and reads error codes.
- 10 new frontend tests (20) and 1 new backend test (169). Challenges 48 to 52.
### Fixed
- Signed-in header overflowed on a 360 px phone; it now wraps.
- Phase 3 checks on `main`: 169 backend tests, 20 frontend tests, worker killed mid-job and restarted (all jobs finished once, no duplicates).

### Added (3B: ingestion pipeline and API)
- Migration `0002`: documents, document_versions, document_chunks (vector(384), tsv), ingestion_jobs, notifications; enables the `vector` extension.
- Upload validation (extension plus magic bytes, 50 MB limit, zip-bomb guard, clean file names), parsers for PDF, DOCX, TXT and MD, sentence-based chunker (about 450 tokens, 50 overlap, page and section aware).
- Ingestion pipeline and Celery task: idempotent, publishes in one transaction, fixed error codes, retries, admin notifications on failure, start-up re-send of unfinished jobs.
- Admin API: upload, list, get, edit, soft delete, versions, re-index, ingestion jobs; notifications API (CR-002).
- Synthetic documents (`app/scripts/synthetic_docs.py`, `load_synthetic_docs.py`, `sample-data/synthetic/`).
- 86 new tests (168 total). ADR 026, CR-002, challenges 41 to 47.

### Added (3A: storage, worker, embeddings)
- `storage` service (SeaweedFS 4.48, S3 API, private network) replacing the archived MinIO (CR-001, ADR 025).
- `worker` service (Celery 5.6.3 over Redis) sharing the backend image; retry-safe job settings.
- Storage adapter `app/storage` (boto3), object key builder, `storage_check` script.
- Local embeddings (`BAAI/bge-small-en-v1.5`, 384 dimensions) baked into the image, offline at run time.
- Env doctor checks the S3 settings; `setup_env.ps1` adds missing keys to an existing `.env`.
- 17 new backend tests (82 total). ADR 024, ADR 025, CR-001, Phase 3 docs, challenges 35 to 40.

## [v0.2] - 2026-10-19
Phase 2 (authentication and user flow) signed off by the owner. Tag created after the Phase 2 close PR.
### Added
- `app/scripts/set_user_passwords.py`: sets individual demo passwords from a git-ignored local file (stdin, `email: password` lines). 8 parser tests (backend now 65 tests).
- Demo user emails are name-based (for example `swara@demo`).

### Added (2C-2)
- Phase 2C-2: forgot/reset password pages, profile (change password, sign out of all devices), shared header, welcome tour (3 steps, skippable, remembered per browser), role-based first-2-minutes guide, login notices. 10 unit tests.
- Demo users now use team member names.
- `docs/BACKLOG.md`, updated architecture overview, Phase 1 status corrected.
### Changed
- The admin users page (planned as 2C-3) moves to Phase 4.

### Added (2C-1)
- Phase 2C-1: Login UI
- `/login` page (validation, shake, Caps Lock hint, Remember me, spinner, lockout and network messages), minimal `/home`, client-side guards.
- Frontend API client with 15 s timeout, in-memory session store with single-flight refresh.
- Vitest (dev-only, `5.0.3`) with 5 unit tests.
- `docs/CHALLENGES.md`: running log of build problems (owner rule).

### Added (2B)
- Phase 2B: Authentication backend
- Tables and migration `0001`: departments, roles, users, user_roles, auth_tokens.
- Login (Argon2id), lockout, IP rate limit, refresh-token rotation with reuse detection, logout, logout-all.
- Forgot, reset and change password; reset and invite emails through Mailpit.
- `/auth/me`; admin endpoints for users, roles and departments (role `system_admin`, checked from the database).
- Demo seed script (`python -m app.scripts.seed_users`) and `scripts/setup_env.ps1`.
- 57 backend tests. ADR 023. `greenlet` dependency (ADR 022).
### Fixed
- Alembic could not run (missing logging config and `prepend_sys_path`); database session no longer falls back to a missing sqlite driver.

### Added (earlier)
- Phase 2A: Backend Foundation
- Docker Compose setup with Postgres (pgvector 0.8.0), Redis (7.4.2), and Mailpit (v1.22.0).
- FastAPI backend modular monolith skeleton.
- Environment variables validation (env doctor).
- Structured JSON logging and X-Request-ID middleware.
- Problem Details error handling.
- Health (`/api/v1/health`) and ready (`/api/v1/ready`) endpoints.
- Alembic database migration configuration.
- Basic test suite for health check and env doctor.

## [v0.1] - 2026-10-09
### Added
- Phase 1: Landing Page
- Frontend built with Next.js 16.4.0, React 19.3.0, Tailwind 4.3.3, TypeScript 5.9.
- Dark premium design with interactive components (Hover-glow cards, scroll reveal).
- Interactive demo component and 60-second tour dialog.
- Responsive layout with accessibility features (Performance 99, Accessibility 96).

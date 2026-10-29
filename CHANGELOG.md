# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added (Phase 10A, branch `feat/scale-10a`, awaiting owner review)
- Scale demo: a separate stack (`docker-compose.big.yml`, own database, file store and ports), `scripts/big/download.sh` (public Kubernetes, Docker and GitLab handbook documentation, kept outside Git), `app.scripts.big_load` (synthetic people, cleaning, placement by path, canary markers, access rules) and `app.scripts.big_check` (status, search time per mode, leak check against an independent fast oracle). ADR 039, `docs/phases/phase-10-scale-demo/` with a kept `RESULTS.md`.
- `docs/error-handling.md` (errors, retries and fallbacks) and `docs/scale-and-limits.md` (what is tested, expected limits, roadmap, rough cost, why no agents).
- 27 backend tests (`tests/test_scale.py`).
- Security: `pypdf` 6.21.1 to 6.21.2 (3 new known vulnerabilities in the PDF parser, found by the dependency scan of this pull request).
- Full run measured (2026-10-29): 5,850 real documents, 90,956 passages, 1,000 people; 1,040 queries checked against the oracle, 0 violations. Findings (exact-identifier search weak, default search P95 5.4 s) recorded in `RESULTS.md`.

## [v1.0] - 2026-10-24
### Added (Phase 9D, branch `feat/launch-9d`, awaiting owner review)
- README rewritten for a stranger (pitch, screenshots, architecture, security model, measured evaluation, quick start verified on a clean copy); ten screenshots in `docs/images/`; architecture page with diagrams (system, question flow, ingestion and sync); `docs/deployment.md`.
- `scripts/check_prereqs.sh` and `.ps1` (is this computer ready, read-only); `docker-compose.prod.yml` and `frontend/Dockerfile` (restart policies, production mode, website as a container, no test mailbox).
- Landing page: "View on GitHub" buttons and a demo-data banner; honest SSO answer in the FAQ; home guide steps link to their screens.
- 1 backend test (737 total).

### Fixed (Phase 9D)
- The status page reported file storage as down on a brand-new installation (the bucket did not exist yet). Challenges 147 to 149.

### Added (Phase 9C, branch `feat/docs-9c`, awaiting owner review)
- `SECURITY.md` (private vulnerability reporting), `docs/security.md` (rules, six walls, 16 threats tied to tests, OWASP LLM Top 10, what the project does not do), `docs/api.md` generated from the application with a CI diff, Lighthouse CI job on the six public pages. ADR 038.
- 4 backend tests (736 total).

### Changed (Phase 9C)
- The landing and sign-in dot-sphere animation draws far fewer shapes per frame (same look, much less processor time: main-thread work 5.5 s to 2.1 s in a speed test) and starts 300 ms after the page shows its text.
- Privacy, Terms and Security pages rewritten to match what the software really does (the sign-in cookie, what goes to the AI provider, retention).
- Accessibility: empty table-header cells on the audit and evaluation tables and a skipped heading level fixed (axe audit of 14 pages, zero violations). Challenges 140 to 146.

### Added (Phase 9B, merged)
- Audit retention (`AUDIT_RETENTION_DAYS`, default 365, never below 30) with a guarded purge (migration `0009`), a nightly job and `maintenance audit-purge`.
- Public status page (`/status`, API `GET /api/v1/status`) with real checks and a worker heartbeat; request, server-error and rate-limit counters in the Overview; audit retention number in the Overview.
- Nightly cleanup of passages of old versions (`KEEP_VERSIONS`, default 3).
- `scripts/backup.sh`, `scripts/restore.sh`, `docs/runbook.md` and a restore tested on an empty stack. ADR 037.
- 35 backend tests (732 total), 9 frontend tests (132 total), 15 mutation checks all caught. Challenges 135 to 139.

### Changed (Phase 9B)
- The object storage listing pages through results (the store returns at most 1000 keys at a time).

### Added (Phase 9A, merged)
- Continuous integration (GitHub Actions): ruff, ESLint, TypeScript, mypy, all tests with a coverage gate on the security code, a named leak gate (canary scan, access oracle, evaluation), a secret scan of the whole history (gitleaks), dependency scans (pip-audit, npm audit), alembic check and an image build. Dependabot, pull request template, CONTRIBUTING, MIT licence, pre-commit config, `scripts/setup_env.sh`, `docs/ci.md`, ADR 036.

### Security (Phase 9A)
- `pypdf` 6.19.0 to 6.21.1 (8 known vulnerabilities in the PDF parser).

### Changed (Phase 9A)
- 36 type errors fixed (no behaviour change), imports sorted, a few `raise ... from None`. The Dockerfile downloads the models before the other packages. Challenges 128 to 134.


## [v0.8] - 2026-10-23
Phase 8 (incremental sync) complete: new versions, restore and the version date (8A), the sync engine with scheduler and API (8B), the GitHub connector and the Sources screen (8C). 697 backend and 123 frontend tests.
### Added (Phase 8C, merged)
- GitHub connector: imports a folder of `.md`, `.txt`, `.pdf` and `.docx`; who may read comes from `.securesearch/access.json` (teams, longest folder rule wins) and `users.json`, and by default from the repository's real collaborators. Read-only token, worker only. `demo-docs/` with six invented documents. ADR 035.
- **Sources** screen (Manage menu): add a GitHub source, Sync now, automatic sync on or off, interval, last run and recent runs in plain words.
- 45 backend tests (697 total), 16 mutation checks all caught, 22 frontend tests (123 total). Challenges 123 to 127.

### Changed (Phase 8C)
- The worker joins the public network for outgoing connections (no port is published) and receives `GITHUB_TOKEN`; the backend never does.

### Added (Phase 8B, merged)
- Sync engine: connector interface, per-item diff (new, unchanged, changed file = new version, permission-only change = rules only, removed = soft delete, returned = restore), teams and members that follow the source, guards against a broken or empty source, one run per source, scheduler (the worker now runs Celery beat) and `/sync/sources`, `/sync/runs` routes (system administrator). CR-004, migration `0008`, ADR 034.
- 46 backend tests (652 total), 18 mutation checks all caught, real worker and scheduler check. Challenges 118 to 122.

### Changed (Phase 8B)
- The group screens refuse to edit a team that a sync source manages.

### Added (Phase 8A, merged)
- New versions: `POST /documents/{id}/versions` (same content as the newest version does nothing; the old version keeps answering until the new one is complete; rules untouched), restore of a deleted document (`POST /documents/{id}/restore`, `GET /documents?deleted=true`).
- Screens: "Upload a new version" and the version in use on the document page, Active and Deleted tabs with Restore on the list.
- ADR 033, Phase 8 docs. 14 backend tests (606 total), 5 frontend tests (101 total), 11 mutation checks all caught. Challenges 114 to 117.

### Changed (Phase 8A)
- The date shown with a cited passage and in the evidence panel is the date of the passage's version.

### Security
- Next.js 16.4.0 to 16.4.2 (fixes a known vulnerability). Tests, type check and build pass.

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

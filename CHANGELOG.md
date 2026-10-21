# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
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

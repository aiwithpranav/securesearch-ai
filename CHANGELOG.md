# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added (Phase 3A, branch `feat/documents-3a`, awaiting owner review)
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

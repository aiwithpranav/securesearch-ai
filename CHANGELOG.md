# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Phase 2C-1: Login UI (branch `feat/login-ui`, awaiting owner review)
- `/login` page (validation, shake, Caps Lock hint, Remember me, spinner, lockout and network messages), minimal `/home`, client-side guards.
- Frontend API client with 15 s timeout, in-memory session store with single-flight refresh.
- Vitest (dev-only, `5.0.3`) with 5 unit tests.
- `docs/CHALLENGES.md`: running log of build problems (owner rule).

### Added (2B)
- Phase 2B: Authentication backend (branch `feat/auth-backend`, awaiting owner review)
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

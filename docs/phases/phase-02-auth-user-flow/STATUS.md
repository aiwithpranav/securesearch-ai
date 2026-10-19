# STATUS: Phase 2, Layer 2B (authentication backend)

Branch: `feat/auth-backend` (local only, nothing pushed). Last pushed phase work: Phase 2A, merged to `main`.

## Done
- 2A: Docker Compose, FastAPI skeleton, env doctor, JSON logs, request IDs, Problem Details, health and ready.
- 2B: tables and migration `0001`; login, lockout, refresh rotation with reuse detection, logout, logout-all; forgot, reset and change password with Mailpit emails; `/auth/me`; admin users, roles, departments; seed script; `scripts/setup_env.ps1`.
- 2B checks run by Claude: 57 tests pass in the backend container; migration applies; seed works and is re-runnable; live login for all 8 demo users returns 200 (deactivated user gets 401); mutation check proved the tests catch a broken lockout and broken reuse detection.
- 2B fixes to 2A: `alembic.ini` lacked logging sections and `prepend_sys_path`, so `alembic` could not run; the DB session fell back to a missing sqlite driver; added missing `greenlet`.

## In progress
- Nothing. Waiting for owner review of 2B.

## Exact next action
1. Owner follows the manual checks in the 2B report (WALKTHROUGH.md sections 5 and 6) and answers the ADR 023 "OWNER CHECK" items.
2. After "Approved": push `feat/auth-backend`, open PR, merge. Then plan 2C (login UI). The `v0.2` tag is created only when all of Phase 2 (2A, 2B, 2C) is signed off.

## Blockers
- None technical. Owner decisions needed: ADR 023 items 1 to 4 (extra columns, role-set semantics, admin-initiated reset, persona departments), and the 12-character password rule.

## Decisions this session
- See `docs/adr/023-auth-implementation-details.md`.
- Added dependency `greenlet==3.5.6` (ADR 022).

## Prerequisites
- Docker Desktop running; `.env` exists (created locally from `.env.example` by `scripts/setup_env.ps1`, git-ignored). Existing dev Postgres volume (from 9 Oct) was kept; its role password was changed to match the new `.env`. No data was deleted.

## Open issues
- Starlette `httpx` deprecation warning in test output (from 2A).
- Admin-initiated reset not built (needs Change Request).
- Expired tokens are not purged yet.
- Phase 1 `STATUS.md` still says "Layer 3 waiting for owner review" although the owner has signed off Phase 1 and `v0.1` exists. Not edited (finished phase); can be corrected on request.
- Live manual browser/Swagger checks not done by Claude.

## Resume prompt
"Read docs/phases/phase-02-auth-user-flow/STATUS.md and WALKTHROUGH.md in D:\AI\RAG\Secure_Search_AI. Phase 2B is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi."

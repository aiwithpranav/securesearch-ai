# STATUS: Phase 2 (authentication and user flow): CLOSED

All Phase 2 work is merged to `main` (PRs #1 to #5) and tagged **`v0.2`** on merge commit `41e06af` (pushed and verified on 2026-10-19). The rest of this file is the state at close-out. Current work: `docs/phases/phase-03-documents-and-ingestion/STATUS.md`.

## Done
- **2A** backend foundation: Docker Compose (Postgres + pgvector, Redis, Mailpit, backend), env doctor, JSON logs, request IDs, Problem Details, health and ready.
- **2B** auth backend: tables and migration `0001`, login with lockout and rate limit, refresh rotation with theft detection, logout, logout-all, forgot/reset/change password, `/auth/me`, admin users, roles and departments, seed script, `scripts/setup_env.ps1`.
- **2C** login UI: `/login` (all blueprint states), `/forgot-password`, `/reset-password`, `/home` (details, first-2-minutes guide, welcome tour), `/profile` (change password, sign out of all devices), session store with single-flight refresh.
- Demo users: team member names, name-based emails, individual passwords in a git-ignored local file, `set_user_passwords.py` script.
- Project-wide documents: `docs/CHALLENGES.md` (34 entries), `docs/BACKLOG.md`, ADR 022 and 023, updated architecture and README.

## Final checks run by Claude on `main` (19 Oct 2026)
- Backend: 65 tests passed. Migration at head (`0001`).
- Frontend: 10 unit tests passed, `tsc` clean, `npm run build` OK.
- Live API: all 8 demo users log in (200) and `/auth/me` shows the right department; only `prashant@demo` can call `/users` (others get 403); wrong password and the deactivated user get 401; no token gives 401; health and ready are 200.
- Secret scan of the tracked tree: no `.env` value, no demo password, no `.env` or credentials file tracked.
- Earlier browser walkthroughs of the login, reset, profile, tour and lockout flows are described in `WALKTHROUGH-2C.md`.

## Owner decisions recorded
- ADR 023 items 1, 2 and 4 and the 12-character password rule: accepted. Admin-initiated reset: not built, moved to the backlog.
- Tour flag in `localStorage`. Admin users page moved to Phase 4. Demo users renamed.

## In progress
- Nothing.

## Exact next action
1. Owner merges the Phase 2 close-out PR on GitHub and tells Claude.
2. Claude checks `main`, creates tag `v0.2` on the merge commit (after the owner's "go"), pushes it, and verifies the remote.
3. Claude then writes the Phase 3 plan (documents and ingestion) and waits for the owner's approval. No Phase 3 work before that.

## Blockers
- None. GitHub default branch is still `feat/auth-backend`; the owner needs to change it to `main` in GitHub settings (challenge 34).

## Prerequisites
- Docker stack running and seeded; Node 20.9+ (running frontend tests needs 22+); `.env` exists (git-ignored); local `demo-credentials.local.txt` (git-ignored). Frontend on port 3000.

## Open issues
- Screen-reader and full keyboard-only checks of the portal pages not done.
- Caps Lock hint and the browser's "Save password?" prompt were not verified by automation (owner check).
- Tour flag is per browser. Expired tokens are not purged. See `docs/BACKLOG.md`.

## Resume prompt
"Read docs/phases/phase-02-auth-user-flow/STATUS.md, docs/BACKLOG.md and docs/CHALLENGES.md in D:\AI\RAG\Secure_Search_AI. Phase 2 is closing; continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English."

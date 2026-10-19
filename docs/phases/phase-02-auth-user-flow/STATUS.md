# STATUS: Phase 2, Layer 2C-2 (forgot/reset, profile, tour)

Branch: `feat/login-ui` (2C-1 pushed; 2C-2 committed locally, not pushed yet). `main` contains Phase 1, 2A and 2B (PR #1 merged).

## Done
- 2A and 2B: see `WALKTHROUGH.md`. Merged to `main`.
- 2C-1: API client, in-memory session store, `/login` with every state from blueprint 19.2, client-side guards, `docs/CHALLENGES.md` (project-wide rule). Pushed.
- 2C-2: `/forgot-password`, `/reset-password`, `/profile` (change password, sign out of all devices), shared header, welcome tour, first-2-minutes guide, login notices, 10 unit tests, live browser walkthrough (see `WALKTHROUGH-2C.md`).
- Demo users renamed to team names (display names only; emails unchanged).
- Checks run by Claude: `npm test` (10 passed), `tsc`, `npm run build`, real-browser walkthrough against the live backend.

## In progress
- Nothing. Waiting for owner review of 2C-2.

## Exact next action
1. Owner creates and merges the PR for `feat/login-ui` on GitHub, then tells Claude.
2. Claude verifies `main`, then runs the Phase 2 close steps (see the close plan in the chat report): final checks, owner sign-off on ADR 023 items, tag `v0.2` on the merge commit, push the tag, verify the remote.
3. Only after that: plan Phase 3 (documents and ingestion).

## Blockers
- None. Owner decisions still open from ADR 023 (items 1 to 4; admin-initiated reset is still not built).

## Decisions this session
- Owner approved 2C-1 and 2C-2 (2026-10-19). **2C-3 (admin users page) is moved to Phase 4** (owner decision), so the Phase 4 brief must include a users/groups admin screen. The admin API for users, roles and departments already exists from 2B.
- Welcome tour "seen" flag lives in `localStorage` per user (owner approved).
- Plain React + Tailwind, no shadcn/ui for now. Native `<dialog>` for the tour.
- Vitest pinned to 5.0.3 (dev-only).
- Every challenge goes into `docs/CHALLENGES.md` (owner rule).

## Prerequisites
- Docker stack running and seeded; Node 20.9+ (running tests needs 22+); `.env` exists (git-ignored). Frontend must run on port 3000.

## Open issues
- Tour flag is per browser (localStorage).
- Phase 1 `STATUS.md` is stale (says waiting for review).
- Admin-initiated reset not built (needs a Change Request).
- Expired tokens not purged.
- Keyboard-only, screen reader and password-manager prompts not verified by Claude.
- GitHub default branch: owner reports it is set to `main`.

## Resume prompt
"Read docs/phases/phase-02-auth-user-flow/STATUS.md and WALKTHROUGH-2C.md and docs/CHALLENGES.md in D:\AI\RAG\Secure_Search_AI. Layer 2C-2 is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English."

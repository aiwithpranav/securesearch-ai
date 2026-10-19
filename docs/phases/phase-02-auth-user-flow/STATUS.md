# STATUS: Phase 2, Layer 2C-1 (login UI)

Branch: `feat/login-ui` (local, nothing pushed). `main` contains Phase 1, 2A and 2B (PR #1 merged).

## Done
- 2A and 2B: see `WALKTHROUGH.md`. Merged to `main`.
- 2C-1: API client, in-memory session store, `/login` with every state from blueprint 19.2, minimal `/home`, client-side guards, 5 unit tests, `docs/CHALLENGES.md` (new project-wide rule).
- 2C-1 checks run by Claude: `npm test` (5 passed), `tsc`, `npm run build`, and a real-browser walkthrough against the live backend (see `WALKTHROUGH-2C.md` section 7).

## In progress
- Nothing. Waiting for owner review of 2C-1.

## Exact next action
1. Owner runs the manual checks from the 2C-1 report (Caps Lock, Save-password prompt, Remember me, visual review) and replies "Approved" or lists fixes.
2. After approval: start 2C-2 (forgot/reset pages, profile with change password and sign out everywhere, expanded home with tour and first-2-minutes guide, 404 fix for "Forgot password?"). Ask for approval before starting.
3. 2C-3 (admin users page) stays optional.
4. When all of Phase 2 is approved: push, PR, merge, tag `v0.2`.

## Blockers
- None. Owner decisions still open from ADR 023 (items 1 to 4; admin-initiated reset still not built).

## Decisions this session
- Welcome tour "seen" flag lives in `localStorage` per user (owner approved).
- Plain React + Tailwind, no shadcn/ui for now.
- Vitest pinned to 5.0.3 (dev-only).
- Every challenge goes into `docs/CHALLENGES.md` (owner rule).

## Prerequisites
- Docker stack running and seeded; Node 20.9+ (tests need 22+); `.env` exists (git-ignored).

## Open issues
- `Forgot password?` link shows the 404 page until 2C-2.
- Phase 1 `STATUS.md` is stale (says waiting for review).
- Admin-initiated reset not built (needs Change Request).
- Expired tokens not purged.
- GitHub default branch was still `feat/auth-backend` when last checked with `git ls-remote origin HEAD`.

## Resume prompt
"Read docs/phases/phase-02-auth-user-flow/STATUS.md and WALKTHROUGH-2C.md and docs/CHALLENGES.md in D:\AI\RAG\Secure_Search_AI. Layer 2C-1 is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English."

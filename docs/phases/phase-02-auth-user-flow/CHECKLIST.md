# Phase 2 Checklist

## 2A Backend foundation
- [x] Compose: postgres, redis, mailpit, backend
- [x] Env doctor, JSON logs, request IDs, Problem Details, health and ready
- [x] Alembic configured (2B fixed the missing logging config and `prepend_sys_path`)

## 2B Auth backend
- [x] Tables and migration `0001` (departments, roles, users, user_roles, auth_tokens)
- [x] Login with one generic failure message, lockout, IP rate limit
- [x] Refresh rotation and reuse detection; logout; logout-all
- [x] Forgot / reset / change password; emails land in Mailpit
- [x] `/auth/me`; roles are read from the DB, not the token
- [x] Admin: users, roles, departments; deactivate is immediate
- [x] Seed script (8 personas + 1 deactivated user)
- [x] 57 automated tests pass in the container (65 after the password-script tests)
- [x] Owner approved 2B; PR #1 merged to `main`
- [ ] Owner decisions on the ADR 023 "OWNER CHECK" items (items 1 to 4)

## 2C Login UI
### 2C-1 Login and session (built, pushed)
- [x] API client, in-memory session store, single-flight refresh
- [x] `/login` with all states from blueprint 19.2
- [x] Minimal `/home` and client-side guards
- [x] Unit tests (5), typecheck, build, browser walkthrough
- [ ] Owner manual checks (Caps Lock, Save-password prompt, Remember me)
### 2C-2 Forgot/reset, profile, tour (built, owner approved 2026-10-19)
- [x] Forgot and reset pages
- [x] Profile: change password, sign out of all devices
- [x] Shared header, welcome tour, first-2-minutes guide, login notices
- [x] Unit tests (10 total), typecheck, build, browser walkthrough
- [x] Owner approval
### 2C-3 Admin users page: moved to Phase 4 (owner decision, 2026-10-19)
- [x] Not part of Phase 2 any more; added to the Phase 4 brief

## Phase 2 close
- [x] PRs #1 to #4 merged (owner, on GitHub)
- [x] Final checks on `main`: 65 backend tests, 10 frontend tests, typecheck, build, live login (19 Oct 2026)
- [x] Owner answers on ADR 023 recorded
- [x] Stale Phase 1 `STATUS.md` fixed, Phase 2 STATUS written, CHANGELOG `[v0.2]` section, backlog, architecture, README
- [ ] Close-out PR merged (owner)
- [ ] Tag `v0.2` on the merge commit, pushed, verified (after the owner's "go")

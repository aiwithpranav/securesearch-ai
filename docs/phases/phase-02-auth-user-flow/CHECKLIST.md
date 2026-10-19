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
- [x] 57 automated tests pass in the container
- [x] Owner approved 2B; PR #1 merged to `main`
- [ ] Owner decisions on the ADR 023 "OWNER CHECK" items (items 1 to 4)

## 2C Login UI
### 2C-1 Login and session (built, waiting for owner review)
- [x] API client, in-memory session store, single-flight refresh
- [x] `/login` with all states from blueprint 19.2
- [x] Minimal `/home` and client-side guards
- [x] Unit tests (5), typecheck, build, browser walkthrough
- [ ] Owner manual checks and approval
### 2C-2 (not started)
- [ ] Forgot and reset pages, profile (change password, sign out everywhere)
- [ ] Expanded home, welcome tour, first-2-minutes guide
### 2C-3 (optional, not started)
- [ ] Admin users page

## Phase 2 close
- [ ] Owner approval of all of Phase 2, then PR, merge, tag `v0.2`

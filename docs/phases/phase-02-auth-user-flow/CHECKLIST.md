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
- [ ] Owner manual verification (see WALKTHROUGH.md)
- [ ] Owner decisions on the ADR 023 "OWNER CHECK" items
- [ ] Owner approval, then PR, merge, tag

## 2C Login UI (not started)
- [ ] Login page, reset pages, profile, protected routes, welcome tour

# Phase 4 Checklist

## 4A Core (built, owner approved, merged)
- [x] Migration `0003`: groups, user_groups, document_acl, permission_change_events (`alembic check` clean)
- [x] Database refuses malformed rules (bad words, COMPANY with a principal, missing principal, duplicates)
- [x] Access resolver: READ (rules A to E), DOWNLOAD, MANAGE, explanations, allow-list SELECT
- [x] Table-driven tests: every principal type, deny beats allow (25 combinations), expiry, clearance edges, country lists, document and user state, revocation, admin is not reader, MANAGE, DOWNLOAD
- [x] Independent Python oracle agrees with the SQL in 8 random worlds
- [x] Mutation check: 8 deliberate mistakes, all caught
- [x] ADR 027
- [x] 92 new tests (261 backend tests in total)
- [x] Owner approval (2026-10-20)

## 4B API (built, waiting for owner review)
- [x] Groups API (admin only) and `GET /groups/{id}` (CR-003)
- [x] ACL API with MANAGE enforced; non-managers get the same 404 as for a missing document
- [x] Rule history written in the same transaction as the change (forced failure leaves nothing)
- [x] Access preview with reason codes and matching rules (CR-003)
- [x] Seed groups and rules for the 12 demo documents; persona matrix matches exactly, in tests and live (117 answers)
- [x] Negative tests: bad principals, past expiry, duplicates, MANAGE holder limits, DENY MANAGE, no document text
- [x] 22 new tests (283 backend tests in total)
- [x] Owner manual checks and approval (merged, PR #11)

## 4C UI (built, waiting for owner review)
- [x] Users page: invite, edit, roles, deactivate and reactivate (not for yourself)
- [x] Groups page: create, members add and remove with confirmation
- [x] Access section: rules list, add, edit, remove, Deny confirmation, MANAGE note, expiry, history, who-can-read preview
- [x] Admin menu links (Users, Groups)
- [x] Typecheck, 28 frontend tests, production build
- [x] Real-browser checks with temporary users (removed afterwards); 360 px layout measured
- [ ] Owner manual checks and approval

## Phase 4 close
- [ ] Owner approval, PRs merged, tag `v0.4`

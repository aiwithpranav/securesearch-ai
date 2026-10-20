# Phase 4 Checklist

## 4A Core (built, waiting for owner review)
- [x] Migration `0003`: groups, user_groups, document_acl, permission_change_events (`alembic check` clean)
- [x] Database refuses malformed rules (bad words, COMPANY with a principal, missing principal, duplicates)
- [x] Access resolver: READ (rules A to E), DOWNLOAD, MANAGE, explanations, allow-list SELECT
- [x] Table-driven tests: every principal type, deny beats allow (25 combinations), expiry, clearance edges, country lists, document and user state, revocation, admin is not reader, MANAGE, DOWNLOAD
- [x] Independent Python oracle agrees with the SQL in 8 random worlds
- [x] Mutation check: 8 deliberate mistakes, all caught
- [x] ADR 027
- [x] 92 new tests (261 backend tests in total)
- [ ] Owner manual checks and approval

## 4B API (not started)
- [ ] Groups API, ACL API (MANAGE enforced), rule history in the same transaction
- [ ] Access preview and `GET /groups/{id}` (CR-003)
- [ ] Seed groups and rules for the demo documents (persona scenarios)
- [ ] Negative tests: non-managers get 403, unknown principals refused, expiry in the past refused

## 4C UI (not started)
- [ ] Users page, Groups page, Access section on the document page, "who can read" preview

## Phase 4 close
- [ ] Owner approval, PRs merged, tag `v0.4`

# Phase 4 Brief: Permissions and ACL

**Goal:** the system decides who may read, download or manage each document. All checks happen in SQL, fresh on every request. Deny by default; a DENY always beats an ALLOW; an administrator can manage documents but never read them.

**Requirement IDs:** FR-07 (ALLOW/DENY entries for user, role, group, department, company), FR-08 (access computed per request in SQL with clearance and country gates), FR-04 (groups); also supports NFR-01 for Phase 5.

## Layers (each needs the owner's approval)
| Layer | Content | Status |
|---|---|---|
| **4A** Core | Migration `0003` (groups, user_groups, document_acl, permission_change_events), the access resolver (rules A to E, MANAGE, DOWNLOAD), table-driven, oracle and mutation tests, ADR 027 | Built, merged |
| **4B** API | Groups API, ACL API, rule history, access preview, seed groups and rules for the demo documents, CR-003 | Merged (PR #11) |
| **4C** UI | Users page, Groups page, Access section on the document page, "who can read" preview | Merged (PR #12) |

## Security rules that apply
- Deny by default: a document with no rule is invisible to everybody.
- DENY beats ALLOW (the only exception: the admin's implicit MANAGE, so rules can always be repaired).
- Roles, groups and department are read from the database on every request, never from the token. No cache, so revocation is instant.
- Admin is not reader: `system_admin` never grants READ.
- Every rule change is recorded (before and after) in the same transaction.

## Out of scope
Search and answers (Phases 5 and 6), the audit dashboard (Phase 7), a download endpoint (not in the API contract), a MANAGE-holder screen for non-admins (backlog).

## Open decisions (confirmed by the owner's "Approve" on 2026-10-20)
1. `system_admin` has implicit MANAGE (never READ); MANAGE is also a per-document permission enforced by the API.
2. DOWNLOAD is stored and tested, but there is no download endpoint.
3. The resolver uses `READY` (not `PUBLISHED`).
4. Additive endpoints (CR-003, in 4B): `GET /groups/{id}` and `GET /documents/{id}/access-preview?user_id=`.
5. Seed 6 or more groups and rules for the 12 demo documents, including the "CEO reads everything except one document" case.
6. Group membership changes are not in `permission_change_events` (that table is for document rules); they go to the security log now and to the audit in Phase 7.
7. `GET /documents` stays admin-only; a readable-documents list for employees comes later.
8. `principal_id` is polymorphic text; the service validates that the principal exists.

## Estimate
Blueprint: 7 to 10 days. Plan: 4A about 3, 4B about 2, 4C about 3.

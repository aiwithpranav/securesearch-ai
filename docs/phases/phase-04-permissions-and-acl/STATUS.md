# STATUS: Phase 4, Layer 4C (admin screens)

Branch: `feat/access-4c` (local, not pushed). `main` has Phases 1 to 3 (tags `v0.1`, `v0.2`, `v0.3`) and layers 4A and 4B (PRs #10, #11).

## Done
- ADR 027 (access decision design); Phase 4 docs (BRIEF, PREREQUISITES, CHECKLIST, PROMPT-4, WALKTHROUGH).
- Migration `0003` and models; the access resolver (READ rules A to E, DOWNLOAD, MANAGE, explanations).
- 4A (merged): `alembic check` clean; 92 new tests; oracle agrees with the SQL; mutation check caught all 8 deliberate mistakes.
- 4B: groups API, ACL API (MANAGE enforced), history, access preview, seed script, CR-003, 22 new tests (283 total). Checks: live persona matrix through the API (9 people by 13 documents = 117 answers, 0 mismatches), instant revocation, seed safe to run twice.

- 4C: Users page (invite, edit, roles, deactivate and reactivate), Groups page (create, members), Access section on the document page (rules add, edit, remove, Deny confirmation, expiry, history, who-can-read preview), menu links. 28 frontend tests; typecheck and build clean. Checked in the real browser with temporary users (removed afterwards) and measured at 360 px.

## In progress
- Nothing. Waiting for owner review of 4C.

## Exact next action
1. Owner checks the screens and approves 4C ("4C Approved").
2. Claude pushes `feat/access-4c` and gives the PR link with click-by-click steps. The owner merges; Claude checks the remote.
3. Phase 4 close: final checks on `main`, close-out docs PR, tag `v0.4` only after the owner says "go".

## Blockers
- None.

## Decisions this session
- Owner approved the Phase 4 plan and its 8 decisions (see BRIEF and ADR 027).
- Expiry applies to both ALLOW and DENY rules; the admin's implicit MANAGE cannot be blocked by a DENY.
- 4C: owner approved the plan and its 5 decisions (users page does invite, edit, deactivate and roles; no admin password reset; rule form picks the type first; preview only on the document page; rule edit changes effect, permission and expiry only).
- 4B: owner approved the plan and its 6 decisions (sales executive clearance 2, finance analyst blocked by clearance as a demo, 404 instead of 403, no group delete or rename yet, CR-003 endpoints, MANAGE holders may edit metadata).

## Prerequisites
- Docker running; nothing new.

## Open issues
- GitHub default branch is still `feat/auth-backend` (owner must change it to `main`).
- Groups cannot be renamed or deleted (backlog).

## Resume prompt
"Read docs/phases/phase-04-permissions-and-acl/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\AI\RAG\Secure_Search_AI. Layer 4C is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

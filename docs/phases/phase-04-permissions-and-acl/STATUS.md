# STATUS: Phase 4, Layer 4B (groups, rules, history, preview, seed)

Branch: `feat/access-4b` (local, not pushed). `main` has Phases 1 to 3 (tags `v0.1`, `v0.2`, `v0.3`) and layer 4A (PR #10).

## Done
- ADR 027 (access decision design); Phase 4 docs (BRIEF, PREREQUISITES, CHECKLIST, PROMPT-4, WALKTHROUGH).
- Migration `0003` and models; the access resolver (READ rules A to E, DOWNLOAD, MANAGE, explanations).
- 4A (merged): `alembic check` clean; 92 new tests; oracle agrees with the SQL; mutation check caught all 8 deliberate mistakes.
- 4B: groups API, ACL API (MANAGE enforced), history, access preview, seed script, CR-003, 22 new tests (283 total). Checks: live persona matrix through the API (9 people by 13 documents = 117 answers, 0 mismatches), instant revocation, seed safe to run twice.

## In progress
- Nothing. Waiting for owner review of 4B.

## Exact next action
1. Owner approves 4B ("Approved").
2. Claude pushes `feat/access-4b` and gives the PR link with click-by-click steps. The owner merges; Claude checks the remote.
3. Claude writes the 4C detail plan (users page, groups page, access section on the document page, who-can-read preview) and waits for approval.

## Blockers
- None.

## Decisions this session
- Owner approved the Phase 4 plan and its 8 decisions (see BRIEF and ADR 027).
- Expiry applies to both ALLOW and DENY rules; the admin's implicit MANAGE cannot be blocked by a DENY.
- 4B: owner approved the plan and its 6 decisions (sales executive clearance 2, finance analyst blocked by clearance as a demo, 404 instead of 403, no group delete or rename yet, CR-003 endpoints, MANAGE holders may edit metadata).

## Prerequisites
- Docker running; nothing new.

## Open issues
- GitHub default branch is still `feat/auth-backend` (owner must change it to `main`).
- No screens for rules yet (4C). Groups cannot be renamed or deleted (backlog).

## Resume prompt
"Read docs/phases/phase-04-permissions-and-acl/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\AI\RAG\Secure_Search_AI. Layer 4A is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

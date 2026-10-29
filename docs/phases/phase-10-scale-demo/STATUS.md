# STATUS: Phase 10, Layer 10B (Users list at scale)

Branch: `feat/users-10b` (local, not pushed). `main` has Phases 1 to 9 (tag `v1.0`) and layer 10A (PR #36).

## Done
- 10A merged: scale demo (90,956 passages, 1,000 people, 0 violations), findings in `RESULTS.md`.
- 10B plan approved by the owner (defaults: 50 per page; filters department, role, status; Previous / Next like the Documents screen).
- Backend: search and filters on `GET /users` (CR-005), 11 tests, mutation checks.
- Frontend: Users screen with search, filters and paging; `UserPicker` for Groups members and for the document access rules; 8 tests.
- Real browser check on the scale stack with 1,009 people: 15 of 15 checks.

## In progress
- Nothing. Waiting for the owner's review.

## Exact next action
1. Owner approves ("10B Approved"); Claude pushes `feat/users-10b`, gives the PR link, the owner watches the checks and merges.
2. Tag `v1.1` after "go" (scale demo and Users list at scale in one release).
3. Later, only when the space is needed: delete the scale stack (`down -v`) and the folder `C:/Users/prana/ss-big`; `RESULTS.md` stays.

## Blockers
- None.

## Decisions this session
- The same person picker is used wherever a person is chosen from the whole company (Groups members, access rule "Who", access preview), so no screen is limited to 100 people any more.
- The search is a plain case-insensitive "contains" (LIKE with escaped wildcards): fine for thousands of people; a trigram index is backlog 59.
- The open weak spots of 10A (backlog 55, 56, 57) stay open: they are search quality and answer rules, not the Users list.

## Open issues
- Backlog 55, 56, 57 (exact-identifier search, reranker time, command-line answers), 59 (trigram index for very many people).

## Resume prompt
"Read docs/phases/phase-10-scale-demo/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\\AI\\RAG\\Secure_Search_AI. Layer 10B is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

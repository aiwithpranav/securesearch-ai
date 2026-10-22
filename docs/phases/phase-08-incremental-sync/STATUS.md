# STATUS: Phase 8, Layer 8A (versions)

Branch: `feat/sync-8a` (local, not pushed). `main` has Phases 1 to 7 (tag `v0.7`) and the Next.js 16.4.2 upgrade.

## Done
- Phase 8 plan (3 layers) approved by the owner ("do what you think right"); the five decisions apply (GitHub connector, synthetic repository, read-only token in `.env`, sync every 15 minutes plus Sync now, source deletes are soft deletes).
- 8A: new versions, UNCHANGED skip, restore, deleted list, version date on passages, screens; ADR 033.

## In progress
- Nothing. Waiting for owner review of 8A.

## Exact next action
1. Owner checks 8A and approves ("8A Approved").
2. Claude pushes `feat/sync-8a` and gives the PR link with click-by-click steps; checks the remote after the merge.
3. Claude writes the 8B plan and waits for approval.

## Blockers
- None.

## Decisions this session
- The date shown with a passage is now the date of the version it comes from (`DocumentVersion.created_at`), not the last change of the document row. The field name stays `document_updated_at` (the API contract is frozen); see ADR 033.
- Restoring queues one re-indexing job instead of switching old passages back on, so the index is always built from the stored file.

## Prerequisites
- Docker running. Nothing for 8A and 8B.

## Open issues
- Passages of older versions are kept (inactive) forever; cleanup is backlog 38.
- Evaluation runs write real audit rows (backlog 36).

## Resume prompt
"Read docs/phases/phase-08-incremental-sync/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\\AI\\RAG\\Secure_Search_AI. Layer 8A is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

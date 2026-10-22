# STATUS: Phase 8, Layer 8B (sync engine)

Branch: `feat/sync-8b` (local, not pushed). `main` has Phases 1 to 7 (tag `v0.7`), the Next.js 16.4.2 upgrade and layer 8A (PR #28).

## Done
- Phase 8 plan approved; 8A merged.
- 8B: CR-004, migration `0008`, the engine, the scheduler, the API, ADR 034; 46 new tests (652 total), 18 mutations all caught, real worker and scheduler check.

## In progress
- Nothing. Waiting for owner review of 8B.

## Exact next action
1. Owner approves 8B ("8B Approved"). There is nothing to click yet; the owner can read the walkthrough, or ask Claude to show a run in a terminal.
2. Claude pushes `feat/sync-8b`, gives the PR link with click-by-click steps and checks the remote after the merge.
3. Claude writes the 8C plan (GitHub connector, Sources screen) and lists what the owner must prepare (a private repository with synthetic files and a read-only token in `.env`).

## Blockers
- None.

## Decisions this session
- The sync only ever writes ALLOW READ rules for teams it created (prefix `<kind>:<source name>:`). Everything else is left alone.
- An empty or mostly-empty listing stops the run (a broken source must not wipe the index).
- Settings may not contain secrets; tokens stay in `.env`.

## Prerequisites
- Docker running. Nothing for 8B. For 8C: a GitHub repository and a read-only token.

## Open issues
- A file is always read from the source to compare its SHA-256 (backlog 40).
- Old passages stay (backlog 38). Evaluation runs write real audit rows (backlog 36).

## Resume prompt
"Read docs/phases/phase-08-incremental-sync/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:AIRAGSecure_Search_AI. Layer 8B is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

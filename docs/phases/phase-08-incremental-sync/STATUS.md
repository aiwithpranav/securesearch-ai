# STATUS: Phase 8, Layer 8C (GitHub connector and Sources screen)

Branch: `feat/github-8c` (local, not pushed). `main` has Phases 1 to 7 (tag `v0.7`) and layers 8A (PR #28) and 8B (PR #29).

## Done
- 8C: the GitHub connector, the token wiring (worker only), the Sources screen, the `demo-docs/` folder, ADR 035.
- 45 new backend tests (697 total), 16 mutations all caught, 22 new frontend tests (123 total), real-browser check with the real worker, 360 px.

## In progress
- Nothing. Waiting for owner review of 8C.

## Exact next action
1. Owner checks the Sources screen ("8C Approved").
2. Claude pushes `feat/github-8c`, gives the PR link with click-by-click steps and checks the remote after the merge.
3. Live check with the real repository: the owner makes a 7-day read-only token (steps in PREREQUISITES), Claude runs one sync of `demo-docs/` on `main`, shows what was imported and who can read what, and the owner deletes the token.
4. Phase 8 close: close-out docs, tag `v0.8` after the owner says go, then the Phase 9 plan.

## Blockers
- None. The live check needs the owner's token.

## Decisions this session
- Same repository (`securesearch-ai`), folder `demo-docs/` (owner: "same repo"). The repository is made public when the project is finished; the demo documents are invented.
- Collaborator check on by default; it fails closed (`PERMISSIONS_UNAVAILABLE`) when GitHub will not list collaborators.
- The worker joins the public network for outgoing connections (only the worker holds the token).

## Prerequisites
- Docker running. For the live check: a 7-day read-only token (PREREQUISITES).

## Open issues
- Live check not done yet. Every run reads every file again (backlog 40). Old passages stay (backlog 38).

## Resume prompt
"Read docs/phases/phase-08-incremental-sync/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\\AI\\RAG\\Secure_Search_AI. Layer 8C is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

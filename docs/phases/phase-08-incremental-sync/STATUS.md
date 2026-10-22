# STATUS: Phase 8 (incremental sync) COMPLETE

Branch: `docs/phase-8-close` (docs only). `main` has Phases 1 to 8 (8A PR #28, 8B PR #29, 8C PR #30). Tag `v0.8` after this docs PR is merged.

## Done
- 8C: the GitHub connector, the token wiring (worker only), the Sources screen, the `demo-docs/` folder, ADR 035.
- 45 new backend tests (697 total), 16 mutations all caught, 22 new frontend tests (123 total), real-browser check with the real worker, 360 px.

## In progress
- Nothing. Phase 8 is complete and merged.

## Exact next action
1. Merge this close-out docs PR; Claude checks the remote and tags `v0.8`.
2. Claude writes the Phase 9 plan (hardening and launch: CI, rate limits, health page, backup and restore, privacy text, SECURITY.md, README, demo) and waits for approval.
3. Optional, any time: the live check against the real repository (backlog 43).

## Blockers
- None. The live check needs the owner's token.

## Decisions this session
- Same repository (`securesearch-ai`), folder `demo-docs/` (owner: "same repo"). The repository is made public when the project is finished; the demo documents are invented.
- Collaborator check on by default; it fails closed (`PERMISSIONS_UNAVAILABLE`) when GitHub will not list collaborators.
- The worker joins the public network for outgoing connections (only the worker holds the token).

## Prerequisites
- Docker running. For the live check: a 7-day read-only token (PREREQUISITES).

## Open issues
- The live check against the real repository was not done (it needs a short-lived read-only token; backlog 43). The connector is proven against a fake GitHub and the real worker.
- Every run reads every file again (backlog 40). Old passages stay (backlog 38).

## Resume prompt
"Read docs/phases/phase-08-incremental-sync/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\\AI\\RAG\\Secure_Search_AI. Phase 8 is complete. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

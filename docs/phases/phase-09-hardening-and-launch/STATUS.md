# STATUS: Phase 9, Layer 9B (operations)

Branch: `feat/ops-9b` (local, not pushed). `main` has Phases 1 to 8 (tag `v0.8`) and layer 9A (PR #32, CI green).

## Done
- 9A merged. 9B plan approved (retention 365 days with a guarded purge, public status page, backup and restore with a tested restore, keep 3 versions).
- 9B: retention and purge, status and counters, cleanup, backup and restore scripts, runbook, ADR 037; a real restore on an empty stack.

## In progress
- Nothing. Waiting for owner review of 9B, then the CI run on the pull request.

## Exact next action
1. Owner checks 9B ("9B Approved").
2. Claude pushes `feat/ops-9b`, gives the PR link; the owner watches the Checks (green) and merges.
3. Claude writes the 9C plan (privacy and terms made accurate, SECURITY.md, docs/security.md, docs/api.md, accessibility checks).

## Blockers
- None.

## Decisions this session
- `/health` and `/ready` are unchanged (frozen contract); the new public `/status` carries only names and up or down.
- The audit purge flag is an accident guard with a 30-day floor, not a defence against someone who controls the database login (written down in ADR 037).
- Backups are made with Bash scripts (Git Bash on Windows); secrets are never in a backup.

## Prerequisites
- Docker running.

## Open issues
- Backups are manual (a schedule is documented in the runbook, not set up).
- Lighthouse and axe checks come in 9C (backlog 45).

## Resume prompt
"Read docs/phases/phase-09-hardening-and-launch/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\\AI\\RAG\\Secure_Search_AI. Layer 9B is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

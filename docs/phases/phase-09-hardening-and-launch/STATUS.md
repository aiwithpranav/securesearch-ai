# STATUS: Phase 9, Layer 9A (quality gates and CI)

Branch: `feat/ci-9a` (local, not pushed). `main` has Phases 1 to 8 (tag `v0.8`).

## Done
- Phase 9 plan approved (MIT licence, public at the end, CI on GitHub, retention 365 days, the owner records the demo video, deployment is documented only).
- 9A: type fixes, lint setup, CI workflow, scans, Dependabot, templates, licence, `setup_env.sh`, `docs/ci.md`, ADR 036; `pypdf` security upgrade; Dockerfile layer order.

## In progress
- Nothing. Waiting for owner review of 9A, then the first CI run on the pull request.

## Exact next action
1. Owner approves 9A ("9A Approved").
2. Claude pushes `feat/ci-9a`, gives the PR link with click-by-click steps. The owner opens the PR page and tells Claude whether the **Checks** are green or red (and pastes the failing step's name if red). Claude fixes anything red in the same branch.
3. After the merge: Claude writes the 9B plan (retention, status page, backup and restore).

## Blockers
- None.

## Decisions this session
- Prettier is not adopted (it would rewrite the whole history of every file); ESLint and ruff cover the rules.
- The React Compiler advisory rules of Next.js 16 are warnings with a ceiling, not errors (backlog 44).
- Security fixes may use a package version younger than the usual two-week rule (pypdf 6.21.1).

## Prerequisites
- Docker running.

## Open issues
- The workflow can only be proven by GitHub. The first run is expected to take about 20 minutes (no image cache yet).
- Lighthouse and axe checks come in 9C.

## Resume prompt
"Read docs/phases/phase-09-hardening-and-launch/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\\AI\\RAG\\Secure_Search_AI. Layer 9A is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

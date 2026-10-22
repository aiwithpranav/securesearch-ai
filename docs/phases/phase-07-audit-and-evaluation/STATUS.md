# STATUS: Phase 7, Layer 7C (dashboards)

Branch: `feat/dashboards-7c` (local, not pushed). `main` has Phases 1 to 6 (tags `v0.1` to `v0.6`), the design refresh, 7A and 7B.

## Done
- Phase 7 plan; ADR 031; Phase 7 docs.
- 7A: append-only audit tables (migration `0006`), audit written with every search and answer ("no audit, no answer"), security events saved, audit routes and CSV export for security_admin and auditor, 42 new tests (526 total), 14 mutations all caught, live check through the API.

- 7B: 36 extra synthetic documents (48 total), 62 cases, canary scanner, runner, metrics and mode comparison, evaluation tables (migration `0007`) and API, `load_eval_corpus` and `run_eval` scripts, `docs/evaluation-report.md`, ADR 032; refusal threshold tuned from 0.03 to 0.30; 46 new tests (572 total), 14 mutations (13 caught, 1 equivalent); real-stack run 62 of 62 with 0 leaks.

- 7C: dashboards API (admin overview, knowledge gaps with masking, suggested questions), a role-based Manage menu, Audit, Overview, Knowledge gaps and Evaluation screens, employee Home with ideas and recent questions, weak-match note aligned to 0.30; 20 new backend tests (592 total), 37 new frontend tests (96 total), 6 mutations all caught; checked in a real browser with temporary people and at 360 px.

## In progress
- Nothing. Waiting for owner review of 7C.

## Exact next action
1. Owner checks 7C and approves ("7C Approved").
2. Claude pushes `feat/dashboards-7c` and gives the PR link with click-by-click steps. The owner merges; Claude checks the remote.
3. Phase 7 close: final checks on main, close-out docs, tag `v0.7` after the owner says "go", then the Phase 8 plan.

## Blockers
- None.

## Decisions this session
- Owner: "do what you think right" and "7A suru": the six proposed decisions apply (see PROMPT-7 and ADR 031).
- 7B (owner: "do what you think right"): the evaluation uses a fake answer writer by default; the refusal threshold was changed from 0.03 to 0.30 because the measurements showed 0.03 let unrelated documents answer (see `docs/evaluation-report.md`). The cost is that paraphrases are answered 4 of 8 times.
- When no model key is set, `/chat` answers 503 before anything is asked, so nothing is audited; with a key, a model failure is audited as UNAVAILABLE.

## Prerequisites
- Docker running. No key is needed for 7A.

## Open issues
- No retention rule for the audit trail yet (backlog 32). Screens are built in 7C.
- Paraphrase answer rate 4 of 8 (backlog 34); the real model has not been evaluated (backlog 35).

## Resume prompt
"Read docs/phases/phase-07-audit-and-evaluation/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\AI\RAG\Secure_Search_AI. Layer 7C is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

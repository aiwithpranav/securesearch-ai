# STATUS: Phase 5, Layer 5B (search API)

Branch: `feat/search-api-5b` (local, not pushed). `main` has Phases 1 to 4 (tags `v0.1` to `v0.4`) and layer 5A (PR #14).

## Done
- Phase 5 plan approved with 5 decisions; ADR 028; Phase 5 docs.
- 5A: migration `0004` (GIN and HNSW indexes), retrieval module, reranker baked into the image, 52 new tests (335 total), mutation check, live measurement on the demo data.
- 5B: `POST /search` (modes, rate limit 30 per minute per person, validation, no question text in logs, no-store, score details for admin only), start-up warm-up, 20 new tests (355 total), 6 mutations caught, live concurrency check.

## In progress
- Nothing. Waiting for owner review of 5B.

## Exact next action
1. Owner approves 5B ("5B Approved").
2. Claude pushes `feat/search-api-5b` and gives the PR link with click-by-click steps. The owner merges; Claude checks the remote.
3. Claude writes the 5C plan (search screen) and waits for approval.

## Blockers
- None.

## Decisions this session
- Owner approved the Phase 5 plan and its 5 decisions (see PROMPT-5 and ADR 028).
- Keyword search matches any word of the question (an AND query found nothing for natural questions).
- Provisional reranker refusal threshold 0.03.
- 5B (owner said "do what you think right" after the plan): mode optional, 30 searches per minute per person, score details for system_admin only, no search history until Phase 6, models warmed at start-up.

## Prerequisites
- Docker running. The image was rebuilt once (reranker download, internet needed once).

## Open issues
- No search screen yet (5C).
- Reranker latency about 0.5 to 2 s per search, up to 9 s with 6 at once (target P95 under 5 s).

## Resume prompt
"Read docs/phases/phase-05-hybrid-retrieval/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\AI\RAG\Secure_Search_AI. Layer 5B is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

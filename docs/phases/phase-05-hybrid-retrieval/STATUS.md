# STATUS: Phase 5 complete (5A, 5B, 5C merged)

Branch: `docs/phase-5-close`. `main` has Phases 1 to 4 (tags `v0.1` to `v0.4`) and all of Phase 5 (PRs #14, #15, #16). Tag `v0.5` comes after this docs PR is merged.

## Done
- Phase 5 plan approved with 5 decisions; ADR 028; Phase 5 docs.
- 5A: migration `0004` (GIN and HNSW indexes), retrieval module, reranker baked into the image, 52 new tests (335 total), mutation check, live measurement on the demo data.
- 5B: `POST /search` (modes, rate limit 30 per minute per person, validation, no question text in logs, no-store, score details for admin only), start-up warm-up, 20 new tests (355 total), 6 mutations caught, live concurrency check.

- 5C: the `/search` screen (question box, results with relevance bar, weak-match note, empty, error and rate-limit states, administrator score details), menu link, Home and tour wording. 41 frontend tests; checked in the real browser with temporary people (removed afterwards) and at 360 px.

## In progress
- Nothing.

## Exact next action
1. Owner merges the close-out docs PR; Claude verifies the remote.
2. Claude tags `v0.5` (after the owner says go), pushes it and verifies the tag on the remote.
3. Claude writes the Phase 6 (answers and citations) plan and waits for approval. Phase 6 needs an OpenAI API key and a spend limit: see the blueprint prerequisites.

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
- Reranker latency about 0.5 to 2 s per search, up to 9 s with 6 at once (target P95 under 5 s).

## Resume prompt
"Read docs/phases/phase-05-hybrid-retrieval/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\AI\RAG\Secure_Search_AI. Phase 5 is complete; the v0.5 tag is next. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

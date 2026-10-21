# STATUS: Phase 6, Layer 6B (answer API)

Branch: `feat/chat-api-6b` (local, not pushed). `main` has Phases 1 to 5 (tags `v0.1` to `v0.5`), the design refresh (PR #18) and layer 6A.

## Done
- Phase 6 plan approved; ADR 030; Phase 6 docs.
- 6A: LLM adapter, prompt, validator, answer pipeline, 83 new tests (438 total), 11 mutations caught, live check with the real model (8 questions, about $0.0005).

- 6B: `POST /chat`, `/chat/stream`, `/chat/feedback`, `GET /chunks/{id}/preview`, `GET /me/search-history`, `DELETE /me/search-history/{id}`; migration `0005`; 45 new tests (483 total); 12 mutations (10 caught, 2 equivalent); live check through the running API with the real model.

## In progress
- Nothing. Waiting for owner review of 6B.

## Exact next action
1. Owner approves 6B ("6B Approved").
2. Claude pushes `feat/chat-api-6b` and gives the PR link with click-by-click steps. The owner merges; Claude checks the remote.
3. Claude writes the 6C plan (answer, citations and evidence panel on the search screen, thumbs, history) and waits for approval.

## Blockers
- None.

## Decisions this session
- GPT-4o mini; English only; fake model in tests; the owner puts the key in `.env` and deletes it when not needed.
- Inline `[S#]` markers are optional (the real model often leaves them out); the citations field is the validated contract.
- Refusal threshold 0.03 stays provisional until Phase 7.
- 6B: history keeps the question and cited ids, not the answer; 10 answers per minute per person; stage events only; the preview shows the full passage only to people who may read it; one 503 message when answers are unavailable.

## Prerequisites
- Docker running. An OpenAI key was already in the local `.env` (not read, only checked for its shape). The owner should delete it at OpenAI when no live check is needed.

## Open issues
- Docker image rebuild takes about 15 minutes whenever `requirements.txt` changes (backlog 31).
- Answer quality on a larger question set is measured in Phase 7.

## Resume prompt
"Read docs/phases/phase-06-answers-and-citations/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\AI\RAG\Secure_Search_AI. Layer 6B is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

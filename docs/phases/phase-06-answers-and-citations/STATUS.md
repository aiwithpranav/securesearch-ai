# STATUS: Phase 6, Layer 6C (Ask screen)

Branch: `feat/answers-ui-6c` (local, not pushed). `main` has Phases 1 to 5 (tags `v0.1` to `v0.5`), the design refresh (PR #18) and layers 6A and 6B.

## Done
- Phase 6 plan approved; ADR 030; Phase 6 docs.
- 6A: LLM adapter, prompt, validator, answer pipeline, 83 new tests (438 total), 11 mutations caught, live check with the real model (8 questions, about $0.0005).

- 6B: `POST /chat`, `/chat/stream`, `/chat/feedback`, `GET /chunks/{id}/preview`, `GET /me/search-history`, `DELETE /me/search-history/{id}`; migration `0005`; 45 new tests (483 total); 12 mutations (10 caught, 2 equivalent); live check through the running API with the real model.

- 6C: Ask screen (Ask and Find modes, progress, answer with sources, evidence panel, thumbs, recent questions, error states), menu, Home and tour wording; 59 frontend tests; 18 real-browser checks with the real model; 360 px measured. One backend fix: the model client retries a dropped connection once (484 backend tests).

## In progress
- Nothing. Waiting for owner review of 6C.

## Exact next action
1. Owner approves 6C ("6C Approved").
2. Claude pushes `feat/answers-ui-6c` and gives the PR link with click-by-click steps. The owner merges; Claude checks the remote.
3. Phase 6 close: final checks on `main`, close-out docs PR, tag `v0.6` only after the owner says "go". Then the Phase 7 plan.

## Blockers
- None.

## Decisions this session
- GPT-4o mini; English only; fake model in tests; the owner puts the key in `.env` and deletes it when not needed.
- Inline `[S#]` markers are optional (the real model often leaves them out); the citations field is the validated contract.
- Refusal threshold 0.03 stays provisional until Phase 7.
- 6C (owner: "do what you think right"): Ask is the default mode; evidence in a side panel or bottom sheet; thumbs only on answers; progress through the streaming route; history shows questions only and Ask again writes a fresh answer.
- 6B: history keeps the question and cited ids, not the answer; 10 answers per minute per person; stage events only; the preview shows the full passage only to people who may read it; one 503 message when answers are unavailable.

## Prerequisites
- Docker running. An OpenAI key was already in the local `.env` (not read, only checked for its shape). The owner should delete it at OpenAI when no live check is needed.

## Open issues
- Docker image rebuild takes about 15 minutes whenever `requirements.txt` changes (backlog 31).
- Answer quality on a larger question set is measured in Phase 7.

## Resume prompt
"Read docs/phases/phase-06-answers-and-citations/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\AI\RAG\Secure_Search_AI. Layer 6C is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."

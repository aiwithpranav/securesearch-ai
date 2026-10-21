# Phase 6 Checklist

## 6A Engine (built, waiting for owner review)
- [x] LLM adapter (OpenAI client and a fake), key never logged or in errors, backend container only
- [x] Prompt with untrusted-data rules and defused tags
- [x] Validator: JSON shape, citations only to given passages, no links, HTML or code, length cap
- [x] Answer pipeline: allow-list, second wall, confidence gate, model, validation, uniform refusal
- [x] 83 new tests (438 backend tests in total), random worlds against the Phase 4 oracle
- [x] 11 mutation checks all caught
- [x] Live check with the real model on the demo documents
- [x] ADR 030, docs, challenges 81 to 85
- [x] Owner manual checks and approval (merged, PR #19)

## 6B API (built, waiting for owner review)
- [x] `POST /chat` in the blueprint shape, rate limit, 503 without a key, uniform refusal
- [x] `POST /chat/stream`: stage events, then one result, no answer text before validation
- [x] Evidence preview that re-checks READ every time (one identical 404)
- [x] Search history (private, paged, deletable) and feedback; migration `0005`
- [x] No question or answer text in logs
- [x] 45 new tests (483 total), 12 mutations (10 caught, 2 equivalent), live check through the API
- [x] Owner manual checks and approval (merged, PR #20)

## 6C UI (built, waiting for owner review)
- [x] Ask and Find modes; progress stages; answer with S1 badges and sources
- [x] Evidence panel (side panel and bottom sheet), Esc, focus return, re-checked on the server
- [x] Thumbs with optional comment; recent questions with Ask again and Remove
- [x] Uniform no-answer message with Show matching passages; 503 and 429 messages
- [x] 59 frontend tests, 18 real-browser checks with the real model, 360 px measured
- [ ] Owner manual checks and approval

## Phase 6 close
- [ ] Owner approval, PRs merged, tag `v0.6`

# Phase 6 Walkthrough: Answers and citations

## Layer 6A: the answer engine (backend)

### 1. What we built
The engine that turns a question into a short written answer with citations, or one uniform refusal. There is no API route or screen yet (6B, 6C). The language model is used only as a writer: it never decides who may read what.

### 2. How it works, step by step
1. **Search** (Phase 5): the allow-list is built first; full-text and vector search run inside it; the reranker orders the best passages.
2. **Second wall:** the access resolver is asked again for every document behind the chosen passages. Any "no" stops everything.
3. **Confidence:** if even the best passage is a weak match (reranker score below 0.03) the system refuses and does not call the model at all. Only passages at or above that score go on, at most 6.
4. **Prompt:** the question and the passages go to the model inside `<question>` and `<sources>` blocks, each passage numbered S1, S2... The system prompt says all of it is untrusted data. Tag-like text is defused so nothing can close a block.
5. **Model:** GPT-4o mini, temperature 0, JSON only, at most 500 output tokens, no tools.
6. **Validation:** the reply must be the exact JSON shape; a real answer must cite at least one source; every cited id and every `[S#]` marker must be a passage the model was given; no links, images, HTML or code; at most 1,500 characters. A bad reply gets one retry, then the refusal.
7. **Result:** `ANSWERED` with the answer and the cited passages (title, section, page, a 240-character snippet, updated time), or a refusal with the same text for every reason.

### 3. Important files
`backend/app/llm/` (interface, OpenAI client), `backend/app/answers/` (`prompt.py`, `validator.py`, `service.py`), `backend/app/scripts/answer_check.py` (live check), settings in `backend/app/core/config.py`, key wiring in `docker-compose.yml`. Tests: `tests/test_answers_unit.py`, `tests/test_llm_client.py`, `tests/test_answers.py`. Decision record: `docs/adr/030-grounded-answers.md`.

### 4. Tools: why we chose them
- GPT-4o mini through plain HTTPS (`httpx`): cheap, one small adapter, easy to replace.
- A fake model in tests: every rule is proven without a key, without internet and without cost.
- A pure validator with no database: easy to test hard (links, hallucinated ids, huge answers).

### 5. How to run it
`docker compose build backend && docker compose up -d`. Live check (needs your key in `.env` and the demo data): `docker compose exec backend python -m app.scripts.answer_check`. The API route arrives in 6B.

### 6. How to test it
`docker compose exec backend python -m pytest -q` (438 tests; 83 are new).

### 7. Actual results (checked by me)
- 438 backend tests pass; `alembic check` clean (no migration in 6A).
- Safety: in 6 random worlds the independent oracle agrees the model, the answer and the citations only ever hold allowed documents; forbidden text never reaches the prompt; a restricted and a missing topic are refused identically; an obedient model that returns a link or a made-up citation is blocked.
- Mutation check: 11 deliberate mistakes all caught.
- Live, real model, demo documents (8 questions, 2,252 input and 256 output tokens, about $0.0005): leave, payments, escalation, discount and phishing questions answered correctly with the right citation; the salary question (not readable by the person) and the football question refused without calling the model; the document that says "ignore all previous instructions" was answered normally and its instruction ignored. Answers took 1.6 to 7 s.

### 8. Limitations and open issues
- Not verified: answer quality on many questions (Phase 7), Marathi or other languages (English only).
- The first live run refused everything because the model leaves out inline markers (challenge 85); fixed by making markers optional.
- Provider outages and rate limits surface as a short error that 6B turns into a clear message.
- See `docs/CHALLENGES.md` entries 81 to 85.

## Layer 6B: the answer API

### 1. What we built
The HTTP routes for answers: `POST /chat`, `POST /chat/stream` (progress as Server-Sent Events), `POST /chat/feedback`, `GET /chunks/{id}/preview` (the passage behind a citation), `GET /me/search-history` and `DELETE /me/search-history/{id}`. They follow the blueprint contract; no change request was needed. There is no screen yet (6C). Decisions taken: the history keeps the question but not the answer; 10 answers per minute per person; stage events only (no word-by-word answer); the preview shows the full passage but only to a person who may read it; one friendly 503 message when answers are unavailable.

### 2. How it works, step by step
1. **Signed in** (token, active account), then **rate limit** (10 answers a minute per person, shared by `/chat` and `/chat/stream`; `Retry-After` on 429).
2. **Validation:** the question is trimmed and must be 1 to 500 characters (422 otherwise).
3. **Model available?** No key, or a model failure, gives one 503: "Answers are not available right now. You can still search." Search is not affected.
4. **Engine (6A)** runs in a worker thread, at most 2 at a time, with the allow-list first, the confidence gate, the model, and validation.
5. **Response** in the blueprint shape: `status`, `answer`, `citations`, `request_id`, plus `refusal` (the one uniform text, only on refusals) and `history_id` so the screen can send feedback. Refusals carry no answer and no citations.
6. **History:** one row for the person: the question, the outcome and the cited passage ids. The answer text is never stored, so an answer cannot outlive the permission it was built on.
7. **Stream:** the same work, but small `stage` messages first (searching N documents you can read, writing the answer, checking the sources) and one final `result` message with the same shape as `/chat`. Stage labels contain no document text, and no answer text is sent before validation.
8. **Preview:** READ is checked again every time. No rule, a deny rule, a deleted or unfinished document, an old passage and an unknown id all give the same 404, even to an administrator.
9. **Feedback:** thumbs up or down (and an optional comment up to 500 characters) on your own answer; rating again replaces the rating. **History** is newest first, paged (at most 50), and only yours; you can delete an item and its feedback goes with it.
10. **Log:** one `chat` line with ids, status, a reason code, token counts and time. Never the question or the answer.

### 3. Important files
`backend/app/api/v1/chat.py`, `backend/app/schemas/chat.py`, `backend/app/models/chat.py`, migration `0005_chat_tables.py` (tables `search_history` and `chat_feedback`), progress callbacks in `backend/app/answers/service.py`. Tests: `backend/tests/test_chat_api.py`. Decision record: `docs/adr/030-grounded-answers.md` (6B addendum).

### 4. Tools: why we chose them
Existing building blocks only: FastAPI, the Redis rate limiter, the structured security log, the 6A engine. Server-Sent Events are plain HTTP, so no new server or library is needed.

### 5. How to run it
`docker compose build backend && docker compose up -d`, then `docker compose exec backend alembic upgrade head`. Try it in the API docs page at `/api/docs` (sign in first), or from the 6C screen later. A live answer needs your key in `.env`.

### 6. How to test it
`docker compose exec backend python -m pytest -q` (483 tests; 45 are new for 6B).

### 7. Actual results (checked by me)
- 483 backend tests pass; `alembic check` clean after migration `0005`.
- API tests: 401 on every route and for deactivated people; the agreed answer shape; forbidden text and ids never appear in any response or in the model prompt; a restricted topic and a missing topic give identical responses; revoking a rule changes the next answer; no key or a failing model gives a clean 503 and saves nothing; 7 kinds of bad question give 422; the rate limit is per person; history is private, paged, capped and deletable; feedback only on your own answers; the preview gives one identical 404 for every not-allowed case; the stream sends stages in order, then one result; the question and the answer never appear in logs; random worlds against the Phase 4 oracle over HTTP.
- Mutation check: 12 deliberate mistakes; 10 caught and 2 are equivalent (the engine already guarantees a refusal has no answer or citations, so the route's second guard cannot be seen from outside).
- Live, real model through the running API with a temporary person (deleted afterwards): a leave question answered with a Leave policy citation in 5 s; the evidence preview, feedback, history and delete worked; the restricted salary question got the uniform refusal; the stream showed all stages and then the result.

### 8. Limitations and open issues
- No screen yet (6C). History has no automatic expiry (a retention period can be added later).
- Answers take about 2 to 7 s; with many people at once they queue (2 at a time).
- See `docs/CHALLENGES.md` entries 86 to 90.

## Layer 6C: the Ask screen (frontend)

### 1. What we built
The page `/search` (menu link **Ask**) now has two modes: **Ask a question** (a short cited answer, the default) and **Find passages** (the Phase 5 search). It adds an evidence panel for the passage behind a citation, thumbs up or down, and a list of your recent questions. Backend unchanged except one small robustness fix (see section 7). Decisions taken: Ask is the default; history shows the question only and "Ask again" writes a fresh answer; evidence is a side panel on a laptop and a bottom sheet on a phone; thumbs only on answers; the progress view uses the streaming route.

### 2. How it works, step by step
1. The person types a question (up to 500 characters, with a counter) and presses **Ask** (or **Search** in Find mode). An empty question shows a message and sends nothing. The question never goes into the web address.
2. **Progress** appears while waiting: "Searching 4 documents you can read", "Writing the answer from your sources", with a tick when a stage is done. Only the newest request may update the screen.
3. **Answer card:** the answer, small S1, S2 badges where the answer cites a source, then **Sources**: document, section or page, a snippet and **View passage**.
4. **Evidence panel:** opens with the whole passage (title, place, updated date). It fetches the passage again from the server, which re-checks READ; if it is no longer allowed the panel says "This passage is no longer available." Esc or Close shuts it and focus returns to the button that opened it.
5. **Thumbs:** Yes or No (pressed state shown), then an optional comment; rating again replaces the rating.
6. **No answer:** one plain message (the same for every reason), plus **Show matching passages** which switches to Find mode. Nothing says why, so it cannot reveal restricted documents.
7. **Errors:** answers off (no key, provider down) shows "Answers are not available right now. You can still search." with **Find passages instead**; too many questions shows how many seconds to wait; network problems have plain words and Try again.
8. **Recent questions:** your last 10, with status and age, **Ask again** and **Remove** (asks to confirm). Only the question is kept, never the answer.

### 3. Important files
`frontend/lib/chat.ts` and `chat.test.ts` (API calls, the event-stream reader, wording helpers), `frontend/lib/session.ts` (`authedFetch` for streaming) and `lib/api.ts` (shared error parsing), `frontend/app/(portal)/(app)/search/` (`SearchView.tsx`, `AnswerCard.tsx`, `EvidencePanel.tsx`, `HistoryList.tsx`), menu, Home and tour wording.

### 4. Tools: why we chose them
Same stack as the other screens. The event stream is read with the browser's own `fetch` and a small tested parser, so no new library is needed.

### 5. How to run it
`docker compose up -d`, `cd frontend && npm run dev`, sign in, click **Ask** in the menu. Live answers need your key in `.env`.

### 6. How to test it
`cd frontend && npx tsc --noEmit && npm test && npm run build` (59 frontend tests); backend `docker compose exec backend python -m pytest -q` (484).

### 7. Actual results (checked by me)
- Typecheck, 59 frontend tests, production build; backend 484 tests and `alembic check` clean.
- Real browser, temporary people (deleted afterwards), real model, 18 checks all passed: both modes; progress stages; a leave answer with a Leave policy source; the evidence panel (opens with the passage, focus moves to Close, Esc closes and returns focus); thumbs; recent questions appear, survive a reload, ask again, remove with confirmation; the salary question (not readable by the person) shows the uniform message, no salary text, and Show matching passages works; Find mode still works; 503 and 429 (simulated server answers) show the right messages; no sideways scrolling at 360 px with the answer and the bottom sheet.
- Finding: twice during the run the provider call failed once with a dropped connection and the screen correctly showed the friendly 503. The model client now retries a dropped connection once (new test), like it already did for busy or failing responses.

### 8. Limitations and open issues
- Not verified: screen readers beyond labels, roles and live regions; very long answers (capped at 1,500 characters by the server).
- Answers take 2 to 7 seconds; when many people ask at once they queue (2 at a time).
- See `docs/CHALLENGES.md` entries 91 to 94.

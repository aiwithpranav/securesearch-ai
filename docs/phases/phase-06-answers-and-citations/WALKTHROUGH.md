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

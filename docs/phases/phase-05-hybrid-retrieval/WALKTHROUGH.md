# Phase 5 Walkthrough: Hybrid retrieval

## Layer 5A: the search engine (backend)

### 1. What we built
The engine that finds the best passages ("chunks") for a question, for one person, using only documents that person may read. There is no screen or API yet (5B, 5C). It combines two ways of searching: keyword search (exact words) and vector search (meaning), merges them, and lets a second model put the best ones in final order.

### 2. How it works, step by step
1. **Allow-list first.** The Phase 4 resolver builds, in SQL, the list of documents this person may READ (deny by default, DENY wins, clearance, country, expiry, document ready and not deleted).
2. **Keyword search** (PostgreSQL full-text, GIN index) runs only inside that list. A question becomes "any of these words" so natural questions work; chunks with more matching words rank higher.
3. **Vector search** (pgvector, HNSW index) runs only inside that list. The question is turned into 384 numbers with the same local model that embedded the documents; the closest chunks win.
4. **RRF** (Reciprocal Rank Fusion) merges the two lists: each chunk gets `1/(60+rank)` from every list it appears in.
5. **Reranker** (a cross-encoder model, local) reads the question together with each of the best 20 chunks and scores how well they answer it (0 to 1). The top 5 to 8 are returned.
6. **Final guard.** The text of the chosen chunks is loaded with the allow-list applied once more.
7. **Modes.** `keyword`, `vector`, `hybrid` all use the same allow-list (setting `RETRIEVAL_MODE`, default hybrid). The reranker is on by default in hybrid only.

### 3. Important files
- `backend/app/retrieval/search.py` (the pipeline), `fusion.py` (RRF), `reranker.py` (cross-encoder).
- `backend/migrations/versions/2026_10_21_1000-0004_retrieval_indexes.py`; indexes also declared in `app/models/document.py`.
- `backend/app/core/config.py` (retrieval settings), `backend/Dockerfile` (reranker baked in).
- `backend/app/scripts/retrieval_check.py` (quick measurement on the demo data).
- Tests: `tests/test_retrieval.py`, `tests/retrieval_world.py`. Decision record: `docs/adr/028-authorized-hybrid-retrieval.md`.

### 4. Tools: why we chose them
- PostgreSQL full-text + pgvector: one database, one transaction, one allow-list; no second search server to keep in sync with permissions.
- `BAAI/bge-reranker-base` (MIT, local CPU): orders the final candidates better than the fast searches; the document text never leaves the machine.
- RRF: needs no score tuning between two very different scoring systems.

### 5. How to run it
`docker compose build backend && docker compose up -d`, then `docker compose exec backend alembic upgrade head`. Quick demo measurement: `docker compose exec backend python -m app.scripts.retrieval_check`.

### 6. How to test it
`docker compose exec backend python -m pytest -q` (335 tests; 52 are new).

### 7. Actual results (checked by me)
- `alembic check` clean; 335 backend tests pass.
- Safety: in 6 random worlds the independent oracle agrees that every mode returns only allowed documents, and keyword mode returns all of them. Every blocking rule hides the best match in every mode, the reranker never sees forbidden text, revocation applies on the next search, and the vector search still fills the result when 60 closer chunks are forbidden.
- Mutation check: 5 deliberate mistakes caught (see ADR 028 for the one that is blocked by the final guard on purpose).
- Demo data, as shivam@demo (may read 8 of the 12 documents, 12 of 20 test questions apply): Recall@5 is 1.00 in keyword, vector, hybrid and hybrid+rerank; MRR 0.94, 1.00, 1.00, 1.00; median time 8, 21, 24 and 2,145 ms. On such a small, easy set the modes tie; the real comparison is Phase 7.
- Reranker scores: best chunk for off-topic questions at most 0.016; for on-topic questions at least 0.044 (median 0.97). Provisional refusal threshold 0.03.
- Admin check: prashant@demo (admin plus employee) found documents only through the employee rules.

### 8. Limitations and open issues
- Not verified: speed and quality with thousands of documents; the reranker costs about 2 s per search on a laptop CPU.
- `ts_rank` is not BM25. Quotes and search operators are ignored.
- The threshold 0.03 is provisional (tiny question set).
- See `docs/CHALLENGES.md` entries 65 to 70.

## Layer 5B: the search API

### 1. What we built
`POST /api/v1/search`: a signed-in person sends a question and gets the best matching passages from the documents they may read. No screen yet (5C). Decisions taken: mode optional (server default hybrid), 30 searches per minute per person, score details only for `system_admin`, no search history yet (Phase 6), models loaded when the API starts.

### 2. How it works, step by step
1. The caller must be signed in (same checks as every route: token, active account).
2. The question is trimmed and checked: 1 to 500 characters, otherwise 422 with a plain message. `mode` must be `keyword`, `vector` or `hybrid` or left out.
3. Rate limit: 30 per minute per person (Redis); more gives 429 with `Retry-After`.
4. The search runs in a worker thread (so the API stays responsive), at most 2 at a time; the rest wait in line.
5. The engine of 5A does the work: allow-list first, then both searches inside it, fusion, rerank.
6. One log line is written with ids only: user id, mode, result count, time. The question text is never logged or stored.
7. The answer carries `Cache-Control: no-store`. Ordinary people get the final score; a `system_admin` also gets every score signal (keyword rank, vector rank, RRF, rerank) to tune and debug.

### 3. Important files
`backend/app/api/v1/search.py` (route, warm-up), `backend/app/schemas/search.py` (request and response), `backend/app/main.py` (router and start-up warm-up), `backend/app/core/config.py` (limits), `backend/tests/test_search_api.py`.

### 4. Tools: why we chose them
Existing building blocks only: FastAPI, the Redis rate limiter used for login and upload, the structured security log. `asyncio.to_thread` keeps CPU-heavy model work off the event loop.

### 5. How to run it
Rebuild and start (`docker compose build backend && docker compose up -d`), sign in, then call `POST /api/v1/search` with a bearer token (try it in the API docs page at `/api/docs`).

### 6. How to test it
`docker compose exec backend python -m pytest -q` (355 tests; 20 are new for 5B).

### 7. Actual results (checked by me)
- 355 backend tests pass; `alembic check` clean.
- Tests cover: 401 without or with a bad token and for deactivated users; allowed text returned and forbidden text never present; the three modes; default mode; admin is not reader but sees scores for what the rules allow; revoking a rule changes the next search; odd questions (quotes, operators, SQL, long, non-English) never crash; 8 kinds of bad request give 422; the rate limit is per person and sends `Retry-After`; the question text never appears in logs while one search event does; only the search route can return chunk text.
- Mutation check: 6 deliberate mistakes caught.
- Live with real models: 6 searches at once all succeeded; the slowest took 9.4 s, while health checks stayed at most 13 ms; first search after a cold start about 8 s (now warmed at start-up).

### 8. Limitations and open issues
- Under many simultaneous searches latency rises (CPU only); fine for one or two users.
- No search history yet (Phase 6). No screen yet (5C).
- See `docs/CHALLENGES.md` entries 71 to 73.

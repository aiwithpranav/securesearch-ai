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

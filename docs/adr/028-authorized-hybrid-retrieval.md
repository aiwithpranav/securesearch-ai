# ADR 028: Authorized hybrid retrieval (Phase 5)

## Status
Accepted (2026-10-21). The owner approved the Phase 5 plan and its 5 decisions. The owner can reverse any item.

## Context
Blueprint sections 9 (retrieval pipe) and 23 (why hybrid) require: authorize first, then full-text 30 and vector 30, RRF with k=60, cross-encoder rerank of 20, keep 5 to 8. No unauthorized chunk may ever be scored, returned or logged as content (NFR-01). Three modes (keyword, vector, hybrid) must share one allow-list so the Phase 7 comparison is fair.

## Decision
- **Order of work (the security design):** (1) the access resolver builds the allow-list of readable document ids in SQL; (2) full-text and vector search both run only inside it; (3) RRF fuses, the reranker reorders the best 20; (4) the text of the chosen chunks is loaded with the allow-list applied again. Step 4 is deliberate duplication: a bug in steps 2 or 3 still cannot widen access.
- **Only active chunks** (`is_active`) of READY, not-deleted documents are searched. `system_admin` has no special search right: an admin finds only what the rules allow (admin is not reader).
- **Full-text:** PostgreSQL `websearch_to_tsquery` on the stored `tsv` column with a GIN index, ranked by `ts_rank_cd` (this is not BM25; say so honestly). A question is turned into "any word" matching (`word or word or ...`): an AND query returned nothing for natural questions. Quotes and operators are not supported; stop words are dropped by Postgres.
- **Vector:** cosine distance on the normalised 384-number vectors with an HNSW index (m 16, ef_construction 64). pgvector filters after the index scan, so each search sets `hnsw.iterative_scan = strict_order` and `hnsw.ef_search = 100` for that transaction, so enough allowed rows are still found when most rows are forbidden. Query text gets the bge instruction prefix.
- **Fusion:** RRF with k=60 over the two ranked lists (pure function, deterministic ties).
- **Reranker:** `BAAI/bge-reranker-base` (MIT), revision pinned, baked into the Docker image (offline at run time, like the embedding model), CPU only. Scores are the raw logit passed through one sigmoid (0 to 1). It only reorders chunks that already passed the access check.
- **Modes:** setting `RETRIEVAL_MODE` = `keyword` | `vector` | `hybrid` (default hybrid, kept only if the Phase 7 comparison supports it). Rerank defaults to on in hybrid mode only and can be forced per call, so "hybrid" and "hybrid + reranker" can both be measured.
- **Query hygiene:** whitespace collapsed, capped at 500 characters; empty or stop-word-only queries return nothing and never raise.
- **Refusal threshold (changed to 0.30 in Phase 7B, ADR 032):** a provisional reranker threshold of **0.03** is recorded from the demo data (off-topic best score at most 0.016, on-topic questions at least 0.044). Phase 6 uses it for refusals and Phase 7 tunes it on the larger question set.

## Addition in 5B
- `POST /search` needs only a signed-in, active user; the allow-list decides the content. Admin has no special search right. Mode is optional (server default); question 1 to 500 characters.
- 30 searches per minute per person (Redis); `Retry-After` on 429. Responses are `no-store`.
- The question text is never logged or stored. One `search` event is logged with user id, mode, result count and time.
- Score details (rank per list, RRF, rerank) are returned to `system_admin` only; other people get the final score.
- The search runs in a worker thread, at most 2 at a time. Both models load in the background at API start-up.

## How it is proven
- 52 tests in `tests/test_retrieval.py`: RRF maths; each mode finds what it should; odd input (quotes, operators, SQL, 5,000 characters) never crashes; every kind of blocking rule (no rule, DENY, clearance, country, expiry, deleted, not ready, inactive chunk, inactive user, admin without rule) hides the best match in every mode, and the reranker never even sees it; lifting one gate at a time reveals exactly that document; revocation applies on the very next search; the vector search still fills the result when 60 closer chunks are forbidden.
- Random worlds (6 seeds) compared with the independent Python oracle from Phase 4: in every mode only oracle-allowed documents are returned, and keyword mode returns all of them.
- Mutation check: 5 deliberate mistakes (keyword filter and final guard removed, vector filter removed, inactive chunks allowed, allow-list ignored, candidate list cut) are all caught. Removing only the first-stage keyword filter is NOT caught on purpose: the final load guard still blocks the leak. Removing both is caught.

## Consequences
- The reranker adds about 2 seconds on a laptop CPU for 20 candidates (median 2.1 s measured, target P95 under 5 s). Lowering the candidate count is the first lever if needed.
- Image grows by about 1.1 GB (reranker). One more pinned model to keep up to date.
- ts_rank is weaker than BM25; the Phase 7 comparison shows whether it matters.

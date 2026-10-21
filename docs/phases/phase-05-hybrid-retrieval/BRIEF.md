# Phase 5 Brief: Hybrid retrieval

**Goal:** a person asks a question and gets the best matching chunks, but only from documents they may read. Authorization happens first, in SQL; full-text and vector search run inside the allow-list; RRF fuses; a cross-encoder reranks.

**Requirement IDs:** FR-09 (search only inside the authorized set, RRF, rerank); NFR-01 (no unauthorized chunk scored), NFR-04 (P95 under 5 s), NFR-03 (rate limit search, in 5B).

## Layers (each needs the owner's approval)
| Layer | Content | Status |
|---|---|---|
| **5A** Engine | Migration `0004` (GIN and HNSW indexes), retrieval module (allow-list, keyword, vector, RRF, reranker), reranker baked into the image, tests with the Phase 4 oracle, ADR 028 | Built, waiting for owner review |
| **5B** API | `POST /search` with `mode`, rate limit, validation, no query text in logs, an `explain` of scores | Not started |
| **5C** UI | Search screen for employees showing result chunks | Not started |

## Security rules that apply
- Allow-list first; both searches only inside it; final text loaded with the allow-list applied again.
- Same allow-list in all three modes: no mode can leak.
- Admin is not reader: no special search right.
- The reranker only sees allowed text.
- Query text is not stored in logs (5B).

## Out of scope
Answers and citations (Phase 6), audit of searches (Phase 7), the full evaluation with 60+ questions (Phase 7), upload-time re-indexing changes.

## Estimate
Blueprint: 7 to 10 days. Plan: 5A about 3, 5B about 2, 5C about 2.

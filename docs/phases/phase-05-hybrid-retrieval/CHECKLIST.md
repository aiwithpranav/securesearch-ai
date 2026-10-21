# Phase 5 Checklist

## 5A Engine (built, waiting for owner review)
- [x] Migration `0004`: GIN index on `tsv`, HNSW index on `embedding`; `alembic check` clean
- [x] Retrieval module: allow-list first, keyword, vector (iterative scan), RRF, reranker, three modes
- [x] Reranker model baked into the image (pinned revision), offline at run time
- [x] 52 new tests (335 backend tests in total), random worlds against the Phase 4 oracle, 5 mutations caught
- [x] Live check on the 12 demo documents (Recall@5 and MRR, reranker scores, latency)
- [x] ADR 028, docs, challenges 65 to 70
- [ ] Owner manual checks and approval

## 5B API (not started)
- [ ] `POST /search`, modes, rate limit, validation, safe logging

## 5C UI (not started)
- [ ] Search screen

## Phase 5 close
- [ ] Owner approval, PRs merged, tag `v0.5`

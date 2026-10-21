# Phase 5 Checklist

## 5A Engine (built, waiting for owner review)
- [x] Migration `0004`: GIN index on `tsv`, HNSW index on `embedding`; `alembic check` clean
- [x] Retrieval module: allow-list first, keyword, vector (iterative scan), RRF, reranker, three modes
- [x] Reranker model baked into the image (pinned revision), offline at run time
- [x] 52 new tests (335 backend tests in total), random worlds against the Phase 4 oracle, 5 mutations caught
- [x] Live check on the 12 demo documents (Recall@5 and MRR, reranker scores, latency)
- [x] ADR 028, docs, challenges 65 to 70
- [x] Owner manual checks and approval (merged, PR #14)

## 5B API (built, waiting for owner review)
- [x] `POST /search` with optional mode, validation (422), rate limit (429 with Retry-After), no-store
- [x] No question text in logs; one search event with ids only
- [x] Score details for system_admin only; admin is not reader
- [x] Start-up warm-up of the models
- [x] 20 new tests (355 total), 6 mutations caught, live concurrency check
- [ ] Owner manual checks and approval

## 5C UI (not started)
- [ ] Search screen

## Phase 5 close
- [ ] Owner approval, PRs merged, tag `v0.5`

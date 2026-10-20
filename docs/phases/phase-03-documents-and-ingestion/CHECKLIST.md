# Phase 3 Checklist

## 3A Infrastructure (built, owner approved, merged)
- [x] CR-001 written (MinIO is archived upstream), ADR 024 (versions) and ADR 025 (SeaweedFS)
- [x] `storage` service on the private network only, healthcheck, named volume
- [x] Storage adapter (`app/storage`), bounded retries and timeouts, errors without secrets
- [x] Object keys use IDs and hash only
- [x] Embedding model baked into the image, offline at run time, 384 dimensions verified
- [x] `worker` service (Celery, Redis), acks-late and reject-on-worker-lost settings, healthcheck
- [x] Worker proven offline (no internet) and able to embed text
- [x] Env doctor checks the storage settings; `setup_env.ps1` adds missing keys
- [x] 17 new tests (82 backend tests in total), all pass
- [x] Owner approval (2026-10-20)

## 3B Pipeline and API (built, waiting for owner review)
- [x] Migration `0002` and models (`alembic check` clean); `vector` extension enabled
- [x] Upload validation (type, magic bytes, size, zip bomb, file names), storage, parse (PDF, DOCX, TXT, MD), chunk, embed, publish in one transaction
- [x] Failed job leaves previous data intact; retry is safe (no duplicate chunks)
- [x] Admin API, notifications (CR-002), negative authorization tests
- [x] 12 synthetic documents (canaries, one injection test) and broken-file fixtures
- [x] Worker kill test on the real worker: all jobs finished once, no duplicates
- [x] 86 new tests (168 backend tests in total), all pass
- [ ] Owner manual checks and approval

## 3C Admin UI (not started)
- [ ] Upload form, document list with status, re-index, failed alert

## Phase 3 close
- [ ] Owner approval, PR merged, tag `v0.3`
